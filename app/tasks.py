from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.analyzer import build_analysis
from app.config import (
    DEFAULT_MAX_COMMENTS,
    DEFAULT_MAX_NOTES,
    DEFAULT_SLEEP_SECONDS,
    MEDIA_CRAWLER_ROOT,
    PYTHON_EXECUTABLE,
    RUN_DATA_ROOT,
)
from app.data_loader import load_profile_run, latest_jsonl
from app.history import save_history
from app.llm_analysis import enhance_with_llm, llm_enabled
from app.models import AnalyzeRequest


def stable_key(value: str) -> str:
    return hashlib.sha1(value.strip().encode("utf-8")).hexdigest()[:16]


def is_usable_profile_dir(path: Path) -> bool:
    return bool(latest_jsonl(path, "contents"))


@dataclass
class AnalysisTask:
    task_id: str
    request: AnalyzeRequest
    status: str = "queued"
    stage: str = "等待开始"
    progress: int = 0
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    qrcode_file: Path | None = None
    sms_code_file: Path | None = None

    def add_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")
        self.logs = self.logs[-300:]


class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, AnalysisTask] = {}
        self._lock = asyncio.Lock()

    async def create(self, request: AnalyzeRequest) -> AnalysisTask:
        task = AnalysisTask(task_id=uuid.uuid4().hex[:12], request=request)
        self.tasks[task.task_id] = task
        asyncio.create_task(self._run(task))
        return task

    def get(self, task_id: str) -> AnalysisTask | None:
        return self.tasks.get(task_id)

    async def _run(self, task: AnalysisTask) -> None:
        async with self._lock:
            try:
                task.status = "running"
                task.stage = "准备采集"
                task.progress = 5
                task.add_log("开始准备小红书主页采集与分析。")

                ensure_runtime_ready()
                RUN_DATA_ROOT.mkdir(parents=True, exist_ok=True)

                my_dir = await self._collect_profile(task, "mine", task.request.my_homepage, 10, 45)
                target_dir = await self._collect_profile(task, "target", task.request.target_homepage, 50, 82)

                task.stage = "生成本地分析"
                task.progress = 86
                task.add_log("采集完成，正在汇总笔记、评论和主页数据。")

                my_payload = load_profile_run(my_dir)
                target_payload = load_profile_run(target_dir)
                result = build_analysis(my_payload, target_payload)

                task.stage = "大模型增强"
                task.progress = 92
                if task.request.enable_ai_analysis:
                    if llm_enabled():
                        task.add_log("正在调用大模型生成增强洞察。")
                    else:
                        task.add_log("未配置大模型 Key，跳过增强分析。")
                    result["ai_analysis"] = await enhance_with_llm(result)
                else:
                    result["ai_analysis"] = {
                        "enabled": False,
                        "message": "本次未启用大模型增强。",
                        "insights": [],
                        "action_plan": [],
                        "content_experiments": [],
                    }

                task.stage = "保存历史"
                task.progress = 96
                history_item = save_history(task.task_id, task.request.model_dump(), result)
                result["history"] = history_item
                task.result = result

                task.progress = 100
                task.stage = "完成"
                task.status = "completed"
                task.add_log("分析完成，结果已保存到历史记录。")
            except Exception as exc:
                task.status = "failed"
                task.stage = "失败"
                task.error = str(exc)
                task.add_log(f"任务失败：{exc}")
            finally:
                _cleanup_qrcode(task)

    async def _collect_profile(
        self,
        task: AnalysisTask,
        role: str,
        homepage: str,
        start_progress: int,
        end_progress: int,
    ) -> Path:
        key = stable_key(
            f"{homepage}|{task.request.max_notes}|{task.request.max_comments_per_note}|{task.request.include_comments}"
        )
        role_dir = RUN_DATA_ROOT / key
        label = "我的主页" if role == "mine" else "目标用户"

        if task.request.reuse_existing_data and is_usable_profile_dir(role_dir):
            task.add_log(f"{label}已有本地数据，直接复用。")
            task.progress = end_progress
            return role_dir

        if role_dir.exists():
            shutil.rmtree(role_dir)
        role_dir.mkdir(parents=True, exist_ok=True)

        task.stage = f"采集{label}"
        task.progress = start_progress
        task.add_log(f"开始采集{label}：{homepage}")

        # Clean up stale Chromium lock files from previous crashes
        _cleanup_browser_locks()

        command = build_crawler_command(
            homepage=homepage,
            output_dir=role_dir,
            max_notes=task.request.max_notes or DEFAULT_MAX_NOTES,
            max_comments=task.request.max_comments_per_note or DEFAULT_MAX_COMMENTS,
            include_comments=task.request.include_comments,
            headless=task.request.headless,
        )

        # QR code file for remote login
        qrcode_path = RUN_DATA_ROOT / f"{task.task_id}_qrcode.png"
        sms_code_path = RUN_DATA_ROOT / f"{task.task_id}_sms_code.txt"
        task.qrcode_file = qrcode_path
        task.sms_code_file = sms_code_path

        env = {
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "XHS_QRCODE_FILE": str(qrcode_path),
            "XHS_SMS_CODE_FILE": str(sms_code_path),
        }
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(MEDIA_CRAWLER_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        assert process.stdout is not None
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            task.add_log(compact_log(line))
            if task.progress < end_progress - 4:
                task.progress += 1

        code = await process.wait()
        if code != 0:
            raise RuntimeError(f"{label}采集失败，退出码 {code}。请检查登录状态、主页链接和浏览器授权。")
        if not is_usable_profile_dir(role_dir):
            raise RuntimeError(f"{label}没有采集到笔记数据，请确认主页链接可访问，并尽量使用带 xsec_token 的完整主页链接。")

        task.progress = end_progress
        task.add_log(f"{label}采集完成。")
        return role_dir


def _cleanup_browser_locks() -> None:
    """Remove stale Chromium SingletonLock files left by crashed processes."""
    lock_dir = MEDIA_CRAWLER_ROOT / "browser_data" / "xhs_user_data_dir"
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        lock_file = lock_dir / name
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass


def _cleanup_qrcode(task: AnalysisTask) -> None:
    """Remove temporary QR code and SMS code files after task completes."""
    for f in (task.qrcode_file, task.sms_code_file):
        if f and f.exists():
            try:
                f.unlink()
            except OSError:
                pass


def compact_log(line: str) -> str:
    if len(line) <= 220:
        return line
    return f"{line[:200]}..."


def ensure_runtime_ready() -> None:
    if not PYTHON_EXECUTABLE.exists():
        raise RuntimeError(f"没有找到 Python 环境：{PYTHON_EXECUTABLE}")
    if not MEDIA_CRAWLER_ROOT.exists():
        raise RuntimeError(f"没有找到 MediaCrawler-main：{MEDIA_CRAWLER_ROOT}")


def build_crawler_command(
    homepage: str,
    output_dir: Path,
    max_notes: int,
    max_comments: int,
    include_comments: bool,
    headless: bool,
) -> list[str]:
    return [
        str(PYTHON_EXECUTABLE),
        "main.py",
        "--platform",
        "xhs",
        "--lt",
        "qrcode",
        "--type",
        "creator",
        "--creator_id",
        homepage.strip(),
        "--save_data_option",
        "jsonl",
        "--save_data_path",
        str(output_dir),
        "--get_comment",
        "true" if include_comments else "false",
        "--get_sub_comment",
        "false",
        "--max_notes_count",
        str(max_notes),
        "--max_comments_count_singlenotes",
        str(max_comments),
        "--max_concurrency_num",
        "1",
        "--crawl_sleep_seconds",
        str(DEFAULT_SLEEP_SECONDS),
        "--headless",
        "true" if headless else "false",
        "--enable_cdp_mode",
        "false",
    ]


task_manager = TaskManager()
