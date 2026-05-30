"""AI 提供方的统一接口。

一个 Provider 既能扮演「答案引擎」（模拟用户向某个 AI 平台提问并拿到回答），
也能扮演「分析器」（用 LLM 判断回答里有没有提到目标品牌等）。
"""
from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    name: str

    def chat(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> str:
        """发送一次对话，返回模型的文本输出。"""
        ...
