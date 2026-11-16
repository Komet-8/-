# 自律监督（iOS 原生版）

每天设定必须完成的目标。没做完时，用苹果的“屏幕使用时间”接口屏蔽你选中的 App；全部完成才放行。每天零点自动重新上锁。

## 需要准备

- 一台 Mac，安装 Xcode 15 或更新版本
- Apple 开发者账号（99 美元/年，上架必需）
- 一台 iOS 16 以上的 iPhone（屏蔽功能在模拟器里不生效，要用真机测）

## 在 Mac 上打开工程

```bash
brew install xcodegen
```

```bash
cd ZiLv && xcodegen generate && open ZiLv.xcodeproj
```

然后在 Xcode 里：

1. 把 `project.yml` 里的 `com.komet8.zilv`、`com.komet8.zilv.monitor`、`group.com.komet8.zilv` 换成你自己的标识（`Shared/Shared.swift` 里的 group 也要一起改），重新运行 `xcodegen generate`。
2. 两个 target（ZiLv、ZiLvMonitor）的 Signing & Capabilities 里选你的开发者团队。
3. 连上 iPhone，运行。

## 上架 App Store 前必须做

1. **申请 Family Controls 分发权限**：开发调试可以直接用，但上架必须先向苹果申请，App 和监控扩展两个标识都要申请：
   https://developer.apple.com/contact/request/family-controls-distribution
   审批通常要几天到几周。
2. 在 App Store Connect 创建 App，填写名称、截图、隐私政策网址（本 App 不收集任何数据，数据只存在手机本地）。
3. Xcode → Product → Archive → 上传，提交审核。

## 已知限制

- 打卡靠自觉：App 无法验证你是否真的完成了目标。
- 你可以在系统设置里关掉本 App 的“屏幕使用时间”权限来解除屏蔽，苹果不允许个人模式下阻止这一点。

## 结构

- `App/`：界面与逻辑（SwiftUI）
- `Monitor/`：DeviceActivity 监控扩展，每天零点重新上锁
- `Shared/`：两边共用的数据模型和屏蔽逻辑
- `project.yml`：XcodeGen 工程描述
