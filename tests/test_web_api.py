import time

import pytest
from fastapi.testclient import TestClient

from src.deliverynotechg.web.server import app


def test_index_page_loads():
    client = TestClient(app)
    resp = client.get("/")

    assert resp.status_code == 200
    assert "Delivery Note PDF Tool" in resp.text
    assert 'id="apiKey"' in resp.text
    assert "Save Excel Files" in resp.text
    assert "Process PDF" in resp.text


def test_process_job_returns_job_id():
    client = TestClient(app)
    with open("archive/ZSD_DELIVERY_NOTE_SF.pdf", "rb") as pdf_fp:
        resp = client.post(
            "/api/process",
            files={
                "pdf": ("input.pdf", pdf_fp, "application/pdf"),
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["jobs"]
    assert body["jobs"][0]["job_id"]
    assert body["jobs"][0]["status"] == "queued"

    job_id = body["jobs"][0]["job_id"]
    deadline = time.time() + 30
    while time.time() < deadline:
        status = client.get(f"/api/jobs/{job_id}")
        assert status.status_code == 200
        if status.json()["status"] == "done":
            break
        time.sleep(0.2)
    else:
        pytest.fail("job did not finish in time")

    download = client.get(f"/api/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")


def test_process_job_accepts_multiple_pdfs():
    client = TestClient(app)
    with open("archive/ZSD_DELIVERY_NOTE_SF.pdf", "rb") as pdf_fp:
        resp = client.post(
            "/api/process",
            files=[
                ("pdfs", ("input-1.pdf", pdf_fp, "application/pdf")),
                ("pdfs", ("input-2.pdf", pdf_fp, "application/pdf")),
            ],
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["jobs"]) == 2
    assert body["jobs"][0]["status"] == "queued"
    assert body["jobs"][1]["status"] == "queued"
    assert body["jobs"][0]["download_url"].endswith("/download")
    assert body["jobs"][1]["download_url"].endswith("/download")


def test_process_job_accepts_replace_batch_number_flag():
    client = TestClient(app)
    with open("archive/ZSD_DELIVERY_NOTE_SF.pdf", "rb") as pdf_fp:
        resp = client.post(
            "/api/process",
            data={"replace_batch_number": "false"},
            files={
                "pdf": ("input.pdf", pdf_fp, "application/pdf"),
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["jobs"][0]["status"] == "queued"
    assert body["replace_batch_number"] is False


def test_upload_excels_and_list_files(tmp_path, monkeypatch):
    from src.deliverynotechg.web import server

    monkeypatch.setattr(
        server,
        "config",
        type(server.config)(
            base_dir=tmp_path / "web_data",
            excel_dir=tmp_path / "web_data" / "excels",
            db_path=tmp_path / "web_data" / "jobs.db",
            upload_dir=tmp_path / "web_data" / "uploads",
            max_upload_size_mb=server.config.max_upload_size_mb,
            job_retention_hours=server.config.job_retention_hours,
            cleanup_interval_seconds=server.config.cleanup_interval_seconds,
            api_token=server.config.api_token,
        ),
    )

    client = TestClient(app)
    resp = client.post(
        "/api/excels",
        files={
            "excels": (
                "customer_combined.xlsx",
                open("customer_combined.xlsx", "rb"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "customer_combined.xlsx" in body["saved_files"]

    listing = client.get("/api/excels")
    assert listing.status_code == 200
    assert "customer_combined.xlsx" in listing.json()["files"]


def test_rejects_empty_uploads():
    client = TestClient(app)
    resp = client.post(
        "/api/process",
        files={
            "pdf": ("empty.pdf", b"", "application/pdf"),
        },
    )

    assert resp.status_code == 400
    assert "Empty file" in resp.json()["detail"]


def test_rejects_large_uploads(monkeypatch):
    from src.deliverynotechg.web import server

    monkeypatch.setattr(server, "config", type(server.config)(
        base_dir=server.config.base_dir,
        db_path=server.config.db_path,
        upload_dir=server.config.upload_dir,
        max_upload_size_mb=0,
        job_retention_hours=server.config.job_retention_hours,
        api_token=server.config.api_token,
    ))

    client = TestClient(app)
    resp = client.post(
        "/api/process",
        files={
            "pdf": ("input.pdf", b"1234", "application/pdf"),
        },
    )

    assert resp.status_code == 413
    assert "File too large" in resp.json()["detail"]


def test_requires_api_key_when_configured(monkeypatch):
    from src.deliverynotechg.web import server

    monkeypatch.setattr(server, "config", type(server.config)(
        base_dir=server.config.base_dir,
        db_path=server.config.db_path,
        upload_dir=server.config.upload_dir,
        max_upload_size_mb=server.config.max_upload_size_mb,
        job_retention_hours=server.config.job_retention_hours,
        api_token="secret-token",
    ))

    client = TestClient(app)
    resp = client.get("/api/jobs/any")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid API key"
