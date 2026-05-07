from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_CRAWLER_ROOT = PROJECT_ROOT / "MediaCrawler-main"
WEB_ROOT = PROJECT_ROOT / "web"
RUN_DATA_ROOT = PROJECT_ROOT / "data" / "runs"
HISTORY_ROOT = PROJECT_ROOT / "data" / "history"

DEFAULT_PYTHON = sys.executable
PYTHON_EXECUTABLE = Path(os.getenv("XHS_ANALYZER_PYTHON", DEFAULT_PYTHON))

DEFAULT_MAX_NOTES = int(os.getenv("XHS_ANALYZER_MAX_NOTES", "30"))
DEFAULT_MAX_COMMENTS = int(os.getenv("XHS_ANALYZER_MAX_COMMENTS", "20"))
DEFAULT_SLEEP_SECONDS = float(os.getenv("XHS_ANALYZER_SLEEP_SECONDS", "1"))

LLM_API_KEY = os.getenv("XHS_LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("XHS_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("XHS_LLM_MODEL", "gpt-4o-mini")
