"""本地浏览器自动化 Worker 入口。

两种模式：
1) 单次抓取（调试用）：
     python run.py --platform deepseek --channel 网页 --thinking \
        --question "做牙齿矫正哪家机构性价比更高？"

2) 队列模式（与后端对接）：从后端拉任务、抓取、回传结果。
     python run.py --serve

复用本地登录态：通过持久化用户目录（AIDSO_USER_DATA_DIR），
首次需在弹出的浏览器里手动登录各平台，之后可无人值守。
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

from adapters import get_adapter

USER_DATA_DIR = os.environ.get("AIDSO_USER_DATA_DIR", os.path.expanduser("~/.aidso-chrome"))
BACKEND = os.environ.get("AIDSO_BACKEND", "http://localhost:8000")

# 平台 id -> 显示名
ID_TO_NAME = {
    "deepseek": "DeepSeek", "doubao": "豆包", "qwen": "千问",
    "yuanbao": "元宝", "wenxin": "文心", "kimi": "Kimi",
    "baidu": "百度AI", "douyin": "AI抖音",
}


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


def scrape_once(platform_name: str, channel: str, thinking: bool, question: str, headless: bool):
    adapter_cls = get_adapter(platform_name)
    if not adapter_cls:
        raise SystemExit(f"暂无 [{platform_name}] 的适配器，请在 worker/adapters/ 下新增。")

    pw, ctx = _make_context(headless)
    try:
        page = ctx.new_page()
        adapter = adapter_cls(page, channel=channel, thinking=thinking)
        result = adapter.run(question)
        return result
    finally:
        ctx.close()
        pw.stop()


def cmd_single(args):
    name = ID_TO_NAME.get(args.platform, args.platform)
    print(f"[worker] 抓取 {name}·{args.channel} thinking={args.thinking}")
    res = scrape_once(name, args.channel, args.thinking, args.question, headless=args.headless)
    print("=" * 60)
    print(res.text[:1500])
    print("=" * 60)
    print(f"引用来源 {len(res.sources)} 条：")
    for s in res.sources[:10]:
        print("  -", s.get("url") or s.get("site"))


def cmd_serve(args):
    """队列模式：轮询后端任务 → 抓取 → 回传。

    需后端实现 /api/jobs/next 与 /api/ingest（属本地协同扩展，按需开启）。
    """
    client = httpx.Client(base_url=BACKEND, timeout=180)
    print(f"[worker] serve 模式，backend={BACKEND}")
    while True:
        try:
            r = client.get("/api/jobs/next")
            if r.status_code == 204:
                time.sleep(3)
                continue
            job = r.json()
            name = ID_TO_NAME.get(job["platform"], job["platform"])
            res = scrape_once(name, job.get("channel", "网页"), job.get("thinking", True),
                              job["question"], headless=args.headless)
            client.post("/api/ingest", json={
                "job_id": job["id"],
                "platform": name,
                "channel": job.get("channel", "网页"),
                "question": job["question"],
                "text": res.text,
                "sources": res.sources,
            })
            print(f"[worker] 完成 job {job['id']} ({name})")
        except KeyboardInterrupt:
            print("\n[worker] 退出"); break
        except Exception as e:  # noqa: BLE001
            print(f"[worker] 出错：{e}", file=sys.stderr)
            time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description="爱搜式本地浏览器自动化 Worker")
    ap.add_argument("--platform", default="deepseek", help="平台 id：deepseek/doubao/qwen…")
    ap.add_argument("--channel", default="网页", choices=["网页", "手机"])
    ap.add_argument("--thinking", action="store_true", help="开启深度思考")
    ap.add_argument("--question", help="单次抓取的问题")
    ap.add_argument("--serve", action="store_true", help="队列模式")
    ap.add_argument("--headless", action="store_true", help="无头模式（首次登录请勿开启）")
    args = ap.parse_args()

    if args.serve:
        cmd_serve(args)
    elif args.question:
        cmd_single(args)
    else:
        ap.error("请提供 --question 或 --serve")


if __name__ == "__main__":
    main()
