import pdfplumber
import pandas as pd
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import shutil
import subprocess
import time

def create_customer_excel():
    file1 = "PT AR001 BP_Customer Master V5 20260226.xlsx"
    file2 = "PT International Address - Customer V4 20260225.xlsx"
    file3 = "PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx"
    
    df1 = pd.read_excel(file1, sheet_name="General Data")
    df2 = pd.read_excel(file2, sheet_name="Sheet1")
    df3 = pd.read_excel(file3, sheet_name="Contact Person loading template")
    
    customer_data = []
    
    for _, row in df2.iterrows():
        customer_number = str(row['Customer Number']) if pd.notna(row['Customer Number']) else ''
        if not customer_number:
            continue
        
        chinese_name = str(row['Name']) if pd.notna(row['Name']) else ''
        
        english_name = ''
        for _, row1 in df1.iterrows():
            if str(row1['CUSTOMER']) == customer_number:
                english_name = str(row1['NAME_ORG1']) if pd.notna(row1['NAME_ORG1']) else ''
                break
        
        contact = ''
        mobile = ''
        for _, row3 in df3.iterrows():
            if str(row3['Customer Number']) == customer_number:
                contact = str(row3['Notes Mobile Number']) if pd.notna(row3['Notes Mobile Number']) else ''
                mobile = str(row3['Mobile number']) if pd.notna(row3['Mobile number']) else ''
                if mobile.endswith('.0'):
                    mobile = mobile[:-2]
                break
        
        customer_data.append({
            'customer_number': customer_number,
            'english_name': english_name,
            'chinese_name': chinese_name,
            'contact': contact,
            'mobile': mobile
        })
    
    result_df = pd.DataFrame(customer_data)
    result_df.to_excel("customer_combined.xlsx", index=False)
    print(f"已创建 customer_combined.xlsx，共 {len(result_df)} 条记录")

def extract_company_name_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

        lines = all_text.split('\n')
        chinese_name = None
        english_name = None
        
        for i, line in enumerate(lines):
            if "送货地址" in line or "送货点" in line:
                if i + 1 < len(lines):
                    company_line = lines[i + 1].strip()
                    if company_line and len(company_line) > 2:
                        chinese_name = company_line
            if "Ship To" in line:
                if i + 1 < len(lines):
                    company_line = lines[i + 1].strip()
                    if company_line and len(company_line) > 2:
                        # 过滤掉以 "Shipment" 开头的内容
                        if company_line.lower().startswith('shipment'):
                            continue
                        # 如果公司名中包含 "Shipment No"，只取前面部分
                        if 'Shipment No' in company_line:
                            company_line = company_line.split('Shipment No')[0].strip()
                        # 如果公司名中包含 "Shipment No:"，只取前面部分
                        if 'Shipment No:' in company_line:
                            company_line = company_line.split('Shipment No:')[0].strip()
                        english_name = company_line
        
        if chinese_name:
            return {'chinese': chinese_name, 'english': english_name}
        elif english_name:
            return {'chinese': None, 'english': english_name}
        else:
            return None

def find_contact_in_excel(company_name, excel_path):
    if not company_name:
        return None
    
    df = pd.read_excel(excel_path)
    
    chinese_name_pdf = company_name.get('chinese')
    english_name_pdf = company_name.get('english')

    for _, row in df.iterrows():
        chinese_name_excel = str(row['chinese_name']) if pd.notna(row['chinese_name']) else ''
        english_name_excel = str(row['english_name']) if pd.notna(row['english_name']) else ''

        match_found = False
        
        if chinese_name_pdf and chinese_name_excel:
            if chinese_name_pdf in chinese_name_excel or chinese_name_excel in chinese_name_pdf:
                match_found = True
        
        if not match_found and english_name_pdf and english_name_excel:
            if english_name_pdf in english_name_excel or english_name_excel in english_name_pdf:
                match_found = True
        
        if match_found:
            mobile = str(row['mobile']) if pd.notna(row['mobile']) else ''
            if mobile.endswith('.0'):
                mobile = mobile[:-2]
            return {
                'contact': row['contact'] if pd.notna(row['contact']) else '',
                'mobile': mobile
            }

    return None

