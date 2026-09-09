from elasticsearch import Elasticsearch
import pandas as pd

# 连接 Elasticsearch
es = Elasticsearch(
    "https://127.0.0.1:9200",
    ca_certs="/home/qluai/lzy/jointcoder/project_deploy/http_ca.crt",
    http_auth=("elastic", "qluai1358")
)

index_name = "surgery_icd_tree"

# 检查索引是否存在，若不存在则创建
if not es.indices.exists(index=index_name):
    es.indices.create(index=index_name)
    print(f"Index '{index_name}' created.")
else:
    print(f"Index '{index_name}' already exists.")

# 读取 Excel 文件（请替换为实际路径）
df = pd.read_excel(
    '/home/qluai/lzy/jointcoder/es_save/surgery_icd_code.xlsx',
    converters={
        '主要编码': lambda x: str(x).strip() if pd.notna(x) else '',
        '附加编码': lambda x: str(x).strip() if pd.notna(x) else '',
        '手术操作名称': str,
        '类别': str,
        '录入选项': str
    }
)

def get_parents(icd_code):
    """解析ICD代码的层级关系"""
    if '.' not in icd_code:
        integer_part = icd_code
        decimal_part = ''
    else:
        parts = icd_code.split('.')
        integer_part = parts[0]
        decimal_part = '.'.join(parts[1:])  # 处理多个点号的情况
    
    # 处理各级父节点
    parent_level_1 = f"{integer_part}.{decimal_part[:2]}" if len(decimal_part) >= 2 else None
    parent_level_2 = f"{integer_part}.{decimal_part[:4]}" if len(decimal_part) >= 4 else None
    parent_level_3 = f"{integer_part}.{decimal_part[:8]}" if len(decimal_part) >= 8 else None
    
    return {
        "parent_level_1": parent_level_1,
        "parent_level_2": parent_level_2,
        "parent_level_3": parent_level_3,
    }

def process_icd_range(icd_str):
    """处理ICD编码范围，转换为逗号分隔的完整列表"""
    if not icd_str or pd.isna(icd_str):
        return ''
    
    # 处理多个编码用逗号分隔的情况
    icd_list = []
    for part in str(icd_str).split(','):
        part = part.strip()
        if '-' in part:
            # 处理范围
            start, end = part.split('-')
            start = format_icd_code(start)
            end = format_icd_code(end)
            # 生成范围内的所有编码
            icd_list.extend(generate_icd_range(start, end))
        else:
            # 单个编码
            icd_list.append(format_icd_code(part))
    
    # 去重并排序
    icd_list = sorted(list(set(icd_list)))
    return ','.join(icd_list)

def format_icd_code(icd_code):
    """格式化ICD编码，确保小数部分为4位，且第三位和第四位为0"""
    if '.' in icd_code:
        parts = icd_code.split('.')
        integer_part = parts[0]
        decimal_part = '.'.join(parts[1:])  # 处理多个点号的情况
        # 只保留小数点后两位，后两位补0
        decimal_part = decimal_part[:2].ljust(4, '0')
        return f"{integer_part}.{decimal_part}"
    else:
        # 如果没有小数点，直接返回整数部分，小数部分补0
        return f"{icd_code}.0000"

def generate_icd_range(start, end):
    """生成ICD编码范围内的所有编码（只生成小数点后两位的编码）"""
    start_int = int(start.replace('.', ''))
    end_int = int(end.replace('.', ''))
    step = 100  # 每次增加100，确保只生成小数点后两位的编码
    return [format_icd_code(f"{code // 10000}.{code % 10000:04d}") for code in range(start_int, end_int + 1, step)]

# 遍历数据并存入ES
for index, row in df.iterrows():
    # 处理主要/附加编码
    main_code = str(row['主要编码']).strip() if pd.notna(row['主要编码']) else ''
    add_code = str(row['附加编码']).strip() if pd.notna(row['附加编码']) else ''
    
    if main_code:
        icd_code = main_code
        additional = 0
    elif add_code:
        icd_code = add_code
        additional = 1
    else:
        raise ValueError(f"行 {index+2} 主要编码和附加编码均为空")
    
    # 获取层级关系
    parents = get_parents(icd_code)
    
    # 构建基础文档
    doc = {
        "icd_code": icd_code,
        "name": row['手术操作名称'],
        "additional": additional,
        "category": row['类别'],
        "Enter options": row['录入选项'],
        "parent_level_1": parents["parent_level_1"],
        "parent_level_2": parents["parent_level_2"],
        "parent_level_3": parents["parent_level_3"]
    }

    # 处理新字段逻辑
    # 1. 处理"注"字段
    if '注' in df.columns:
        note_value = str(row['注']).strip() if pd.notna(row['注']) else ''
        if note_value:
            doc['注'] = note_value

    # 2. 处理包括1-19
    for i in range(1, 20):
        col_name = f'包括{i}'
        if col_name in df.columns:
            value = str(row[col_name]).strip() if pd.notna(row[col_name]) else ''
            if value:
                doc[col_name] = value

    # 3. 处理不包括组（按顺序处理每对字段）
    for i in range(1, 28):
        excl_col = f'不包括{i}'
        excl_icd_col = f'不包括icd{i}'
        # 确保两个字段都存在才处理
        if excl_col in df.columns and excl_icd_col in df.columns:
            excl_val = str(row[excl_col]).strip() if pd.notna(row[excl_col]) else ''
            excl_icd_val = process_icd_range(row[excl_icd_col]) if pd.notna(row[excl_icd_col]) else ''
            # 只要有一个字段有值就保留
            if excl_val or excl_icd_val:
                doc[excl_col] = excl_val
                doc[excl_icd_col] = excl_icd_val

    # 4. 处理另编码组
    for i in range(1, 16):
        alt_col = f'另编码{i}'
        alt_icd_col = f'另编码icd{i}'
        if alt_col in df.columns and alt_icd_col in df.columns:
            alt_val = str(row[alt_col]).strip() if pd.notna(row[alt_col]) else ''
            alt_icd_val = process_icd_range(row[alt_icd_col]) if pd.notna(row[alt_icd_col]) else ''
            if alt_val or alt_icd_val:
                doc[alt_col] = alt_val
                doc[alt_icd_col] = alt_icd_val

    # 5. 处理共用细目
    for i in range(1, 11):
        col_name = f'共用细目{i}'
        if col_name in df.columns:
            value = str(row[col_name]).strip() if pd.notna(row[col_name]) else ''
            if value:
                doc[col_name] = value

    # 6. 处理评估字段
    for i in range(1, 11):
        col_name = f'评估{i}'
        if col_name in df.columns:
            value = str(row[col_name]).strip() if pd.notna(row[col_name]) else ''
            if value:
                doc[col_name] = value

    # 存储到ES
    res = es.index(index=index_name, document=doc)
    print(f"已存入 {icd_code}: {res['_id']}")

print("数据已全部存入Elasticsearch")