import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WebConfig:
    base_dir: Path = Path(os.getenv("DELIVERYNOTE_WEB_BASE_DIR", "web_data"))
    excel_dir: Path = Path(os.getenv("DELIVERYNOTE_WEB_EXCEL_DIR", "web_data/excels"))
    db_path: Path = Path(os.getenv("DELIVERYNOTE_WEB_DB_PATH", "web_data/jobs.db"))
    upload_dir: Path = Path(os.getenv("DELIVERYNOTE_WEB_UPLOAD_DIR", "web_data/uploads"))
    max_upload_size_mb: int = int(os.getenv("DELIVERYNOTE_WEB_MAX_UPLOAD_SIZE_MB", "25"))
    job_retention_hours: int = int(os.getenv("DELIVERYNOTE_WEB_JOB_RETENTION_HOURS", "24"))
    cleanup_interval_seconds: int = int(os.getenv("DELIVERYNOTE_WEB_CLEANUP_INTERVAL_SECONDS", "86400"))
    api_token: str = os.getenv("DELIVERYNOTE_WEB_API_TOKEN", "")


CONFIG = WebConfig()
