"""引用来源（GEO 核心维度之一）。

真实产品里这些来自「开启了联网搜索的消费端 App」返回的引用角标。
- API 模式下：从回答文本里解析 URL / markdown 链接；
- 模拟模式下：生成贴近真实报告（附录C）的来源池，含网站分类与引用率。

本模块还负责把逐条来源聚合成「引用来源榜单」。
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from random import Random
from typing import Any
from urllib.parse import urlparse

# 与真实报告附录C一致的网站分类
CATEGORIES = [
    "官网/独立站/行业垂直",
    "门户/自媒体平台",
    "教育/学术",
    "地方媒体/新闻",
    "政府/公共机构",
    "社区/论坛/博客",
    "视频平台",
    "央媒/主流媒体",
]

# 口腔/医疗行业来源池（贴近真实导出报告）
_DENTAL_SOURCES = [
    ("牙舒丽网", "官网/独立站/行业垂直"),
    ("看牙记网", "官网/独立站/行业垂直"),
    ("39健康网", "官网/独立站/行业垂直"),
    ("复禾健康", "官网/独立站/行业垂直"),
    ("家庭医生在线", "官网/独立站/行业垂直"),
    ("有来医生", "官网/独立站/行业垂直"),
    ("名医汇", "官网/独立站/行业垂直"),
    ("春雨医生", "官网/独立站/行业垂直"),
    ("非常爱美网", "官网/独立站/行业垂直"),
    ("今日头条", "门户/自媒体平台"),
    ("搜狐", "门户/自媒体平台"),
    ("网易", "门户/自媒体平台"),
    ("抖音", "视频平台"),
    ("哔哩哔哩", "视频平台"),
    ("知乎", "社区/论坛/博客"),
    ("小红书", "社区/论坛/博客"),
    ("大众点评", "社区/论坛/博客"),
    ("新华网", "央媒/主流媒体"),
    ("人民网", "央媒/主流媒体"),
    ("北京大学医学部", "教育/学术"),
    ("国家卫健委", "政府/公共机构"),
    ("北京市卫生健康委员会", "政府/公共机构"),
]

# 通用行业来源池
_GENERIC_SOURCES = [
    ("百度百科", "官网/独立站/行业垂直"),
    ("天眼查", "官网/独立站/行业垂直"),
    ("企查查", "官网/独立站/行业垂直"),
    ("36氪", "门户/自媒体平台"),
    ("亿欧网", "门户/自媒体平台"),
    ("今日头条", "门户/自媒体平台"),
    ("知乎", "社区/论坛/博客"),
    ("CSDN", "社区/论坛/博客"),
    ("微博", "社区/论坛/博客"),
    ("抖音", "视频平台"),
    ("哔哩哔哩", "视频平台"),
    ("新华网", "央媒/主流媒体"),
    ("人民网", "央媒/主流媒体"),
    ("艾瑞咨询", "教育/学术"),
    ("国家市场监督管理总局", "政府/公共机构"),
]

# 已知域名 -> 分类（用于真实回答里的 URL 归类）
_DOMAIN_CATEGORY = {
    "zhihu.com": "社区/论坛/博客",
    "xiaohongshu.com": "社区/论坛/博客",
    "weibo.com": "社区/论坛/博客",
    "csdn.net": "社区/论坛/博客",
    "douyin.com": "视频平台",
    "bilibili.com": "视频平台",
    "toutiao.com": "门户/自媒体平台",
    "sohu.com": "门户/自媒体平台",
    "163.com": "门户/自媒体平台",
    "qq.com": "门户/自媒体平台",
    "xinhuanet.com": "央媒/主流媒体",
    "people.com.cn": "央媒/主流媒体",
    "gov.cn": "政府/公共机构",
    "edu.cn": "教育/学术",
    "baike.baidu.com": "官网/独立站/行业垂直",
    "baidu.com": "官网/独立站/行业垂直",
}

_DENTAL_KEYWORDS = ("口腔", "牙", "齿")
_URL_RE = re.compile(r"https?://[^\s)\]，。、）]+")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


def _seed(*parts: str) -> int:
    return int(hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:12], 16)


def _pool(brand: str, industry: str | None) -> list[tuple[str, str]]:
    blob = f"{brand}{industry or ''}"
    if any(k in blob for k in _DENTAL_KEYWORDS):
        return list(_DENTAL_SOURCES)
    return list(_GENERIC_SOURCES)


def categorize(host_or_name: str) -> str:
    """根据域名 / 站点名推断分类。"""
    h = host_or_name.lower()
    for dom, cat in _DOMAIN_CATEGORY.items():
        if dom in h:
            return cat
    if h.endswith(".gov.cn") or "gov" in h:
        return "政府/公共机构"
    if h.endswith(".edu.cn") or "edu" in h:
        return "教育/学术"
    return "官网/独立站/行业垂直"


def mock_sources(brand: str, industry: str | None, question: str, platform_key: str) -> list[dict[str, Any]]:
    """为一条（问题 × 平台）回答生成可信的引用来源。"""
    rnd = Random(_seed("src", brand, question, platform_key))
    pool = _pool(brand, industry)
    rnd.shuffle(pool)
    k = rnd.randint(3, 8)
    out = []
    for site, cat in pool[:k]:
        out.append(
            {
                "site": site,
                "category": cat,
                "url": f"https://www.baidu.com/s?wd={site} {question[:10]}",
                "title": f"{site}：{question[:14]}相关推荐与解析",
            }
        )
    return out


def extract_sources_from_text(text: str) -> list[dict[str, Any]]:
    """从真实回答文本里抽取 URL / markdown 链接作为来源。"""
    urls: list[str] = []
    urls.extend(_MD_LINK_RE.findall(text))
    urls.extend(_URL_RE.findall(text))

    seen: set[str] = set()
    out = []
    for u in urls:
        host = urlparse(u).netloc or u
        if host in seen:
            continue
        seen.add(host)
        out.append(
            {
                "site": host.replace("www.", ""),
                "category": categorize(host),
                "url": u,
                "title": host.replace("www.", ""),
            }
        )
    return out


def normalize_source(raw: dict[str, Any]) -> dict[str, Any]:
    """把 worker 抓到的原始来源（site 可能是整条 URL）规整为标准结构。"""
    url = raw.get("url") or raw.get("site") or ""
    host = urlparse(url).netloc if url.startswith("http") else (raw.get("site") or "")
    host = host.replace("www.", "")
    site = host or (raw.get("site") or "未知来源")
    category = raw.get("category") or categorize(site)
    title = (raw.get("title") or "").strip() or site
    return {"site": site, "category": category, "url": url, "title": title}


def aggregate_citations(answers: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    """把逐条来源聚合成引用来源榜单。"""
    by_site: dict[str, dict[str, Any]] = {}
    questions_of: dict[str, set[str]] = defaultdict(set)
    platforms_of: dict[str, set[str]] = defaultdict(set)

    for a in answers:
        for s in a.get("sources", []) or []:
            site = s.get("site")
            if not site:
                continue
            entry = by_site.setdefault(
                site,
                {
                    "site": site,
                    "category": s.get("category") or categorize(site),
                    "url": s.get("url", ""),
                    "title": s.get("title") or site,
                    "cite_count": 0,
                },
            )
            entry["cite_count"] += 1
            questions_of[site].add(a.get("question", ""))
            platforms_of[site].add(a.get("platform", ""))

    rows = []
    for site, entry in by_site.items():
        rows.append(
            {
                **entry,
                "questions": len(questions_of[site]),
                "platforms": sorted(platforms_of[site]),
            }
        )
    rows.sort(key=lambda r: (r["cite_count"], r["questions"]), reverse=True)
    return rows[:limit]
