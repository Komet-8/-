#!/bin/bash
# 桌面「GitHub同步」文件夹 ⇄ GitHub 私有仓库（macOS）
#
# 拖进桌面这个文件夹的文件/文件夹会自动上传到 GitHub 私有仓库（同名路径）；
# 仓库 main 分支上的改动（比如让 Claude 改完推到 main）也会自动拉回本地。
#
# 安装：/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Komet-8/-/claude/cool-franklin-s6z6tw/github-sync/install.sh)"
# 卸载：bash ~/.github-sync/uninstall.sh
#
# 可选环境变量（安装前设置）：
#   REPO_NAME    GitHub 仓库名，默认 desktop-sync
#   FOLDER_NAME  桌面文件夹名，默认 GitHub同步
set -euo pipefail

REPO_NAME="${REPO_NAME:-desktop-sync}"
FOLDER_NAME="${FOLDER_NAME:-GitHub同步}"
BASE="$HOME/.github-sync"
# 真实文件夹放在家目录：macOS 不允许后台任务直接读写「桌面」，桌面上放的是指向它的快捷方式
SYNC_DIR="$HOME/$FOLDER_NAME"
DESKTOP_LINK="$HOME/Desktop/$FOLDER_NAME"
LABEL="com.github-sync.desktop"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m错误：\033[0m%s\n' "$*" >&2; exit 1; }
xml() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

[ "$(uname)" = "Darwin" ] || die "这个脚本只支持 macOS。"
command -v git >/dev/null || die "没找到 git，先在终端运行：xcode-select --install"

# ---------- GitHub 登录 ----------
if ! command -v gh >/dev/null; then
  command -v brew >/dev/null || die "需要 GitHub CLI：先安装 Homebrew（https://brew.sh），再重新运行本脚本。"
  say "安装 GitHub CLI（gh）…"
  brew install gh
fi
if ! gh auth status -h github.com >/dev/null 2>&1; then
  say "登录 GitHub（会打开浏览器）…"
  gh auth login -h github.com -p https -w
fi
gh auth setup-git -h github.com
OWNER="$(gh api user -q .login)"
URL="https://github.com/$OWNER/$REPO_NAME"

# ---------- 私有仓库 ----------
if gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1; then
  [ "$(gh repo view "$OWNER/$REPO_NAME" --json visibility -q .visibility)" = "PRIVATE" ] \
    || die "$URL 已存在但不是私有仓库，为安全起见停止。换个 REPO_NAME 再试。"
  say "使用已有私有仓库 $URL"
else
  say "创建私有仓库 $URL"
  gh repo create "$OWNER/$REPO_NAME" --private --description "Mac 桌面「${FOLDER_NAME}」文件夹自动同步" >/dev/null
fi

# ---------- 本地文件夹 ----------
if [ -d "$SYNC_DIR/.git" ]; then
  cur="$(git -C "$SYNC_DIR" remote get-url origin 2>/dev/null || true)"
  case "$cur" in
    *"github.com/$OWNER/$REPO_NAME" | *"github.com/$OWNER/$REPO_NAME.git" | *"github.com:$OWNER/$REPO_NAME.git") ;;
    *) die "$SYNC_DIR 已经关联了别的仓库（${cur}）。换个 FOLDER_NAME 再试。" ;;
  esac
elif [ -e "$SYNC_DIR" ]; then
  die "$SYNC_DIR 已存在且不是同步文件夹，为免覆盖停止。先改名或换个 FOLDER_NAME。"
else
  err="$(git clone -q "$URL.git" "$SYNC_DIR" 2>&1)" || die "克隆 $URL 失败：$err"
fi

cd "$SYNC_DIR"
git config core.quotepath false
git config core.precomposeunicode true
if [ -z "$(git config user.email || true)" ]; then
  git config user.name "$OWNER"
  git config user.email "$OWNER@users.noreply.github.com"
fi

if ! git rev-parse -q --verify HEAD >/dev/null; then
  # 空仓库：写入初始文件
  git symbolic-ref HEAD refs/heads/main
  cat > .gitignore <<'EOF'
.DS_Store
._*
node_modules/
.venv/
__pycache__/
EOF
  cat > README.md <<EOF
# $REPO_NAME

这个私有仓库和 Mac 桌面上的「${FOLDER_NAME}」文件夹自动双向同步：