def extract_handling_units_from_pdf(pdf_path):
    """从PDF中提取搬运单元号码 - 提取每行的第二个数字"""
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

        lines = all_text.split('\n')
        handling_units = []
        
        for i, line in enumerate(lines):
            # 查找包含"搬运单元"或"Handling Unit"的标题行
            if "搬运单元" in line or "Handling Unit" in line or "Top HU" in line:
                # 获取后面的数据行（包含搬运单元号码的行）
                for j in range(1, 20):  # 最多向后查找20行
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        # 跳过空行和页码行（包含/的行）
                        if not next_line or '/' in next_line:
                            continue
                        # 提取行中的所有数字
                        import re
                        matches = re.findall(r'\b\d+\b', next_line)
                        # 搬运单元号是每行的第二个数字（第一个是批次号）
                        if len(matches) >= 2:
                            handling_units.append(matches[1])  # 取第二个数字
                        else:
                            # 如果连续2行都没有匹配到，说明数据行结束
                            if j > 1:
                                break
        
        return handling_units

def find_hu_info_in_excel(handling_units, excel_path):
    """在Excel中查找对应的HU identification 2和Total Weight"""
    df = pd.read_excel(excel_path)
    
    hu_info_list = []
    total_weight_sum = 0.0
    
    for hu in handling_units:
        # 在Handling Unit列中查找匹配
        mask = df['Handling Unit'].astype(str).str.contains(str(hu))
        matched = df[mask]
        
        if not matched.empty:
            for _, row in matched.iterrows():
                hu_id2 = str(row['HU identification 2']) if pd.notna(row['HU identification 2']) else ''
                total_weight = float(row['Total Weight']) if pd.notna(row['Total Weight']) else 0.0
                
                hu_info_list.append({
                    'handling_unit': hu,
                    'hu_identification_2': hu_id2,
                    'total_weight': total_weight
                })
                total_weight_sum += total_weight
    
    return {
        'hu_info_list': hu_info_list,
        'total_weight_sum': round(total_weight_sum, 3)
    }

