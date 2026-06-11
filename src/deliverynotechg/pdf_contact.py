import io
import os
import logging
import re
from pathlib import Path

import pandas as pd
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


_FONT_DIR = Path(os.getenv("DELIVERYNOTE_FONT_DIR", "fonts"))
_SYSTEM_FONT_FILES = {
    "SimHei": [
        _FONT_DIR / "SimHei.ttf",
        _FONT_DIR / "simhei.ttf",
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ],
    "NSimSun": [
        _FONT_DIR / "NSimSun.ttc",
        _FONT_DIR / "NSimSun.ttf",
        _FONT_DIR / "simsun.ttc",
        _FONT_DIR / "simsun.ttf",
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ],
    "SimSun": [
        _FONT_DIR / "SimSun.ttc",
        _FONT_DIR / "SimSun.ttf",
        _FONT_DIR / "simsun.ttc",
        _FONT_DIR / "simsun.ttf",
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ],
}


logger = logging.getLogger(__name__)


def build_batch_replacements(batch_number_positions, hu_info_list):
    replacements = []
    for pos, info in zip(batch_number_positions, hu_info_list):
        batch_number = info.get("batch_number") or info.get("hu_identification_2", "")
        if not batch_number:
            continue
        replacements.append(
            {
                "text": batch_number,
                "x": pos["x"],
                "y": pos["y"],
                "font_size": pos.get("font_size", 10),
            }
        )
    return replacements


def build_weight_replacement_text(original_text, total_weight_sum):
    if not original_text:
        return f"{total_weight_sum:,.3f}   /400.000    KG"

    match = re.match(r"^\s*([^/]+?)(\s*/\s*[\d.]+)(?:\s*(KG))?", original_text)
    if not match:
        return f"{total_weight_sum:,.3f}   /400.000    KG"

    right_side = match.group(2).split("/", 1)[1].strip()
    return f"{total_weight_sum:,.3f}   /{right_side}    KG"


def get_fixed_layout_positions(item_count):
    batch_positions = []
    for index in range(item_count):
        batch_positions.append(
            {
                "x": 19.8,
                "y": 471.21 + index * 14.5,
                "font_size": 10,
            }
        )

    weight_position = {"x": 394.0, "y": 171.96}
    return batch_positions, weight_position


def _normalize_company_text(text):
    if not text:
        return ""
    cleaned = str(text).strip()
    for suffix in ["装运单号:", "卸货点:", "工厂代码:", "Shipment No:", "Shipment No"]:
        if suffix in cleaned:
            cleaned = cleaned.split(suffix)[0].strip()
    return cleaned


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
        if "送货地址" in line or "Ship To" in line:
            if i + 1 < len(lines):
                company_line = _normalize_company_text(lines[i + 1])
                if len(company_line) <= 2:
                    continue
                if line.startswith("Ship To"):
                    english_name = company_line
                else:
                    chinese_name = company_line

    if not chinese_name and not english_name:
        for i, line in enumerate(lines):
            if "客户地址" in line or "开票地址" in line:
                if i + 1 < len(lines):
                    fallback_name = _normalize_company_text(lines[i + 1])
                    if len(fallback_name) > 2:
                        chinese_name = fallback_name
                        break

    if chinese_name:
        return {"chinese": chinese_name, "english": english_name}
    if english_name:
        return {"chinese": None, "english": english_name}
    return None


def find_contact_in_excel(company_name, excel_path):
    return find_contact_in_excels(company_name, [excel_path] if excel_path else [])


def find_contact_in_excels(company_name, excel_paths):
    if not company_name:
        return None

    chinese_name_pdf = _normalize_company_text(company_name.get("chinese"))
    english_name_pdf = _normalize_company_text(company_name.get("english"))

    for excel_path in excel_paths:
        if not excel_path or not os.path.exists(excel_path):
            continue

        df = pd.read_excel(excel_path)
        for _, row in df.iterrows():
            chinese_name_excel = _normalize_company_text(row.get("chinese_name"))
            english_name_excel = _normalize_company_text(row.get("english_name"))

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
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

    lines = all_text.split("\n")
    handling_units = []

    for i, line in enumerate(lines):
        if "搬运单元" in line or "Handling Unit" in line or "Top HU" in line:
            for j in range(1, 20):
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    if not next_line or "/" in next_line:
                        continue
                    matches = re.findall(r"\b\d+\b", next_line)
                    if len(matches) >= 2:
                        handling_units.append(matches[1])
                    elif j > 1:
                        break

    return handling_units
