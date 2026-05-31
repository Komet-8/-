"""本地浏览器自动化 Worker 入口。

子命令（用法见 README）：
  --doctor                环境自检：Playwright/Chromium/网络/登录目录
  --inspect --platform X  打开页面→你登录→回车→dump 候选选择器+截图+HTML（校准用）
  --question "…"          单次抓取（调试）
  --serve                 队列模式：从后端拉任务、抓取、回传

复用本地登录态：持久化用户目录 AIDSO_USER_DATA_DIR，首次需手动登录各平台。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from adapters import build_adapter, get_spec, load_specs

USER_DATA_DIR = os.environ.get("AIDSO_USER_DATA_DIR", os.path.expanduser("~/.aidso-chrome"))
BACKEND = os.environ.get("AIDSO_BACKEND", "http://localhost:8000")
OUT_DIR = os.environ.get("AIDSO_OUT_DIR", os.path.join(os.path.dirname(__file__), "captures"))

ID_TO_NAME = {k: v["name"] for k, v in load_specs().items()}


def _make_context(headless: bool):
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=headless,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    return pw, ctx


# ───────────────────────── doctor ─────────────────────────
def cmd_doctor(_args):
    ok = True
    print("== AIDSO worker doctor ==")
    try:
        import playwright  # noqa: F401
        print("[ok] playwright 已安装")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"[!!] playwright 未安装：{e}  ->  pip install -r requirements.txt")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            exe = pw.chromium.executable_path
            print(f"[ok] Chromium: {exe}")
            if not os.path.exists(exe):
                ok = False
                print("[!!] Chromium 未下载  ->  python -m playwright install chromium")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"[!!] 无法初始化 Chromium：{e}")

    print(f"[..] 登录态目录 AIDSO_USER_DATA_DIR = {USER_DATA_DIR}")
    print(f"[..] 后端 AIDSO_BACKEND = {BACKEND}")
    specs = load_specs()
    ready = [k for k, v in specs.items() if v.get("ready")]
    todo = [k for k, v in specs.items() if not v.get("ready")]
    print(f"[..] 已标记可用平台: {', '.join(ready) or '无'}")
    print(f"[..] 待校准平台: {', '.join(todo) or '无'}")
    print("== 结果:", "OK" if ok else "存在问题，请按上面提示修复", "==")
    return 0 if ok else 1


# ───────────────────────── inspect ─────────────────────────
def cmd_inspect(args):
    """打开页面，等你登录并就绪，然后采集候选选择器 + 截图 + HTML，便于校准。"""
    name = ID_TO_NAME.get(args.platform, args.platform)
    spec = get_spec(args.platform)
    if not spec:
        raise SystemExit(f"selectors.json 里没有 [{args.platform}]")
    os.makedirs(OUT_DIR, exist_ok=True)
    pw, ctx = _make_context(headless=False)
    try:
        page = ctx.new_page()
        print(f"[inspect] 打开 {spec['url']} …")
        page.goto(spec["url"], wait_until="domcontentloaded")
        print("[inspect] 请在浏览器里完成登录，并停在对话首页。")
        if args.question:
            input(f"[inspect] 准备好后回车，我会先发一条测试问题：{args.question!r} > ")
            try:
                box = page.locator(spec["input"]).last
                box.click(); box.fill(args.question)
                page.keyboard.press(spec.get("send_key", "Enter"))
                print("[inspect] 已发送，等待 12s 让回答生成…")
                page.wait_for_timeout(12_000)
            except Exception as e:  # noqa: BLE001
                print(f"[inspect] 发送测试问题失败（不影响采集）：{e}")
        else:
            input("[inspect] 登录并就绪后回车开始采集 > ")

        report = _probe(page, spec)
        base = os.path.join(OUT_DIR, args.platform)
        with open(base + ".inspect.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        page.screenshot(path=base + ".png", full_page=True)
        with open(base + ".html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("\n[inspect] 采集完成，请把以下文件发我校准：")
        print("   ", base + ".inspect.json")
        print("   ", base + ".png")
        print("   ", base + ".html")
        print("\n候选输入框 / 按钮预览：")
        print(json.dumps(report["candidates"], ensure_ascii=False, indent=2)[:1500])
    finally:
        ctx.close(); pw.stop()


def _probe(page, spec: dict) -> dict:
    """在页面里探测候选选择器，验证当前 spec 是否命中。"""
    js = r"""
    () => {
      const vis = el => { const r = el.getBoundingClientRect();
        return r.width>0 && r.height>0 && getComputedStyle(el).visibility!=='hidden'; };
      const desc = el => ({
        tag: el.tagName.toLowerCase(),
        cls: (el.className||'').toString().slice(0,120),
        ph: el.getAttribute && (el.getAttribute('placeholder')||''),
        text: (el.innerText||'').trim().slice(0,40),
      });
      const inputs = [...document.querySelectorAll('textarea, [contenteditable=\"true\"], input[type=text]')]
        .filter(vis).map(desc);
      const btns = [...document.querySelectorAll('button, [role=button]')]
        .filter(vis).map(desc).filter(b => b.text);
      const links = [...document.querySelectorAll('a[href^=\"http\"]')].slice(0,40)
        .map(a => ({text:(a.innerText||'').trim().slice(0,30), href:a.href}));
      return {inputs, buttons: btns.slice(0,60), links};
    }
    """
    cands = page.evaluate(js)

    def count(sel):
        try:
            return page.locator(sel).count()
        except Exception:
            return -1

    hits = {
        "input": count(spec["input"]),
        "answer": count(spec["answer"]),
        "citation": count(spec.get("citation") or "a[href^='http']"),
    }
    return {"url": spec["url"], "spec_name": spec.get("name"), "current_spec_hits": hits, "candidates": cands}


# ───────────────────────── single ─────────────────────────
def scrape_once(platform: str, channel: str, thinking: bool, question: str, headless: bool):
    pw, ctx = _make_context(headless)
    try:
        page = ctx.new_page()
        adapter = build_adapter(page, platform, channel=channel, thinking=thinking)
        if not adapter:
            raise SystemExit(f"selectors.json 里没有 [{platform}]")
        return adapter.run(question)
    finally:
        ctx.close(); pw.stop()


def cmd_single(args):
    name = ID_TO_NAME.get(args.platform, args.platform)
    print(f"[worker] 抓取 {name}·{args.channel} thinking={args.thinking}")
    res = scrape_once(args.platform, args.channel, args.thinking, args.question, headless=args.headless)
    print("=" * 60); print(res.text[:1500]); print("=" * 60)
    print(f"引用来源 {len(res.sources)} 条：")
    for s in res.sources[:10]:
        print("  -", s.get("url") or s.get("site"))


# ───────────────────────── serve ─────────────────────────
def cmd_serve(args):
    import httpx

    client = httpx.Client(base_url=BACKEND, timeout=180)
    print(f"[worker] serve 模式，backend={BACKEND}")
    while True:
        try:
            r = client.get("/api/jobs/next")
            if r.status_code == 204:
                time.sleep(3); continue
            job = r.json()
            res = scrape_once(job["platform"], job.get("channel", "网页"),
                              job.get("thinking", True), job["question"], headless=args.headless)
            client.post("/api/ingest", json={
                "job_id": job["id"], "platform": ID_TO_NAME.get(job["platform"], job["platform"]),
                "channel": job.get("channel", "网页"), "question": job["question"],
                "text": res.text, "sources": res.sources,
            })
            print(f"[worker] 完成 job {job['id']}")
        except KeyboardInterrupt:
            print("\n[worker] 退出"); break
        except Exception as e:  # noqa: BLE001
            print(f"[worker] 出错：{e}", file=sys.stderr); time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description="爱搜式本地浏览器自动化 Worker")
    ap.add_argument("--platform", default="deepseek", help="平台 id：deepseek/doubao/qwen…")
    ap.add_argument("--channel", default="网页", choices=["网页", "手机"])
    ap.add_argument("--thinking", action="store_true", help="开启深度思考")
    ap.add_argument("--question", help="问题文本")
    ap.add_argument("--doctor", action="store_true", help="环境自检")
    ap.add_argument("--inspect", action="store_true", help="采集页面选择器/截图/HTML 以校准")
    ap.add_argument("--serve", action="store_true", help="队列模式")
    ap.add_argument("--headless", action="store_true", help="无头模式（首次登录/采集请勿开启）")
    args = ap.parse_args()

    if args.doctor:
        raise SystemExit(cmd_doctor(args))
    if args.inspect:
        cmd_inspect(args)
    elif args.serve:
        cmd_serve(args)
    elif args.question:
        cmd_single(args)
    else:
        ap.error("请提供 --doctor / --inspect / --question / --serve 之一")


if __name__ == "__main__":
    main()
