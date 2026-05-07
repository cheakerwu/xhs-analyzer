from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def latest_jsonl(base_dir: Path, item_type: str) -> Path | None:
    candidates = sorted(base_dir.glob(f"xhs/jsonl/*_{item_type}_*.jsonl"))
    return candidates[-1] if candidates else None


def load_profile_run(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    contents_path = latest_jsonl(run_dir, "contents")
    comments_path = latest_jsonl(run_dir, "comments")
    creators_path = latest_jsonl(run_dir, "creators")

    return {
        "notes": read_jsonl(contents_path) if contents_path else [],
        "comments": read_jsonl(comments_path) if comments_path else [],
        "creators": read_jsonl(creators_path) if creators_path else [],
    }
