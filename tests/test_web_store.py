from src.deliverynotechg.web.store import SQLiteJobStore


def test_job_store_persists_status(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.db")
    job = store.create_job(original_pdf_name="input.pdf", original_excel_name="input.xlsx")

    store.update_status(job.job_id, "processing")
    loaded = store.get_job(job.job_id)

    assert loaded.job_id == job.job_id
    assert loaded.status == "processing"
