import shutil
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ..job_runner import process_uploaded_pdf_job
from .config import CONFIG
from .store import SQLiteJobStore


app = FastAPI()
config = CONFIG
store = SQLiteJobStore(config.db_path)


def _save_upload(upload: UploadFile, target_path: Path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return target_path


def _validate_upload(upload: UploadFile, expected_suffix: str):
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not upload.filename.lower().endswith(expected_suffix):
        raise HTTPException(status_code=400, detail=f"Only {expected_suffix} files are allowed")


def _validate_upload_size(upload: UploadFile):
    current_pos = upload.file.tell()
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(current_pos)

    if size <= 0:
        raise HTTPException(status_code=400, detail="Empty file is not allowed")
    if size > config.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")


def _require_api_key(x_api_key: str | None):
    if not config.api_token:
        return
    if x_api_key != config.api_token:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _run_job(job_id: str, pdf_path: Path, excel_path: Path, job_dir: Path):
    store.update_status(job_id, "processing")
    result = process_uploaded_pdf_job(
        job_id=job_id,
        pdf_path=str(pdf_path),
        customer_excel_path=str(excel_path),
        export_excel_paths=[],
        job_dir=str(job_dir),
    )
    if result["status"] == "done":
        store.update_status(job_id, "done", output_pdf=result["output_pdf"])
    else:
        store.update_status(job_id, "failed", error_message=result["error_message"])


def _cleanup_loop():
    while True:
        store.cleanup_expired_jobs(
            config.upload_dir,
            retention_hours=config.job_retention_hours,
            keep_last_excels=2,
        )
        time.sleep(config.cleanup_interval_seconds)


cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
cleanup_thread.start()


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
      <body>
        <h1>Delivery Note PDF Tool</h1>
        <form id="uploadForm">
          <div><label>API Key <input type="password" id="apiKey" /></label></div>
          <div><label>Excel <input type="file" name="excel" accept=".xlsx" /></label></div>
          <div><label>PDF <input type="file" name="pdf" accept=".pdf" /></label></div>
          <button type="submit">Process</button>
        </form>
        <script>
          const form = document.getElementById('uploadForm');
          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = new FormData();
            data.append('excel', form.querySelector('input[name="excel"]').files[0]);
            data.append('pdf', form.querySelector('input[name="pdf"]').files[0]);
            const resp = await fetch('/api/process', {
              method: 'POST',
              headers: { 'X-API-Key': document.getElementById('apiKey').value },
              body: data,
            });
            alert(await resp.text());
          });
        </script>
      </body>
    </html>
    """


@app.post("/api/process")
async def process_job(
    excel: UploadFile = File(...),
    pdf: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_api_key(x_api_key)
    _validate_upload(excel, ".xlsx")
    _validate_upload(pdf, ".pdf")
    _validate_upload_size(excel)
    _validate_upload_size(pdf)

    job = store.create_job(original_pdf_name=pdf.filename, original_excel_name=excel.filename)
    job_dir = config.upload_dir / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    excel_path = _save_upload(excel, job_dir / "input.xlsx")
    pdf_path = _save_upload(pdf, job_dir / "input.pdf")

    worker = threading.Thread(target=_run_job, args=(job.job_id, pdf_path, excel_path, job_dir), daemon=True)
    worker.start()

    return {
        "job_id": job.job_id,
        "status": "queued",
        "output_pdf": "",
        "error_message": "",
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _require_api_key(x_api_key)
    job = store.get_job(job_id)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "error_message": job.error_message,
        "output_pdf": job.output_pdf,
        "original_pdf_name": job.original_pdf_name,
        "original_excel_name": job.original_excel_name,
    }


@app.get("/api/jobs/{job_id}/download")
async def download_job_pdf(job_id: str, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _require_api_key(x_api_key)
    job = store.get_job(job_id)
    if not job.output_pdf:
        raise HTTPException(status_code=404, detail="Output not ready")
    output_path = Path(job.output_pdf)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing")
    return FileResponse(path=str(output_path), filename=output_path.name, media_type="application/pdf")
