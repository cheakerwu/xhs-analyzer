# -*- coding: utf-8 -*-
# Helper module for structured login state communication between
# MediaCrawler subprocess and the XHS Analyzer backend.

import asyncio
import json
import os
import time

from . import utils


def write_state(
    state_file: str,
    state: str,
    message: str,
    sms_attempts: int = 0,
    max_sms_attempts: int = 3,
) -> None:
    """Atomically write login state to a JSON file."""
    data = {
        "state": state,
        "message": message,
        "sms_attempts": sms_attempts,
        "max_sms_attempts": max_sms_attempts,
        "updated_at": time.time(),
    }
    tmp = state_file + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, state_file)
    except Exception as e:
        utils.logger.error(f"[login_state] Failed to write state: {e}")


async def take_screenshot(screenshot_file: str, page) -> None:
    """Take a screenshot of the current page (JPEG, smaller size)."""
    tmp = screenshot_file + ".bak"
    try:
        screenshot_bytes = await page.screenshot(full_page=False, type="jpeg", quality=60)
        with open(tmp, "wb") as f:
            f.write(screenshot_bytes)
        os.replace(tmp, screenshot_file)
    except Exception as e:
        utils.logger.error(f"[login_state] Screenshot failed: {e}")
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


async def wait_for_sms_code(sms_code_file: str, timeout: int = 120) -> str | None:
    """Poll for a new SMS code from the file. Returns the code or None on timeout."""
    initial_mtime = _get_mtime(sms_code_file)
    for _ in range(timeout):
        if os.path.exists(sms_code_file):
            current_mtime = _get_mtime(sms_code_file)
            if current_mtime != initial_mtime:
                try:
                    code = open(sms_code_file, encoding="utf-8").read().strip()
                    if code:
                        return code
                except Exception:
                    pass
        await asyncio.sleep(1)
    return None


def clear_file(path: str) -> None:
    """Remove a file if it exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _get_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0
