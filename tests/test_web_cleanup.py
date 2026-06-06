from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.deliverynotechg.web.store import SQLiteJobStore


def test_cleanup_keeps_recent_two_and_stock_excels(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.db")
    job_dir = tmp_path / "uploads"
    job_dir.mkdir()

    files = [
        job_dir / "EXPORT_20260101.xlsx",
        job_dir / "EXPORT_20260102.xlsx",
        job_dir / "EXPORT_stock_20260103.xlsx",
        job_dir / "EXPORT_20260104.xlsx",
        job_dir / "EXPORT_20260105.xlsx",
    ]
    for index, file_path in enumerate(files):
        file_path.write_text("data", encoding="utf-8")
        file_path.touch()

    removed = store.cleanup_uploaded_excels(job_dir, keep_last=2)

    remaining = sorted(p.name for p in job_dir.glob("*.xlsx"))
    assert "EXPORT_stock_20260103.xlsx" in remaining
    assert "EXPORT_20260105.xlsx" in remaining
    assert "EXPORT_20260104.xlsx" in remaining
    assert "EXPORT_20260101.xlsx" not in remaining
    assert "EXPORT_20260102.xlsx" not in remaining
    assert all(Path(path).suffix == ".xlsx" for path in removed)


def test_cleanup_expired_jobs_removes_old_job_dirs(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.db")
    job = store.create_job("a.pdf", "b.xlsx")
    job_dir = tmp_path / "uploads" / job.job_id
    job_dir.mkdir(parents=True)
    (job_dir / "input.xlsx").write_text("x", encoding="utf-8")
    (job_dir / "input.pdf").write_text("y", encoding="utf-8")

    old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    with store._connect() as conn:
        conn.execute("UPDATE jobs SET created_at = ?, updated_at = ? WHERE job_id = ?", (old_time, old_time, job.job_id))
        conn.commit()

    result = store.cleanup_expired_jobs(tmp_path / "uploads", retention_hours=24)

    assert job.job_id in result["jobs"]
    assert not job_dir.exists()
    assert result["excels"] == []
