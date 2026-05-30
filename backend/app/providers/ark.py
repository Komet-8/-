"""火山方舟 / 豆包 Provider（OpenAI 兼容协议）。"""
from __future__ import annotations

import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class ArkProvider:
    """通过 OpenAI 兼容接口调用豆包（Doubao）模型。"""

    name = "doubao"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 60):
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model

    def chat(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {"model": self._model, "messages": messages, "temperature": 0.7}
        if json_mode:
            # 部分豆包模型支持 JSON 模式；不支持也不报错，下游会做兜底解析。
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception:  # noqa: BLE001 —— 上层会捕获并降级
            if json_mode:
                # JSON 模式可能不被支持，去掉后重试一次
                kwargs.pop("response_format", None)
                resp = self._client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            raise
