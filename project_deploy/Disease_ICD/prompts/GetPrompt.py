import json

def get_prompt(prompt_name, kwargs):
    '''
    获取并格式化prompt。
    疾病ICD各个Agent的prompt名称如下:
        疾病标准化智能体 Standardization - disease_standardized
        潜在疾病抽取智能体 - disease_potential_extract
        潜在疾病标准化智能体 Standardization - disease_potential_strandarized
        疾病主诊断智能体 - disease_main_diagnosis

    手术ICD各个Agent的prompt名称如下
    - 待补充
    ''' 
### 如需更改prompt内容，请在对应的prompt文件中修改，若更改了prompt名称，请在此处同步修改 ###

    '''
    目前其中所需内容为：
    {
    "disease_standardized": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n既往史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声提示：{}\n超声印象：{}",
    "disease_potential_extract": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n既往史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声提示：{}\n超声印象：{}",
    "disease_potential_standardized": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声印象:{}\n超声提示：{}\n当前疾病：{}",
    "disease_main_diagnosis": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声印象:{}\n超声提示：{}\n当前疾病：{}",
    }

    代码匹配内容已此注释为准
    '''

    prompt = ""
    file_path = './prompts/disease_prompt.json'

    # 读取JSON文件
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if prompt_name in data:
            prompt = data[prompt_name]
        else:
            raise ValueError(f"Prompt '{prompt_name}' not found in {file_path}")
        
    content = ""
    for key, value in kwargs.items():
        content += f"{key}:{value}\n"
    # print(content, prompt)

    prompt = content.replace("{content}", content)

    # 返回格式化后的prompt
    return prompt

def get_prompt_agent6(prompt_name, kwargs):
    '''
    获取并格式化prompt。
    疾病ICD各个Agent的prompt名称如下:
        疾病标准化智能体 Standardization - disease_standardized
        潜在疾病抽取智能体 - disease_potential_extract
        潜在疾病标准化智能体 Standardization - disease_potential_strandarized
        疾病主诊断智能体 - disease_main_diagnosis

    手术ICD各个Agent的prompt名称如下
    - 待补充
    ''' 
### 如需更改prompt内容，请在对应的prompt文件中修改，若更改了prompt名称，请在此处同步修改 ###

    '''
    目前其中所需内容为：
    {
    "disease_standardized": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n既往史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声提示：{}\n超声印象：{}",
    "disease_potential_extract": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n既往史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声提示：{}\n超声印象：{}",
    "disease_potential_standardized": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声印象:{}\n超声提示：{}\n当前疾病：{}",
    "disease_main_diagnosis": "病案标识号：{}\n出院诊断：{}\n现病史：{}\n诊疗经过：{}\n入院情况：{}\n病程记录：{}\n影像学意见：{}\n超声印象:{}\n超声提示：{}\n当前疾病：{}",
    }

    代码匹配内容已此注释为准
    '''

    prompt = ""
    file_path = './prompts/disease_prompt.json'

    # 读取JSON文件
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if prompt_name in data:
            prompt = data[prompt_name]
        else:
            raise ValueError(f"Prompt '{prompt_name}' not found in {file_path}")
        
    content = ""
    items = list(kwargs.items())
    for key, value in items[:-1]:   # 去掉最后一个
        content += f"{key}:{value}\n"
    content += "待筛查的疾病列表："
    content += ",".join(map(str, kwargs['待筛查的疾病列表']))

    prompt = content.replace("{content}", content)

    # 返回格式化后的prompt
    return prompt


if __name__ == "__main__":
    # 测试获取prompt
    test_prompt = get_prompt("disease_standardized",
                             {
                             "病案标识号": "12345",
                             "出院诊断":"高血压",
                             "现病史":"无明显症状",
                             "既往史":"无重大疾病史",
                             "诊疗经过":"常规治疗",
                             "入院情况":"无异常",
                             "病程记录":"稳定",
                             "影像学意见":"正常",
                             "超声提示":"无异常",
                             "超声印象":"正常"
    })

    print(test_prompt)