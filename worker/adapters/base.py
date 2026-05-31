"""平台适配器基类。

每个适配器负责：在某个 AI 的网页/手机端，输入一个问题、（可选）开启深度思考、
等待流式回答结束，然后抓取「回答正文」和「引用来源角标」。

所有 UI 选择器都集中在子类顶部常量里，便于按真实页面校准——
这是整套方案里唯一与"页面长什么样"强耦合的部分。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScrapeResult:
    text: str
    sources: list[dict] = field(default_factory=list)  # [{site, category, url, title}]
    raw_html: str | None = None


class BaseAdapter:
    #: 平台显示名，对齐后端 platforms.py
    name: str = "base"

    def __init__(self, page, *, channel: str = "网页", thinking: bool = True):
        self.page = page
        self.channel = channel
        self.thinking = thinking

    # —— 子类需实现 ——
    def open(self) -> None:
        """导航到对话页面（必要时切换网页/手机视图）。"""
        raise NotImplementedError

    def ensure_thinking(self) -> None:
        """根据 self.thinking 打开/关闭「深度思考」。无该功能则忽略。"""

    def ask(self, question: str) -> None:
        """把问题填入输入框并发送。"""
        raise NotImplementedError

    def wait_complete(self, timeout_ms: int = 120_000) -> None:
        """等待流式回答结束（通常等"停止生成"按钮消失/"发送"按钮恢复）。"""
        raise NotImplementedError

    def collect(self) -> ScrapeResult:
        """抓取最新一条回答的正文与引用来源。"""
        raise NotImplementedError

    # —— 通用编排 ——
    def run(self, question: str, *, timeout_ms: int = 120_000) -> ScrapeResult:
        self.open()
        self.ensure_thinking()
        self.ask(question)
        self.wait_complete(timeout_ms=timeout_ms)
        return self.collect()
