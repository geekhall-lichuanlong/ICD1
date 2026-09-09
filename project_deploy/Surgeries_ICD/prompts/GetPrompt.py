import json

def get_prompt(prompt_name, kwargs):
    '''
    获取并格式化prompt。
    手术ICD各个Agent的prompt名称如下
    - 待补充
    ''' 
### 如需更改prompt内容，请在对应的prompt文件中修改，若更改了prompt名称，请在此处同步修改 ###
# 标准化   找额外手术（可选）  匹配零编码   排序（主手术）  生成表格
    '''
    目前其中所需内容为：
    {
    "S_standardized": "病案标识号：{}\n手术名称：{}\n手术经过：{}\n病程记录：{}",
    "S_additional": "病案标识号：{}\n手术名称：{}\n手术经过：{}\n病程记录：{}",
    "S_another_coding": "病案标识号：{}\n手术名称：{}\n手术经过：{}\n病程记录：{}",
    "S_sorting": "病案标识号：{}\n手术名称：{}\n手术经过：{}\n病程记录：{}\",
    }

    代码匹配内容已此注释为准
    '''

        
    content = ""
    for key, value in kwargs.items():
        content += f"{key}:{value}\n"
    # print(content, prompt)

    prompt = content.replace("{content}", content)

    # 返回格式化后的prompt
    return prompt

if __name__ == "__main__":
    # 测试获取prompt
    test_prompt = get_prompt("disease_standardized",
                             {
                             "病案标识号": "12345",
                             "手术名称":"高血压",
                             "手术经过":"无",
                             "病程记录":"稳定"
    })
    print(test_prompt)