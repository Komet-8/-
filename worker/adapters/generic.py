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
        stop_text = self.spec.get("stop_text")
        if stop_text:
            # 先等"停止"出现(开始生成)，再等它消失(生成结束)
            try:
                self.page.get_by_text(stop_text, exact=False).wait_for(timeout=15_000)
            except Exception:
                pass
            try:
                self.page.get_by_text(stop_text, exact=False).wait_for(
                    state="hidden", timeout=timeout_ms
                )
                return
            except Exception:
                pass
        # 兜底：等网络空闲 + 固定等待
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass
        self.page.wait_for_timeout(2_000)

    def collect(self) -> ScrapeResult:
        answer = self.page.locator(self.spec["answer"]).last
        text = answer.inner_text()
        sources: list[dict] = []
        cite_sel = self.spec.get("citation")
        if cite_sel:
            try:
                seen = set()
                for a in answer.locator(cite_sel).all():
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
