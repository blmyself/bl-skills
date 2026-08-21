---
name: figma-to-ios-pro
description: 全链路 Figma 转 iOS 专家。支持从 Figma URL 自动提取全局设计系统（Colors/Fonts/Tokens）、扫描整套 App 页面大纲、单页/组件精细化 UIKit (Masonry/XIB) 或 SwiftUI 代码生成与组件拆分，以及现有 iOS 代码对齐 Figma 的视觉保真度审计。当用户提供 Figma 链接、要求将设计稿转换为 iOS 代码、提炼设计规范或进行 UI 还原度审计时自动触发。
---

# Figma to iOS Pro (全链路 Figma 转 iOS 专家)

## 核心定位

`figma-to-ios-pro` 融合了 **Figma 数据提取、自动化设计系统提炼、技术栈智能对齐、组件化代码生成与视觉保真度审计** 的全流程能力。通过统一的智能调度中枢，支持从免费的 Figma Personal Access Token / REST API 或本地 Figma Desktop MCP 自动拉取数据并输出生产级 iOS 代码。

---

## 🚀 三大智能工作模式

根据用户的输入与意图，自动路由至对应工作模式：

```
                              ┌── [整文件 URL] ────────► 模式 1: 全局扫描与设计系统生成
                              │
[用户输入 Figma 链接/需求] ───┼── [具体 Node URL] ─────► 模式 2: 单页 / 组件精细化实现
                              │
                              └── [包含现有代码文件] ────► 模式 3: 视觉保真度审计与修复
```

---

### 🌟 模式 1：全局设计系统提取与大纲扫描 (Full Project Mode)

**适用场景**：
- 用户提供了 Figma 文件总链接（不带 `node-id`），或要求“扫描全项目”、“提炼设计规范”。

**执行步骤**：
1. **提取全局 Token**：
   运行内置脚本提取全文件的 Color Styles、Text Styles 与阴影规范：
   ```bash
   python3 scripts/export_design_tokens.py "<Figma_File_URL>" --prefix "App"
   ```
   - 自动生成 Markdown 规范表、Objective-C `AppDesignSystem.h` 与 Swift `DesignTokens.swift`。
2. **扫描整套 App 架构与页面清单**：
   ```bash
   python3 scripts/scan_app_screens.py "<Figma_File_URL>"
   ```
   - 输出整套 App 的页面脑图、各画板 Node ID、尺寸及所有 Master Components 清单。

---

### 🌟 模式 2：单页 / 组件精细化实现 (Single Screen / Component Mode)

**适用场景**：
- 用户提供了具体页面的 Figma URL（带 `node-id`），要求实现 UIKit 视图或 SwiftUI 视图。

**执行步骤**：
1. **拉取节点数据与渲染截图**：
   ```bash
   python3 scripts/extract_node_spec.py "<Figma_Node_URL>" --out-dir "/tmp/figma_spec"
   ```
   - 自动获取该 Node 的完整树形 JSON 与 2x/3x 高清截图。
2. **识别目标工程技术栈**：
   - 检测当前 Xcode 工程风格（如本项目中的 `Objective-C + Masonry`，或 `SwiftUI`，或 `UIKit + XIB`）。
   - 绝不生搬硬套 Web/React 样式，严格转换为 iOS 原生约束与组件。
3. **组件化拆分原则 (Component Decomposition)**：
   - 严禁将几百行代码全堆在一个 ViewController 中！
   - 按照 Figma 逻辑层级将页面解耦为独立的可复用组件（如 `HeaderSegmentView`、`OddsGridView`、`FeedCardView`、`CustomTabBarView` 等）。
4. **绑定全局 Design Tokens**：
   - 优先引用模式 1 生成的颜色宏 / Token，坚决避免硬编码十六进制色值。
5. **工程注册与语法校验**：
   - 自动将新代码注册至 `.xcodeproj/project.pbxproj`。
   - 运行 Clang 或 `xcodebuild` 做静态编译语法检查，确保 0 错误 0 警告交付。

---

### 🌟 模式 3：视觉保真度审计与修复 (Audit & Diff Mode)

**适用场景**：
- 用户提供了现有的 `.m` / `.xib` / `.swift` 代码，并附带 Figma 链接，要求检查视觉还原度。

**执行步骤**：
1. 读取现有代码视图层级与约束。
2. 比对 Figma 设计稿标准参数（间距、字体、圆角、背景色、自适应伸缩性）。
3. 运行审计脚本生成差异报告：
   ```bash
   python3 scripts/figma_uikit_audit.py --design-spec ... --impl-snapshot ...
   ```
4. 输出最小化 Patch 修复代码，避免不必要的重构。

---

## 🔑 自动鉴权与配置规范

本技能内置三级自动 Token 探测机制：
1. **环境变量**：`FIGMA_ACCESS_TOKEN` / `FIGMA_TOKEN`。
2. **Skill 本地配置文件**：读取 [`.env`](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/.env)。
3. **本地 MCP 服务**：如果开启了 Figma Desktop，支持通过本地 `127.0.0.1:3845` 零 Token 直接读取选中图层。

---

## 📚 规范参考库 (References)

按需查阅 `references/` 目录下的专业指南：
- [**Objective-C & Masonry 规范**](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/references/ios-uikit-xib-lane.md)
- [**SwiftUI 状态流与数据绑定**](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/references/swiftui-state-and-data-flow.md)
- [**SwiftUI 视图拆分与布局**](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/references/swiftui-view-structure-and-layout.md)
- [**复用组件防爆盾与极端变体处理**](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/references/shared-uikit-component-hardening.md)
- [**实施后保真度验证流程**](file:///Users/kylin/.gemini/config/skills/figma-to-ios-pro/references/post-implementation-validation-and-learning.md)
