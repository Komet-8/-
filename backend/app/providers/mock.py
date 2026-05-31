"""模拟数据 Provider。

没有配置 ARK_API_KEY 时使用：用确定性的伪随机生成可信的问题与回答，
让整条「生成问题 → 多平台提问 → 分析回答 → 汇总指标」流程在没有任何
外部 API 时也能完整跑通。`heuristic_analyze` 也作为真实分析失败时的兜底。
"""
from __future__ import annotations

import hashlib
import re
from random import Random

from ..scoring import is_same_brand

# 牙科 / 口腔行业的拟真品牌池（贴近截图）
_DENTAL_POOL = [
    "北京大学口腔医院", "四川大学华西口腔医院", "劲松口腔", "北大口腔", "爱牙仕",
    "泰康拜博口腔", "美奥口腔", "拜尔口腔", "维乐口腔", "中诺口腔",
    "南昌大学附属口腔医院", "时代天使", "隐适美", "瑞尔齿科",
]

# 通用品牌前缀（拼接行业后缀，适配任意行业）
_GENERIC_PREFIX = [
    "华美", "众安", "优答", "智选", "领航", "百川", "新和", "康正",
    "瑞普", "同方", "盛世", "金牌", "卓越", "立信",
]

_POSITIVE_WORDS = ("推荐", "优秀", "领先", "靠谱", "知名", "专业", "口碑好", "实力强")
_NEGATIVE_WORDS = ("不推荐", "较差", "避免", "不建议", "问题较多", "差评", "谨慎")
_DENTAL_KEYWORDS = ("口腔", "牙", "齿")

# 意图分类关键词
_COMPARE_KW = ("性价比", "对比", "排名", "选择", "更高", "更好", "最好", "比较", "哪家更", "更靠谱")


def _seed(*parts: str) -> int:
    return int(hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:12], 16)


def classify_intent(text: str) -> str:
    return "对比/选择" if any(k in text for k in _COMPARE_KW) else "咨询/查询"


def estimate_heat(text: str) -> int:
    """问题热度（搜索量近似）：3000~19999 的确定性伪随机值。"""
    rnd = Random(_seed("heat", text))
    return rnd.randint(3000, 19999)


def question_meta(text: str) -> dict:
    return {"text": text, "intent": classify_intent(text), "heat": estimate_heat(text)}


def _industry_suffix(industry: str | None) -> str:
    ind = industry or ""
    table = [
        ("口腔", "口腔"), ("牙", "口腔"), ("医", "医院"), ("教育", "教育"),
        ("律", "律所"), ("汽", "汽车"), ("装", "装饰"), ("健身", "健身"),
        ("旅", "旅行"), ("餐", "餐饮"),
    ]
    for kw, suf in table:
        if kw in ind:
            return suf
    return ind[-2:] if len(ind) >= 2 else "优选"


def competitor_pool(brand: str, industry: str | None) -> list[str]:
    blob = f"{brand}{industry or ''}"
    if any(k in blob for k in _DENTAL_KEYWORDS):
        return list(_DENTAL_POOL)
    suf = _industry_suffix(industry)
    return [f"{p}{suf}" for p in _GENERIC_PREFIX]


# —— 问题生成 ——
_QUESTION_TEMPLATES = [
    "{ind}哪家机构比较好？",
    "选择{ind}服务时应该注意什么，有哪些值得推荐的品牌？",
    "国内做{ind}比较专业的有哪些？",
    "{ind}哪家性价比更高？",
    "口碑好的{ind}品牌有哪些推荐？",
    "想找一家靠谱的{ind}，有什么建议？",
    "{ind}领域的头部品牌有哪些？",
]


def mock_questions(brand: str, industry: str | None, n: int) -> tuple[str, list[dict]]:
    ind = industry or _industry_suffix(industry)
    rnd = Random(_seed("q", brand, ind))
    pool = _QUESTION_TEMPLATES.copy()
    rnd.shuffle(pool)
    items = [question_meta(pool[i % len(pool)].format(ind=ind)) for i in range(n)]
    return ind, items


# —— 回答生成 ——
def mock_answer(brand: str, industry: str | None, question: str, platform_key: str) -> str:
    rnd = Random(_seed("a", brand, question, platform_key))
    pool = [b for b in competitor_pool(brand, industry) if not is_same_brand(b, brand)]
    rnd.shuffle(pool)
    k = rnd.randint(3, 6)
    chosen = pool[:k]

    # 约 38% 的回答会提及目标品牌，并随机插入到某个名次
    if rnd.random() < 0.38:
        pos = rnd.randint(0, len(chosen))
        chosen.insert(pos, brand)

    lines = []
    for i, name in enumerate(chosen, start=1):
        tone = rnd.choice(["综合实力强，口碑较好", "性价比不错，服务专业", "知名度高，值得参考", "技术成熟，评价稳定"])
        lines.append(f"{i}. {name}：{tone}。")
    head = f"针对「{question}」，可以参考以下几家（排名不分绝对先后）：\n"
    tail = "\n\n建议结合自身需求与实地了解后再做选择。"
    return head + "\n".join(lines) + tail


# —— 启发式分析（兼作真实分析失败时的兜底）——
_LIST_RE = re.compile(r"^\s*(?:\d+[.、)]|[-*•])\s*\**([^：:，,。\n（(*]+)")


def _sentiment_of(text: str, brand: str) -> str:
    if any(w in text for w in _NEGATIVE_WORDS):
        return "negative"
    if any(w in text for w in _POSITIVE_WORDS):
        return "positive"
    return "neutral"


def heuristic_analyze(brand: str, text: str, known_brands: list[str] | None = None) -> dict:
    """从「编号 / 项目符号」式推荐文本中提取品牌顺序与目标品牌名次。"""
    brands: list[str] = []
    for line in text.splitlines():
        m = _LIST_RE.match(line)
        if m:
            name = m.group(1).strip()
            if name:
                brands.append(name)

    if not brands and known_brands:
        positions = [(text.find(b), b) for b in known_brands if b in text]
        brands = [b for pos, b in sorted(positions) if pos != -1]

    rank = None
    mentioned = brand in text
    for idx, b in enumerate(brands, start=1):
        if is_same_brand(b, brand):
            mentioned = True
            rank = idx
            break

    return {
        "mentioned": mentioned,
        "rank": rank,
        "sentiment": _sentiment_of(text, brand) if mentioned else "neutral",
        "brands": brands,
    }
