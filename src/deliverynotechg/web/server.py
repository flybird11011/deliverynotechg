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
config.base_dir.mkdir(parents=True, exist_ok=True)
config.excel_dir.mkdir(parents=True, exist_ok=True)
config.upload_dir.mkdir(parents=True, exist_ok=True)


def _list_excel_files():
    return sorted(
        [path for path in config.excel_dir.glob("*.xlsx") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _get_customer_excel_path():
    customer_path = config.excel_dir / "customer_combined.xlsx"
    if customer_path.exists():
        return customer_path

    excel_files = _list_excel_files()
    for path in excel_files:
        if not path.name.lower().startswith("export_"):
            return path

    return None


def _get_export_excel_paths():
    return [
        path
        for path in _list_excel_files()
        if path.name.lower().startswith("export_")
    ]


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


def _run_job(job_id: str, pdf_path: Path, excel_path: Path, export_excel_paths: list[Path], job_dir: Path):
    store.update_status(job_id, "processing")
    result = process_uploaded_pdf_job(
        job_id=job_id,
        pdf_path=str(pdf_path),
        customer_excel_path=str(excel_path),
        export_excel_paths=[str(path) for path in export_excel_paths],
        job_dir=str(job_dir),
    )
    if result["status"] == "done":
        store.update_status(job_id, "done", output_pdf=result["output_pdf"])
    else:
        store.update_status(job_id, "failed", error_message=result["error_message"])


def _queue_pdf_job(pdf: UploadFile, customer_excel_path: Path | None, export_excel_paths: list[Path]):
    original_excel_name = customer_excel_path.name if customer_excel_path else ""
    if not original_excel_name and export_excel_paths:
        original_excel_name = ", ".join(path.name for path in export_excel_paths)
    if not original_excel_name:
        original_excel_name = "workspace"

    job = store.create_job(original_pdf_name=pdf.filename, original_excel_name=original_excel_name)
    job_dir = config.upload_dir / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = _save_upload(pdf, job_dir / "input.pdf")
    excel_path = customer_excel_path if customer_excel_path else Path("customer_combined.xlsx")
    worker = threading.Thread(
        target=_run_job,
        args=(job.job_id, pdf_path, excel_path, export_excel_paths, job_dir),
        daemon=True,
    )
    worker.start()

    return {
        "job_id": job.job_id,
        "status": "queued",
        "output_pdf": "",
        "error_message": "",
        "download_url": f"/api/jobs/{job.job_id}/download",
        "original_pdf_name": pdf.filename,
        "original_excel_name": original_excel_name,
    }


def _cleanup_loop():
    while True:
        store.cleanup_expired_jobs(
            config.upload_dir,
            retention_hours=config.job_retention_hours,
            keep_last_excels=2,
        )
        store.cleanup_uploaded_excels(config.excel_dir, keep_last=2)
        time.sleep(config.cleanup_interval_seconds)


cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
cleanup_thread.start()


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
      <body>
        <h1>Delivery Note PDF Tool</h1>
        <p><strong>提示:</strong> 本程序不保存数据信息，文件会在 1 小时内自动删除。</p>
        <p><strong>Notice:</strong> This program does not keep your data. Files will be deleted automatically within 1 hour.</p>
        <p>Excel 和 PDF 分开处理。先上传 Excel 到工作目录，再上传 PDF 生成结果。</p>
        <form id="excelForm">
          <h2>Upload Excel Files</h2>
          <div><label>API Key <input type="password" id="apiKey" /></label></div>
          <div><label>Excel files <input type="file" name="excels" accept=".xlsx" multiple /></label></div>
          <button type="button" id="saveExcelBtn">Save Excel Files</button>
        </form>
        <hr />
        <form id="pdfForm">
          <h2>Process PDF Files</h2>
          <div><label>PDF files <input type="file" name="pdfs" accept=".pdf" multiple /></label></div>
          <button type="button" id="processPdfBtn">Process PDF</button>
        </form>
        <hr />
        <div>
          <h2>Excel files in workspace</h2>
          <pre id="excelList">Loading...</pre>
        </div>
        <hr />
        <div>
          <h2>Job status</h2>
          <pre id="jobStatus">No job started yet.</pre>
          <div id="jobLinks"></div>
        </div>
        <script>
          const apiKeyInput = document.getElementById('apiKey');
          const excelForm = document.getElementById('excelForm');
          const pdfForm = document.getElementById('pdfForm');
          const saveExcelBtn = document.getElementById('saveExcelBtn');
          const processPdfBtn = document.getElementById('processPdfBtn');
          const excelList = document.getElementById('excelList');
          const jobStatus = document.getElementById('jobStatus');
          const jobLinks = document.getElementById('jobLinks');
          let currentJobIds = [];

          async function refreshExcelList() {
            const resp = await fetch('/api/excels', {
              headers: { 'X-API-Key': apiKeyInput.value },
            });
            const data = await resp.json();
            const files = data.files || [];
            excelList.textContent = files.length ? files.join('\\n') : '(no excel files uploaded)';
          }

          saveExcelBtn.addEventListener('click', async () => {
            const data = new FormData();
            const files = excelForm.querySelector('input[name="excels"]').files;
            for (const file of files) {
              data.append('excels', file);
            }
            const resp = await fetch('/api/excels', {
              method: 'POST',
              headers: { 'X-API-Key': apiKeyInput.value },
              body: data,
            });
            if (!resp.ok) {
              alert(await resp.text());
              return;
            }
            await refreshExcelList();
            alert('Excel files saved');
          });

          async function loadJob(jobId) {
            const resp = await fetch(`/api/jobs/${jobId}`, {
              headers: { 'X-API-Key': apiKeyInput.value },
            });
            if (!resp.ok) {
              return null;
            }
            return await resp.json();
          }

          function renderJobLinks(jobs) {
            if (!jobs.length) {
              jobLinks.innerHTML = '';
              return;
            }
            jobLinks.innerHTML = jobs.map((job) => {
              const download = job.status === 'done' && job.output_pdf
                ? `<a href="/api/jobs/${job.job_id}/download" target="_blank" rel="noopener">Download ${job.original_pdf_name}</a>`
                : '';
              return `<div style="margin: 0.5rem 0;">
                <div><strong>${job.job_id}</strong> - ${job.status} - ${job.original_pdf_name}</div>
                ${download}
              </div>`;
            }).join('');
          }

          async function refreshAllJobs() {
            if (!currentJobIds.length) {
              return true;
            }
            const jobs = [];
            let allFinished = true;
            for (const jobId of currentJobIds) {
              const data = await loadJob(jobId);
              if (!data) {
                allFinished = false;
                continue;
              }
              jobs.push(data);
              if (data.status !== 'done' && data.status !== 'failed') {
                allFinished = false;
              }
            }
            jobStatus.textContent = JSON.stringify(jobs, null, 2);
            renderJobLinks(jobs);
            return allFinished;
          }

          function schedulePolling() {
            const poll = async () => {
              if (!currentJobIds.length) {
                return;
              }
              const done = await refreshAllJobs();
              if (!done) {
                setTimeout(poll, 2000);
              }
            };
            setTimeout(poll, 1000);
          }

          processPdfBtn.addEventListener('click', async () => {
            const pdfInput = pdfForm.querySelector('input[name="pdfs"]');
            if (!pdfInput.files.length) {
              alert('Please choose one or more PDF files first');
              return;
            }
            const data = new FormData();
            for (const file of pdfInput.files) {
              data.append('pdfs', file);
            }
            const resp = await fetch('/api/process', {
              method: 'POST',
              headers: { 'X-API-Key': apiKeyInput.value },
              body: data,
            });
            if (!resp.ok) {
              alert(await resp.text());
              return;
            }
            const result = await resp.json();
            const jobs = result.jobs || [];
            currentJobIds = jobs.map((job) => job.job_id);
            jobStatus.textContent = JSON.stringify(jobs, null, 2);
            renderJobLinks(jobs);
            alert(`Queued ${jobs.length} PDF job(s)`);
            schedulePolling();
          });

          refreshExcelList().catch(() => {
            excelList.textContent = '(failed to load excel list)';
          });
        </script>
      </body>
    </html>
    """


@app.get("/api/excels")
async def list_excels(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _require_api_key(x_api_key)
    files = _list_excel_files()
    customer_path = _get_customer_excel_path()
    return {
        "files": [path.name for path in files],
        "customer_excel": customer_path.name if customer_path else "",
    }


@app.post("/api/excels")
async def upload_excels(
    excels: list[UploadFile] = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_api_key(x_api_key)
    if not excels:
        raise HTTPException(status_code=400, detail="At least one Excel file is required")

    saved_files = []
    for excel in excels:
        _validate_upload(excel, ".xlsx")
        _validate_upload_size(excel)
        saved_path = _save_upload(excel, config.excel_dir / excel.filename)
        saved_files.append(saved_path.name)

    return {
        "status": "ok",
        "saved_files": saved_files,
        "files": [path.name for path in _list_excel_files()],
    }


@app.post("/api/process")
async def process_job(
    pdfs: list[UploadFile] | None = File(default=None),
    pdf: UploadFile | None = File(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_api_key(x_api_key)
    uploads = list(pdfs or [])
    if pdf is not None:
        uploads.append(pdf)

    if not uploads:
        raise HTTPException(status_code=400, detail="At least one PDF file is required")

    for upload in uploads:
        _validate_upload(upload, ".pdf")
        _validate_upload_size(upload)

    customer_excel_path = _get_customer_excel_path()
    export_excel_paths = _get_export_excel_paths()
    jobs = [_queue_pdf_job(upload, customer_excel_path, export_excel_paths) for upload in uploads]

    return {
        "jobs": jobs,
        "customer_excel": customer_excel_path.name if customer_excel_path else "",
        "export_excels": [path.name for path in export_excel_paths],
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
