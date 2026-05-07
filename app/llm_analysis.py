from __future__ import annotations

import json
from typing import Any

import httpx

from app.settings_store import get_llm_settings


def llm_enabled() -> bool:
    settings = get_llm_settings()
    return settings.enabled and bool(settings.api_key)


def compact_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "overview": profile.get("overview", {}),
        "topics": profile.get("topics", [])[:8],
        "keywords": profile.get("keywords", [])[:10],
        "comment_keywords": profile.get("comment_keywords", [])[:8],
        "top_notes": [
            {
                "title": note.get("title"),
                "liked_count": note.get("liked_count"),
                "collected_count": note.get("collected_count"),
                "comment_count": note.get("comment_count"),
                "share_count": note.get("share_count"),
                "tags": note.get("tags", []),
            }
            for note in profile.get("top_notes", [])[:6]
        ],
    }


async def enhance_with_llm(analysis: dict[str, Any]) -> dict[str, Any]:
    settings = get_llm_settings()
    if not settings.enabled:
        return {
            "enabled": False,
            "message": "大模型增强未启用，当前使用本地规则分析。",
            "insights": [],
            "action_plan": [],
            "content_experiments": [],
        }
    if not settings.api_key:
        return {
            "enabled": False,
            "message": "未配置大模型 API Key，当前使用本地规则分析。",
            "insights": [],
            "action_plan": [],
            "content_experiments": [],
        }

    payload = {
        "mine": compact_profile(analysis.get("mine", {})),
        "target": compact_profile(analysis.get("target", {})),
        "comparison": analysis.get("comparison", {}),
    }
    prompt = (
        "你是小红书账号增长分析师。请基于采集到的主页、笔记和评论统计，输出严格 JSON，"
        "字段为 insights、action_plan、content_experiments。"
        "insights 给 4 条目标用户优势洞察；action_plan 给 5 条我方可执行改进动作；"
        "content_experiments 给 3 个下一周可测试的内容实验。"
        "要求具体、可执行，避免空话。数据如下：\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.model,
                    "messages": [
                        {"role": "system", "content": "你只输出合法 JSON，不要输出 Markdown。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return {
                "enabled": True,
                "model": settings.model,
                "insights": parsed.get("insights", []),
                "action_plan": parsed.get("action_plan", []),
                "content_experiments": parsed.get("content_experiments", []),
            }
    except Exception as exc:
        return {
            "enabled": False,
            "message": f"大模型增强失败，已保留本地规则分析：{exc}",
            "insights": [],
            "action_plan": [],
            "content_experiments": [],
        }