def _extract_total_package_count_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
            for line in _cluster_words_by_top(words):
                line_text = " ".join(word["text"] for word in line["words"])
                if "总包装数:" not in line_text and "总包装数" not in line_text:
                    continue
                for idx, word in enumerate(line["words"]):
                    if word["text"].startswith("总包装数"):
                        for next_word in line["words"][idx + 1:]:
                            if next_word["text"].isdigit():
                                return int(next_word["text"])
    return None




def _get_value_from_row(row, candidates):
    for column_name in candidates:
        if column_name in row and pd.notna(row[column_name]):
            value = str(row[column_name]).strip()
            if value and value.lower() != "nan":
                if value.endswith(".0") and value.replace(".", "", 1).isdigit():
                    value = value[:-2]
                return value
    return ""


def find_hu_info_in_excel(handling_units, excel_path):
    df = pd.read_excel(excel_path)

    hu_info_list = []
    total_weight_sum = 0.0

    for hu in handling_units:
        matched = df[df["Handling Unit"].astype(str).str.strip().eq(str(hu).strip())]
        if matched.empty:
            continue

        batch_number = ""
        total_weight = 0.0

        for _, row in matched.iterrows():
            if not batch_number:
                batch_number = _get_value_from_row(row, ["HU identification 2", "HU Identification 2"])

            try:
                total_weight += float(row["Total Weight"]) if pd.notna(row["Total Weight"]) else 0.0
            except (TypeError, ValueError):
                total_weight += 0.0

        hu_info_list.append(
            {
                "handling_unit": hu,
                "batch_number": batch_number,
                "hu_identification_2": batch_number,
                "total_weight": round(total_weight, 3),
            }
        )
        total_weight_sum += total_weight

    return {
        "hu_info_list": hu_info_list,
        "total_weight_sum": round(total_weight_sum, 3),
    }


def _cluster_words_by_top(words, tolerance=2.0):
    lines = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        for line in lines:
            if abs(line["top"] - word["top"]) <= tolerance:
                line["words"].append(word)
                line["top"] = min(line["top"], word["top"])
                line["bottom"] = max(line["bottom"], word["bottom"])
                break
        else:
            lines.append({"top": word["top"], "bottom": word["bottom"], "words": [word]})

    for line in lines:
        line["words"].sort(key=lambda item: item["x0"])

    return sorted(lines, key=lambda item: (item["top"], item["words"][0]["x0"]))


def _is_numeric_token(text):
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", text or ""))


def _is_hu_token(text):
    return bool(re.fullmatch(r"\d{6,}", text or ""))


def _normalize_weight_token(text):
    if not text:
        return ""

    value = str(text).strip().replace(" ", "")
    if not value:
        return ""

    if "," in value and "." in value:
        last_comma = value.rfind(",")
        last_dot = value.rfind(".")
        if last_comma > last_dot:
            integer_part = value[:last_comma].replace(".", "")
            decimal_part = value[last_comma + 1 :]
            return f"{integer_part}.{decimal_part}"
        integer_part = value[:last_dot].replace(",", "")
        decimal_part = value[last_dot + 1 :]
        return f"{integer_part}.{decimal_part}"

    if "," in value:
        left, right = value.split(",", 1)
        if right.isdigit():
            return f"{left.replace('.', '').replace(',', '')}.{right}"

    return value


