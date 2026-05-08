from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    my_homepage: str = Field(..., min_length=5, description="自己的小红书主页链接")
    target_homepage: str = Field(..., min_length=5, description="目标用户的小红书主页链接")
    max_notes: int = Field(default=30, ge=1, le=200)
    max_comments_per_note: int = Field(default=20, ge=0, le=200)
    include_comments: bool = True
    enable_ai_analysis: bool = True
    headless: bool = True
    reuse_existing_data: bool = True


class TaskCreated(BaseModel):
    task_id: str
    status: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    stage: str
    progress: int
    logs: list[str]
    result: dict[str, Any] | None = None
    error: str | None = None


class HistoryItem(BaseModel):
    id: str
    created_at: str
    my_homepage: str
    target_homepage: str
    my_name: str
    target_name: str
    summary: list[str] = []
