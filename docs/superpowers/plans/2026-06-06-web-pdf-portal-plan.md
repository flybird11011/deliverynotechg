# Web PDF Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current PDF/Excel batch tool into a public web app that accepts Excel and PDF uploads, processes them as a job, and returns a downloadable output PDF.

**Architecture:** Keep the current PDF business logic as the core engine, but move the execution path from "scan the working directory" to "process one explicit job workspace". Add a small FastAPI web layer on top that handles uploads, job state, and downloads. Use a filesystem job directory plus SQLite metadata so the app can run cleanly on a public server without requiring a full database stack on day one.

**Tech Stack:** Python, FastAPI, Uvicorn, Jinja2 templates, `python-multipart`, `sqlite3`, existing `pdfplumber` + `reportlab` + `PyPDF2` pipeline, pytest.

---

### Task 1: Refactor the core pipeline into a job-oriented processor

**Files:**
- Modify: `src/deliverynotechg/pipeline.py`
- Create: `src/deliverynotechg/job_runner.py`
- Create: `tests/test_job_runner.py`

- [ ] **Step 1: Write the failing test**

Add a test that processes one explicit PDF job instead of scanning the current directory:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_job_runner.py::test_process_uploaded_pdf_job_creates_output -q
```

Expected: fail because `process_uploaded_pdf_job` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `src/deliverynotechg/job_runner.py` with a single public entry point:

```python
def process_uploaded_pdf_job(job_id, pdf_path, customer_excel_path, export_excel_paths, job_dir):
    ...
```

Implementation rules:
- Reuse `extract_company_name_from_pdf`, `find_contact_in_excel`, `extract_handling_units_from_pdf`, `_find_hu_info_from_exports`, `add_contact_to_pdf`, and `update_pdf_with_hu_info`.
- Stop scanning `os.listdir(".")` inside the job path.
- Write outputs under the provided `job_dir`.
- Return a dict with `job_id`, `status`, `output_pdf`, and `error_message`.

Then update `src/deliverynotechg/pipeline.py` so the CLI wrapper still works by:
- collecting PDFs from the current directory,
- creating a job dir for each file,
- calling `process_uploaded_pdf_job(...)`,
- moving the original PDF to `archive/` exactly as it does now.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/test_job_runner.py::test_process_uploaded_pdf_job_creates_output -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/deliverynotechg/job_runner.py src/deliverynotechg/pipeline.py tests/test_job_runner.py
git commit -m "refactor: add job-oriented PDF processor"
```

### Task 2: Add job storage, config, and upload validation

**Files:**
- Create: `src/deliverynotechg/web/config.py`
- Create: `src/deliverynotechg/web/store.py`
- Create: `src/deliverynotechg/web/schemas.py`
- Create: `tests/test_web_store.py`

- [ ] **Step 1: Write the failing test**

Add a persistence test that creates a job, updates its state, and reads it back:

```python
from src.deliverynotechg.web.store import SQLiteJobStore


def test_job_store_persists_status(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.db")
    job = store.create_job(original_pdf_name="input.pdf", original_excel_name="input.xlsx")

    store.update_status(job.job_id, "processing")
    loaded = store.get_job(job.job_id)

    assert loaded.job_id == job.job_id
    assert loaded.status == "processing"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_web_store.py::test_job_store_persists_status -q
```

Expected: fail because `SQLiteJobStore` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a small SQLite-backed store in `src/deliverynotechg/web/store.py` with these methods:

```python
class SQLiteJobStore:
    def __init__(self, db_path): ...
    def create_job(self, original_pdf_name, original_excel_name): ...
    def update_status(self, job_id, status, error_message=None, output_pdf=None): ...
    def get_job(self, job_id): ...
    def list_jobs(self, limit=20): ...
```

Add `src/deliverynotechg/web/config.py` for environment-driven settings:
- upload directory
- job retention hours
- max upload size
- API token

Add `src/deliverynotechg/web/schemas.py` for response models:
- `JobCreateResponse`
- `JobStatusResponse`
- `UploadResponse`

Validation rules to implement now:
- accept only `.pdf` and `.xlsx`
- reject empty uploads
- normalize filenames before saving
- create one directory per job id

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/test_web_store.py::test_job_store_persists_status -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/deliverynotechg/web/config.py src/deliverynotechg/web/store.py src/deliverynotechg/web/schemas.py tests/test_web_store.py
git commit -m "feat: add web job store and config"
```

### Task 3: Build the FastAPI app, upload endpoints, and result pages

**Files:**
- Create: `src/deliverynotechg/web/server.py`
- Create: `web/templates/index.html`
- Create: `web/templates/job.html`
- Create: `web/static/style.css`
- Create: `tests/test_web_api.py`

- [ ] **Step 1: Write the failing test**

Add an API test that uploads an Excel file and a PDF, then starts a job:

```python
from fastapi.testclient import TestClient
from src.deliverynotechg.web.server import app


