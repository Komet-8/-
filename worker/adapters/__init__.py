"""平台适配器注册表。"""
from __future__ import annotations

from .base import BaseAdapter, ScrapeResult
from .deepseek import DeepSeekAdapter
from .doubao import DoubaoAdapter
from .qwen import QwenAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "DeepSeek": DeepSeekAdapter,
    "豆包": DoubaoAdapter,
    "千问": QwenAdapter,
    # TODO: 元宝 / 文心 / Kimi / 百度AI / AI抖音 —— 复制骨架按需补
}


def get_adapter(name: str) -> type[BaseAdapter] | None:
    return ADAPTERS.get(name)


__all__ = ["BaseAdapter", "ScrapeResult", "ADAPTERS", "get_adapter"]