def update_pdf_with_hu_info(input_pdf, output_pdf, hu_info):
    """更新PDF中的批次号和毛重/净重"""
    try:
        pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))
        font_name = 'SimHei'
    except:
        font_name = 'Helvetica'

    # 先提取PDF中的文本和位置信息
    with pdfplumber.open(input_pdf) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        text = page.extract_text()
        lines = text.split('\n')
        
        # 找到批次号标题行的位置，然后获取下方每行第一个数字的位置
        batch_number_positions = []
        gross_weight_position = None
        
        # 查找批次号标题行
        batch_header_line_index = -1
        for i, line in enumerate(lines):
            if '批次号' in line or 'Batch' in line:
                batch_header_line_index = i
                break
        
        # 如果找到了批次号标题行
        if batch_header_line_index >= 0:
            # 获取标题行的y坐标范围
            header_y = None
            for word in words:
                if '批次号' in word.get('text', '') or 'Batch' in word.get('text', ''):
                    header_y = word['top']
                    break
            
            if header_y:
                # 收集标题行正下方的数据行（批次号）
                # PDF的Y坐标从下往上递增，所以下方的行Y坐标更大
                # 只查找标题行下方20像素范围内的数字
                for word in words:
                    # 只考虑标题行正下方（Y坐标比标题行大5-30像素）
                    if header_y + 5 < word['top'] < header_y + 30:
                        text_word = word.get('text', '')
                        # 查找数字（批次号）
                        if text_word.isdigit() and len(text_word) >= 6:  # 批次号通常至少6位
                            # 检查是否已经记录了该行的数字（避免重复）
                            already_added = False
                            for pos in batch_number_positions:
                                if abs(pos['y'] - word['top']) < 5:
                                    already_added = True
                                    break
                            if not already_added:
                                batch_number_positions.append({
                                    'x': word['x0'],  # 使用左边界位置（替换原数字）
                                    'y': word['top'],
                                    'font_size': word.get('size', 10)
                                })
        
        # 查找毛重/净重关键字位置
        for word in words:
            text_word = word.get('text', '')
            if '毛重' in text_word or '净重' in text_word or 'Gross' in text_word or 'Net' in text_word:
                gross_weight_position = {
                    'x': word['x1'],  # 使用右边界位置
                    'y': word['top']
                }

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    can.setFillColorRGB(0, 0, 0)
    
    # 处理批次号替换 - 将HU identification 2替换原批次号
    hu_info_list = hu_info.get('hu_info_list', [])
    total_weight_sum = hu_info.get('total_weight_sum', 0.0)
    
    for i, info in enumerate(hu_info_list):
        if info['hu_identification_2'] and i < len(batch_number_positions):
            pos = batch_number_positions[i]
            # 使用检测到的字体大小，如果没有则使用默认大小
            font_size = pos.get('font_size', 10)
            
            # 先绘制白色矩形覆盖原批次号（宽度根据字体大小估算）
            can.setFillColorRGB(1, 1, 1)  # 白色
            text_width = len(info['hu_identification_2']) * font_size * 0.6  # 估算文本宽度
            can.rect(pos['x'] - 2, pos['y'] - font_size * 0.2, text_width + 4, font_size + 4, fill=True, stroke=False)
            
            # 再写入新的HU identification 2
            can.setFillColorRGB(0, 0, 0)  # 黑色
            can.setFont(font_name, font_size)
            can.drawString(pos['x'], pos['y'], info['hu_identification_2'])
    
    # 处理毛重/净重 - 将总和写在毛重/净重后面
    can.setFont(font_name, 10)
    if gross_weight_position:
        can.drawString(gross_weight_position['x'] + 10, gross_weight_position['y'], f"{total_weight_sum:.3f}")
    else:
        # 如果没找到精确位置，使用默认位置
        can.drawString(550, 400, f"{total_weight_sum:.3f}")

    can.save()
    packet.seek(0)

    new_pdf = PdfReader(packet)
    output = PdfWriter()

    with open(input_pdf, "rb") as inputStream:
        existing_pdf = PdfReader(inputStream)
        
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

        for page_num in range(1, len(existing_pdf.pages)):
            output.add_page(existing_pdf.pages[page_num])

    with open(output_pdf, "wb") as outputStream:
        output.write(outputStream)

def add_contact_to_pdf(input_pdf, output_pdf, contact_info, is_english_company=False):
    try:
        pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))
        font_name = 'SimHei'
    except:
        font_name = 'Helvetica'

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    can.setFont(font_name, 10)
    can.setFillColorRGB(0, 0, 0)

    y_position = 675
    x_position = 84
    
    if is_english_company:
        x_position += 10
        y_position -= 15
    
    if contact_info['contact']:
        contact_text = f"联系人: {contact_info['contact']}"
        if font_name == 'Helvetica':
            contact_text = f"Contact: {contact_info['contact']}"
        can.drawString(x_position, y_position, contact_text)
        y_position -= 15

    if contact_info['mobile']:
        mobile_text = f"电话: {contact_info['mobile']}"
        if font_name == 'Helvetica':
            mobile_text = f"Phone: {contact_info['mobile']}"
        can.drawString(x_position, y_position, mobile_text)

    can.save()
    packet.seek(0)

    new_pdf = PdfReader(packet)
    output = PdfWriter()

    with open(input_pdf, "rb") as inputStream:
        existing_pdf = PdfReader(inputStream)
        
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

        for page_num in range(1, len(existing_pdf.pages)):
            output.add_page(existing_pdf.pages[page_num])

    with open(output_pdf, "wb") as outputStream:
        output.write(outputStream)

