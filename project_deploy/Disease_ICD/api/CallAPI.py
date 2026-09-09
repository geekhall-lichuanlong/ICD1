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
        print(f"Debug - Response status: {response.status_code}")
        print(f"Debug - Response headers: {dict(response.headers)}")
        
        response.raise_for_status()

        # 逐行读取流式响应
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
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
                            "next_agent_url": "",
                            "usage": 0#response_data.get("usage", {})
                        }, ensure_ascii=False) + "\n"
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                    except KeyError as e:
                        print(f"Key error in response data: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: '{e}'")
        
        # 尝试获取更详细的错误信息
        if hasattr(e, "response") and e.response is not None:
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
    pattern = r"病案标识\s*[:：]\s*(ZY\d+)"
    
    match = re.search(pattern, text)
    print(f"Debug - Extracting medical ID with pattern: {match}")
    if match:
        return match.group(1)  # 返回捕获组中的 ID
    else:
        return '0001097391'

def mock_llm_stream(content, model, url, agent_label="none", delay=0.01):
    """
    模拟大模型 API 的流式响应
    返回类似 {"content": "字", "finish_reason": null} 的结构
    """
    output = ""
    medical_id = __extract_medical_id(content)
    if medical_id == "ZY010000984572":
        if agent_label == "disease_standardized":
            output = """{"出院诊断标准化": ["冠状动脉粥样硬化性心脏病", "急性ST段抬高型心肌梗死", "静脉溶栓术后", "心功能I级", "高血压病2级（极高危）", "2型糖尿病"]}"""
        elif agent_label == "disease_main_diagnosis":
            output = """{"排序后的疾病列表": ["急性ST段抬高型心肌梗死","冠状动脉粥样硬化性心脏病","高血压病2级（极高危）","2型糖尿病","心功能I级","静脉溶栓术后"]}"""
        elif agent_label == "disease_screening":
            output = """{"筛查后的结果": ["急性前壁心肌梗死","冠状动脉粥样硬化性心脏病","高血压病3级（极高危）","2型糖尿病","心功能Ⅱ级"]}"""
    elif medical_id == "ZY010001097391":
        if agent_label == "disease_standardized":
            output = """{"出院诊断标准化": ["急性ST段抬高型心肌梗死", "冠状动脉粥样硬化性心脏病", "不稳定型心绞痛", "孤立性肺结节", "高脂血症", "慢性萎缩性胃炎"]}"""
        elif agent_label == "disease_main_diagnosis":
            output = """{"排序后的疾病列表": ["急性ST段抬高型心肌梗死","冠状动脉粥样硬化性心脏病","不稳定型心绞痛","慢性萎缩性胃炎孤立性肺结节","高脂血症"]}"""
        elif agent_label == "disease_screening":
            output = """{"筛查后的结果": ["急性心肌梗死","冠状动脉粥样硬化性心脏病","慢性胃炎","肺诊断性影像异常","高脂血症"]}"""
    elif medical_id == "ZY030000216959":
        if agent_label == "disease_standardized":
            output = """{"出院诊断标准化": ["病态窦性综合征", "心脏起搏器植入感染", "高血压病2级（极高危）", "高脂血症"]}"""
        elif agent_label == "disease_main_diagnosis":
            output = """{"排序后的疾病列表": ["病态窦性综合征","高血压病2级（极高危）","高脂血症","心脏起搏器植入感染"]}"""
        elif agent_label == "disease_screening":
            output = """{"筛查后的结果": ["病态窦房结综合征","高血压病3级（极高危）","高脂血症","具有心脏起搏器"]}"""
    elif medical_id == "ZY030000367210":
        if agent_label == "disease_standardized":
            output = """{"出院诊断标准化": ["冠状动脉粥样硬化性心脏病", "不稳定型心绞痛", "高血压病2级（极高危）", "2型糖尿病", "结肠息肉切除术后", "慢性胃炎"]}"""
        elif agent_label == "disease_main_diagnosis":
            output = """{"排序后的疾病列表": ["不稳定型心绞痛","冠状动脉粥样硬化性心脏病","高血压病2级（极高危）","2型糖尿病","慢性胃炎","结肠息肉切除术后"]}"""
        elif agent_label == "disease_screening":
            output = """{"筛查后的结果": ["不稳定型心绞痛","冠状动脉粥样硬化性心脏病","高血压病2级（极高危）","2型糖尿病","慢性萎缩性胃炎","乙状结肠息肉"]}"""
    elif medical_id == "0001097391":
        if agent_label == "disease_standardized":
            output = """{"出院诊断标准化": ["急性ST段抬高型心肌梗死", "冠状动脉粥样硬化性心脏病", "不稳定型心绞痛", "孤立性肺结节", "高脂血症", "慢性萎缩性胃炎"]}"""
        elif agent_label == "disease_main_diagnosis":
            output = """{"排序后的疾病列表": ["急性ST段抬高型心肌梗死","冠状动脉粥样硬化性心脏病","不稳定型心绞痛","慢性萎缩性胃炎孤立性肺结节","高脂血症"]}"""
        elif agent_label == "disease_screening":
            output = """{"筛查后的结果": ["急性心肌梗死","冠状动脉粥样硬化性心脏病","慢性胃炎","肺诊断性影像异常","高脂血症"]}"""

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
            "next_agent_url": "",
            "usage": 0#response_data.get("usage", {})
        }
        yield json.dumps(chunk, ensure_ascii=False) + "\n"

if __name__ == "__main__":
    # 测试函数
    content = "病案标识 ：ZY010000984572I21"
    print(__extract_medical_id(content))