"""AI 平台注册表。

每个平台可有「网页 / 手机」两个渠道，以及「思考 / 深度思考」开关——
这对应爱搜界面里每张平台卡片的勾选项，也是诊断记录里
「豆包·手机」「DeepSeek·手机」这种命名的来源。

注意：除豆包通过火山方舟 API 真实接入外，其余平台（DeepSeek/元宝/千问/
百度AI/文心/Kimi/AI抖音）的真实结果需要在本地用浏览器自动化抓取
（见 providers/browser/），云端默认走模拟数据。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Platform:
    id: str
    name: str
    label: str                  # 头像文字
    color: str                  # 头像底色
    channels: tuple[str, ...]   # 可用渠道：网页 / 手机
    thinking_label: str         # 思考开关文案：思考 / 深度
    api_capable: bool = False   # 是否已接入真实 API（仅豆包）


# 顺序对齐爱搜界面从左到右
PLATFORMS: list[Platform] = [
    Platform("doubao", "豆包", "豆", "#3b82f6", ("网页", "手机"), "思考", api_capable=True),
    Platform("deepseek", "DeepSeek", "DS", "#4f46e5", ("网页", "手机"), "深度"),
    Platform("yuanbao", "元宝", "元", "#12b76a", ("网页", "手机"), "深度"),
    Platform("qwen", "千问", "千", "#615ced", ("网页", "手机"), "深度"),
    Platform("baidu", "百度AI", "百", "#7c5cfc", ("网页",), "深度"),
    Platform("wenxin", "文心", "文", "#3b82f6", ("网页",), "深度"),
    Platform("kimi", "Kimi", "Km", "#111827", ("网页",), "思考"),
    Platform("douyin", "AI抖音", "抖", "#111827", ("网页",), "深度"),
]

_BY_NAME = {p.name: p for p in PLATFORMS}
_BY_ID = {p.id: p for p in PLATFORMS}


def get_platform(name_or_id: str) -> Platform | None:
    return _BY_NAME.get(name_or_id) or _BY_ID.get(name_or_id)


def run_key(platform_name: str, channel: str) -> str:
    """诊断结果里一个「运行单元」的展示名，如「豆包·手机」。"""
    return f"{platform_name}·{channel}"


def platform_of_key(key: str) -> str:
    """从运行单元名取回平台名：「豆包·手机」-> 「豆包」。"""
    return key.split("·", 1)[0]