def test_upload_and_process_job(client):
    with open("customer_combined.xlsx", "rb") as excel_fp, open("archive/ZSD_DELIVERY_NOTE_SF.pdf", "rb") as pdf_fp:
        resp = client.post(
            "/api/process",
            files={
                "excel": ("customer_combined.xlsx", excel_fp, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "pdf": ("input.pdf", pdf_fp, "application/pdf"),
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"queued", "processing", "done"}
    assert "job_id" in body
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_web_api.py::test_upload_and_process_job -q
```

Expected: fail because the FastAPI app and `/api/process` route do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `src/deliverynotechg/web/server.py` with:
- a `FastAPI()` app
- a home page route `GET /`
- upload/process route `POST /api/process`
- status route `GET /api/jobs/{job_id}`
- download route `GET /api/jobs/{job_id}/download`
- token auth for public access using an `X-API-Key` header

Route behavior:
- save uploads into the job directory created by `SQLiteJobStore`
- call `process_uploaded_pdf_job(...)` for the job
- update the store with `processing`, `done`, or `failed`
- render the HTML pages with Jinja2

Keep the UI deliberately simple:
- one upload form
- one job status panel
- one download button

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/test_web_api.py::test_upload_and_process_job -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/deliverynotechg/web/server.py web/templates/index.html web/templates/job.html web/static/style.css tests/test_web_api.py
git commit -m "feat: add FastAPI upload and job UI"
```

### Task 4: Add async processing, cleanup, and deployment artifacts

**Files:**
- Modify: `src/deliverynotechg/web/server.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `deploy/nginx.conf`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

Add a test that confirms long-running processing happens in the background and the API returns a job id immediately:

```python
def test_process_endpoint_returns_job_id_quickly(client):
    resp = client.post("/api/process", files={...})
    assert resp.status_code == 200
    assert resp.json()["job_id"]
```

If a background worker is not yet implemented, this test should fail or hang before the refactor.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_web_api.py::test_process_endpoint_returns_job_id_quickly -q
```

Expected: fail until background execution is in place.

- [ ] **Step 3: Write minimal implementation**

Update `src/deliverynotechg/web/server.py` to:
- queue processing in a background thread or FastAPI `BackgroundTasks`
- mark job status as `queued` before work starts
- mark job status as `processing` inside the worker
- add a periodic cleanup helper that deletes old job directories and stale SQLite rows

Add deployment files:
- `Dockerfile` that installs dependencies and launches `uvicorn`
- `docker-compose.yml` for local container testing
- `deploy/nginx.conf` for reverse proxying a public HTTPS site

Update `README.md` with:
- environment variables
- upload limits
- API token setup
- Docker run command
- production notes for Nginx and HTTPS

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/test_web_api.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/deliverynotechg/web/server.py Dockerfile docker-compose.yml deploy/nginx.conf README.md
git commit -m "feat: add web deployment and background jobs"
```

### Task 5: Final verification and packaging sanity check

**Files:**
- Modify: `README.md`
- Modify: `PDFContactTool.spec` only if the packaging story needs to keep the desktop EXE and the web app side-by-side

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest -q
```

Expected: all web tests and existing PDF tests pass.

- [ ] **Step 2: Run the web app locally**

Run:

```bash
uvicorn src.deliverynotechg.web.server:app --reload
```

Expected:
- home page loads
- upload form works
- job status updates
- output PDF downloads successfully

- [ ] **Step 3: Smoke-test one real job**

Upload:
- `customer_combined.xlsx`
- one real PDF from `archive/`

Expected:
- output file appears in the job workspace
- the generated PDF opens correctly
- contact, batch number, and weight replacements still look right

- [ ] **Step 4: Commit**

```bash
git add README.md PDFContactTool.spec
git commit -m "docs: finish web portal verification"
```

---

**Coverage check**
- The current PDF processing logic is preserved and reused in Task 1.
- Public upload, job state, and downloads are covered in Tasks 2 and 3.
- Authentication, cleanup, and deployment are covered in Task 4.
- End-to-end verification is covered in Task 5.

