# 桌面「GitHub同步」文件夹

Mac 桌面上放一个「GitHub同步」文件夹，拖进去的文件/文件夹会自动上传到你的 GitHub **私有**仓库（同名路径）；仓库 `main` 分支上的改动也会自动同步回这个文件夹。这样在网页版 Claude 里选这个仓库，就能直接对这些文件派任务。

## 安装

在 Mac 的「终端」里粘贴运行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Komet-8/-/claude/cool-franklin-s6z6tw/github-sync/install.sh)"
```

默认建私有仓库 `desktop-sync`，桌面文件夹叫「GitHub同步」。想换名字：

```bash
REPO_NAME=my-files FOLDER_NAME=Claude任务 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Komet-8/-/claude/cool-franklin-s6z6tw/github-sync/install.sh)"
```

## 它做了什么

| 东西 | 位置 |
|---|---|
| 同步文件夹（真实位置） | `~/GitHub同步`，桌面上是它的快捷方式 |
| GitHub 私有仓库 | `github.com/<你的账号>/desktop-sync` |
| 同步脚本 / 日志 | `~/.github-sync/sync.sh`、`~/.github-sync/sync.log` |
| 后台任务 | `~/Library/LaunchAgents/com.github-sync.desktop.plist` |

- 文件夹一有变化就同步（等拷贝完成后再传），另外每 2 分钟检查一次 GitHub 上的新改动。
- 上传完成、拉回改动时会弹 macOS 通知。
- 真实文件夹不放在桌面，是因为 macOS 不允许后台任务直接读写「桌面」。

## 目录和每级 README

第一次安装会建一套空目录骨架（可随意改名、删除、新建）：

```
01-GEO业务/{客户方案, GEO报告, 公司经营}
02-客户项目/安澜口腔
03-培训与讲课/{ITI, 种植课程}
04-AI与开发
05-英语教育
90-收件箱
99-归档
```

前 4 级（`README_DEPTH`）的每个文件夹都会自动有一个 `README.md`：

- 顶部 `> 用途：` 那一行手写一句话，说明这个文件夹放什么（没写就显示「未填写」）。
- 下面「目录:开始 … 目录:结束」那一段每次同步自动刷新：列出子文件夹（带各自用途）和文件。
- 根目录 `README.md` 里是整棵目录树的总览，和 Claude 沟通时先看它。
- 自带 README.md 的文件夹（比如拖进来的代码项目）当成完整项目，里面不再加 README。
- GitHub 上打开任何一个文件夹，都会直接显示它的 README。

## 规则

- 单个文件超过 95MB（GitHub 上限）不上传，弹通知提醒。
- 自带 `.git` 的项目文件夹不上传（它本身就是独立仓库，直接把那个仓库地址给 Claude）。
- `node_modules/`、`.venv/`、`__pycache__/`、`.DS_Store` 不上传。
- 同一个文件本地和 GitHub 都改了：本地版本保留原名，GitHub 版本另存为「文件名 (GitHub版本).扩展名」，两边都不丢。
- 删除文件也会同步删除（GitHub 历史里仍可找回）。

## 常用命令

```bash
bash ~/.github-sync/sync.sh        # 立即同步一次
tail -20 ~/.github-sync/sync.log   # 看同步记录
bash ~/.github-sync/uninstall.sh   # 停止自动同步（文件和仓库都保留）
```
