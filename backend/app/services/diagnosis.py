"""诊断编排：生成问题 → 各平台运行单元并发提问与分析 → 汇总指标 + 引用来源 + 对话记录。"""
from __future__ import annotations

import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from .. import scoring, sources as sources_mod
from ..config import Settings
from ..platforms import run_key
from ..providers import AIProvider, default_targets
from ..sources import mock_sources
from .analyze import analyze_answer, answer_question
from .questions import generate_questions

logger = logging.getLogger(__name__)


def _build_conversations(questions: list[dict], answers: list[dict]) -> list[dict]:
    """按问题分组成「AI对话记录」。"""
    out = []
    for q in questions:
        items = [a for a in answers if a["question"] == q["text"]]
        counter: Counter = Counter()
        order: list[str] = []
        for a in items:
            for b in a.get("brands", []):
                if b not in counter:
                    order.append(b)
                counter[b] += 1
        mentioned_brands = sorted(order, key=lambda b: -counter[b])[:12]
        out.append(
            {
                "question": q["text"],
                "intent": q["intent"],
                "heat": q["heat"],
                "mentioned_brands": mentioned_brands,
                "answers": [
                    {
                        "platform": a["platform"],
                        "engine": a["engine"],
                        "text": a["text"],
                        "mentioned": a["mentioned"],
                        "rank": a["rank"],
                        "sentiment": a["sentiment"],
                        "brands": a["brands"],
                    }
                    for a in items
                ],
            }
        )
    return out


def run_diagnosis(
    *,
    brand: str,
    industry: str | None,
    targets: list[dict] | None,
    num_questions: int | None,
    provider: AIProvider | None,
    settings: Settings,
) -> dict:
    n = num_questions or settings.num_questions
    targets = targets or default_targets(settings)

    resolved_industry, questions = generate_questions(brand, industry, n, provider)

    real = provider is not None
    tasks = [(q, t) for t in targets for q in questions]

    def _run_one(task: tuple[dict, dict]) -> dict:
        q, t = task
        platform_name = t["platform"]
        channel = t.get("channel", "手机")
        key = run_key(platform_name, channel)
        # 仅豆包在配置了 key 时真实调用；其余平台走模拟（真实结果需本地浏览器自动化）
        use_real = real and platform_name == "豆包"
        prov = provider if use_real else None
        engine = "doubao" if use_real else "mock"

        text = answer_question(brand, resolved_industry, q["text"], key, prov)
        analysis = analyze_answer(brand, q["text"], text, prov)

        if engine == "mock":
            srcs = mock_sources(brand, resolved_industry, q["text"], key)
        else:
            srcs = sources_mod.extract_sources_from_text(text)

        return {
            "question": q["text"],
            "platform": key,
            "channel": channel,
            "engine": engine,
            "text": text,
            "mentioned": analysis["mentioned"],
            "rank": analysis["rank"],
            "sentiment": analysis["sentiment"],
            "brands": analysis["brands"],
            "sources": srcs,
        }

    workers = max(1, min(settings.max_workers, len(tasks))) if tasks else 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        answers = list(pool.map(_run_one, tasks))

    # —— 聚合指标 ——
    metrics = scoring.aggregate_metrics(brand, answers)
    sov = scoring.share_of_voice(brand, answers)
    score = scoring.brand_score(metrics, sov)
    plat_metrics = scoring.platform_metrics(brand, answers)
    leaderboard = scoring.build_leaderboard(brand, answers)
    citations = sources_mod.aggregate_citations(answers)
    conversations = _build_conversations(questions, answers)

    # 运行单元名列表（按 targets 顺序，去重）
    platform_keys: list[str] = []
    for t in targets:
        key = run_key(t["platform"], t.get("channel", "手机"))
        if key not in platform_keys:
            platform_keys.append(key)

    return {
        "brand": brand,
        "industry": resolved_industry or industry,
        "provider": provider.name if provider else "mock",
        "brand_score": score,
        "mention_rate": metrics["mention_rate"],
        "avg_rank": metrics["avg_rank"],
        "mention_count": metrics["mention_count"],
        "sentiment_score": metrics["sentiment_score"],
        "total_questions": len(questions),
        "total_answers": metrics["total_answers"],
        "questions": questions,
        "platforms": platform_keys,
        "platform_metrics": plat_metrics,
        "leaderboard": leaderboard,
        "answers": answers,
        "citations": citations,
        "conversations": conversations,
    }
