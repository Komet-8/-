# 本地浏览器自动化 Worker（"像爱搜一样"的真实抓取层）

## 为什么需要它

经分析，爱搜的核心并不是"单纯调 API"，而是**驱动真实的消费端 AI**（网页端 / 手机端 App），
依据有三点（见仓库根 README 的「实现原理分析」）：

1. 记录里区分「豆包·**手机**版 / DeepSeek·**手机**版」——API 不分网页/手机，只有真实端才有；
2. 有「思考 / 深度思考」开关——这是 App 里的按钮，不是 API 参数；
3. 有「引用来源」面板（带网站、分类、引用率）——只有**开启联网搜索的消费端**才会返回来源。

加上元宝、文心、Kimi、**AI抖音**这些根本没有好用公开 API 的平台，**只能靠浏览器/设备自动化**。

> 因此这一层必须运行在**你本地**（有你的登录态、在国内网络环境）。云端容器无法访问你本地 Chrome，
> 也无法登录这些站点。后端的云端部分负责"编排 + 分析 + 报告"，本 worker 负责"真实抓取"。

## 架构

```
浏览器 Worker (本地, Playwright)                后端 (FastAPI)
┌─────────────────────────────┐    POST 任务结果   ┌──────────────────┐
│ 复用你已登录的 Chrome 资料    │ ───────────────▶ │ /api/ingest      │
│ 逐个平台适配器：             │                   │ 分析品牌提及/排名 │
│  doubao / deepseek / qwen…   │ ◀─────────────── │ 汇总→落库→报告    │
│  输入问题→开思考→等流式完成   │    拉取待执行任务  │ /api/jobs/next   │
│  抓正文 + 引用来源角标        │                   └──────────────────┘
└─────────────────────────────┘
```

## 安装与运行（本地 Mac）

```bash
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# 复用你本地登录态：用持久化用户目录（首次需手动登录各平台一次）
export AIDSO_USER_DATA_DIR="$HOME/.aidso-chrome"
export AIDSO_BACKEND="http://localhost:8000"

python run.py --platform deepseek --channel 网页 --thinking \
  --question "做牙齿矫正哪家机构性价比更高？"
```

首跑会打开一个带界面的 Chromium，请在其中登录 DeepSeek/豆包/千问等；
之后登录态保存在 `AIDSO_USER_DATA_DIR`，可无人值守复跑。

## 适配器状态

| 平台 | 适配器 | 状态 |
| --- | --- | --- |
| DeepSeek | `adapters/deepseek.py` | 选择器骨架，待按真实页面校准 |
| 豆包 | `adapters/doubao.py` | 骨架（云端已有 API 路径，可二选一） |
| 千问 | `adapters/qwen.py` | 骨架 |
| 元宝 / 文心 / Kimi / 百度AI / AI抖音 | TODO | 复制骨架按需补 |

> 选择器（输入框、发送、思考开关、引用角标）需要按各站点当前 DOM 校准——
> 这部分必须在能打开真实页面的本地环境里调。骨架已把"在哪儿改"标注清楚。
