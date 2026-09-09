import requests
import json


def call_api_stream(content, model, url, agent_label="none"):

    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "stream": True  # 启用流式返回
    }

    headers = {
        "Content-Type": "application/json"
    }

    # 添加调试信息
    print(f"Debug - Calling API with:")
    print(f"  URL: {url}")
    print(f"  Model: {model}")
    print(f"  Content length: {len(content) if content else 0}")
    print(f"  Agent label: {agent_label}")

    try:
        # 发送请求并启用流式读取
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=200)
        
        # 添加响应状态调试
        # print(f"Debug - Response status: {response.status_code}")
        # print(f"Debug - Response headers: {dict(response.headers)}")
        
        response.raise_for_status()

        # 逐行读取流式响应
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    # 提取 JSON 数据
                    json_data = decoded_line[5:].strip()
                    if json_data == "[DONE]":
                        break  # 流式响应结束
                    try:
                        response_data = json.loads(json_data)
                        # 提取所需内容
                        result_content = response_data["choices"][0]["delta"].get("content", "")
                        reasoning_content = response_data["choices"][0]["delta"].get("reasoning_content", "")

                        # 流式返回当前片段
                        yield json.dumps({
                            "model": model,
                            "agent_label": agent_label,
                            "message": {
                                "content": result_content,
                                "reasoning_content": reasoning_content
                            },
                            "next_agent": 0,  # 没有下一个 agent
                            "next_agent_url": '',
                            "usage": 0#response_data.get("usage", {})
                        }, ensure_ascii=False) + "\n"
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                    except KeyError as e:
                        print(f"Key error in response data: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: '{e}'")
        
        # 尝试获取更详细的错误信息
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.text
                print(f"Error response body: {error_detail}")
            except:
                print("Could not read error response body")
        
        yield json.dumps({"error": "API调用失败，请检查网络或API配置。"}) + "\n"


import time
import json

import re
def __extract_medical_id(text):
    """
    从文本中提取病案标识号
    格式匹配：ZY + 数字 + I + 数字
    """
    # 正则表达式解释：
    # 病案标识号      : 匹配固定标签
    # \s*           : 匹配可能的空白字符
    # [:：]         : 匹配中文或英文冒号
    # \s*           : 匹配冒号后的空白
    # (ZY\d+I\d+)   : 捕获组，匹配 ZY + 数字 + I + 数字
    pattern = r"病案标识号\s*[:：]\s*(ZY\d+)"
    print(f"Debug - Extracting medical ID with pattern: {pattern} from text: {text}")
    match = re.search(pattern, text)
    print(f"Debug - Extracting medical ID with pattern: {match}")
    if match:
        return match.group(1)  # 返回捕获组中的 ID
    else:   
        return '0001097391'
import random

def mock_llm_stream(content, model, url, agent_label="none", delay=0.01):
    """
    模拟大模型 API 的流式响应
    返回类似 {"content": "字", "finish_reason": null} 的结构
    """
    output = ""
    medical_id = __extract_medical_id(content)
    if medical_id == 'ZY010000984572':
        if agent_label == "surgery_standardized":
            output = """{"手术名称标准": ["单根导管的冠状动脉造影术","药物洗脱冠状动脉支架置入"]}"""
        elif agent_label == "surgery_additional":
            output = """{"挖掘额外手术": ["经皮冠状动脉球囊扩张成形术"]}"""
        elif agent_label == "surgery_sorting":
            output = """{"排序后的手术列表": ["药物洗脱冠状动脉支架置入","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术"]}"""
        elif agent_label == "surgery_screening":
            output = """{"经筛查后的手术列表": ["药物洗脱冠状动脉支架置入","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术","三根血管操作","置入一根血管的支架"]}"""
    elif medical_id == "ZY010001097391":
        if agent_label == "surgery_standardized":
            output = """{"手术名称标准": ["药物洗脱冠状动脉支架置入","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术"]}"""
        elif agent_label == "surgery_additional":
            output = """{"挖掘额外手术": ["冠状动脉药物涂层支架置入术","术中心脏电生理检查"]}"""
        elif agent_label == "surgery_sorting":
            output = """{"排序后的手术列表": ["冠状动脉药物涂层支架置入术","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术"]}"""
        elif agent_label == "surgery_screening":
            output = """{"经筛查后的手术列表": ["冠状动脉药物涂层支架置入术","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术","单根血管操作","置入一根血管的支架"]}"""
    elif medical_id == "ZY030000216959":
        if agent_label == "surgery_standardized":
            output = """{"手术名称标准": ["暂时性经静脉起搏器系统的置入","永久起搏器置换术"]}"""
        elif agent_label == "surgery_additional":
            output = """{"挖掘额外手术": ["术中心脏电生理检查"]}"""
        elif agent_label == "surgery_sorting":
            output = """{"排序后的手术列表": ["永久起搏器置换术","暂时性经静脉起搏器系统的置入","术中心脏电生理检查"]}"""
        elif agent_label == "surgery_screening":
            output = """{"经筛查后的手术列表": ["永久起搏器置换术","暂时性经静脉起搏器系统的置入"]}"""
    elif medical_id == "0001097391":
        if agent_label == "surgery_standardized":
            output = """{"手术名称标准": ["药物洗脱冠状动脉支架置入","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术"]}"""
        elif agent_label == "surgery_additional":
            output = """{"挖掘额外手术": ["冠状动脉药物涂层支架置入术","术中心脏电生理检查"]}"""
        elif agent_label == "surgery_sorting":
            output = """{"排序后的手术列表": ["冠状动脉药物涂层支架置入术","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术"]}"""
        elif agent_label == "surgery_screening":
            output = """{"经筛查后的手术列表": ["冠状动脉药物涂层支架置入术","经皮冠状动脉球囊扩张成形术","单根导管的冠状动脉造影术","单根血管操作","置入一根血管的支架"]}"""

    for i, char in enumerate(output):
        # 模拟网络/生成延迟
        time.sleep(delay)
        
        # 模拟 API 返回的数据块
        chunk = {
            "model": model,
            "agent_label": agent_label,
            "message": {
                "content": char,
                "reasoning_content": ""
            },
            "next_agent": 0,  # 没有下一个 agent
            "next_agent_url": '',
            "usage": 0#response_data.get("usage", {})
        }
        yield json.dumps(chunk, ensure_ascii=False) + "\n"


        # "手术标准化智能体 Standardization": "surgery_standardized",
        # "提取额外手术智能体 Candidate Mining": "surgery_additional",
        # "另编码智能体 Code Also": "surgery_another_coding",
        # "排序智能体 Prioritization": "surgery_sorting",
        # "筛查智能体 Validation": "surgery_screening"


if __name__ == "__main__":
    # 测试函数
    content =  '"病案标识": "ZY010000984572"'
    model = "gpt-4"
    agent_label = "surgery_standardized"
    url = "http://localhost:8000/surgery_standardized"
    print("Testing mock_llm_stream with content:", __extract_medical_id(content))