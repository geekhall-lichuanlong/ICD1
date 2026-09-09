"""LangChain + LangGraph orchestration for disease ICD coding.

Workflow:
    medical record -> standardization -> potential-disease decision
    -> (conditional potential mining) -> ranking -> validation -> final diseases

LangGraph's SQLite checkpointer is the short-term, thread-scoped memory.  The
separate SQLite repository in ``memory.py`` is the reviewed, cross-thread long-
term memory.  Raw medical records are never written to the long-term store.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from parse import get_model, get_output_dir, get_url

from .memory import get_long_term_memory_repository, get_memory_directory


class DiseaseWorkflowState(TypedDict, total=False):
    medical_record: dict[str, Any]
    record_id: str
    tenant_id: str
    thread_id: str
    recalled_memories: list[dict[str, Any]]
    standardized_diseases: list[str]
    need_potential_disease: bool
    potential_decision_reason: str
    potential_diseases: list[str]
    ranked_diseases: list[str]
    final_diseases: list[str]
    warnings: list[str]


AGENT_DISPLAY_NAMES = {
    "standardize": "疾病标准化智能体 Standardization",
    "potential_decision": "判断有无潜在疾病智能体",
    "potential_extract": "发现潜在疾病智能体",
    "ranking": "疾病排序智能体 Prioritization",
    "validation": "疾病筛查智能体 Validation",
}

AGENT_OUTPUT_KEYS = {
    "standardize": "出院诊断标准化",
    "potential_decision": "有无潜在疾病",
    "potential_extract": "发现潜在疾病",
    "ranking": "排序后的疾病列表",
    "validation": "筛查后的结果",
}

SERVICE_LABELS = {
    "standardize": "disease_standardized",
    "potential_decision": "disease_potential_verify",
    "potential_extract": "disease_potential_extract",
    "ranking": "disease_main_diagnosis",
    "validation": "disease_screening",
}

SYSTEM_PROMPTS = {
    "standardize": (
        "你是疾病诊断标准化智能体。根据完整病历规范化明确记录的出院诊断，"
        "不得凭空新增疾病。仅输出严格 JSON："
        '{"出院诊断标准化":["疾病1","疾病2"]}。'
    ),
    "potential_decision": (
        "你是潜在疾病判断智能体。比较病历证据与已标准化诊断，判断是否存在"
        "有明确证据但尚未进入诊断列表的疾病。仅输出严格 JSON："
        '{"有无潜在疾病":"有或无","理由":"简短理由"}。'
    ),
    "potential_extract": (
        "你是潜在疾病挖掘智能体。只抽取病历中有明确检查、影像、病程或治疗"
        "证据支持，但未包含在当前标准化诊断中的疾病；不要抽取手术名称。"
        "仅输出严格 JSON："
        '{"发现潜在疾病":["疾病1","疾病2"]}。没有则返回空列表。'
    ),
    "ranking": (
        "你是疾病排序智能体。结合完整病历，按主要诊断选择规则对给定候选疾病"
        "排序。不得新增候选列表之外的疾病。仅输出严格 JSON："
        '{"排序后的疾病列表":["疾病1","疾病2"]}。'
    ),
    "validation": (
        "你是疾病验证智能体。结合完整病历审核排序后的疾病，删除无证据项并做"
        "最终名称标准化，保持主要诊断在第一位。仅输出严格 JSON："
        '{"筛查后的结果":["疾病1","疾病2"]}。'
    ),
}

_RESULT_FILE_LOCK = threading.Lock()


def _is_configured(value: Any) -> bool:
    return bool(value and str(value).strip().lower() not in {"none", "null", ""})


def _openai_base_url(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    suffix = "/chat/completions"
    return normalized[: -len(suffix)] if normalized.endswith(suffix) else normalized


def _clean_model_text(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


def _json_payload(text: str) -> Any:
    cleaned = _clean_model_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    object_start, object_end = cleaned.find("{"), cleaned.rfind("}")
    if object_start >= 0 and object_end > object_start:
        try:
            return json.loads(cleaned[object_start : object_end + 1])
        except json.JSONDecodeError:
            pass
    list_start, list_end = cleaned.find("["), cleaned.rfind("]")
    if list_start >= 0 and list_end > list_start:
        candidate = cleaned[list_start : list_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(candidate)
            except (ValueError, SyntaxError):
                pass
    return cleaned


def _extract_list(text: str, keys: tuple[str, ...]) -> list[str]:
    payload = _json_payload(text)
    value: Any = payload
    if isinstance(payload, dict):
        value = None
        for key in keys:
            if key in payload:
                value = payload[key]
                break
        if value is None:
            value = next((item for item in payload.values() if isinstance(item, list)), [])
    if isinstance(value, str):
        parsed = _json_payload(value)
        value = parsed if isinstance(parsed, list) else [value]
    if not isinstance(value, list):
        value = []
    return _dedupe_diseases(value)


def _dedupe_diseases(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        disease = str(value).strip().strip("'\"")
        if not disease or disease in {"无", "无潜在疾病", "None", "null"}:
            continue
        if disease not in result:
            result.append(disease)
    return result


def _record_text(record: dict[str, Any]) -> str:
    return "\n".join(f"{key}：{value}" for key, value in record.items() if value not in (None, "", []))


def _memory_text(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return "无已审核的长期编码规则"
    return "\n".join(f"- {item['content']}" for item in memories)


def _parse_medical_record(data: dict[str, Any]) -> dict[str, Any]:
    messages = data.get("messages") or []
    if not messages:
        raise ValueError("messages 不能为空")
    raw: Any = messages[0].get("content", "")
    if isinstance(raw, dict):
        parsed: Any = raw
    else:
        text = str(raw).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {}
            for line in text.splitlines():
                if "：" in line:
                    key, value = line.split("：", 1)
                elif ":" in line:
                    key, value = line.split(":", 1)
                else:
                    continue
                parsed[key.strip()] = value.strip()
    if isinstance(parsed, dict) and "data" in parsed and len(parsed) == 1:
        wrapped = parsed["data"]
        if isinstance(wrapped, dict):
            parsed = wrapped
        elif isinstance(wrapped, str):
            return _parse_medical_record({"messages": [{"content": wrapped}]})
    if not isinstance(parsed, dict):
        raise ValueError("病历 content 必须是 JSON 对象或键值文本")
    record = dict(parsed)
    if not record.get("病案标识"):
        record["病案标识"] = record.get("病案标识号") or record.get("住院号") or ""
    return record


class DiseaseAgentChains:
    """LangChain LCEL chains backed by the existing OpenAI-compatible Qwen APIs."""

    def __init__(self) -> None:
        self._chains: dict[tuple[str, str], Any] = {}

    def configured(self, stage: str) -> bool:
        service = SERVICE_LABELS[stage]
        return _is_configured(get_url(service)) and _is_configured(get_model(service))

    def _service_for(self, stage: str) -> str:
        service = SERVICE_LABELS[stage]
        if self.configured(stage):
            return service
        if stage == "potential_extract":
            fallback = os.getenv("POTENTIAL_EXTRACTION_FALLBACK_AGENT", "disease_standardized")
            if _is_configured(get_url(fallback)) and _is_configured(get_model(fallback)):
                return fallback
        raise RuntimeError(f"{stage} 对应的模型服务未配置")

    def invoke(self, stage: str, *, record: dict[str, Any], variables: dict[str, Any], memories: list[dict[str, Any]]) -> str:
        service = self._service_for(stage)
        cache_key = (stage, service)
        chain = self._chains.get(cache_key)
        if chain is None:
            endpoint = get_url(service)
            llm = ChatOpenAI(
                model=get_model(service),
                base_url=_openai_base_url(endpoint),
                api_key=os.getenv("LOCAL_LLM_API_KEY", "EMPTY"),
                temperature=0,
                timeout=float(os.getenv("ICD_AGENT_TIMEOUT_SECONDS", "200")),
                max_retries=int(os.getenv("ICD_AGENT_MAX_RETRIES", "1")),
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=SYSTEM_PROMPTS[stage]),
                    (
                        "human",
                        "病历：\n{record}\n\n当前流程数据：\n{variables}\n\n"
                        "已审核的机构编码经验（仅作辅助，病历证据优先）：\n{memories}",
                    ),
                ]
            )
            chain = prompt | llm | StrOutputParser()
            self._chains[cache_key] = chain
        return chain.invoke(
            {
                "record": _record_text(record),
                "variables": json.dumps(variables, ensure_ascii=False),
                "memories": _memory_text(memories),
            }
        )


_agent_chains = DiseaseAgentChains()


def _recall_long_term_memory(state: DiseaseWorkflowState) -> dict[str, Any]:
    query = _record_text(state["medical_record"])
    memories = get_long_term_memory_repository().search(
        tenant_id=state.get("tenant_id", "default"), query=query, limit=5
    )
    return {"recalled_memories": memories}


def _standardize(state: DiseaseWorkflowState) -> dict[str, Any]:
    response = _agent_chains.invoke(
        "standardize",
        record=state["medical_record"],
        variables={},
        memories=state.get("recalled_memories", []),
    )
    diseases = _extract_list(response, ("出院诊断标准化", "标准化后的诊断", "疾病列表"))
    if not diseases:
        raise RuntimeError(f"标准化智能体未返回有效疾病列表：{_clean_model_text(response)[:300]}")
    return {"standardized_diseases": diseases}


_POTENTIAL_EVIDENCE_TERMS = (
    "结节", "占位", "肿块", "感染", "积液", "狭窄", "血栓", "梗死", "肺炎",
    "心衰", "糖尿病", "高血压", "贫血", "肾功能不全", "呼吸衰竭",
)


def _heuristic_potential_decision(record: dict[str, Any], standardized: list[str]) -> tuple[bool, str]:
    evidence_fields = ("影像学意见", "超声提示", "超声印象", "病程记录", "术中诊断", "诊疗经过")
    evidence = " ".join(str(record.get(field, "")) for field in evidence_fields)
    known = " ".join(standardized)
    unmatched = [term for term in _POTENTIAL_EVIDENCE_TERMS if term in evidence and term not in known]
    if unmatched:
        return True, f"规则回退检测到尚未覆盖的病历证据关键词：{','.join(unmatched[:5])}"
    return False, "未配置潜在疾病判断模型，规则回退未发现未覆盖的明确证据"


def _decide_potential(state: DiseaseWorkflowState) -> dict[str, Any]:
    record = state["medical_record"]
    forced = record.get("是否挖掘潜在疾病")
    if forced is not None:
        decision = str(forced).strip().lower() in {"是", "有", "true", "1", "yes"}
        return {"need_potential_disease": decision, "potential_decision_reason": "由请求显式指定"}
    if not _agent_chains.configured("potential_decision"):
        decision, reason = _heuristic_potential_decision(record, state["standardized_diseases"])
        return {"need_potential_disease": decision, "potential_decision_reason": reason}
    response = _agent_chains.invoke(
        "potential_decision",
        record=record,
        variables={"标准化后的诊断": state["standardized_diseases"]},
        memories=state.get("recalled_memories", []),
    )
    payload = _json_payload(response)
    raw_decision: Any = payload
    reason = "模型判断"
    if isinstance(payload, dict):
        raw_decision = payload.get("有无潜在疾病", payload.get("是否需要挖掘", "无"))
        reason = str(payload.get("理由", reason))
    decision_text = str(raw_decision).strip().lower()
    decision = decision_text in {"有", "是", "true", "1", "yes"} or decision_text.startswith("有")
    return {"need_potential_disease": decision, "potential_decision_reason": reason}


def _route_after_potential_decision(state: DiseaseWorkflowState) -> str:
    return "potential_extract" if state.get("need_potential_disease") else "ranking"


def _extract_potential(state: DiseaseWorkflowState) -> dict[str, Any]:
    try:
        response = _agent_chains.invoke(
            "potential_extract",
            record=state["medical_record"],
            variables={"标准化后的诊断": state["standardized_diseases"]},
            memories=state.get("recalled_memories", []),
        )
        candidates = _extract_list(
            response, ("发现潜在疾病", "潜在疾病", "出院诊断标准化", "疾病列表")
        )
        known = set(state["standardized_diseases"])
        return {"potential_diseases": [item for item in candidates if item not in known]}
    except Exception as exc:  # potential mining is optional; keep the core path available
        warnings = list(state.get("warnings", []))
        warnings.append(f"潜在疾病挖掘失败，已按无潜在疾病继续：{exc}")
        return {"potential_diseases": [], "warnings": warnings}


def _correct_ranked_diseases(record: dict[str, Any], diseases: list[str]) -> list[str]:
    corrected = list(diseases)
    discharge = str(record.get("出院诊断", ""))
    wall_match = re.search(r"急性(?:ST段抬高型)?([前下侧后间隔广泛]+壁)心肌梗死", discharge)
    if wall_match:
        for index, disease in enumerate(corrected):
            if "急性ST段抬高型心肌梗死" in disease:
                corrected[index] = f"急性{wall_match.group(1)}心肌梗死"
                break
    if corrected and corrected[0] == "冠状动脉粥样硬化性心脏病" and "不稳定型心绞痛" in corrected[1:]:
        ua_index = corrected.index("不稳定型心绞痛")
        corrected[0], corrected[ua_index] = corrected[ua_index], corrected[0]
    return _dedupe_diseases(corrected)


def _rank(state: DiseaseWorkflowState) -> dict[str, Any]:
    candidates = _dedupe_diseases(
        state["standardized_diseases"] + state.get("potential_diseases", [])
    )
    try:
        response = _agent_chains.invoke(
            "ranking",
            record=state["medical_record"],
            variables={
                "标准化后的诊断": state["standardized_diseases"],
                "潜在疾病": state.get("potential_diseases", []),
                "待排序的疾病列表": candidates,
            },
            memories=state.get("recalled_memories", []),
        )
        ranked = _extract_list(response, ("排序后的疾病列表", "排序", "选择主诊断"))
        # Prevent the ranking model from inventing diseases.
        ranked = [item for item in ranked if item in candidates]
        for item in candidates:
            if item not in ranked:
                ranked.append(item)
    except Exception as exc:
        ranked = candidates
        warnings = list(state.get("warnings", []))
        warnings.append(f"疾病排序失败，已保留候选顺序：{exc}")
        return {"ranked_diseases": _correct_ranked_diseases(state["medical_record"], ranked), "warnings": warnings}
    return {"ranked_diseases": _correct_ranked_diseases(state["medical_record"], ranked)}


def _validate(state: DiseaseWorkflowState) -> dict[str, Any]:
    try:
        response = _agent_chains.invoke(
            "validation",
            record=state["medical_record"],
            variables={"排序后的疾病": state["ranked_diseases"]},
            memories=state.get("recalled_memories", []),
        )
        final = _extract_list(response, ("筛查后的结果", "标准化后的疾病", "最终疾病"))
        if not final:
            raise RuntimeError("验证智能体返回空列表")
        return {"final_diseases": final}
    except Exception as exc:
        warnings = list(state.get("warnings", []))
        warnings.append(f"疾病验证失败，已使用排序结果：{exc}")
        return {"final_diseases": state["ranked_diseases"], "warnings": warnings}


def build_disease_graph(checkpointer: SqliteSaver):
    builder = StateGraph(DiseaseWorkflowState)
    builder.add_node("recall_memory", _recall_long_term_memory)
    builder.add_node("standardize", _standardize)
    builder.add_node("potential_decision", _decide_potential)
    builder.add_node("potential_extract", _extract_potential)
    builder.add_node("ranking", _rank)
    builder.add_node("validation", _validate)
    builder.add_edge(START, "recall_memory")
    builder.add_edge("recall_memory", "standardize")
    builder.add_edge("standardize", "potential_decision")
    builder.add_conditional_edges(
        "potential_decision",
        _route_after_potential_decision,
        {"potential_extract": "potential_extract", "ranking": "ranking"},
    )
    builder.add_edge("potential_extract", "ranking")
    builder.add_edge("ranking", "validation")
    builder.add_edge("validation", END)
    return builder.compile(checkpointer=checkpointer)


_checkpoint_connection = sqlite3.connect(
    str(get_memory_directory() / "short_term_checkpoints.sqlite3"),
    check_same_thread=False,
    timeout=30,
)
_checkpointer = SqliteSaver(_checkpoint_connection)
_graph = build_disease_graph(_checkpointer)


def delete_short_term_memory(thread_id: str) -> None:
    _checkpointer.delete_thread(str(thread_id))


def _agent_event(agent_name: str, content: str) -> dict[str, Any]:
    response = {
        "agent_name": agent_name,
        "message": {"content": content, "reasoning_content": ""},
        "next_agent": 0,
        "next_agent_url": "",
        "usage": 0,
    }
    return {
        "type": "agent_response",
        "agent_name": agent_name,
        "raw_response": json.dumps(response, ensure_ascii=False),
        "message": response["message"],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }


def _stage_event(node: str, update: dict[str, Any]) -> dict[str, Any] | None:
    if node == "standardize":
        payload = {AGENT_OUTPUT_KEYS[node]: update.get("standardized_diseases", [])}
    elif node == "potential_decision":
        payload = {
            AGENT_OUTPUT_KEYS[node]: "有" if update.get("need_potential_disease") else "无",
            "理由": update.get("potential_decision_reason", ""),
        }
    elif node == "potential_extract":
        payload = {AGENT_OUTPUT_KEYS[node]: update.get("potential_diseases", [])}
    elif node == "ranking":
        payload = {AGENT_OUTPUT_KEYS[node]: update.get("ranked_diseases", [])}
    elif node == "validation":
        payload = {AGENT_OUTPUT_KEYS[node]: update.get("final_diseases", [])}
    else:
        return None
    return _agent_event(AGENT_DISPLAY_NAMES[node], json.dumps(payload, ensure_ascii=False))


def _safe_icd_lookup(icd_lookup: Callable[[str], Any], disease: str) -> Any:
    try:
        return icd_lookup(disease)
    except Exception as exc:
        print(f"ICD 查询失败 ({disease}): {exc}")
        return None


def _append_result(result: dict[str, Any]) -> None:
    output_directory = Path(get_output_dir())
    output_directory.mkdir(parents=True, exist_ok=True)
    output_file = output_directory / "disease_diagnosis_results_langgraph.jsonl"
    with _RESULT_FILE_LOCK:
        with output_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")


def stream_disease_workflow(
    data: dict[str, Any],
    *,
    icd_lookup: Callable[[str], Any],
    markdown_builder: Callable[[str, str, Any, list[str], list[Any]], str],
    save_callback: Callable[..., Any] | None = None,
):
    """Execute the graph and yield events compatible with the existing frontend."""

    record = _parse_medical_record(data)
    thread_id = str(data.get("thread_id") or data.get("session_id") or uuid.uuid4())
    tenant_id = str(data.get("tenant_id") or "default")
    initial_state: DiseaseWorkflowState = {
        "medical_record": record,
        "record_id": str(record.get("病案标识", "")),
        "tenant_id": tenant_id,
        "thread_id": thread_id,
        "recalled_memories": [],
        "standardized_diseases": [],
        "need_potential_disease": False,
        "potential_decision_reason": "",
        "potential_diseases": [],
        "ranked_diseases": [],
        "final_diseases": [],
        "warnings": [],
    }
    state: dict[str, Any] = dict(initial_state)
    config = {"configurable": {"thread_id": thread_id}}

    yield {
        "type": "status",
        "status": "running",
        "stage": "LangGraph初始化",
        "message": "开始执行疾病 ICD 多智能体工作流",
        "thread_id": thread_id,
    }
    try:
        for chunk in _graph.stream(initial_state, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                if isinstance(update, dict):
                    state.update(update)
                    event = _stage_event(node, update)
                    if event:
                        event["thread_id"] = thread_id
                        yield event
    except Exception as exc:
        yield {
            "type": "error",
            "status": "error",
            "message": f"LangGraph 工作流执行失败：{exc}",
            "thread_id": thread_id,
        }
        return

    final_diseases = _dedupe_diseases(state.get("final_diseases", []))
    main_name = final_diseases[0] if final_diseases else ""
    other_names = final_diseases[1:]
    main_icd = _safe_icd_lookup(icd_lookup, main_name) if main_name else None
    other_icds = [_safe_icd_lookup(icd_lookup, name) for name in other_names]
    record_id = str(record.get("病案标识", ""))
    markdown_table = markdown_builder(record_id, main_name, main_icd, other_names, other_icds)

    if save_callback and main_icd:
        try:
            save_callback(
                record_id,
                state.get("standardized_diseases", []),
                state.get("ranked_diseases", []),
                final_diseases,
                main_name,
                main_icd,
                other_names,
                other_icds,
            )
        except Exception as exc:
            state.setdefault("warnings", []).append(f"Excel 结果保存失败：{exc}")

    yield _agent_event("表格展示", markdown_table)
    result = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "thread_id": thread_id,
        "病例内容": record,
        "疾病标准化智能体 Standardization": state.get("standardized_diseases", []),
        "判断有无潜在疾病智能体": ["有" if state.get("need_potential_disease") else "无"],
        "潜在疾病判断理由": state.get("potential_decision_reason", ""),
        "发现潜在疾病智能体": state.get("potential_diseases", []),
        "排序智能体": state.get("ranked_diseases", []),
        "筛查智能体": final_diseases,
        "召回的长期记忆": [item.get("content", "") for item in state.get("recalled_memories", [])],
        "警告": state.get("warnings", []),
        "表格展示": markdown_table,
    }
    _append_result(result)
    yield {
        "type": "final_result",
        "status": "success",
        "message": "诊断处理完成",
        "thread_id": thread_id,
        "result": result,
    }
