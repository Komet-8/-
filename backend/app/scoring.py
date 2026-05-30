"""指标聚合与品牌得分计算。

每条 answer 是一次「问题 × 平台」的结果，结构为：
    {question, platform, text, mentioned, rank, sentiment, brands: [...]}

本模块把这些原始结果聚合成对外展示的各项指标。

注意：品牌得分公式是我们自己定义的「透明、可调」近似，
并非 aidso 的专有公式 —— 权重集中在文件顶部，方便随时调整。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

# —— 品牌得分权重（合计 100）——
W_MENTION_RATE = 40   # 出现广度：被多少比例的回答提及
W_RANK_QUALITY = 25   # 出现质量：被提及时排名靠前的程度
W_SENTIMENT = 20      # 情感：正面/中性占比
W_SHARE_OF_VOICE = 15  # 竞争度：相对所有品牌的声量占比

POSITIVE_SENTIMENTS = {"positive", "neutral"}


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "")


def is_same_brand(a: str, b: str) -> bool:
    """宽松匹配：完全相等，或一方包含另一方（如 "瑞泰口腔" vs "瑞泰"）。"""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def _avg(values: list[float]) -> float | None:
    nums = [v for v in values if v is not None]
    return round(sum(nums) / len(nums), 2) if nums else None


def aggregate_metrics(target: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
    """计算目标品牌的汇总指标。"""
    total = len(answers)
    mentioned = [a for a in answers if a.get("mentioned")]
    mention_count = len(mentioned)
    mention_rate = round(mention_count / total, 4) if total else 0.0

    ranks = [a["rank"] for a in mentioned if a.get("rank")]
    avg_rank = _avg(ranks)

    if mentioned:
        pos = sum(1 for a in mentioned if a.get("sentiment") in POSITIVE_SENTIMENTS)
        sentiment_score = round(pos / len(mentioned), 4)
    else:
        sentiment_score = 0.0

    return {
        "total_answers": total,
        "mention_count": mention_count,
        "mention_rate": mention_rate,
        "avg_rank": avg_rank,
        "sentiment_score": sentiment_score,
    }


def share_of_voice(target: str, answers: list[dict[str, Any]]) -> float:
    """目标品牌提及次数 / 所有品牌提及总次数。"""
    target_hits = 0
    total_hits = 0
    for a in answers:
        for b in a.get("brands", []):
            total_hits += 1
            if is_same_brand(b, target):
                target_hits += 1
    return round(target_hits / total_hits, 4) if total_hits else 0.0


def brand_score(metrics: dict[str, Any], sov: float) -> int:
    """综合品牌得分 0~100（透明可调公式，见文件头注释）。"""
    mention_rate = metrics["mention_rate"]
    avg_rank = metrics["avg_rank"]
    sentiment = metrics["sentiment_score"]

    # 排名质量：rank=1 -> 1.0，rank 越大越低；再乘以提及率，避免「偶尔提及但排第一」被高估。
    rank_quality = (1.0 / avg_rank) * mention_rate if avg_rank else 0.0

    score = (
        W_MENTION_RATE * mention_rate
        + W_RANK_QUALITY * rank_quality
        + W_SENTIMENT * sentiment * mention_rate
        + W_SHARE_OF_VOICE * sov
    )
    return max(0, min(100, round(score)))


def platform_metrics(target: str, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按平台分组的指标。"""
    by_platform: dict[str, list[dict]] = defaultdict(list)
    for a in answers:
        by_platform[a["platform"]].append(a)

    out = []
    for platform, items in by_platform.items():
        m = aggregate_metrics(target, items)
        out.append(
            {
                "platform": platform,
                "mention_rate": m["mention_rate"],
                "mention_count": m["mention_count"],
                "avg_rank": m["avg_rank"],
            }
        )
    return out


def build_leaderboard(target: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
    """竞品榜单：统计所有出现过的品牌的提及率 / 次数 / 平均排名。"""
    total = len(answers)
    # 用规范化名做聚合 key，但保留首次见到的展示名。
    display: dict[str, str] = {}
    hits: dict[str, set[int]] = defaultdict(set)   # 哪些回答(下标)提到了该品牌
    counts: dict[str, int] = defaultdict(int)
    ranks: dict[str, list[int]] = defaultdict(list)

    for idx, a in enumerate(answers):
        seen_in_answer: set[str] = set()
        for pos, b in enumerate(a.get("brands", []), start=1):
            key = _norm(b)
            if not key:
                continue
            display.setdefault(key, b.strip())
            counts[key] += 1
            ranks[key].append(pos)
            seen_in_answer.add(key)
        for key in seen_in_answer:
            hits[key].add(idx)

    rows = []
    for key, name in display.items():
        n_answers = len(hits[key])
        rows.append(
            {
                "brand": name,
                "mention_rate": round(n_answers / total, 4) if total else 0.0,
                "mention_count": counts[key],
                "avg_rank": _avg(ranks[key]),
                "is_target": is_same_brand(name, target),
            }
        )

    by_rate = sorted(rows, key=lambda r: (r["mention_rate"], r["mention_count"]), reverse=True)[:10]
    by_count = sorted(rows, key=lambda r: (r["mention_count"], r["mention_rate"]), reverse=True)[:10]
    by_avg_rank = sorted(
        rows,
        key=lambda r: (r["avg_rank"] is None, r["avg_rank"] if r["avg_rank"] is not None else 1e9, -r["mention_rate"]),
    )[:10]

    return {"by_rate": by_rate, "by_count": by_count, "by_avg_rank": by_avg_rank}
