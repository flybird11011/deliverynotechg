import os
import shutil
import sys
import time
from pathlib import Path

from .customer_excel import create_customer_excel
from .job_runner import _find_hu_info_from_exports, process_uploaded_pdf_job


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
    excel_path = "customer_combined.xlsx"
    hu_excel_paths = _find_export_excel_candidates(".")

    os.makedirs("output", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("褰撳墠鐩綍娌℃湁 PDF 鏂囦欢")
        return

    print(f"鎵惧埌 {len(pdf_files)} 涓?PDF 鏂囦欢")
    time_suffix = time.strftime("%H%M")

    for pdf_filename in pdf_files:
        pdf_path = pdf_filename
        print(f"\n澶勭悊鏂囦欢: {pdf_path}")

        try:
            from .pdf_contact import extract_company_name_from_pdf, extract_handling_units_from_pdf, find_contact_in_excel

            company_name = extract_company_name_from_pdf(pdf_path)
            if company_name:
                if company_name.get("chinese"):
                    print(f"浠?PDF 鎻愬彇鐨勪腑鏂囧叕鍙稿悕: {company_name['chinese']}")
                if company_name.get("english"):
                    print(f"浠?PDF 鎻愬彇鐨勮嫳鏂囧叕鍙稿悕: {company_name['english']}")
            else:
                print("鏈粠 PDF 鎻愬彇鍒板叕鍙稿悕绉?")

            contact_info = find_contact_in_excel(company_name, excel_path)
            handling_units = extract_handling_units_from_pdf(pdf_path)
            print(f"浠?PDF 鎻愬彇鐨勬惉杩愬崟鍏冨彿: {handling_units}")

            hu_info = None
            if handling_units and hu_excel_paths:
                hu_info, matched_hu_excel = _find_hu_info_from_exports(handling_units, hu_excel_paths)
                if hu_info:
                    print(f"鍖归厤鎴愬姛鐨?HU Excel: {os.path.basename(matched_hu_excel)}")
                    print(f"鍖归厤鍒扮殑 HU 璁板綍鏁? {len(hu_info.get('hu_info_list', []))}")
                    print(f"Total Weight 姹傚拰: {hu_info.get('total_weight_sum', 0.0)}")
                else:
                    print("鏈壘鍒拌兘瀹屾暣鍖归厤褰撳墠鎼繍鍗曞厓鍙风殑 EXPORT_*.xlsx 鏂囦欢")
            elif handling_units and not hu_excel_paths:
                print("鏈壘鍒颁换浣?EXPORT_*.xlsx 鏂囦欢")

            name_without_ext = os.path.splitext(pdf_filename)[0]
            output_dir = Path("output")
            job_dir = output_dir / f"{name_without_ext}_{time_suffix}"
            job_dir.mkdir(parents=True, exist_ok=True)

            job_result = process_uploaded_pdf_job(
                job_id=name_without_ext,
                pdf_path=pdf_path,
                customer_excel_path=excel_path,
                export_excel_paths=hu_excel_paths,
                job_dir=str(job_dir),
            )

            if job_result["status"] == "done":
                print(f"宸蹭繚瀛樻柊鏂囦欢: {job_result['output_pdf']}")
            else:
                print(f"澶勭悊澶辫触: {job_result['error_message']}")

            archive_path = f"archive/{name_without_ext}_{time_suffix}.pdf"
            max_retries = 3
            for i in range(max_retries):
                try:
                    shutil.move(pdf_path, archive_path)
                    print(f"宸插皢鍘?PDF 绉诲姩鍒? {archive_path}")
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                        print(f"鏂囦欢琚崰鐢紝閲嶈瘯涓?({i + 1}/{max_retries})...")
                    else:
                        print(f"鏃犳硶绉诲姩鏂囦欢 {pdf_path}锛屽彲鑳借鍏朵粬绋嬪簭鍗犵敤")
        except Exception as e:
            print(f"澶勭悊鏂囦欢 {pdf_path} 鏃跺彂鐢熼敊璇? {str(e)}")


def main():
    _configure_stdout()

    excel_file = "customer_combined.xlsx"

    if not os.path.exists(excel_file):
        print(f"{excel_file} 涓嶅瓨鍦紝姝ｅ湪鍒涘缓...")
        create_customer_excel()
        print(f"{excel_file} 鍒涘缓瀹屾垚")
    else:
        print(f"{excel_file} 宸插瓨鍦紝璺宠繃鍒涘缓")

    print("\n姝ｅ湪澶勭悊 PDF 鏂囦欢...")
    process_pdf_files()
    print("\n瀹屾垚")
