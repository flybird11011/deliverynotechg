import io

import pandas as pd
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def extract_company_name_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

        lines = all_text.split("\n")
        chinese_name = None
        english_name = None

        for i, line in enumerate(lines):
            if "閫佽揣鍦板潃" in line or "閫佽揣鐐?" in line:
                if i + 1 < len(lines):
                    company_line = lines[i + 1].strip()
                    if company_line and len(company_line) > 2:
                        chinese_name = company_line
            if "Ship To" in line:
                if i + 1 < len(lines):
                    company_line = lines[i + 1].strip()
                    if company_line and len(company_line) > 2:
                        if company_line.lower().startswith("shipment"):
                            continue
                        if "Shipment No" in company_line:
                            company_line = company_line.split("Shipment No")[0].strip()
                        if "Shipment No:" in company_line:
                            company_line = company_line.split("Shipment No:")[0].strip()
                        english_name = company_line

        if chinese_name:
            return {"chinese": chinese_name, "english": english_name}
        if english_name:
            return {"chinese": None, "english": english_name}
        return None


def find_contact_in_excel(company_name, excel_path):
    if not company_name:
        return None

    df = pd.read_excel(excel_path)

    chinese_name_pdf = company_name.get("chinese")
    english_name_pdf = company_name.get("english")

    for _, row in df.iterrows():
        chinese_name_excel = str(row["chinese_name"]) if pd.notna(row["chinese_name"]) else ""
        english_name_excel = str(row["english_name"]) if pd.notna(row["english_name"]) else ""

        match_found = False

        if chinese_name_pdf and chinese_name_excel:
            if chinese_name_pdf in chinese_name_excel or chinese_name_excel in chinese_name_pdf:
                match_found = True

        if not match_found and english_name_pdf and english_name_excel:
            if english_name_pdf in english_name_excel or english_name_excel in english_name_pdf:
                match_found = True

        if match_found:
            mobile = str(row["mobile"]) if pd.notna(row["mobile"]) else ""
            if mobile.endswith(".0"):
                mobile = mobile[:-2]
            return {
                "contact": row["contact"] if pd.notna(row["contact"]) else "",
                "mobile": mobile,
            }

    return None


def extract_handling_units_from_pdf(pdf_path):
    """浠嶱DF涓彁鍙栨惉杩愬崟鍏冨彿鐮?- 鎻愬彇姣忚鐨勭浜屼釜鏁板瓧"""
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

        lines = all_text.split("\n")
        handling_units = []

        for i, line in enumerate(lines):
            if "鎼繍鍗曞厓" in line or "Handling Unit" in line or "Top HU" in line:
                for j in range(1, 20):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if not next_line or "/" in next_line:
                            continue
                        import re

                        matches = re.findall(r"\b\d+\b", next_line)
                        if len(matches) >= 2:
                            handling_units.append(matches[1])
                        else:
                            if j > 1:
                                break

        return handling_units


def find_hu_info_in_excel(handling_units, excel_path):
    """鍦‥xcel涓煡鎵惧搴旂殑HU identification 2鍜孴otal Weight"""
    df = pd.read_excel(excel_path)

    hu_info_list = []
    total_weight_sum = 0.0

    for hu in handling_units:
        mask = df["Handling Unit"].astype(str).str.contains(str(hu))
        matched = df[mask]

        if not matched.empty:
            for _, row in matched.iterrows():
                hu_id2 = str(row["HU identification 2"]) if pd.notna(row["HU identification 2"]) else ""
                total_weight = float(row["Total Weight"]) if pd.notna(row["Total Weight"]) else 0.0

                hu_info_list.append(
                    {
                        "handling_unit": hu,
                        "hu_identification_2": hu_id2,
                        "total_weight": total_weight,
                    }
                )
                total_weight_sum += total_weight

    return {
        "hu_info_list": hu_info_list,
        "total_weight_sum": round(total_weight_sum, 3),
    }


