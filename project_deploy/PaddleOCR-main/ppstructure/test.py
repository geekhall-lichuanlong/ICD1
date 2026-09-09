from docx import Document
import re
import pandas as pd

def process_word_document(file_path):
    # 读取Word文档
    doc = Document(file_path)
    
    # 存储所有文本
    all_text = ""
    
    # 遍历文档中的每个段落并合并文本
    for paragraph in doc.paragraphs:
        all_text += paragraph.text
    
    # 提取住院号
    hospital_number = None
    header_match = re.search(r'姓名：.*?科室：.*?住院号：(\d+)', all_text)
    if header_match:
        hospital_number = header_match.group(1)
    
    # 清理文本函数
    def clean_text(text):
        # 删除所有空格（包括中文空格、英文空格）和换行符
        text = re.sub(r'[\s\u3000]', '', text)
        text = text.replace('山东第一医科大学第一附属医院（山东省千佛山医院）', '')
        
        # 替换英文冒号为中文冒号
        text = text.replace(':', '：')
        
        # 删除完整的表头字段（包括两种情况）
        if hospital_number:
            # 删除包含门诊号的完整表头
            pattern1 = rf'姓名：[^：]*?科室：[^：]*?住院号：{hospital_number}(?:门诊号：[^：]*?)?(?=\S|$)'
            # 删除不包含门诊号的表头
            pattern2 = rf'姓名：[^：]*?科室：[^：]*?住院号：{hospital_number}(?=\S|$)'
            text = re.sub(pattern1, '', text)
            text = re.sub(pattern2, '', text)
        
        text = re.sub(r'第\d+页', '', text)
        return text
    
    # 清理并存储处理后的文本
    cleaned_text = clean_text(all_text)
    
    return cleaned_text

def clean_extracted_text(text):
    """
    清理提取的文本内容
    """
    if not text:
        return ''
    # 如果文本以冒号开头，删除冒号
    if text.startswith('：'):
        text = text[1:]
    return text.strip()

def extract_fields(cleaned_text):
    """
    提取所有字段到一个字典中
    """
    fields_data = {}
    
    # 提取入院情况
    admission_match = re.search(r'入院情况：(.*?)(?=入院诊断：|$)', cleaned_text)
    if admission_match:
        fields_data['入院情况'] = clean_extracted_text(admission_match.group(1))
    
    # 提取入院诊断
    diagnosis_match = re.search(r'入院诊断：(.*?)(?=诊疗经过|$)', cleaned_text)
    if diagnosis_match:
        fields_data['入院诊断'] = clean_extracted_text(diagnosis_match.group(1))
    
    # 提取诊疗经过
    treatment_match = re.search(r'诊疗经过[：]?(.*?)(?=出院诊断|$)', cleaned_text)
    if treatment_match:
        fields_data['诊疗经过'] = clean_extracted_text(treatment_match.group(1))
    
    # 提取出院诊断
    discharge_diagnosis_match = re.search(r'出院诊断[：]?(.*?)(?=出院情况|$)', cleaned_text)
    if discharge_diagnosis_match:
        fields_data['出院诊断'] = clean_extracted_text(discharge_diagnosis_match.group(1))

    # 提取出院情况（考虑OCR可能的错误）
    discharge_condition_match = re.search(r'出院情况[：]?(.*?)(?=出院医[嘱瞩]|$)', cleaned_text)
    if discharge_condition_match:
        fields_data['出院情况'] = clean_extracted_text(discharge_condition_match.group(1))
    
    # 提取出院医嘱（考虑OCR可能的错误）
    discharge_advice_match = re.search(r'出院医[嘱瞩][：]?(.*?)(?=专家门诊|咨询电话|科室联系方式|主任门诊|$)', cleaned_text)
    if discharge_advice_match:
        fields_data['出院医嘱'] = clean_extracted_text(discharge_advice_match.group(1))
    
    # 提取病史相关字段（不包括月经生育史）
    history_fields = [
        ('主诉', r'主诉：(.*?)(?=现病史：|$)'),
        ('现病史', r'现病史：(.*?)(?=既往史：|$)'),
        ('既往史', r'既往史：(.*?)(?=个人史：|$)'),
        ('个人史', r'个人史：(.*?)(?=婚姻史：|$)'),
        ('婚姻史', r'婚姻史：(.*?)(?=家族史：|$)'),
        ('家族史', r'家族史：(.*?)(?=体格检查|$)')
    ]
    
    # 提取所有病史字段
    for field_name, pattern in history_fields:
        match = re.search(pattern, cleaned_text)
        if match:
            fields_data[field_name] = clean_extracted_text(match.group(1))
        else:
            fields_data[field_name] = ''  # 如果字段不存在，设置为空字符串
    
    return fields_data

def save_to_excel(data_dict, output_path):
    """
    将提取的数据保存到Excel文件
    """
    try:
        # 创建DataFrame
        df = pd.DataFrame([data_dict])
        
        # 定义字段的顺序（不包括体格检查、辅助检查和月经生育史）
        columns_order = [
            '主诉', '现病史', '既往史', '个人史', '婚姻史', '家族史',
            '入院情况', '入院诊断', '诊疗经过', 
            '出院诊断', '出院情况', '出院医嘱'
        ]
        
        # 确保所有列都存在，如果不存在则添加空列
        for col in columns_order:
            if col not in df.columns:
                df[col] = ''
        
        # 重新排序列
        df = df[columns_order]
        
        # 保存到Excel
        df.to_excel(output_path, index=False)
        print(f"数据已成功保存到: {output_path}")
        
    except Exception as e:
        print(f"保存Excel文件时发生错误: {str(e)}")

def main():
    try:
        file_path = "1_ocr.docx"
        excel_output_path = "extracted_data.xlsx"
        
        # 获取清理后的文本
        cleaned_text = process_word_document(file_path)
        
        # 提取所有字段到字典中
        extracted_data = extract_fields(cleaned_text)
        
        # 保存到Excel
        save_to_excel(extracted_data, excel_output_path)
        
    except Exception as e:
        print(f"处理文档时发生错误: {str(e)}")

if __name__ == "__main__":
    main()