from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import DEFAULT_MAX_COMMENTS, DEFAULT_MAX_NOTES, WEB_ROOT
from app.history import get_history, list_history
from app.llm_analysis import llm_enabled
from app.models import AnalyzeRequest, HistoryItem, TaskCreated, TaskStatus
from app.settings_store import PublicLlmSettings, UpdateLlmSettings, get_public_llm_settings, update_llm_settings
from app.tasks import task_manager


app = FastAPI(title="XHS Analyzer", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/health")
async def health() -> dict:
    llm_settings = get_public_llm_settings()
    return {
        "status": "ok",
        "default_max_notes": DEFAULT_MAX_NOTES,
        "default_max_comments": DEFAULT_MAX_COMMENTS,
        "llm_enabled": llm_enabled(),
        "llm_model": llm_settings.model,
        "llm_has_api_key": llm_settings.has_api_key,
    }


@app.get("/api/settings/llm", response_model=PublicLlmSettings)
async def read_llm_settings() -> PublicLlmSettings:
    return get_public_llm_settings()


@app.post("/api/settings/llm", response_model=PublicLlmSettings)
async def save_llm_settings(settings: UpdateLlmSettings) -> PublicLlmSettings:
    return update_llm_settings(settings)


@app.post("/api/analyze", response_model=TaskCreated)
async def analyze(request: AnalyzeRequest) -> TaskCreated:
    task = await task_manager.create(request)
    return TaskCreated(task_id=task.task_id, status=task.status)


@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
async def task_status(task_id: str) -> TaskStatus:
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(
        task_id=task.task_id,
        status=task.status,
        stage=task.stage,
        progress=task.progress,
        logs=task.logs,
        result=task.result,
        error=task.error,
    )


@app.get("/api/qrcode/{task_id}")
async def qrcode_image(task_id: str) -> Response:
    task = task_manager.get(task_id)
    if not task or not task.qrcode_file or not task.qrcode_file.exists():
        return Response(
            content='{"detail":"暂无二维码"}',
            media_type="application/json",
            status_code=404,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
    return FileResponse(
        task.qrcode_file,
        media_type="image/png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.post("/api/sms_code/{task_id}")
async def submit_sms_code(task_id: str, body: dict) -> dict:
    task = task_manager.get(task_id)
    if not task or not task.sms_code_file:
        raise HTTPException(status_code=404, detail="任务不存在")
    code = str(body.get("code", "")).strip()
    task.sms_code_file.write_text(code)
    return {"status": "ok"}


@app.get("/api/history", response_model=list[HistoryItem])
async def history_items() -> list[dict]:
    return list_history()


@app.get("/api/history/{record_id}")
async def history_detail(record_id: str) -> dict:
    record = get_history(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return record


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


if WEB_ROOT.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_ROOT)), name="web")
