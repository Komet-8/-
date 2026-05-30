"""诊断编排：生成问题 → 多平台并发提问与分析 → 汇总指标。"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ..config import Settings
from ..providers import AIProvider, available_platforms
from .. import scoring
from .analyze import analyze_answer, answer_question
from .questions import generate_questions

logger = logging.getLogger(__name__)


def run_diagnosis(
    *,
    brand: str,
    industry: str | None,
    platforms: list[str] | None,
    num_questions: int | None,
    provider: AIProvider | None,
    settings: Settings,
) -> dict:
    n = num_questions or settings.num_questions
    chosen_platforms = platforms or available_platforms(settings)

    resolved_industry, questions = generate_questions(brand, industry, n, provider)

    # 组装所有 (问题 × 平台) 任务
    tasks = [(q, p) for p in chosen_platforms for q in questions]

    def _run_one(task: tuple[str, str]) -> dict:
        question, platform = task
        text = answer_question(brand, resolved_industry, question, platform, provider)
        analysis = analyze_answer(brand, question, text, provider)
        return {
            "question": question,
            "platform": platform,
            "text": text,
            "mentioned": analysis["mentioned"],
            "rank": analysis["rank"],
            "sentiment": analysis["sentiment"],
            "brands": analysis["brands"],
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
        "platforms": chosen_platforms,
        "platform_metrics": plat_metrics,
        "leaderboard": leaderboard,
        "answers": answers,
    }
