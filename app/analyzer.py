from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any


STOP_WORDS = {
    "一个", "这个", "那个", "就是", "不是", "因为", "所以", "然后", "但是", "如果", "可以", "没有",
    "什么", "怎么", "自己", "我们", "你们", "他们", "进行", "通过", "还是", "真的", "感觉", "时候",
    "小红书", "分享", "笔记", "内容", "今天", "大家", "一起", "一下", "这样", "一些", "不会", "已经",
}


def to_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    multipliers = {"万": 10000, "w": 10000, "W": 10000, "千": 1000, "k": 1000, "K": 1000}
    for suffix, multiplier in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * multiplier)
            except ValueError:
                return 0
    try:
        return int(float(text))
    except ValueError:
        digits = re.findall(r"\d+", text)
        return int("".join(digits)) if digits else 0


def ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_+-]{2,}", text)
    return [token.lower() for token in tokens if token not in STOP_WORDS and len(token) > 1]


def top_counter(counter: Counter, limit: int = 10) -> list[dict[str, Any]]:
    return [{"name": key, "value": value} for key, value in counter.most_common(limit)]


def summarize_profile(label: str, payload: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    notes = payload.get("notes", [])
    comments = payload.get("comments", [])
    creator = payload.get("creators", [{}])[-1] if payload.get("creators") else {}

    note_count = len(notes)
    liked_total = sum(to_int(item.get("liked_count")) for item in notes)
    collected_total = sum(to_int(item.get("collected_count")) for item in notes)
    comment_total = sum(to_int(item.get("comment_count")) for item in notes)
    share_total = sum(to_int(item.get("share_count")) for item in notes)
    engagement_total = liked_total + collected_total + comment_total + share_total

    topic_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    comment_keyword_counter: Counter[str] = Counter()
    note_scores: list[dict[str, Any]] = []
    note_lengths: list[int] = []

    comments_by_note: dict[str, int] = defaultdict(int)
    for comment in comments:
        comments_by_note[str(comment.get("note_id", ""))] += 1
        comment_keyword_counter.update(tokenize(str(comment.get("content", ""))))

    for note in notes:
        title = str(note.get("title") or "")
        desc = str(note.get("desc") or "")
        tags = [tag.strip() for tag in str(note.get("tag_list") or "").split(",") if tag.strip()]
        topic_counter.update(tags)
        keyword_counter.update(tokenize(f"{title} {desc} {' '.join(tags)}"))
        type_counter.update([str(note.get("type") or "unknown")])
        note_lengths.append(len(desc))

        score = (
            to_int(note.get("liked_count"))
            + to_int(note.get("collected_count")) * 1.2
            + to_int(note.get("comment_count")) * 1.5
            + to_int(note.get("share_count")) * 1.8
        )
        note_scores.append(
            {
                "note_id": note.get("note_id"),
                "title": title or desc[:28] or "未命名笔记",
                "note_url": note.get("note_url"),
                "liked_count": to_int(note.get("liked_count")),
                "collected_count": to_int(note.get("collected_count")),
                "comment_count": to_int(note.get("comment_count")),
                "share_count": to_int(note.get("share_count")),
                "score": round(score, 2),
                "tags": tags[:5],
                "comment_samples": comments_by_note.get(str(note.get("note_id")), 0),
            }
        )

    top_notes = sorted(note_scores, key=lambda item: item["score"], reverse=True)[:8]
    avg_engagement = ratio(engagement_total, note_count)
    median_score = sorted([item["score"] for item in note_scores])[note_count // 2] if note_scores else 0
    hit_rate = ratio(sum(1 for item in note_scores if item["score"] >= median_score and item["score"] > 0), note_count)
    avg_length = round(sum(note_lengths) / note_count, 1) if note_lengths else 0

    return {
        "label": label,
        "creator": creator,
        "overview": {
            "note_count": note_count,
            "comment_sample_count": len(comments),
            "fans": to_int(creator.get("fans")),
            "interaction": to_int(creator.get("interaction")),
            "liked_total": liked_total,
            "collected_total": collected_total,
            "comment_total": comment_total,
            "share_total": share_total,
            "engagement_total": engagement_total,
            "avg_engagement": round(avg_engagement, 2),
            "collection_rate": ratio(collected_total, liked_total),
            "comment_rate": ratio(comment_total, liked_total),
            "share_rate": ratio(share_total, liked_total),
            "hit_rate": hit_rate,
            "avg_text_length": avg_length,
        },
        "top_notes": top_notes,
        "topics": top_counter(topic_counter),
        "keywords": top_counter(keyword_counter),
        "comment_keywords": top_counter(comment_keyword_counter),
        "content_types": top_counter(type_counter),
    }


def diff_value(target: float, mine: float) -> dict[str, Any]:
    delta = round(target - mine, 2)
    pct = round(delta / mine * 100, 1) if mine else (100.0 if target else 0.0)
    return {"target": target, "mine": mine, "delta": delta, "percent": pct}


def extract_advantages(profile: dict[str, Any]) -> list[str]:
    overview = profile["overview"]
    topics = [item["name"] for item in profile["topics"][:3]]
    keywords = [item["name"] for item in profile["keywords"][:5]]
    advantages: list[str] = []

    if overview["avg_engagement"] > 0:
        advantages.append(f"单篇平均互动约 {overview['avg_engagement']}，说明内容能稳定触发点赞、收藏或讨论。")
    if overview["collection_rate"] >= 0.35:
        advantages.append("收藏/点赞比例较高，内容具有清单、教程、避坑或长期参考价值。")
    if overview["comment_rate"] >= 0.15:
        advantages.append("评论占比较高，选题具备讨论性，容易让用户表达经历和追问。")
    if overview["share_rate"] >= 0.08:
        advantages.append("分享占比较好，标题或信息结构可能更适合被转发给朋友。")
    if topics:
        advantages.append(f"主题集中在 {', '.join(topics)}，账号识别度比较清晰。")
    if keywords:
        advantages.append(f"高频表达包括 {', '.join(keywords)}，可作为它的内容标签和用户心智入口。")
    return advantages[:6] or ["采集样本较少，暂时只能判断基础表现；建议增加笔记数量后再看优势。"]


def compare_profiles(mine: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    my_overview = mine["overview"]
    target_overview = target["overview"]

    shared_topics = sorted(
        {item["name"] for item in mine["topics"][:10]} & {item["name"] for item in target["topics"][:10]}
    )
    target_unique_topics = [
        item["name"] for item in target["topics"][:10] if item["name"] not in {t["name"] for t in mine["topics"][:10]}
    ]
    target_unique_keywords = [
        item["name"] for item in target["keywords"][:12] if item["name"] not in {k["name"] for k in mine["keywords"][:12]}
    ][:6]

    metrics = {
        "avg_engagement": diff_value(target_overview["avg_engagement"], my_overview["avg_engagement"]),
        "collection_rate": diff_value(target_overview["collection_rate"], my_overview["collection_rate"]),
        "comment_rate": diff_value(target_overview["comment_rate"], my_overview["comment_rate"]),
        "share_rate": diff_value(target_overview["share_rate"], my_overview["share_rate"]),
        "hit_rate": diff_value(target_overview["hit_rate"], my_overview["hit_rate"]),
        "avg_text_length": diff_value(target_overview["avg_text_length"], my_overview["avg_text_length"]),
    }

    lessons: list[str] = []
    if metrics["collection_rate"]["delta"] > 0.05:
        lessons.append("优先学习对方把内容做成可收藏资产的方式，例如步骤化、清单化、模板化和结论前置。")
    if metrics["comment_rate"]["delta"] > 0.05:
        lessons.append("借鉴对方更容易引发回复的提问方式，在结尾加入选择题式互动或真实场景追问。")
    if metrics["share_rate"]["delta"] > 0.03:
        lessons.append("观察对方标题和封面是否有明确受益对象，让内容更像一条能转发给特定人的建议。")
    if target_unique_topics:
        lessons.append(f"可以小范围测试对方表现突出的主题：{', '.join(target_unique_topics[:4])}。")
    if target_unique_keywords:
        lessons.append(f"可参考对方常用表达：{', '.join(target_unique_keywords)}，但要改写成自己的经验语气。")
    if metrics["avg_text_length"]["delta"] > 80:
        lessons.append("对方正文更充分，可以尝试增加背景、步骤、对比和复盘，让信息密度更完整。")
    elif metrics["avg_text_length"]["delta"] < -80:
        lessons.append("对方正文更短，可能胜在直接；可以测试更短标题和更快给结论的写法。")

    return {
        "metrics": metrics,
        "shared_topics": shared_topics,
        "target_unique_topics": target_unique_topics[:8],
        "target_unique_keywords": target_unique_keywords,
        "target_advantages": extract_advantages(target),
        "my_strengths": extract_advantages(mine),
        "lessons": lessons[:8] or ["双方差异暂时不明显，建议增加采集笔记数后再看选题、收藏率和评论率。"],
    }


def build_analysis(my_payload: dict[str, list[dict[str, Any]]], target_payload: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    mine = summarize_profile("我的主页", my_payload)
    target = summarize_profile("目标用户", target_payload)
    comparison = compare_profiles(mine, target)

    return {
        "mine": mine,
        "target": target,
        "comparison": comparison,
        "summary": make_summary(mine, target, comparison),
    }


def make_summary(mine: dict[str, Any], target: dict[str, Any], comparison: dict[str, Any]) -> list[str]:
    target_name = target["creator"].get("nickname") or "目标用户"
    my_name = mine["creator"].get("nickname") or "你的主页"
    avg_delta = comparison["metrics"]["avg_engagement"]["delta"]
    collection_delta = comparison["metrics"]["collection_rate"]["delta"]

    lines = [
        f"{target_name} 的核心特点是：{comparison['target_advantages'][0]}",
        f"与 {my_name} 相比，目标用户单篇平均互动差值为 {avg_delta}，收藏率差值为 {round(collection_delta * 100, 1)} 个百分点。",
    ]
    if comparison["lessons"]:
        lines.append(f"最值得先借鉴的是：{comparison['lessons'][0]}")
    return lines
