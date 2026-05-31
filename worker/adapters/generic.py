"""配置驱动的通用适配器。

所有平台共用同一套抓取流程，差异只在 selectors.json 里的选择器。
这样校准时只改 JSON、不动 Python，新增平台也只是加一段 JSON。

流程：open → ensure_thinking → ask → wait_complete → collect
"""
from __future__ import annotations

from .base import BaseAdapter, ScrapeResult


class GenericAdapter(BaseAdapter):
    def __init__(self, page, spec: dict, *, channel: str = "网页", thinking: bool = True):
        super().__init__(page, channel=channel, thinking=thinking)
        self.spec = spec
        self.name = spec.get("name", "未知")

    # —— 流程实现 ——
    def open(self) -> None:
        self.page.goto(self.spec["url"], wait_until="domcontentloaded")
        self.page.wait_for_selector(self.spec["input"], timeout=30_000)

    def ensure_thinking(self) -> None:
        if not self.thinking:
            return
        text = self.spec.get("thinking_toggle_text")
        if not text:
            return
        try:
            btn = self.page.get_by_text(text, exact=False).first
            active_cls = self.spec.get("thinking_active_class") or ""
            cls = btn.get_attribute("class") or ""
            already_on = active_cls and active_cls in cls
            if not already_on:
                btn.click()
        except Exception:
            pass  # 没有该开关则忽略

    def ask(self, question: str) -> None:
        box = self.page.locator(self.spec["input"]).last
        box.click()
        box.fill(question)
        send_sel = self.spec.get("send")
        if send_sel:
            try:
                self.page.locator(send_sel).last.click()
                return
            except Exception:
                pass
        self.page.keyboard.press(self.spec.get("send_key", "Enter"))

    def wait_complete(self, timeout_ms: int = 120_000) -> None:
        """等待流式回答结束。

        策略（语言/平台无关，几乎免校准）：
        先可选地等"停止"按钮出现以确认开始生成；随后轮询回答容器的文本长度，
        当连续若干轮不再增长即判定完成。stop_text 只作"开始信号"，不强依赖。
        """
        stop_text = self.spec.get("stop_text")
        if stop_text:
            try:  # 等生成开始（出现"停止/Stop"），最多等 12s
                self.page.get_by_text(stop_text, exact=False).wait_for(timeout=12_000)
            except Exception:
                pass

        answer_sel = self.spec["answer"]
        poll_ms = 1_000
        stable_needed = 3          # 连续 3 轮(~3s)文本不变即认为完成
        max_rounds = max(1, timeout_ms // poll_ms)
        last = ""
        stable = 0
        for _ in range(int(max_rounds)):
            try:
                txt = self.page.locator(answer_sel).last.inner_text()
            except Exception:
                txt = ""
            if txt and txt == last:
                stable += 1
                if stable >= stable_needed:
                    return
            else:
                stable = 0
                last = txt
            self.page.wait_for_timeout(poll_ms)
        # 超时则带着已有内容返回，由 collect 决定

    def collect(self) -> ScrapeResult:
        answer = self.page.locator(self.spec["answer"]).last
        try:
            text = answer.inner_text()
        except Exception:
            text = ""

        # 引用来源：可选 page 级作用域（某些平台来源在回答容器外的"参考"面板）
        cite_sel = self.spec.get("citation")
        cite_scope = self.spec.get("citation_scope", "answer")  # answer | page
        scope = self.page if cite_scope == "page" else answer
        sources: list[dict] = []
        if cite_sel:
            try:
                seen = set()
                for a in scope.locator(cite_sel).all():
                    href = a.get_attribute("href") or ""
                    if href.startswith("http") and href not in seen:
                        seen.add(href)
                        sources.append(
                            {"site": href, "category": "", "url": href, "title": (a.inner_text() or "").strip()}
                        )
            except Exception:
                pass

        try:
            html = answer.inner_html()
        except Exception:
            html = None
        return ScrapeResult(text=text, sources=sources, raw_html=html)
