from elasticsearch import Elasticsearch

import pandas as pd

# 连接 Elasticsearch
es = Elasticsearch(
    "https://127.0.0.1:9200",
    ca_certs="/home/qluai/lzy/jointcoder/project_deploy/http_ca.crt",
    http_auth=("elastic", "qluai1358")
    )

index_name = "icd_tree"

# 检查索引是否存在，若不存在则创建
if not es.indices.exists(index=index_name):
    es.indices.create(index=index_name)
    print(f"Index '{index_name}' created.")
else:
    print(f"Index '{index_name}' already exists.")

# 读取 Excel 文件
df = pd.read_excel('/home/qluai/lzy/jointcoder/es_save/ICD2.0.xlsx')

# 解析 ICD 代码层级关系
def get_parents(icd_code):
    """ 计算 ICD 代码的各级父节点 """
    parts = icd_code.split('.')
    base = parts[0]
    if len(parts) > 1:
        decimals = parts[1]
    else:
        decimals = ""

    levels = {
        "level_1": base,  # 整数部分
        "level_2": f"{base}.{decimals[0]}xx" if len(decimals) > 0 else None,
        # "level_3": f"{base}.{decimals[:2]}x" if len(decimals) > 1 else None,
        "level_3": f"{base}.{decimals[:3]}" if len(decimals) > 2 else None,
    }

    return levels

# 遍历 ICD 数据并存入 Elasticsearch
for index, row in df.iterrows():
    icd_code = row['疾病编码']
    icd_name = row['疾病名称']

    # 获取各级父 ICD 编码
    levels = get_parents(icd_code)

    # 存储文档
    doc = {
        "icd_code": icd_code,
        "name": icd_name,
        "parent_level_1": levels["level_1"],
        "parent_level_2": levels["level_2"],
        # "parent_level_3": levels["level_3"],
        "parent_level_3": levels["level_3"],
    }
    
    res = es.index(index=index_name, document=doc)
    print(f"Indexed {icd_code}: {res['_id']}")

print("ICD 数据已存入 Elasticsearch")
