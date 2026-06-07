import os
import shutil
import sys
import time
from pathlib import Path

from .customer_excel import create_customer_excel
from .job_runner import _find_hu_info_from_exports, process_uploaded_pdf_job
from .pdf_contact import (
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_contact_in_excels,
)


def _configure_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _find_export_excel_candidates(directory="."):
    candidates = []
    for filename in os.listdir(directory):
        lower_name = filename.lower()
        if lower_name.startswith("export_") and lower_name.endswith(".xlsx"):
            candidates.append(os.path.join(directory, filename))
    return sorted(candidates)


def process_pdf_files():
    customer_excel_paths = ["customer_combined.xlsx", "customer_combined-ge.xlsx"]
    hu_excel_paths = _find_export_excel_candidates(".")

    os.makedirs("output", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("当前目录没有 PDF 文件")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件")
    time_suffix = time.strftime("%H%M")

    for pdf_filename in pdf_files:
        pdf_path = pdf_filename
        print(f"\n处理文件: {pdf_path}")

        try:
            company_name = extract_company_name_from_pdf(pdf_path)
            if company_name:
                if company_name.get("chinese"):
                    print(f"从PDF提取的中文公司名: {company_name['chinese']}")
                if company_name.get("english"):
                    print(f"从PDF提取的英文公司名: {company_name['english']}")
            else:
                print("未从 PDF 提取到公司名称")

            contact_info = find_contact_in_excels(company_name, customer_excel_paths)
            handling_units = extract_handling_units_from_pdf(pdf_path)
            print(f"从PDF提取的搬运单元号: {handling_units}")

            hu_info = None
            if handling_units and hu_excel_paths:
                hu_info, matched_hu_excel = _find_hu_info_from_exports(handling_units, hu_excel_paths)
                if hu_info:
                    print(f"匹配成功的HU Excel: {os.path.basename(matched_hu_excel)}")
                    print(f"匹配到的 HU 记录数 {len(hu_info.get('hu_info_list', []))}")
                    print(f"Total Weight 求和: {hu_info.get('total_weight_sum', 0.0)}")
                else:
                    print("未找到能完整匹配当前搬运单元号的 EXPORT_*.xlsx 文件")
            elif handling_units and not hu_excel_paths:
                print("未找到任何 EXPORT_*.xlsx 文件")

            name_without_ext = os.path.splitext(pdf_filename)[0]
            output_dir = Path("output")
            job_dir = output_dir / f"{name_without_ext}_{time_suffix}"
            job_dir.mkdir(parents=True, exist_ok=True)

            job_result = process_uploaded_pdf_job(
                job_id=name_without_ext,
                pdf_path=pdf_path,
                customer_excel_paths=customer_excel_paths,
                export_excel_paths=hu_excel_paths,
                job_dir=str(job_dir),
            )

            if job_result["status"] == "done":
                print(f"已保存新文件: {job_result['output_pdf']}")
            else:
                print(f"处理失败: {job_result['error_message']}")

            archive_path = f"archive/{name_without_ext}_{time_suffix}.pdf"
            max_retries = 3
            for i in range(max_retries):
                try:
                    shutil.move(pdf_path, archive_path)
                    print(f"已将原PDF移动到 {archive_path}")
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                        print(f"文件被占用，重试中 ({i + 1}/{max_retries})...")
                    else:
                        print(f"无法移动文件 {pdf_path}，可能被其他程序占用")
        except Exception as e:
            print(f"处理文件 {pdf_path} 时发生错误: {str(e)}")


def main():
    _configure_stdout()

    excel_file = "customer_combined.xlsx"

    if not os.path.exists(excel_file):
        print(f"{excel_file} 不存在，正在创建...")
        create_customer_excel()
        print(f"{excel_file} 创建完成")
    else:
        print(f"{excel_file} 已存在，跳过创建")

    print("\n正在处理 PDF 文件...")
    process_pdf_files()
    print("\n完成")
