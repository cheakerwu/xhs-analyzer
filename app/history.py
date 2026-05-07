from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import HISTORY_ROOT


INDEX_FILE = HISTORY_ROOT / "index.json"


def ensure_history_root() -> None:
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)


def read_index() -> list[dict[str, Any]]:
    ensure_history_root()
    if not INDEX_FILE.exists():
        return []
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def write_index(items: list[dict[str, Any]]) -> None:
    ensure_history_root()
    INDEX_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def save_history(task_id: str, request_payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    ensure_history_root()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{task_id}"
    my_name = result.get("mine", {}).get("creator", {}).get("nickname") or "我的主页"
    target_name = result.get("target", {}).get("creator", {}).get("nickname") or "目标用户"
    summary = result.get("summary", [])

    record = {
        "id": record_id,
        "created_at": created_at,
        "request": request_payload,
        "result": result,
    }
    (HISTORY_ROOT / f"{record_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    item = {
        "id": record_id,
        "created_at": created_at,
        "my_homepage": request_payload.get("my_homepage", ""),
        "target_homepage": request_payload.get("target_homepage", ""),
        "my_name": my_name,
        "target_name": target_name,
        "summary": summary,
    }
    items = [item, *[old for old in read_index() if old.get("id") != record_id]]
    write_index(items[:100])
    return item


def list_history() -> list[dict[str, Any]]:
    return read_index()


def get_history(record_id: str) -> dict[str, Any] | None:
    path = HISTORY_ROOT / f"{record_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
