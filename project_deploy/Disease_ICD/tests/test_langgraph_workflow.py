import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


_TEMP_MEMORY = tempfile.mkdtemp()
os.environ["LANGGRAPH_MEMORY_DIR"] = _TEMP_MEMORY

from langgraph.checkpoint.sqlite import SqliteSaver

from icd.disease import langgraph_workflow as workflow
from icd.disease.memory import LongTermMemoryRepository


class FakeAgentChains:
    def configured(self, stage):
        return False

    def invoke(self, stage, **kwargs):
        variables = kwargs.get("variables", {})
        if stage == "ranking":
            values = variables["待排序的疾病列表"]
            ordered = list(reversed(values)) if len(values) > 1 else values
            return '{"排序后的疾病列表":' + __import__("json").dumps(ordered, ensure_ascii=False) + '}'
        if stage == "validation":
            values = variables["排序后的疾病"]
            return '{"筛查后的结果":' + __import__("json").dumps(values, ensure_ascii=False) + '}'
        responses = {
            "standardize": '{"出院诊断标准化":["高血压病"]}',
            "potential_extract": '{"发现潜在疾病":["孤立性肺结节"]}',
        }
        return responses[stage]


class EmptyMemoryRepository:
    def search(self, **kwargs):
        return []


class DiseaseGraphTests(unittest.TestCase):
    def setUp(self):
        self.original_agents = workflow._agent_chains
        self.original_repository_factory = workflow.get_long_term_memory_repository
        self.original_graph = workflow._graph
        self.original_append_result = workflow._append_result
        workflow._agent_chains = FakeAgentChains()
        workflow.get_long_term_memory_repository = lambda: EmptyMemoryRepository()
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.checkpointer = SqliteSaver(self.connection)
        self.graph = workflow.build_disease_graph(self.checkpointer)
        workflow._graph = self.graph
        workflow._append_result = lambda result: None

    def tearDown(self):
        workflow._agent_chains = self.original_agents
        workflow.get_long_term_memory_repository = self.original_repository_factory
        workflow._graph = self.original_graph
        workflow._append_result = self.original_append_result
        self.connection.close()

    def _state(self, record):
        return {
            "medical_record": record,
            "record_id": "TEST001",
            "tenant_id": "default",
            "thread_id": "test-thread",
            "recalled_memories": [],
            "standardized_diseases": [],
            "need_potential_disease": False,
            "potential_decision_reason": "",
            "potential_diseases": [],
            "ranked_diseases": [],
            "final_diseases": [],
            "warnings": [],
        }

    def test_conditional_branch_mines_potential_disease(self):
        result = self.graph.invoke(
            self._state({"病案标识": "TEST001", "影像学意见": "肺部可见结节"}),
            config={"configurable": {"thread_id": "with-potential"}},
        )
        self.assertTrue(result["need_potential_disease"])
        self.assertEqual(result["potential_diseases"], ["孤立性肺结节"])
        self.assertEqual(result["ranked_diseases"], ["孤立性肺结节", "高血压病"])
        self.assertEqual(result["final_diseases"], ["孤立性肺结节", "高血压病"])
        snapshot = self.graph.get_state(
            {"configurable": {"thread_id": "with-potential"}}
        )
        self.assertEqual(snapshot.values["final_diseases"], result["final_diseases"])

    def test_conditional_branch_skips_potential_disease(self):
        result = self.graph.invoke(
            self._state({"病案标识": "TEST002", "影像学意见": "未见明显异常"}),
            config={"configurable": {"thread_id": "without-potential"}},
        )
        self.assertFalse(result["need_potential_disease"])
        self.assertEqual(result["potential_diseases"], [])
        self.assertEqual(result["final_diseases"], ["高血压病"])

    def test_stream_keeps_frontend_protocol_and_returns_thread_id(self):
        data = {
            "thread_id": "diagnosis:session-1",
            "messages": [
                {
                    "role": "user",
                    "content": '{"病案标识":"TEST001","影像学意见":"肺部可见结节"}',
                }
            ],
        }
        events = list(
            workflow.stream_disease_workflow(
                data,
                icd_lookup=lambda disease: ["R91.1"],
                markdown_builder=lambda *args: "| 测试表格 |",
            )
        )
        self.assertEqual(events[0]["type"], "status")
        self.assertEqual(events[-1]["type"], "final_result")
        self.assertEqual(events[-1]["thread_id"], "diagnosis:session-1")
        self.assertTrue(any(event.get("agent_name") == "判断有无潜在疾病智能体" for event in events))


class LongTermMemoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = LongTermMemoryRepository(
            Path(self.directory.name) / "long-term.sqlite3"
        )

    def tearDown(self):
        self.repository.close()
        self.directory.cleanup()

    def test_approved_rule_is_recalled_by_keyword(self):
        saved = self.repository.add(
            tenant_id="hospital-a",
            content="肺结节需要结合影像证据复核。",
            keywords=["肺结节"],
            approved=True,
        )
        recalled = self.repository.search(
            tenant_id="hospital-a", query="影像提示肺结节", limit=5
        )
        self.assertEqual(recalled[0]["id"], saved["id"])

    def test_unapproved_or_phi_memory_is_rejected(self):
        with self.assertRaises(ValueError):
            self.repository.add(
                tenant_id="default", content="普通规则", approved=False
            )
        with self.assertRaises(ValueError):
            self.repository.add(
                tenant_id="default",
                content="病案标识号：ZY0001 的诊断需要调整",
                approved=True,
            )


if __name__ == "__main__":
    unittest.main()
