"""豆包网页端适配器（骨架）。

注意：豆包在云端已可经火山方舟 API 真实接入；此适配器用于需要"真实 App 体验
（含联网引用角标）"时的网页抓取路径，二者可二选一。

⚠️ 选择器需按 https://www.doubao.com 当前 DOM 校准。
"""
from __future__ import annotations

from .base import BaseAdapter, ScrapeResult

URL = "https://www.doubao.com/chat/"

SEL_INPUT = "textarea"
TXT_THINK = "深度思考"
TXT_STOP = "停止"
SEL_ANSWER = "div[class*='message'], div[class*='markdown']"
SEL_CITATION = "a[href^='http']"


class DoubaoAdapter(BaseAdapter):
    name = "豆包"

    def open(self) -> None:
        self.page.goto(URL, wait_until="domcontentloaded")
        self.page.wait_for_selector(SEL_INPUT, timeout=30_000)

    def ensure_thinking(self) -> None:
        if not self.thinking:
            return
        try:
            self.page.get_by_text(TXT_THINK, exact=False).first.click()
        except Exception:
            pass

    def ask(self, question: str) -> None:
        box = self.page.locator(SEL_INPUT).last
        box.click()
        box.fill(question)
        self.page.keyboard.press("Enter")

    def wait_complete(self, timeout_ms: int = 120_000) -> None:
        try:
            self.page.get_by_text(TXT_STOP, exact=False).wait_for(state="hidden", timeout=timeout_ms)
        except Exception:
            self.page.wait_for_timeout(2_000)

    def collect(self) -> ScrapeResult:
        answer = self.page.locator(SEL_ANSWER).last
        text = answer.inner_text()
        sources = []
        try:
            for a in answer.locator(SEL_CITATION).all():
                href = a.get_attribute("href") or ""
                if href.startswith("http"):
                    sources.append({"site": href, "category": "", "url": href, "title": a.inner_text()})
        except Exception:
            pass
        return ScrapeResult(text=text, sources=sources, raw_html=answer.inner_html())
