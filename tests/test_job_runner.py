from pathlib import Path

from src.deliverynotechg.job_runner import process_uploaded_pdf_job


def test_process_uploaded_pdf_job_creates_output(tmp_path):
    job_dir = tmp_path / "job-001"
    job_dir.mkdir()

    result = process_uploaded_pdf_job(
        job_id="job-001",
        pdf_path="archive/ZSD_DELIVERY_NOTE_SF.pdf",
        customer_excel_path="customer_combined.xlsx",
        export_excel_paths=["EXPORT_20260604132137-hu.xlsx"],
        job_dir=str(job_dir),
    )

    assert result["status"] == "done"
    assert Path(result["output_pdf"]).exists()
    assert Path(result["output_pdf"]).name.endswith("_with_contact.pdf")