def _format_weight_for_output(text):
    normalized = _normalize_weight_token(text)
    if not normalized:
        return ""

    if "." not in normalized:
        return normalized

    integer_part, decimal_part = normalized.split(".", 1)
    integer_part = integer_part.replace(",", "")
    if integer_part.isdigit() and len(integer_part) > 3:
        integer_part = f"{int(integer_part):,}"
    elif integer_part.isdigit():
        integer_part = str(int(integer_part))

    return f"{integer_part}.{decimal_part}"


def _format_weight_like_sample(sample_text, total_weight_sum):
    sample = str(sample_text or "")

    if "." in sample and "," in sample and sample.rfind(",") > sample.rfind("."):
        formatted = f"{total_weight_sum:,.3f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    if "," in sample and "." not in sample:
        return f"{total_weight_sum:.3f}".replace(".", ",")

    return f"{total_weight_sum:,.3f}"


def _is_same_weight_value(original_text, formatted_text):
    return _normalize_weight_token(original_text) == _normalize_weight_token(formatted_text)


def _get_company_font_info(page, company_name, is_english_company=False):
    page_words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
    candidates = []

    if company_name:
        if is_english_company:
            if company_name.get("english"):
                candidates.append(company_name["english"])
        else:
            if company_name.get("chinese"):
                candidates.append(company_name["chinese"])

    for target_text in candidates:
        for word in page_words:
            if target_text and target_text in word.get("text", ""):
                return _get_word_font_info(page, word, target_text)

    return "STSong-Light", 10.0


def _is_english_company_pdf(pdf_path, company_name=None):
    if company_name:
        chinese_name = _normalize_company_text(company_name.get("chinese"))
        english_name = _normalize_company_text(company_name.get("english"))
        if english_name and not chinese_name:
            return True
        if chinese_name and not english_name:
            return False

    with pdfplumber.open(pdf_path) as pdf:
        page_text = pdf.pages[0].extract_text() or ""

    normalized_text = page_text.lower()
    english_markers = (
        "ship to",
        "company address",
        "delivery note",
        "gross/net weight",
        "sold to:",
        "unloading point:",
    )
    chinese_markers = (
        "送货地址",
        "公司地址",
        "毛重/净重",
        "客户地址",
        "卸货点",
    )

    english_score = sum(marker in normalized_text for marker in english_markers)
    chinese_score = sum(marker in page_text for marker in chinese_markers)
    return english_score > chinese_score


def _get_word_font_info(page, target_word, target_text=None):
    word_chars = [
        char
        for char in page.chars
        if char["top"] >= target_word["top"] - 0.5
        and char["bottom"] <= target_word["bottom"] + 0.5
        and char["x0"] >= target_word["x0"] - 0.5
        and char["x1"] <= target_word["x1"] + 0.5
    ]

    if word_chars:
        font_name = _pick_font_from_chars(word_chars, target_text)
        font_size = float(word_chars[0].get("size") or target_word.get("height", 10))
    else:
        font_name = "STSong-Light"
        font_size = float(target_word.get("height", 10))

    return font_name, font_size


def _pick_font_from_chars(word_chars, target_text=None):
    font_names = [char.get("fontname") for char in word_chars if char.get("fontname")]
    if not font_names:
        return "STSong-Light"

    if target_text == "（" or target_text == "）":
        for font_name in font_names:
            if "NSimSun" in font_name or "SimSun" in font_name:
                return "NSimSun"
        return "NSimSun"

    for font_name in font_names:
        if "SimHei" in font_name:
            return "SimHei"

    for font_name in font_names:
        if "NSimSun" in font_name or "SimSun" in font_name:
            return "NSimSun"

    primary_font = font_names[0]
    if primary_font.startswith("CIDFont+F1"):
        return "SimHei"
    if primary_font.startswith("CIDFont+F2"):
        return "NSimSun"
    return primary_font


def _register_pdf_font(font_name):
    try:
        if font_name == "STSong-Light":
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            return "STSong-Light"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font_candidates = _SYSTEM_FONT_FILES.get(font_name, [Path(f"{font_name}.ttf")])
            for font_file in font_candidates:
                if not Path(font_file).exists():
                    continue
                if str(font_file).lower().endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(font_name, str(font_file), fontNumber=0))
                else:
                    pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
                return font_name
            return "STSong-Light"
        return font_name
    except Exception:
        # If the requested font is unavailable in the Linux container, fall back
        # to a Unicode CID font so Chinese text still renders correctly.
        return "STSong-Light"