def process_pdf_files():
    excel_path = "customer_combined.xlsx"
    
    hu_excel_path = "EXPORT_20260604132137-hu.xlsx"
    
    os.makedirs("output", exist_ok=True)
    os.makedirs("archive", exist_ok=True)
    
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("当前目录没有PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    time_suffix = time.strftime("%H%M")
    
    for pdf_filename in pdf_files:
        pdf_path = pdf_filename
        print(f"\n处理文件: {pdf_path}")
        
        try:
            # 处理公司名称和联系人信息
            company_name = extract_company_name_from_pdf(pdf_path)
            if company_name:
                if company_name.get('chinese'):
                    print(f"从PDF提取的中文公司名称: {company_name['chinese']}")
                if company_name.get('english'):
                    print(f"从PDF提取的英文公司名称: {company_name['english']}")
            else:
                print("未从PDF提取到公司名称")

            contact_info = find_contact_in_excel(company_name, excel_path)

            # 处理搬运单元信息
            handling_units = extract_handling_units_from_pdf(pdf_path)
            print(f"从PDF提取的搬运单元号码: {handling_units}")
            
            hu_info = None
            if handling_units and os.path.exists(hu_excel_path):
                hu_info = find_hu_info_in_excel(handling_units, hu_excel_path)
                print(f"匹配到的HU信息数量: {len(hu_info.get('hu_info_list', []))}")
                print(f"Total Weight总和: {hu_info.get('total_weight_sum', 0.0)}")
            elif not os.path.exists(hu_excel_path):
                print(f"未找到HU Excel文件: {hu_excel_path}")

            # 生成输出文件名
            name_without_ext = os.path.splitext(pdf_filename)[0]
            output_pdf = f"output/{name_without_ext}_{time_suffix}_with_contact.pdf"
            temp_pdf = f"output/{name_without_ext}_{time_suffix}_temp.pdf"
            
            # 添加联系人信息到PDF
            if contact_info:
                print(f"找到的联系人: {contact_info['contact']}")
                print(f"找到的电话: {contact_info['mobile']}")
                
                is_english_company = company_name and company_name.get('english') and not company_name.get('chinese')
                
                add_contact_to_pdf(pdf_path, temp_pdf, contact_info, is_english_company)
                print(f"已成功添加联系信息到PDF")
            else:
                # 如果没有联系人信息，直接复制原PDF
                shutil.copy(pdf_path, temp_pdf)
                print("未找到匹配的联系人信息")
            
            # 更新搬运单元信息到PDF
            if hu_info:
                update_pdf_with_hu_info(temp_pdf, output_pdf, hu_info)
                os.remove(temp_pdf)
                print(f"已成功更新搬运单元信息到PDF，新文件保存为: {output_pdf}")
            else:
                os.rename(temp_pdf, output_pdf)
                print(f"新文件保存为: {output_pdf}")
            
            # 移动原文件到archive
            archive_path = f"archive/{name_without_ext}_{time_suffix}.pdf"
            max_retries = 3
            for i in range(max_retries):
                try:
                    shutil.move(pdf_path, archive_path)
                    print(f"已将原PDF文件移动到: {archive_path}")
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                        print(f"文件被占用，重试中 ({i+1}/{max_retries})...")
                    else:
                        print(f"无法移动文件 {pdf_path}，文件可能被其他程序占用")
        except Exception as e:
            print(f"处理文件 {pdf_path} 时发生错误: {str(e)}")

def main():
    excel_file = "customer_combined.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"{excel_file} 不存在，正在创建...")
        create_customer_excel()
        print(f"{excel_file} 创建完成")
    else:
        print(f"{excel_file} 已存在，跳过创建")
    
    print("\n正在处理PDF文件...")
    process_pdf_files()
    print("\n完成！")

if __name__ == "__main__":
    main()