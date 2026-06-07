import os
import shutil
from pathlib import Path

from .pdf_contact import (
    add_contact_to_pdf,
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_contact_in_excel,
    find_hu_info_in_excel,
    _is_english_company_pdf,
    update_pdf_with_hu_info,
)


def _find_hu_info_from_exports(handling_units, export_excel_paths):
    if not handling_units:
        return None, None

    expected_units = {str(unit).strip() for unit in handling_units if str(unit).strip()}

    for excel_path in export_excel_paths:
        if not os.path.exists(excel_path):
            continue

        hu_info = find_hu_info_in_excel(handling_units, excel_path)
        matched_units = {
            str(item.get("handling_unit", "")).strip()
            for item in hu_info.get("hu_info_list", [])
            if item.get("handling_unit")
        }

        if matched_units and matched_units == expected_units:
            return hu_info, excel_path

    return None, None


def process_uploaded_pdf_job(
    job_id,
    pdf_path,
    customer_excel_path,
    export_excel_paths,
    job_dir,
):
    job_dir_path = Path(job_dir)
    job_dir_path.mkdir(parents=True, exist_ok=True)

    result = {
        "job_id": job_id,
        "status": "failed",
        "output_pdf": "",
        "error_message": "",
    }

    try:
        company_name = extract_company_name_from_pdf(pdf_path)
        contact_info = None
        if customer_excel_path and os.path.exists(customer_excel_path):
            contact_info = find_contact_in_excel(company_name, customer_excel_path)
        handling_units = extract_handling_units_from_pdf(pdf_path)
        hu_info, _ = _find_hu_info_from_exports(handling_units, export_excel_paths)

        output_pdf = job_dir_path / f"{Path(pdf_path).stem}_with_contact.pdf"
        temp_pdf = job_dir_path / f"{Path(pdf_path).stem}_temp.pdf"

        if contact_info:
            is_english_company = _is_english_company_pdf(pdf_path, company_name)
            add_contact_to_pdf(pdf_path, str(temp_pdf), contact_info, is_english_company)
        else:
            shutil.copy(pdf_path, temp_pdf)

        if hu_info:
            update_pdf_with_hu_info(str(temp_pdf), str(output_pdf), hu_info)
            if temp_pdf.exists():
                temp_pdf.unlink()
        else:
            temp_pdf.replace(output_pdf)

        result["status"] = "done"
        result["output_pdf"] = str(output_pdf)
        return result
    except Exception as exc:
        result["error_message"] = str(exc)
        return result
