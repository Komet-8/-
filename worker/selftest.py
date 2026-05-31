"""worker 离线自测——不依赖任何真实站点。

用 GenericAdapter 驱动本地 testpage/chat.html，验证整套抓取机制：
  打开 → 开启「深度思考」→ 填写并发送 → 等「停止」消失 → 抓正文 + 引用链接

通过条件：抓到的正文含目标品牌、且解析出 >=1 条引用来源。
这样在没有真实登录态/网络的环境里也能保证「机制」是对的，
真实站点只需在 selectors.json 里把选择器换成对应的即可。
"""
from __future__ import annotations

import sys
from pathlib import Path

from adapters.generic import GenericAdapter

HERE = Path(__file__).resolve().parent
PAGE = (HERE / "testpage" / "chat.html").as_uri()

# 与 testpage/chat.html 结构匹配的本地 spec
SPEC = {
    "name": "MockChat",
    "url": PAGE,
    "input": "textarea",
    "send": None,
    "send_key": "Enter",
    "thinking_toggle_text": "深度思考",
    "thinking_active_class": "active",
    "stop_text": "停止",
    "answer": "#answer",
    "citation": "a[href^='http']",
}


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print(f"[selftest] 需要 playwright：{e}")
        return 2

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        adapter = GenericAdapter(page, SPEC, channel="网页", thinking=True)
        result = adapter.run("做牙齿矫正哪家机构性价比更高？", timeout_ms=20_000)

        # 校验：深度思考已开启
        toggle_cls = page.locator(".thinking-toggle").get_attribute("class") or ""
        browser.close()

    ok = True
    print("---- 抓到的正文 ----")
    print(result.text)
    print("---- 引用来源 ----")
    for s in result.sources:
        print("  -", s["url"])

    if "瑞泰口腔" not in result.text:
        print("[FAIL] 正文未包含预期品牌"); ok = False
    if "1." not in result.text and "1．" not in result.text and "北京大学口腔医院" not in result.text:
        print("[FAIL] 正文未包含编号列表"); ok = False
    if len(result.sources) < 1:
        print("[FAIL] 未解析到引用来源"); ok = False
    if "active" not in toggle_cls:
        print("[FAIL] 深度思考开关未被开启"); ok = False

    print("\n[selftest]", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
