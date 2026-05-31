"""生成「潜在客户会向 AI 提出的」代表性问题（含意图与热度）。"""
from __future__ import annotations

import logging

from ..providers import AIProvider
from ..providers.mock import estimate_heat, classify_intent, mock_questions, question_meta
from ..utils import extract_json

logger = logging.getLogger(__name__)

_SYSTEM = "你是资深的用户调研与市场研究专家，擅长站在消费者视角提问。"

_PROMPT = """品牌名称：{brand}
所属行业：{industry}

请生成 {n} 个该行业的潜在客户最可能向 AI 助手提出的真实问题。要求：
1. 问题应是「选择 / 推荐 / 对比」类的开放问题，回答时自然会列举该行业的品牌或机构；
2. 贴近真实用户口吻，不要出现目标品牌名；
3. 如果上面的行业为「未知」，请你先根据品牌判断其所属行业。

只返回 JSON，格式：{{"industry": "推断或给定的行业", "questions": ["问题1", "问题2", ...]}}
"""


def generate_questions(
    brand: str,
    industry: str | None,
    n: int,
    provider: AIProvider | None,
) -> tuple[str, list[dict]]:
    """返回 (行业, 问题项列表)。每项为 {text, intent, heat}。"""
    if provider is None:
        return mock_questions(brand, industry, n)

    prompt = _PROMPT.format(brand=brand, industry=industry or "未知", n=n)
    try:
        raw = provider.chat(prompt, system=_SYSTEM, json_mode=True)
        data = extract_json(raw)
        texts = [str(q).strip() for q in data.get("questions", []) if str(q).strip()]
        resolved_industry = str(data.get("industry") or industry or "").strip()
        if texts:
            items = [question_meta(t) for t in texts[:n]]
            return resolved_industry or (industry or ""), items
        logger.warning("问题生成返回为空，降级为模拟问题")
    except Exception as exc:  # noqa: BLE001
        logger.warning("问题生成失败（%s），降级为模拟问题", exc)

    return mock_questions(brand, industry, n)
