from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_CRAWLER_ROOT = PROJECT_ROOT / "MediaCrawler-main"
WEB_ROOT = PROJECT_ROOT / "web"
RUN_DATA_ROOT = PROJECT_ROOT / "data" / "runs"
HISTORY_ROOT = PROJECT_ROOT / "data" / "history"

def _resolve_python() -> Path:
    """Resolve the Python executable, falling back to sys.executable if the configured path is missing."""
    configured = os.getenv("XHS_ANALYZER_PYTHON")
    if configured:
        p = Path(configured)
        if p.exists():
            return p
    # sys.executable is always correct when the app is running under Python
    return Path(sys.executable)


PYTHON_EXECUTABLE = _resolve_python()

DEFAULT_MAX_NOTES = int(os.getenv("XHS_ANALYZER_MAX_NOTES", "30"))
DEFAULT_MAX_COMMENTS = int(os.getenv("XHS_ANALYZER_MAX_COMMENTS", "20"))
DEFAULT_SLEEP_SECONDS = float(os.getenv("XHS_ANALYZER_SLEEP_SECONDS", "1"))
DEFAULT_HEADLESS = os.getenv("XHS_ANALYZER_HEADLESS", "true").lower() not in {"0", "false", "no", "off"}

LLM_API_KEY = os.getenv("XHS_LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("XHS_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("XHS_LLM_MODEL", "gpt-4o-mini")