def _find_batch_rows(page_words):
    rows = []
    header_y_threshold = None
    for line in _cluster_words_by_top(page_words):
        line_words = line["words"]
        line_text = " ".join(word["text"] for word in line_words)
        if "批次号" in line_text and ("搬运单元" in line_text or "Top HU" in line_text or "HU" in line_text):
            header_y_threshold = line["bottom"]
            continue

        if not any(word["text"] == "PC" for word in line_words) and header_y_threshold is None:
            continue

        batch_word = None
        hu_word = None
        for word in line_words:
            if not _is_numeric_token(word["text"]):
                continue
            if word["x0"] < 100 and batch_word is None:
                batch_word = word
            if word["x0"] >= 100 and _is_hu_token(word["text"]) and hu_word is None:
                hu_word = word

        if header_y_threshold is not None and line["top"] <= header_y_threshold:
            continue

        if batch_word and hu_word:
            rows.append({"batch_word": batch_word, "handling_unit": hu_word["text"].strip()})
    return rows


def _find_weight_word(page_words):
    for line in _cluster_words_by_top(page_words):
        line_words = line["words"]
        line_text = "".join(word["text"] for word in line_words)
        if "毛重/净重" not in line_text:
            continue

        for idx, word in enumerate(line_words):
            if "毛重/净重" not in word["text"]:
                continue

            next_words = line_words[idx + 1 : idx + 4]
            if not next_words:
                continue

            return {
                "gross": next_words[0] if len(next_words) > 0 else None,
                "net": next_words[1] if len(next_words) > 1 else None,
                "unit": next_words[2] if len(next_words) > 2 else None,
            }
    return None


def build_pdf_replacement_plan(input_pdf, hu_info, replace_batch_number=True):
    hu_info_list = hu_info.get("hu_info_list", [])
    hu_map = {
        str(item.get("handling_unit", "")).strip(): item
        for item in hu_info_list
        if item.get("handling_unit")
    }

    total_package_count = _extract_total_package_count_from_pdf(input_pdf)
    batch_replacements = []
    gross_weight_replacement = None

    with pdfplumber.open(input_pdf) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_words = page.extract_words(keep_blank_chars=False, use_text_flow=True)

            if replace_batch_number:
                for row in _find_batch_rows(page_words):
                    matched_info = hu_map.get(row["handling_unit"])
                    if not matched_info:
                        continue

                    font_name, font_size = _get_word_font_info(page, row["batch_word"])
                    batch_x = row["batch_word"]["x0"]
                    batch_y = row["batch_word"]["top"]
                    if batch_x < 100 and batch_y > 450:
                        batch_y -= 2
                    batch_replacements.append(
                        {
                            "page_index": page_index,
                            "text": matched_info.get("batch_number") or matched_info.get("hu_identification_2", ""),
                            "x": batch_x,
                            "y": batch_y,
                            "width": row["batch_word"]["x1"] - row["batch_word"]["x0"],
                            "height": row["batch_word"]["bottom"] - row["batch_word"]["top"],
                            "font_size": font_size,
                            "font_name": font_name,
                            "raw_width": row["batch_word"]["x1"] - row["batch_word"]["x0"],
                        }
                    )

            if page_index != 0 or gross_weight_replacement is not None:
                continue

            gross_weight_word = _find_weight_word(page_words)
            if not gross_weight_word:
                continue

            gross_word = gross_weight_word.get("gross")
            net_word = gross_weight_word.get("net")
            unit_word = gross_weight_word.get("unit")
            if not gross_word:
                gross_word = net_word
            if not gross_word:
                gross_word = unit_word
            if not gross_word:
                continue

            font_name, font_size = _get_word_font_info(page, gross_word)
            gross_weight_value = _format_weight_like_sample(gross_word["text"], hu_info.get("total_weight_sum", 0.0))
            if _is_same_weight_value(gross_word["text"], gross_weight_value):
                logger.info("重量相同，跳过替换")
                continue

            net_weight_value = net_word["text"].lstrip("/") if net_word else ""
            unit_text = unit_word["text"] if unit_word else "KG"

            if not net_weight_value:
                net_weight_value = "400.000"
            if not unit_text:
                unit_text = "KG"

            gross_weight_replacement = {
                "page_index": 0,
                "text": f"{gross_weight_value} /{net_weight_value} {unit_text}",
                "x": gross_word["x0"],
                "y": gross_word["top"] - 2,
                "width": (unit_word["x1"] if unit_word else gross_word["x1"]) - gross_word["x0"],
                "height": gross_word["bottom"] - gross_word["top"],
                "font_size": font_size,
                "font_name": font_name,
            }

    if total_package_count is not None and len(batch_replacements) != total_package_count:
        logger.warning(
            "搬运单元数量与总包装数不一致: got=%s expected=%s",
            len(batch_replacements),
            total_package_count,
        )

    return {
        "batch_replacements": batch_replacements,
        "gross_weight_replacement": gross_weight_replacement,
        "total_package_count": total_package_count,
    }


