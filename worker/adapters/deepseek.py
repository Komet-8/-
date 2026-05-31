"""DeepSeek 网页端适配器（骨架）。

⚠️ 选择器需按 https://chat.deepseek.com 的当前 DOM 校准。
下面用了较稳健的"按可见文本/role 定位"策略，但仍需在本地真实页面里验证。
"""
from __future__ import annotations

from .base import BaseAdapter, ScrapeResult

URL = "https://chat.deepseek.com/"

# —— 待校准选择器 ——
SEL_INPUT = "textarea"                       # 输入框
SEL_SEND = "div[role='button']:has(svg)"     # 发送按钮（示意）
TXT_DEEP_THINK = "深度思考"                    # 思考开关按钮文案
TXT_STOP = "停止"                             # 生成中出现的"停止"按钮文案
SEL_ANSWER = "div.markdown, div[class*='message']"  # 回答容器
SEL_CITATION = "a[href^='http']"             # 引用角标链接


class DeepSeekAdapter(BaseAdapter):
    name = "DeepSeek"

    def open(self) -> None:
        self.page.goto(URL, wait_until="domcontentloaded")
        self.page.wait_for_selector(SEL_INPUT, timeout=30_000)

    def ensure_thinking(self) -> None:
        if not self.thinking:
            return
        try:
            btn = self.page.get_by_text(TXT_DEEP_THINK, exact=False).first
            cls = (btn.get_attribute("class") or "")
            # 已激活则不重复点击（按真实 active 类名校准）
            if "active" not in cls and "selected" not in cls:
                btn.click()
        except Exception:
            pass  # 没有该开关则忽略

    def ask(self, question: str) -> None:
        box = self.page.locator(SEL_INPUT).last
        box.click()
        box.fill(question)
        self.page.keyboard.press("Enter")

    def wait_complete(self, timeout_ms: int = 120_000) -> None:
        # 先等"停止"出现（开始生成），再等它消失（生成结束）
        try:
            self.page.get_by_text(TXT_STOP, exact=False).wait_for(timeout=15_000)
        except Exception:
            pass
        try:
            self.page.get_by_text(TXT_STOP, exact=False).wait_for(
                state="hidden", timeout=timeout_ms
            )
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
