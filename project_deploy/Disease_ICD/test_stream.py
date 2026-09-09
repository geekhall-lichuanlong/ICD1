#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from icd.disease.GetICD import get_icd_stream

# 测试数据
test_data = {
    "messages": [
        {
            "role": "user", 
            "content": {
                "病案标识号": "TEST001",
                "出院诊断": "急性阑尾炎",
                "现病史": "患者3天前无明显诱因出现右下腹疼痛",
                "既往史": "既往体健",
                "诊疗经过": "给予抗炎治疗",
                "入院情况": "一般状况可",
                "病程记录": "病情平稳",
                "影像学意见": "阑尾增厚",
                "超声提示": "阑尾炎征象",
                "超声印象": "急性阑尾炎"
            }
        }
    ]
}

def test_stream():
    """测试流式处理"""
    print("开始测试流式处理...")
    
    try:
        for result in get_icd_stream(test_data):
            print(f"收到流式数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
            print("-" * 50)
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stream()