- 拖进桌面「${FOLDER_NAME}」的文件/文件夹，几十秒内出现在这里，路径和名字一样。
- 这里 \`main\` 分支上的改动，约 2 分钟内同步回桌面文件夹。
- 超过 95MB 的单个文件、自带 \`.git\` 的项目文件夹不会上传（会弹通知）。
EOF
  git add -A
  git commit -q -m "初始化桌面同步文件夹"
  git push -q -u origin main
fi
BRANCH="$(git symbolic-ref --short HEAD)"

# ---------- 桌面快捷方式 ----------
if [ -L "$DESKTOP_LINK" ] || [ ! -e "$DESKTOP_LINK" ]; then
  ln -sfn "$SYNC_DIR" "$DESKTOP_LINK" \
    || say "⚠️ 没能在桌面放快捷方式（终端没有桌面权限）。可以在访达里按住 Option+Command 把 $SYNC_DIR 拖到桌面。"
else
  say "⚠️ 桌面上已有同名的「${FOLDER_NAME}」，没有覆盖它；真正同步的是 $SYNC_DIR"
fi

# ---------- 同步脚本 ----------
mkdir -p "$BASE" "$HOME/Library/LaunchAgents"
{
  printf 'SYNC_DIR=%q\n' "$SYNC_DIR"
  printf 'BRANCH=%q\n' "$BRANCH"
  printf 'BASE=%q\n' "$BASE"
  printf 'FOLDER_NAME=%q\n' "$FOLDER_NAME"
  printf 'DESKTOP_LINK=%q\n' "$DESKTOP_LINK"
  printf 'LABEL=%q\n' "$LABEL"
  printf 'PLIST=%q\n' "$PLIST"
} > "$BASE/config"

cat > "$BASE/sync.sh" <<'EOF'
#!/bin/bash
# 「GitHub同步」文件夹 ⇄ GitHub（由 install.sh 生成；launchd 在文件夹变化时和每 2 分钟调用）
. "$HOME/.github-sync/config"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
LOG="$BASE/sync.log"
LOCK="$BASE/.lock"
NOTICE="$BASE/.last-notice"
MAX_MB=95

log() {
  local m
  m="$(date '+%F %T') $*"
  echo "$m" >> "$LOG"
  [ -t 1 ] && echo "$m"
  return 0
}
notify() {
  local s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  osascript -e "display notification \"$s\" with title \"$FOLDER_NAME\"" >/dev/null 2>&1 || true
}
# 同一条警告只弹一次，直到下次同步成功
warn_once() {
  [ "$(cat "$NOTICE" 2>/dev/null)" = "$1" ] && return 0
  printf '%s' "$1" > "$NOTICE"
  notify "$1"
}

# 同一时间只跑一个
if ! mkdir "$LOCK" 2>/dev/null; then
  [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ] || exit 0
  rm -rf "$LOCK"
  mkdir "$LOCK" 2>/dev/null || exit 0
fi
trap 'rm -rf "$LOCK"' EXIT

if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1000000 ]; then
  tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

cd "$SYNC_DIR" 2>/dev/null || { log "找不到 $SYNC_DIR"; exit 1; }
git config core.quotepath false   # 中文文件名按原样输出，后面按名字处理冲突要用

# 等拖进来的东西拷完（大小连续两次不变）
prev=""
for _ in $(seq 1 60); do
  cur="$(du -sk . 2>/dev/null | cut -f1)"
  [ "$cur" = "$prev" ] && break
  prev="$cur"
  sleep 3
done

# 自带 .git 的项目文件夹、超大文件：GitHub 收不了，自动排除
nested="$(find . -mindepth 1 \( -path ./.git -o -name node_modules \) -prune -o -name .git -print -prune 2>/dev/null \
  | sed -e 's|^\./||' -e 's|/\.git$||')"
big="$(find . -path ./.git -prune -o -type f -size +${MAX_MB}M -print 2>/dev/null | sed 's|^\./||')"
EXC=.git/info/exclude
mkdir -p .git/info
touch "$EXC"
{
  sed '/^# >>> github-sync/,/^# <<< github-sync/d' "$EXC"
  echo "# >>> github-sync（自动生成，勿手改）"
  printf '%s\n' "$nested" "$big" | sed -e '/^$/d' -e 's/[][*?\\]/\\&/g' -e 's|^|/|'
  echo "# <<< github-sync"
} > "$EXC.tmp" && mv "$EXC.tmp" "$EXC"
printf '%s\n' "$nested" "$big" | sed '/^$/d' | while IFS= read -r p; do
  [ -n "$(git --literal-pathspecs ls-files -- "$p")" ] && git --literal-pathspecs rm -r -q --cached -- "$p"
done
skipped="$(printf '%s\n' "$nested" "$big" | sed '/^$/d')"
if [ -n "$skipped" ] && [ "$(cat "$BASE/.skipped" 2>/dev/null)" != "$skipped" ]; then
  first="$(printf '%s\n' "$skipped" | head -n 1)"
  cnt="$(printf '%s\n' "$skipped" | wc -l | tr -d ' ')"
  log "未上传（超过 ${MAX_MB}MB 或自带 .git）：$(printf '%s\n' "$skipped" | tr '\n' ' ')"
  notify "有 $cnt 项没上传（超过 ${MAX_MB}MB 或是独立 git 项目），如：$first"
fi
printf '%s' "$skipped" > "$BASE/.skipped"

# 空文件夹也要在 GitHub 上出现：放一个 .gitkeep
find . -path ./.git -prune -o -type d -empty -print 2>/dev/null | while IFS= read -r d; do
  git check-ignore -q -- "$d/.gitkeep" 2>/dev/null || touch "$d/.gitkeep"
done

# 1) 本地改动先提交
git add -A
uploaded=0
if ! git diff --cached --quiet; then
  uploaded="$(git diff --cached --name-only | wc -l | tr -d ' ')"
  git commit -q -m "桌面同步 $(date '+%F %T')（$uploaded 个文件）"
  log "提交 $uploaded 个文件"
fi

# 2) 拉取云端改动
if ! git fetch -q origin >>"$LOG" 2>&1; then
  log "连不上 GitHub，稍后重试"
  exit 0
fi
R="origin/$BRANCH"
pulled=0
if git rev-parse -q --verify "$R" >/dev/null; then
  if ! git merge-base --is-ancestor "$R" HEAD; then
    old="$(git rev-parse HEAD)"
    if git rebase -q "$R" >/dev/null 2>&1; then
      pulled="$(git diff --name-only "$old...$R" | wc -l | tr -d ' ')"
      log "拉取云端改动 $pulled 个文件"
    else
      # 两边改了同一个文件：本地版本保留原名，GitHub 上的版本另存为「xxx (GitHub版本)」
      git rebase --abort >/dev/null 2>&1
      mb="$(git merge-base HEAD "$R")"
      both="$(comm -12 <(git diff --name-only "$mb" HEAD | sort) <(git diff --name-only "$mb" "$R" | sort))"
      if git merge -q --no-edit -X ours "$R" >/dev/null 2>&1; then
        printf '%s\n' "$both" | sed '/^$/d' | while IFS= read -r f; do
          git cat-file -e "$R:$f" 2>/dev/null || continue
          [ "$(git rev-parse "$R:$f")" = "$(git rev-parse "HEAD:$f" 2>/dev/null)" ] && continue
          d="$(dirname "$f")"
          b="$(basename "$f")"
          case "$b" in
            ?*.*) copy="$d/${b%.*} (GitHub版本).${b##*.}" ;;
            *) copy="$d/$b (GitHub版本)" ;;
          esac
          git show "$R:$f" > "$copy"
          log "冲突：$f 两边都改了，GitHub 上的版本另存为 ${copy#./}"
        done
        git add -A
        git diff --cached --quiet || git commit -q -m "桌面同步：保留冲突文件的 GitHub 版本"
        pulled="$(git diff --name-only "$old...$R" | wc -l | tr -d ' ')"
        notify "有文件本地和 GitHub 都改了：本地版本保留原名，GitHub 版本另存为「(GitHub版本)」"
      else
        git merge --abort >/dev/null 2>&1
        log "和云端的改动合不上，已暂停同步（本地提交保留，未推送）"
        warn_once "本地和 GitHub 的改动合不上，同步已暂停，详情见 ~/.github-sync/sync.log"
        exit 1
      fi
    fi
  fi
fi

# 3) 推送
if ! git rev-parse -q --verify "$R" >/dev/null || [ -n "$(git rev-list "$R..HEAD")" ]; then
  if ! git push -q origin "HEAD:$BRANCH" >>"$LOG" 2>&1; then
    log "推送失败"
    warn_once "上传 GitHub 失败，详情见 ~/.github-sync/sync.log"
    exit 1
  fi
  log "已推送到 GitHub"
fi

rm -f "$NOTICE"
[ "$uploaded" != 0 ] && notify "已上传 $uploaded 个文件到 GitHub"
[ "$pulled" != 0 ] && notify "GitHub 上的 $pulled 个文件改动已同步到本地"
exit 0
EOF
chmod +x "$BASE/sync.sh"

cat > "$BASE/uninstall.sh" <<'EOF'
#!/bin/bash
# 停止自动同步（文件夹里的文件和 GitHub 仓库都保留）
. "$HOME/.github-sync/config"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$PLIST"
[ -L "$DESKTOP_LINK" ] && rm -f "$DESKTOP_LINK"
rm -rf "$BASE"
echo "已停止自动同步。文件仍在 ${SYNC_DIR}，GitHub 仓库未改动。"
EOF
chmod +x "$BASE/uninstall.sh"

# ---------- 后台任务 ----------
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$(xml "$BASE/sync.sh")</string></array>
  <key>WatchPaths</key>
  <array><string>$(xml "$SYNC_DIR")</string></array>
  <key>StartInterval</key><integer>120</integer>
  <key>RunAtLoad</key><true/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>StandardOutPath</key><string>$(xml "$BASE/launchd.log")</string>
  <key>StandardErrorPath</key><string>$(xml "$BASE/launchd.log")</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$(id -u)" "$PLIST"

cat <<EOF

✅ 装好了
  桌面文件夹：~/Desktop/$FOLDER_NAME   （实际位置 ${SYNC_DIR}）
  GitHub 私有仓库：$URL

  拖进去的文件/文件夹，几十秒内出现在 GitHub 同名路径下；
  GitHub 上 $BRANCH 分支的改动，约 2 分钟内同步回这个文件夹。

  日志：~/.github-sync/sync.log
  立即同步：bash ~/.github-sync/sync.sh
  卸载：bash ~/.github-sync/uninstall.sh
EOF
