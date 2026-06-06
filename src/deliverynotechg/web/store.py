import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass
class JobRecord:
    job_id: str
    original_pdf_name: str
    original_excel_name: str
    status: str
    error_message: str | None
    output_pdf: str | None
    created_at: str
    updated_at: str


class SQLiteJobStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    original_pdf_name TEXT NOT NULL,
                    original_excel_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    output_pdf TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_job(self, original_pdf_name, original_excel_name):
        now = datetime.now(timezone.utc).isoformat()
        job_id = f"job-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, original_pdf_name, original_excel_name,
                    status, error_message, output_pdf, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, original_pdf_name, original_excel_name, "queued", None, None, now, now),
            )
            conn.commit()
        return JobRecord(job_id, original_pdf_name, original_excel_name, "queued", None, None, now, now)

    def update_status(self, job_id, status, error_message=None, output_pdf=None):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, output_pdf = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, error_message, output_pdf, now, job_id),
            )
            conn.commit()

    def get_job(self, job_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT job_id, original_pdf_name, original_excel_name, status,
                       error_message, output_pdf, created_at, updated_at
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if not row:
            raise KeyError(job_id)
        return JobRecord(*row)

    def list_jobs(self, limit=20):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, original_pdf_name, original_excel_name, status,
                       error_message, output_pdf, created_at, updated_at
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [JobRecord(*row) for row in rows]

    def cleanup_uploaded_excels(self, upload_dir, keep_last=2):
        upload_dir = Path(upload_dir)
        excel_files = sorted(
            [path for path in upload_dir.glob("*.xlsx") if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        removed = []
        for index, path in enumerate(excel_files):
            if "stock" in path.name.lower() or index < keep_last:
                continue
            path.unlink(missing_ok=True)
            removed.append(str(path))

        return removed

    def cleanup_expired_jobs(self, job_root_dir, retention_hours, keep_last_excels=2):
        job_root_dir = Path(job_root_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        removed_jobs = []

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, output_pdf, created_at
                FROM jobs
                """,
            ).fetchall()

        for job_id, output_pdf, created_at in rows:
            try:
                created_dt = datetime.fromisoformat(created_at)
            except ValueError:
                continue

            if created_dt > cutoff:
                continue

            job_dir = job_root_dir / job_id
            if job_dir.exists():
                for child in job_dir.rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                for child in sorted(job_dir.rglob("*"), reverse=True):
                    if child.is_dir():
                        child.rmdir()
                job_dir.rmdir()
            removed_jobs.append(job_id)

            with self._connect() as conn:
                conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                conn.commit()

        excel_removed = self.cleanup_uploaded_excels(job_root_dir, keep_last=keep_last_excels)
        return {"jobs": removed_jobs, "excels": excel_removed}