def update_pdf_with_hu_info(input_pdf, output_pdf, hu_info, replace_batch_number=True):
    replacement_plan = build_pdf_replacement_plan(input_pdf, hu_info, replace_batch_number=replace_batch_number)
    batch_replacements = replacement_plan["batch_replacements"]
    gross_weight_replacement = replacement_plan["gross_weight_replacement"]

    output = PdfWriter()

    with open(input_pdf, "rb") as input_stream:
        existing_pdf = PdfReader(input_stream)
        page_groups = {}
        for replacement in batch_replacements:
            page_groups.setdefault(replacement.get("page_index", 0), []).append(replacement)
        if gross_weight_replacement:
            page_groups.setdefault(gross_weight_replacement.get("page_index", 0), []).append(gross_weight_replacement)

        for page_index, page in enumerate(existing_pdf.pages):
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            page_replacements = page_groups.get(page_index, [])
            if not page_replacements:
                output.add_page(page)
                continue

            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))

            for replacement in page_replacements:
                font_name = _register_pdf_font(replacement.get("font_name", "STSong-Light"))
                font_size = replacement.get("font_size", 10)
                text_width = pdfmetrics.stringWidth(replacement["text"], font_name, font_size)
                x = replacement["x"]
                y = page_height - replacement["y"] - font_size
                raw_width = replacement.get("raw_width", replacement.get("width", 0))

                can.setFillColor(white)
                can.rect(x - 1, y - 2, max(text_width, raw_width) + 4, font_size + 5, fill=True, stroke=False)
                can.setFillColorRGB(0, 0, 0)
                can.setFont(font_name, font_size)
                can.drawString(x, y, replacement["text"])

            can.save()
            packet.seek(0)

            overlay_pdf = PdfReader(packet)
            page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

    with open(output_pdf, "wb") as output_stream:
        output.write(output_stream)


def add_contact_to_pdf(input_pdf, output_pdf, contact_info, is_english_company=False):
    with pdfplumber.open(input_pdf) as pdf:
        page = pdf.pages[0]
        page_width = page.width
        page_height = page.height
        company_name = extract_company_name_from_pdf(input_pdf)
        font_name, font_size = _get_company_font_info(page, company_name, is_english_company)

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    font_to_use = _register_pdf_font(font_name if not font_name.startswith("CIDFont+") else "STSong-Light")
    can.setFont(font_to_use, font_size)
    can.setFillColorRGB(0, 0, 0)

    y_position = 675
    x_position = 84

    if is_english_company:
        x_position += 18
        y_position -= 15
    else:
        x_position += 8

    if contact_info["contact"]:
        can.drawString(x_position, y_position, f"联系人: {contact_info['contact']}")
        y_position -= 15

    if contact_info["mobile"]:
        can.drawString(x_position, y_position, f"电话: {contact_info['mobile']}")

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
