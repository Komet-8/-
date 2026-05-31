"""Provider 工厂 + 平台注册表辅助。"""
from __future__ import annotations

from ..config import Settings
from ..platforms import PLATFORMS, get_platform
from .ark import ArkProvider
from .base import AIProvider

__all__ = [
    "AIProvider",
    "ArkProvider",
    "build_provider",
    "platform_registry",
    "default_targets",
]


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


def platform_registry(settings: Settings) -> list[dict]:
    """供前端渲染平台选择网格。"""
    out = []
    for p in PLATFORMS:
        out.append(
            {
                "id": p.id,
                "name": p.name,
                "label": p.label,
                "color": p.color,
                "channels": list(p.channels),
                "thinking_label": p.thinking_label,
                # 仅豆包在配置了 key 时可真实调用；其余需本地浏览器自动化
                "api_capable": bool(p.api_capable and settings.use_real_provider),
            }
        )
    return out


def default_targets(settings: Settings) -> list[dict]:
    """默认运行单元：豆包/DeepSeek/千问 的手机端（对齐爱搜默认勾选）。"""
    out = []
    for name in ("豆包", "DeepSeek", "千问"):
        p = get_platform(name)
        if not p:
            continue
        channel = "手机" if "手机" in p.channels else p.channels[0]
        out.append({"platform": name, "channel": channel, "thinking": True})
    return out