def update_pdf_with_hu_info(input_pdf, output_pdf, hu_info):
    """鏇存柊PDF涓殑鎵规鍙峰拰姣涢噸/鍑€閲?"""
    try:
        pdfmetrics.registerFont(TTFont("SimHei", "simhei.ttf"))
        font_name = "SimHei"
    except Exception:
        font_name = "Helvetica"

    with pdfplumber.open(input_pdf) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        text = page.extract_text()
        lines = text.split("\n")

        batch_number_positions = []
        gross_weight_position = None

        batch_header_line_index = -1
        for i, line in enumerate(lines):
            if "鎵规鍙?" in line or "Batch" in line:
                batch_header_line_index = i
                break

        if batch_header_line_index >= 0:
            header_y = None
            for word in words:
                if "鎵规鍙?" in word.get("text", "") or "Batch" in word.get("text", ""):
                    header_y = word["top"]
                    break

            if header_y:
                for word in words:
                    if header_y + 5 < word["top"] < header_y + 30:
                        text_word = word.get("text", "")
                        if text_word.isdigit() and len(text_word) >= 6:
                            already_added = False
                            for pos in batch_number_positions:
                                if abs(pos["y"] - word["top"]) < 5:
                                    already_added = True
                                    break
                            if not already_added:
                                batch_number_positions.append(
                                    {
                                        "x": word["x0"],
                                        "y": word["top"],
                                        "font_size": word.get("size", 10),
                                    }
                                )

        for word in words:
            text_word = word.get("text", "")
            if "姣涢噸" in text_word or "鍑€閲?" in text_word or "Gross" in text_word or "Net" in text_word:
                gross_weight_position = {
                    "x": word["x1"],
                    "y": word["top"],
                }

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    can.setFillColorRGB(0, 0, 0)

    hu_info_list = hu_info.get("hu_info_list", [])
    total_weight_sum = hu_info.get("total_weight_sum", 0.0)

    for i, info in enumerate(hu_info_list):
        if info["hu_identification_2"] and i < len(batch_number_positions):
            pos = batch_number_positions[i]
            font_size = pos.get("font_size", 10)

            can.setFillColorRGB(1, 1, 1)
            text_width = len(info["hu_identification_2"]) * font_size * 0.6
            can.rect(pos["x"] - 2, pos["y"] - font_size * 0.2, text_width + 4, font_size + 4, fill=True, stroke=False)

            can.setFillColorRGB(0, 0, 0)
            can.setFont(font_name, font_size)
            can.drawString(pos["x"], pos["y"], info["hu_identification_2"])

    can.setFont(font_name, 10)
    if gross_weight_position:
        can.drawString(gross_weight_position["x"] + 10, gross_weight_position["y"], f"{total_weight_sum:.3f}")
    else:
        can.drawString(550, 400, f"{total_weight_sum:.3f}")

    can.save()
    packet.seek(0)

    new_pdf = PdfReader(packet)
    output = PdfWriter()

    with open(input_pdf, "rb") as input_stream:
        existing_pdf = PdfReader(input_stream)

        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

        for page_num in range(1, len(existing_pdf.pages)):
            output.add_page(existing_pdf.pages[page_num])

    with open(output_pdf, "wb") as output_stream:
        output.write(output_stream)


def add_contact_to_pdf(input_pdf, output_pdf, contact_info, is_english_company=False):
    try:
        pdfmetrics.registerFont(TTFont("SimHei", "simhei.ttf"))
        font_name = "SimHei"
    except Exception:
        font_name = "Helvetica"

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    can.setFont(font_name, 10)
    can.setFillColorRGB(0, 0, 0)

    y_position = 675
    x_position = 84

    if is_english_company:
        x_position += 10
        y_position -= 15

    if contact_info["contact"]:
        contact_text = f"鑱旂郴浜? {contact_info['contact']}"
        if font_name == "Helvetica":
            contact_text = f"Contact: {contact_info['contact']}"
        can.drawString(x_position, y_position, contact_text)
        y_position -= 15

    if contact_info["mobile"]:
        mobile_text = f"鐢佃瘽: {contact_info['mobile']}"
        if font_name == "Helvetica":
            mobile_text = f"Phone: {contact_info['mobile']}"
        can.drawString(x_position, y_position, mobile_text)

    can.save()
    packet.seek(0)

    new_pdf = PdfReader(packet)
    output = PdfWriter()

    with open(input_pdf, "rb") as input_stream:
        existing_pdf = PdfReader(input_stream)

        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

        for page_num in range(1, len(existing_pdf.pages)):
            output.add_page(existing_pdf.pages[page_num])

    with open(output_pdf, "wb") as output_stream:
        output.write(output_stream)

