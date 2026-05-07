from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT


SETTINGS_FILE = PROJECT_ROOT / "data" / "settings.json"


class LlmSettings(BaseModel):
    enabled: bool = False
    base_url: str = Field(default_factory=lambda: os.getenv("XHS_LLM_BASE_URL", "https://api.openai.com/v1"))
    model: str = Field(default_factory=lambda: os.getenv("XHS_LLM_MODEL", "gpt-4o-mini"))
    api_key: str = Field(default_factory=lambda: os.getenv("XHS_LLM_API_KEY", ""))


class PublicLlmSettings(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    has_api_key: bool = False


class UpdateLlmSettings(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""


def _read_raw() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_raw(payload: dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_llm_settings() -> LlmSettings:
    raw = _read_raw().get("llm", {})
    defaults = LlmSettings()
    merged = {
        "enabled": raw.get("enabled", defaults.enabled),
        "base_url": raw.get("base_url", defaults.base_url),
        "model": raw.get("model", defaults.model),
        "api_key": raw.get("api_key", defaults.api_key),
    }
    return LlmSettings(**merged)


def get_public_llm_settings() -> PublicLlmSettings:
    settings = get_llm_settings()
    return PublicLlmSettings(
        enabled=settings.enabled,
        base_url=settings.base_url,
        model=settings.model,
        has_api_key=bool(settings.api_key),
    )


def update_llm_settings(update: UpdateLlmSettings) -> PublicLlmSettings:
    raw = _read_raw()
    current = get_llm_settings()
    api_key = update.api_key.strip() if update.api_key.strip() else current.api_key
    raw["llm"] = {
        "enabled": update.enabled,
        "base_url": update.base_url.strip().rstrip("/") or "https://api.openai.com/v1",
        "model": update.model.strip() or "gpt-4o-mini",
        "api_key": api_key,
    }
    _write_raw(raw)
    return get_public_llm_settings()
