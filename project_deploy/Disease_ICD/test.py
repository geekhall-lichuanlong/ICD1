import os
import requests
import time
from openpyxl import load_workbook

import re
# 加载工作簿

# 配置信息
url = "http://localhost:5000/qwen3/diagnosis_qwen"
headers = {
    "Content-Type": "application/json"
}
token = os.getenv("LOCAL_LLM_API_KEY", "EMPTY")
model = "deepseek-chat"


wb = load_workbook('/mnt/suke/001Project/ICD_code_of_Qianfoshan_Hospital/p2/p2/utils/100(1).xlsx')
sheet = wb.active

# 病案标识号0	住院号1	主诉2	现病史3	既往史4	个人史5	婚姻史6	家族史7	入院情况8	入院诊断9	诊疗经过10	
# 病程记录11	手术名称12	手术经过13	影像学意见14	超声提示15	超声印象16	出院诊断17

# 循环执行 100 次
for i in range(2, 102):
    row= [cell.value for cell in sheet[i]]
    # 构造 content 内容（可以根据需要自定义）
    a12="""病案标识号：{p1}\n出院诊断：{p2}\n现病史：{p3}\n既往史：{p4}\n诊疗经过：{p5}\n入院情况：{p6}\n病程记录：{p7}\n影像学意见：{p8}\n超声提示：{p9}\n超声印象：{p10}"""
    
    content = a12.format(
        p1=row[0],
        p2=row[17],
        p3=row[3],
        p4=row[4],
        p5=row[10],
        p6=row[8],
        p7=row[11],
        p8=row[14],
        p9=row[15],
        p10=row[16]
    )
        
        

    # 构造 JSON 数据
    payload = {
        "model": model,
        "token": token,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }

    # 发送 POST 请求
    response = requests.post(url, headers=headers, json=payload)

    # 打印响应状态码和结果
    print(f"[第 {i} 次] 响应状态码: {response.status_code}")
    print(f"返回内容: {response.text}\n")

    # 如果需要控制频率，可以加上延时（例如 0.1 秒）
    time.sleep(1)
