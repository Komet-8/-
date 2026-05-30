"""向各 AI 平台提问 + 分析回答里目标品牌的表现。"""
from __future__ import annotations

import logging

from ..providers import AIProvider
from ..providers.mock import heuristic_analyze, mock_answer
from ..utils import extract_json

logger = logging.getLogger(__name__)

_VALID_SENTIMENTS = {"positive", "neutral", "negative"}

# —— 答案引擎：模拟用户向某个 AI 平台提问 ——
_ANSWER_SYSTEM = "你是一个乐于助人的 AI 助手，会给出具体、可参考的推荐。"


def answer_question(
    brand: str,
    industry: str | None,
    question: str,
    platform: str,
    provider: AIProvider | None,
) -> str:
    if provider is None:
        return mock_answer(brand, industry, question, platform)
    try:
        prompt = f"{question}\n\n请给出 3~6 个具体的推荐，并用「数字编号」逐条列出名称和简要理由。"
        return provider.chat(prompt, system=_ANSWER_SYSTEM)
    except Exception as exc:  # noqa: BLE001
        logger.warning("平台[%s]回答失败（%s），降级为模拟回答", platform, exc)
        return mock_answer(brand, industry, question, platform)


# —— 分析器：判断回答里目标品牌的表现 ——
_ANALYZE_SYSTEM = "你是严谨的文本分析器，只输出 JSON，不输出多余文字。"

_ANALYZE_PROMPT = """目标品牌：{brand}
用户问题：{question}
AI 回答：
\"\"\"
{answer}
\"\"\"

请分析上面这段 AI 回答，并只返回 JSON：
{{
  "mentioned": true 或 false,                       // 回答中是否提及目标品牌（含简称/别名）
  "rank": 数字 或 null,                              // 目标品牌在推荐列表中的名次（从1开始）；未提及为 null
  "sentiment": "positive" | "neutral" | "negative", // 回答对目标品牌的情感；未提及填 "neutral"
  "brands": ["品牌1", "品牌2"]                        // 按出现/推荐顺序列出回答中所有品牌或机构名称
}}
"""


def analyze_answer(
    brand: str,
    question: str,
    answer_text: str,
    provider: AIProvider | None,
) -> dict:
    if provider is None:
        return heuristic_analyze(brand, answer_text)

    try:
        prompt = _ANALYZE_PROMPT.format(brand=brand, question=question, answer=answer_text)
        raw = provider.chat(prompt, system=_ANALYZE_SYSTEM, json_mode=True)
        data = extract_json(raw)
        return _normalize(data, brand, answer_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("分析失败（%s），降级为启发式分析", exc)
        return heuristic_analyze(brand, answer_text)


def _normalize(data: dict, brand: str, answer_text: str) -> dict:
    mentioned = bool(data.get("mentioned"))
    rank = data.get("rank")
    try:
        rank = int(rank) if rank is not None else None
        if rank is not None and rank <= 0:
            rank = None
    except (TypeError, ValueError):
        rank = None

    sentiment = str(data.get("sentiment") or "neutral").lower()
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = "neutral"

    brands = [str(b).strip() for b in data.get("brands", []) if str(b).strip()]

    return {
        "mentioned": mentioned,
        "rank": rank if mentioned else None,
        "sentiment": sentiment if mentioned else "neutral",
        "brands": brands,
    }
