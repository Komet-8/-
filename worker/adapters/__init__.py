"""适配器注册表——配置驱动。

所有平台共用 GenericAdapter，差异在 worker/selectors.json。
按平台 id 或显示名取 spec，再构造适配器。
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import BaseAdapter, ScrapeResult
from .generic import GenericAdapter

_SPEC_PATH = Path(__file__).resolve().parent.parent / "selectors.json"


def load_specs() -> dict[str, dict]:
    with open(_SPEC_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_spec(platform: str) -> dict | None:
    """按平台 id（deepseek）或显示名（DeepSeek）取选择器配置。"""
    specs = load_specs()
    if platform in specs:
        return specs[platform]
    for spec in specs.values():
        if spec.get("name") == platform:
            return spec
    return None


def build_adapter(page, platform: str, *, channel: str = "网页", thinking: bool = True):
    spec = get_spec(platform)
    if not spec:
        return None
    return GenericAdapter(page, spec, channel=channel, thinking=thinking)


__all__ = ["BaseAdapter", "ScrapeResult", "GenericAdapter", "load_specs", "get_spec", "build_adapter"]
