from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import json
import time
import os
import threading
import re
import tempfile
from elasticsearch import Elasticsearch
from datetime import datetime
from icd.SurgeryAgents import get_agent_output_stream
from tools.orthers_search import orthers_search, ORTHER
from tools.save_excel import save_surgery

es = Elasticsearch(
    "https://127.0.0.1:9200/",
    ca_certs="/home/qluai/lzy/jointcoder/project_deploy/http_ca.crt",        # 证书绝对路径
    http_auth=('elastic', 'qluai1358')  # 用户名和密码
)


def get_icd(data):
    '''
    处理前端数据并送给各个agent，得到手术ICD编码（流式版本）
    '''
    for result in get_icd_stream(data):
            yield json.dumps(result, ensure_ascii=False) + "\n"

def get_icd_stream(data):
    '''
    处理前端数据并送给各个agent，得到手术ICD编码（流式版本）
    '''
    messages = data.get("messages")
    content = messages[0]["content"]
    
    # 如果不是json格式，则转换为json格式
    # content = __get_json(content) if not isinstance(content, dict) else content
    
    content = json.loads(content)
    
    if "data" in content.keys():
        content = __get_json(content['data'])
    if "住院号" in content.keys():
        content['病案标识号'] = content["住院号"]

    # 1. 手术标准化
    S_standardized_content=""
    for agent_response in get_agent_output_stream(
        "手术标准化智能体 Standardization",
        {
            "病案标识号": content["病案标识号"],
            "手术名称": content["手术名称"],
            "手术经过": content["手术经过"],
            "病程记录": content["病程记录"],
            # "病案标识": content["病案标识"],
            # "手术名称": content["手术名称"],
            # "手术经过": content["手术经过"],
            # "病程": content["病程"],
        }
    ):
        yield agent_response
        S_standardized_content += agent_response.get("message", {}).get("content", "")
    
    # 处理手术标准化输出
    S_standardized_output =  __extract_agent_result(S_standardized_content, "手术名称标准化")
    
    S_standardized_output = __remove_unmatched_surgery(S_standardized_output)
    
    print(f"---------S_standardized_output---------")
    print(S_standardized_output)
    
    # 2. 提取额外手术智能体 Candidate Mining
    
    S_additiona_content = ""
    for agent_response in get_agent_output_stream(
        "提取额外手术智能体 Candidate Mining",
        {
            "病案标识号": content["病案标识号"],
            "手术名称": content["手术名称"],
            "手术经过": content["手术经过"],
            "病程记录": content["病程记录"],
            # "病案标识": content["病案标识"],
            # "手术名称": content["手术名称"],
            # "手术经过": content["手术经过"],
            # "病程": content["病程"],
        }
    ):
        yield agent_response
        S_additiona_content += agent_response.get("message", {}).get("content", "")
    # 处理额外手术标准化输出
    S_additiona_output =  __extract_agent_result(S_additiona_content, "挖掘额外手术")
    
    S_additiona_output = __remove_unmatched_surgery(S_additiona_output)
    
    for item in S_additiona_output:
        if item in S_standardized_output:
            med_record_id = content["病案标识号"]
            a = list (set(S_additiona_output) - set(S_standardized_output))
            with open("/mnt/bigdisk/ceshiwenjian/ceshi/重复.txt", "a", encoding="utf-8") as f:
                f.write(f"病案标识号：{med_record_id} 标准化手术：{S_standardized_output} 挖掘手术{S_additiona_output} 去重之后的手术{a}\n")
            
            print(f"找到重复记录: {med_record_id}")
            break  # 找到一个匹配就退出，避免重复写入同一病案

        
    S_additiona_output= list(set(S_additiona_output) - set(S_standardized_output))
    
    print(f"---------S_additiona_output---------")
    print(S_additiona_output)
    
    # # 3. 另编码agent
    # S_another_coding_content = ""
    
    # for agent_response in get_agent_output_stream(
    #     "另编码智能体 Code Also",
    #     {
    #         "病案标识号": content["病案标识号"],
    #         "手术名称": content["手术名称"],
    #         "手术经过": content["手术经过"],
    #         "病程记录": content["病程记录"],
    #     }
    # ):
    #     yield agent_response
    #     S_another_coding_content += agent_response.get("message", {}).get("content", "")
    # # 处理另编码标准化输出
    # S_another_coding_output =  __extract_agent_result(S_another_coding_content, "处理另编码")
    # S_another_coding_output = __remove_unmatched_surgery(S_another_coding_output)
    
    # print(f"---------S_another_coding_output---------")
    # print(S_another_coding_output)
    
    # 4. 排序智能体 Prioritization 
    S_sorting_content = ""
    
    for agent_response in get_agent_output_stream(
        "排序智能体 Prioritization",
        {
            "病案标识号": content["病案标识号"],
            "手术名称": content["手术名称"],
            "手术经过": content["手术经过"],
            "病程记录": content["病程记录"],
            # "病案标识": content["病案标识"],
            # "手术名称": content["手术名称"],
            # "手术经过": content["手术经过"],
            # "病程": content["病程"],
            "待排序的手术列表":S_standardized_output + S_additiona_output
        }
    ):
        yield agent_response
        S_sorting_content += agent_response.get("message", {}).get("content", "")
    # 处理另编码标准化输出
    
    print(f" ---------------------------------- S_sorting_content: {S_sorting_content}")
    S_sorting_output =  __extract_agent_result(S_sorting_content, "排序后的列表")
    S_sorting_output = __remove_unmatched_surgery(S_sorting_output)
    
    print(f"---------S_sorting_output---------")
    print(S_sorting_output)
    
    
    if S_sorting_output and len(S_sorting_output) > 0 :
        main_surgery_name = S_sorting_output[0]
        main_surgery_icd = __search_icd(main_surgery_name)
    else:
        main_surgery_name = ""
        main_surgery_icd = None
    
    
    # 查询主手术的编码
    main_surgery_orthers = orthers_search(main_surgery_name)
    main_surgery_orthers_name = main_surgery_orthers.get("names", [])
    print(f"main_surgery_orthers_name: {main_surgery_orthers_name}")
    #判断主手术的另编码是否存在于 给定的的另编码手术名称列表中
    
    main_surgery_orthers_name = [name for name in main_surgery_orthers_name if name in ORTHER]
    
    
        #上传到前端  
    print(f"排除后的surgery_orthers: {main_surgery_orthers_name}")
    if len(main_surgery_orthers_name) != 0:
        surgery_orthers = '<think> </think> ' + json.dumps({"另编码": main_surgery_orthers_name}, ensure_ascii=False)
        
        table_response = {
            "agent_name": "另编码智能体 Code Also",
            # "agent_name": "手术4号智能体",
                    "message": {
                    "content": surgery_orthers,
                    "reasoning_content": ""
                },
                "next_agent": 0,
                "next_agent_url": "",
                "usage": 0
            }
            # 以agent_response格式发送表格
        yield {
                "type": "agent_response",
                "agent_name": "另编码智能体 Code Also",
                # "agent_name": "手术智能体4",
                "raw_response": json.dumps(table_response, ensure_ascii=False),
                "message": table_response["message"],
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }

    # med_record_id = content["病案标识号"]
    # if main_surgery_icd is not None and len(main_surgery_icd) > 0:
    #     save_surgery(med_record_id,S_standardized_output,S_sorting_output,)
    
    # 待筛查的手术列表
    all_surgery_names = S_sorting_output + main_surgery_orthers_name
    S_screening_content = ""
    # 筛查智能体 Validation
    for agent_response in get_agent_output_stream(
        "筛查智能体 Validation",
        {
            "病案标识号": content["病案标识号"],
            "手术名称": content["手术名称"],
            "手术经过": content["手术经过"],
            "病程记录": content["病程记录"],
            # "病案标识": content["病案标识"],
            # "手术名称": content["手术名称"],
            # "手术经过": content["手术经过"],
            # "病程": content["病程"],
            "待筛查的手术列表":all_surgery_names
        }
    ):
        yield agent_response
        S_screening_content += agent_response.get("message", {}).get("content", "")
    # print(f"S_sorting_content: {S_sorting_content}")
    
    S_screening_output =  __extract_agent_result(S_screening_content, "经筛查后的手术列表")
    S_screening_output = __remove_unmatched_surgery(S_screening_output)
    # 删除"术中心脏电生理检查"
    print(f"删除前的S_screening_output: {S_screening_output}")
    S_screening_output = [item for item in S_screening_output if item != "术中心脏电生理检查"]
    print(f"---------S_screening_output---------")
    print(S_screening_output)
    # S_screening_output = all_surgery_names

    print(f"main_surgery_name: {main_surgery_name}")
    # if content["病案标识号"] == '0001097391' and main_surgery_name == '药物洗脱冠状动脉支架置入':
    
    
    # 生成表格
    # 除主手术外的其它手术
    other_surgery_names =[name for name in S_screening_output 
                         if name not in main_surgery_name]

    # 将主手术的另编码加入到其它手术中
    # other_surgery_names = other_surgery_names + main_surgery_orthers_name
    # 查询其它手术的编码
    other_surgery_icds = [__search_icd(name) for name in other_surgery_names]
    
    med_record_id = content["病案标识号"]
    if main_surgery_icd is not None and len(main_surgery_icd) > 0:
        save_surgery(med_record_id,S_standardized_output,S_additiona_output,main_surgery_orthers_name,S_sorting_output,S_screening_output,main_surgery_name,main_surgery_icd,other_surgery_names,other_surgery_icds)
    

    markdown_table = __generate_markdown_table(
        med_record_id,
        main_surgery_name,
        main_surgery_icd,
        other_surgery_names,
        other_surgery_icds
    )
    
        # 将表格作为智能体响应发送到前端
    table_response = {
        "agent_name": "表格展示",
        "message": {
            "content": markdown_table,
            "reasoning_content": ""
        },
        "next_agent": 0,
        "next_agent_url": "",
        "usage": 0
    }
    
    # result_file="/mnt/bigdisk/all_data.json"
    # if os.path.exists(result_file) and os.path.getsize(result_file) > 0:
    #     with open(result_file, "r", encoding="utf-8") as f:
    #         try:
    #             results = json.load(f)
    #             if not isinstance(results, list):
    #                 results = [results]
    #         except Exception:
    #             results = []
    # else:
    #     results = []   
    
    
    # rest={
    #     "病案标识号": content["病案标识号"],
    #     "手术名称": content["手术名称"],
    #     "手术经过": content["手术经过"],
    #     "病程记录": content["病程记录"],
    #     "手术标准化":S_standardized_output,
    #     "提取额外手术":S_additiona_output,
    #     "排序":S_sorting_output,
    #     "另编码":main_surgery_orthers_name,
    #     "筛查":S_screening_output,
    #     "表格": markdown_table
    # }
    # results.append(rest)
    
    # with open(result_file, 'w', encoding='utf-8') as f:
    #         json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 以agent_response格式发送表格
    yield {
        "type": "agent_response",
        "agent_name": "表格展示",
        "raw_response": json.dumps(table_response, ensure_ascii=False),
        "message": table_response["message"],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    
    
    
    
def __get_json(text: str) -> dict:
    """
    将病历字符串解析成结构化 JSON
    :param text: 原始病历字符串
    :return: dict，字段与题目要求保持一致
    """

    # 1. 预定义目标字段顺序（可按需要增删）
    keys = [
        "病案标识","手术名称", "手术经过", "病程"
       
    ]

    # 2. 构造正则：以“key：”开头，非贪婪匹配到下一个“key：”或字符串结尾
    pattern = r'(' + '|'.join(map(re.escape, keys)) + r')：\s*(.*?)(?=(?:' + \
              '|'.join(map(re.escape, keys)) + r')：|$)'
    matches = re.findall(pattern, text, flags=re.S)

    # 3. 先放进一个临时 dict
    tmp = {k: v.strip() for k, v in matches}

    # 4. 整理为目标结构
    result = {}
    for k in keys:
        raw = tmp.get(k, "")            
        # 对多行描述型字段保留换行，其余去掉多余空白
        if k in {"病案标识号","手术名称", "手术经过", "病程记录"}:
            raw = re.sub(r'\s+', ' ', raw)      # 合并连续空白
        result[k] = raw

    return result


def __extract_agent_result(full_content, label):
    '''
    从agent的完整响应中提取特定标签的结果
    '''
    full_content = full_content.replace("<think>\n\n</think>\n\n", "")
    
    try:
        if full_content.strip():
            content_data = json.loads(full_content)
            
            # 1) 原逻辑：优先按 label 精确取值（保持兼容）
            if label in content_data:
                return content_data[label]

            # 2) 兜底策略：label 不存在时，尝试返回“最可能的结果”
            # 2.1 优先返回第一个 list[str]
            for v in content_data.values():
                if isinstance(v, list) and all(isinstance(x, str) for x in v):
                    return v

            # 2.2 再退一步：返回第一个 list（不限制元素类型）
            for v in content_data.values():
                if isinstance(v, list):
                    return v
                
            # 2.3 最后：维持你原来的行为（返回 full_content）
            print(f"Warning: {label} not found in response data")
            return full_content
        else:
            print("Warning: full_content is empty")
            return ""
    except json.JSONDecodeError as e:
        print(f"JSON decode error in full_content: {e}, content: {full_content}")
        return full_content

def __search_icd(surgery_name):
    """
    对单个手术名称进行精确查询，返回所有匹配的 ICD 码和手术名称。
    """

    search_body = {
        "query": {
            "term": {
                "name.keyword": {  # 使用字段的 `.keyword` 后缀进行精确匹配
                    "value": surgery_name
                }
            }
        }
    }
    res = es.search(index="surgery_icd_tree", body=search_body)
    if res["hits"]["total"]["value"] == 0:
        return None
    else:
        # 返回所有匹配的手术信息
        matches = []
        for hit in res["hits"]["hits"]:
            surgery_doc = hit["_source"]
            # print(f"匹配手术: {disease_doc['name']}，ICD码: {disease_doc['icd_code']}")
            matches.append((surgery_doc["icd_code"]))
        return matches

def __remove_unmatched_surgery(full_content):
    """
    移除未匹配的手术名称
    """
    # print(f"原始手术列表: {full_content}")

    matched_surgery = []
    for diagnosis in full_content:
        if __search_icd(diagnosis) is not None:
            matched_surgery.append(diagnosis)
        else:
            print(f"移除无匹配手术: {diagnosis}")
    # print(f"匹配后的手术列表: {matched_surgery}")
    return matched_surgery


import hashlib

def __generate_markdown_table(num_content, fifth_full_content, corresponding_icd, all_result_list, icd_list):
    """
    生成Markdown表格，包含加密的病案标识号和清洗后的ICD编码。
    """
    
    # --- 1. 加密处理函数 (Masking/Hashing) ---
    def mask_id(original_id):
        if not original_id:
            return "N/A"
        # 简单脱敏：显示前2位和后2位，中间用星号代替 (例如: 123456 -> 12***56)
        s_id = str(original_id)
        if len(s_id) > 4:
            return f"{s_id[:2]}***{s_id[-2:]}"
        else:
            # 如果ID太短，全脱敏或使用Hash
            return "***" 

    # --- 2. 列表元素提取函数 (Cleaning List Format) ---
    def clean_icd_code(icd_data):
        # 检查是否为列表或类似列表的字符串 "['36.0700']"
        if isinstance(icd_data, list):
            return icd_data[0] if icd_data else "无编码"
        
        if isinstance(icd_data, str):
            # 去除可能存在的列表符号
            cleaned = icd_data.strip("[]'\" ")
            return cleaned
            
        return str(icd_data) if icd_data else "无编码"

    # 表头部分
    headers = ["病案标识号", "诊断名称", "诊断编码"]
    header_row = "| " + " | ".join(headers) + " |"
    # 分隔行
    separator_row = "| " + " | ".join(["----"] * len(headers)) + " |"
    
    content_rows = []
    
    # 获取加密后的ID
    masked_id = mask_id(num_content)
    
    # --- 处理主诊断信息 ---
    main_diagnosis_name = fifth_full_content or "未找到主诊断"
    # 清洗主诊断编码
    main_diagnosis_icd = clean_icd_code(corresponding_icd)
    
    # 第一行：加密标识 + **主要诊断名称** + **主要诊断编码**
    content_rows.append(f"| {masked_id} | **{main_diagnosis_name}** | **{main_diagnosis_icd}** |")

    # --- 处理其他诊断信息 ---
    if all_result_list and icd_list:
        # 确保循环长度安全
        loop_len = min(len(all_result_list), len(icd_list))
        
        for i in range(loop_len):
            diagnosis_name = all_result_list[i] or "未知诊断"
            # 清洗次要诊断编码
            diagnosis_icd = clean_icd_code(icd_list[i])
            
            content_rows.append(f"| {masked_id} | {diagnosis_name} | {diagnosis_icd} |")

    # 组合成完整的 Markdown 表格
    markdown_table = header_row + "\n" + separator_row + "\n" + "\n".join(content_rows)
    return markdown_table


import re

def __get_json(text: str) -> dict:
    """
    将病历字符串解析成结构化 JSON
    :param text: 原始病历字符串
    :return: dict，字段与题目要求保持一致
    """

    # 1. 预定义目标字段顺序（可按需要增删）
    keys = [
        "病案标识号", "手术名称", "手术经过", "病程记录"
    ]

    # 2. 构造正则：以“key：”开头，非贪婪匹配到下一个“key：”或字符串结尾
    pattern = r'(' + '|'.join(map(re.escape, keys)) + r')：\s*(.*?)(?=(?:' + \
              '|'.join(map(re.escape, keys)) + r')：|$)'
    matches = re.findall(pattern, text, flags=re.S)

    # 3. 先放进一个临时 dict
    tmp = {k: v.strip() for k, v in matches}

    # 4. 整理为目标结构
    result = {}
    for k in keys:
        raw = tmp.get(k, "")
        # 对多行描述型字段保留换行，其余去掉多余空白
        if k in {"病案标识号", "手术名称", "手术经过", "病程记录"}:
            raw = re.sub(r'\s+', ' ', raw)      # 合并连续空白
        result[k] = raw

    return result



