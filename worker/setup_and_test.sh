#!/usr/bin/env bash
# 本地一键安装 + 自检 + 离线自测。
# 用法：在 worker/ 目录下执行  bash setup_and_test.sh
set -e

cd "$(dirname "$0")"
echo "==> [1/5] 创建虚拟环境 .venv"
python3 -m venv .venv
source .venv/bin/activate

echo "==> [2/5] 安装依赖"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "==> [3/5] 下载 Chromium（首次约 30s~2min）"
python -m playwright install chromium

echo "==> [4/5] 环境自检 (doctor)"
python run.py --doctor || true

echo "==> [5/5] 离线自测 (selftest，不连任何真实站点)"
python selftest.py

cat <<'TIP'

============================================================
 ✅ 安装与离线自测完成。

 下一步——校准某个真实平台（以 DeepSeek 为例）：

   source .venv/bin/activate
   export AIDSO_USER_DATA_DIR="$HOME/.aidso-chrome"   # 登录态保存目录
   python run.py --inspect --platform deepseek \
       --question "做牙齿矫正哪家机构性价比更高？"

 会弹出浏览器：手动登录 DeepSeek → 回到对话页 → 回到终端按回车。
 采集结果在 worker/captures/deepseek.inspect.json / .png / .html
 把 .json 和 .png 发给我，我据此给你精确的 selectors.json。
============================================================
TIP
