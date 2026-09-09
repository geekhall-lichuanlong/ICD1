import requests
import json

from prompts.GetPrompt import get_prompt, get_prompt_agent6
from parse import get_flask_url, get_output_dir

flask_url = get_flask_url()
url = {
    "disease_standardized": f"{flask_url}disease_standardized",
    "disease_potential_extract": f"{flask_url}disease_potential_extract",
    "disease_potential_standardized": f"{flask_url}disease_potential_standardized",
    "disease_main_diagnosis": f"{flask_url}disease_main_diagnosis",
    "disease_screening": f"{flask_url}disease_screening"
}
output_dir = get_output_dir()


def get_agent_output(agent_name, kwargs):
    '''
    获取智能体响应（非流式版本，用于向后兼容）
    '''
    full_content = ""
    for response in get_agent_output_stream(agent_name, kwargs):
        full_content += response.get("message", {}).get("content", "")
    
    # 获取agent输出中的标签
    agent_output_label = __get_agent_output_label(agent_name)
    if agent_output_label == "unknown_agent":
        raise ValueError(f"Unknown agent output label for agent: {agent_name}. Please check the agent name.")
    
    # 将完整内容存储到全局变量中
    full_content = full_content.replace("<think>\n\n</think>\n\n", "")
    
    try:
        if full_content.strip():  # 检查内容是否为空
            content_data = json.loads(full_content)
            if agent_output_label in content_data:
                full_content = content_data[agent_output_label]
            else:
                print(f"Warning: {agent_output_label} not found in response data")
                return full_content
        else:
            print("Warning: full_content is empty")
            return ""
    except json.JSONDecodeError as e:
        print(f"JSON decode error in full_content: {e}, content: {full_content}")
        return full_content  # 返回原始内容而不是抛出异常

    return full_content

def get_agent_output_stream(agent_name, kwargs):
    '''
    获取智能体响应（流式版本）
    '''

    # 匹配智能体名称
    agent_label = __get_agent_label(agent_name)
    if agent_label == "unknown_agent":
        raise ValueError(f"Unknown agent name: {agent_name}. Please check the agent name.")
    
    # 获取prompt内容
    if agent_name == "疾病筛查智能体 Validation":
        prompt_content = get_prompt_agent6(agent_label, kwargs) 
    else:  
        prompt_content = get_prompt(agent_label, kwargs)

    # 获得api输出
    for api_response in __call_agent_api(prompt_content, agent_label):
        # 打印调试信息
        # print(f"Received response from agent {agent_name}: {api_response}")  # 调试信息
        # print("agentname：",agent_name)
        agent_name1=agent_name
        try:
            if api_response.strip():  # 检查响应是否为空
                # print(f"Processing API response: {api_response}")  # 调试信息
                response_data = json.loads(api_response)
                # agent_name = replace(agent_name)
                # 将 api_response 发送到前端
                yield {
                    "type": "agent_response",
                    "agent_name": agent_name,
                    "raw_response": api_response,
                    "message": response_data.get("message", {}),
                    "timestamp": json.loads(api_response).get("timestamp", "")
                }
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error in api_response: {e}, response: {api_response}")
            # 即使解析失败，也将原始响应发送到前端
            yield {
                "type": "agent_response",
                "agent_name": agent_name,
                "raw_response": api_response,
                "error": f"JSON decode error: {str(e)}",
                "timestamp": ""
            }
            continue
        agent_name=agent_name1

def __call_agent_api(prompt_content, agent_label):
    '''
    获取智能体响应
    '''
    print(f"Calling agent API: {agent_label}")  # 调试信息
    # print(f"Prompt content: {prompt_content}")  # 打印输入内容

    agent_flask_url = f"{get_flask_url()}/disease/{agent_label}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "messages": [
            {
                "role": "user",
                "content": prompt_content  # 将去除“出院诊断”后的剩余内容作为输入
            }
        ]
    }
    # print(f"Sending data to second API: {data}")  # 打印输入数据

    # 初始化累积变量
    full_content = "" 
    full_reasoning_content = ""

    try:
        response = requests.post(agent_flask_url, headers=headers, json=data, timeout=200, stream=True)
        response.raise_for_status()

        # 逐行解析流式响应
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # print(f"Received line from second API: {decoded_line}")  # 打印每一行响应
                try:
                    if decoded_line.strip():  # 检查行是否为空
                        response_data = json.loads(decoded_line)
                        message = response_data.get("message", {})
                        content = message.get("content", "")
                        reasoning_content = message.get("reasoning_content", "")

                        # 确保 content 和 reasoning_content 不是 None
                        if content is None:
                            content = ""
                        if reasoning_content is None:
                            reasoning_content = ""

                        # 累积内容
                        full_content += content
                        full_reasoning_content += reasoning_content

                        # 流式返回第二个 API 的响应
                        yield json.dumps({
                            "agent_name": agent_label,
                            "message": {
                                "content": content,
                                "reasoning_content": reasoning_content
                            },
                            "next_agent": 0,
                            "next_agent_url": "",
                            "usage": 0
                        }, ensure_ascii=False) + "\n"

                except json.JSONDecodeError as e:
                    print(f"JSON decode error in second API response: {e}, line: {decoded_line}")
                    continue  # 跳过无效的JSON行
    except requests.exceptions.RequestException as e:
        print(f"Error calling {agent_label} API: {e}")
        yield json.dumps({"error": "API调用失败，请检查网络或API配置。"}) + "\n"


def __get_agent_label(agent_name):
    '''
    获取智能体名称
    '''
    agent_dict = {
        "疾病标准化智能体 Standardization": "disease_standardized",
        "疾病排序智能体 Prioritization": "disease_main_diagnosis",
        "疾病筛查智能体 Validation": "disease_screening",

        "发现潜在疾病智能体": "disease_potential_extract",
        "潜在疾病标准化智能体 Disease Standardization Agent": "disease_potential_standardized",
        "判断有无潜在疾病智能体": "disease_potential_verify"
    }

    return agent_dict.get(agent_name, "unknown_agent")

def __get_agent_output_label(agent_name):
    '''
    获取智能体输出标签
    '''
    agent_output_label_dict = {
        "疾病标准化智能体 Standardization" : "出院诊断标准化",
        "疾病排序智能体 Prioritization": "排序",
        "疾病筛查智能体 Validation": "筛查",

        "发现潜在疾病智能体": "发现潜在疾病",
        "排除的低概率疾病智能体": "排除的低概率疾病",
        "判断有无潜在疾病智能体": "有无潜在疾病"
    }

    return agent_output_label_dict.get(agent_name, "unknown_agent")

def replace(agent_name):
    '''
    获取智能体输出标签
    '''
    agent_output_label_dict = {
        "疾病标准化智能体 Standardization" : "疾病1号智能体",
        "疾病排序智能体 Prioritization": "疾病5号智能体5",
        "疾病筛查智能体 Validation": "疾病6号智能体",

        "发现潜在疾病智能体": "疾病3号智能体",
        "潜在疾病标准化智能体 Disease Standardization Agent": "疾病4号智能体",
        "判断有无潜在疾病智能体": "疾病2号智能体"
    }

    return agent_output_label_dict.get(agent_name, "unknown_agent")