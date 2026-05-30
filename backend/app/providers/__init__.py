"""Provider 工厂。"""
from __future__ import annotations

from ..config import Settings
from .ark import ArkProvider
from .base import AIProvider

__all__ = ["AIProvider", "ArkProvider", "build_provider", "available_platforms"]


def build_provider(settings: Settings) -> AIProvider | None:
    """有 API Key 时返回真实豆包 Provider，否则返回 None（走模拟数据）。"""
    if settings.use_real_provider:
        return ArkProvider(
            api_key=settings.ark_api_key,  # type: ignore[arg-type]
            base_url=settings.ark_base_url,
            model=settings.ark_model,
            timeout=settings.request_timeout,
        )
    return None


def available_platforms(settings: Settings) -> list[str]:
    """可用的「AI 平台」列表。

    真实模式下当前仅接入了豆包；模拟模式下提供多个平台以贴近真实产品形态。
    """
    if settings.use_real_provider:
        return ["豆包"]
    return ["豆包", "DeepSeek", "千问"]
