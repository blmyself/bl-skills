# Figma to iOS Pro 🎨 ➡️ 🍏

> **全链路 Figma 转 iOS 专家**：一键提取全局设计系统、整套 App 大纲扫描、按模块 Namespace 自动切图导出、单页/组件精细化 UIKit (Masonry/XIB) 或 SwiftUI 代码生成与视觉保真度审计。

---

## 🌟 核心特性

- 🎯 **单一中枢，智能调度**：无需在提取工具和翻译工具之间来回切换，输入 Figma 链接自动感知意图。
- 🔑 **内置零配置鉴权与防频控**：支持免费的 Figma Personal Access Token，内置 **429 智能指数退避重试** 与 **本地强缓存机制**，无需购买专业版/Dev Mode。
- 🖼️ **模块化切图与 Namespace 隔离**：自动识别图标/切图并批量生成 `@2x/@3x` PNG 写入 `Assets.xcassets/<ModuleName>/`（自动优先标准 `Assets.xcassets`，同时兼容 `Images.xcassets`），开启 `"provides-namespace": true` 彻底杜绝重名冲突。
- 🧭 **整套 App 扫描能力**：一键提取全局 Design Tokens（颜色/字体/阴影）与所有页面画板大纲，杜绝硬编码。
- 🧩 **架构级组件拆分**：严禁单文件无脑堆砌，根据 Figma 结构智能拆分高复用子组件。
- 🛠️ **多平台兼容**：适配 Google Antigravity、Anthropic Claude Code、OpenAI Codex、ByteDance Trae 与 Cursor。

---

## 🚀 快速上手 (Prompt 示例)

### 场景 1：单页面 / 组件精细化实现 (生成代码并拆分组件)
直接将带有 `node-id` 的 Figma 页面或组件链接发送给 AI：
```text
帮我把这个 Figma 设计实现为 UIKit (Masonry) 视图，拆分出可复用的组件：
https://www.figma.com/design/YOUR_FILE_KEY/MyApp?node-id=100-200
```
> **AI 动作**：自动拉取节点属性与高清截图，匹配当前项目技术栈（ObjC+Masonry 或 SwiftUI），拆分独立子视图并注册到 Xcode 工程。

---

### 场景 2：按模块 Namespace 自动切图导出与智能规范重命名
```text
把这个 Figma 节点里的图标切图导出到项目的 Assets.xcassets，归类到 PredictionLeak 模块下：
https://www.figma.com/design/YOUR_FILE_KEY/MyApp?node-id=100-200
```
> **AI 动作**：
> 1. **智能审查与规范化**：自动过滤 `Vector` / `Group 12` 等默认名（自动抓取父容器语义），对中文图层名进行英文语义翻译，统一按 iOS 规范格式化为 `ic_back`、`btn_submit`、`img_empty` 等 `snake_case` 名称。
> 2. **支持审查与自定义重命名**：支持先通过 `--dry-run` 预览命名，并通过 `--rename-map` / `--rename-file` 进行精准覆盖。
> 3. **批量拉取与 Namespace 隔离**：批量获取 `@2x` 与 `@3x` 高清切图，并在 `Assets.xcassets/PredictionLeak/` 下生成带命名空间配置的 `.imageset`。

---

### 场景 3：整套 App 页面大纲扫描与架构梳理
提供 Figma 文件主链接（不带 node-id）：
```text
扫描这个 Figma 文件，帮我整理出整套 App 的页面清单与通用组件脑图：
https://www.figma.com/design/YOUR_FILE_KEY/MyApp
```
> **AI 动作**：输出整套 App 的页面清单、画板尺寸、Node ID 及所有 Master Components，生成开发路线图。

---

### 场景 4：一键提取全局设计系统 (Design Tokens)
```text
提取这个 Figma 文件的全局设计规范，生成 Objective-C 和 Swift 的常量代码：
https://www.figma.com/design/YOUR_FILE_KEY/MyApp
```
> **AI 动作**：生成 `AppDesignTokens.md` 规范表、`AppDesignSystem.h` (宏定义) 与 `DesignTokens.swift`。

---

### 场景 5：现有代码对齐与视觉保真度审计
```text
结合 Figma 设计检查 ProfileHeaderView.m 的还原度：
Figma 链接: https://www.figma.com/design/YOUR_FILE_KEY/MyApp?node-id=102-45
指出间距、字号和颜色偏差，并给出最小化修复代码。
```

---

## ⚙️ Token 鉴权与防频控 (Rate Limiting)

本技能支持三级自动 Token 探测机制，配置一次即可永久免密使用：

1. **技能内置配置**（推荐）：
   在技能目录下的 `.env` 文件中填写：
   ```bash
   FIGMA_ACCESS_TOKEN=figd_你的PersonalAccessToken
   ```
2. **系统环境变量**：
   在 `~/.zshrc` 中添加：
   ```bash
   export FIGMA_ACCESS_TOKEN="figd_你的PersonalAccessToken"
   ```
3. **Figma Desktop 本地模式**：
   若本地开启了 Figma 桌面端开发模式（端口 3845），支持直接通过鼠标选中的图层免 Token 交互。

> 🛡️ **429 防限流保护**：客户端底层内置了 `Cache-First`（本地强缓存）与指数退避重试（`4s -> 8s -> 12s -> 16s`），即使是免费的 Starter 账号在批量操作时也能平稳运行。

---

## 🛠️ 目录结构与工具脚本

```text
figma-to-ios-pro/
├── README.md                          # 本使用指引
├── SKILL.md                           # 技能主调度定义 (Agent 入口)
├── .env                               # Figma Token 配置文件
├── agents/
│   └── openai.yaml                    # Agent 平台元数据
├── scripts/                           # 自动化 Python 工具库
│   ├── figma_api_client.py            # 核心 API 客户端 (含缓存与 429 智能重试)
│   ├── export_assets_to_xcassets.py   # 模块 Namespace 自动切图导出器 (含智能规范清洗、艺术字/描边文本识别、--rename-map 与 --dry-run)
│   ├── export_design_tokens.py        # 全局设计 Token 提取器
│   ├── scan_app_screens.py            # 整套 App 架构大纲扫描器
│   ├── extract_node_spec.py           # 单节点属性、高清截图及 RenderBounds 溢出负边距 Masonry 约束生成
│   ├── extract_uikit_impl_snapshot.py # UIKit 代码快照提取
│   └── figma_uikit_audit.py           # 视觉保真度对比审计
├── references/                        # iOS 技术栈规范手册
│   ├── ios-uikit-xib-lane.md          # UIKit & XIB 规范 (含 RenderBounds 负边距与艺术字规范)
│   ├── swiftui-lane-overview.md       # SwiftUI 架构与布局规范
│   └── shared-uikit-component-hardening.md # 复用组件防爆盾指南
└── templates/                         # 代码与规范模板
```

---

## 🙏 致谢与出处声明 (Credits & Acknowledgments)

本项目及本 Skill 的核心设计规范、iOS 翻译通道与审计基线基于开源项目 [**AmrMohamad/figma-to-ios-ui**](https://github.com/AmrMohamad/figma-to-ios-ui) 进行深度融合与二次开发：
- **上游项目**：[AmrMohamad/figma-to-ios-ui](https://github.com/AmrMohamad/figma-to-ios-ui)
- **原始作者**：[@AmrMohamad](https://github.com/AmrMohamad)
- **本次升级改动**：
  1. 将原本分立的 `figma-mcp` 与 `figma-to-ios-ui` 两个技能合并为单一中枢 `figma-to-ios-pro`。
  2. 引入全自动 Figma REST API 客户端，内置 429 指数退避与本地强缓存，消除本地 MCP 付费限制。
  3. 新增按模块 Namespace 自动切图与 Asset Catalog 导出器 (`export_assets_to_xcassets.py`)：
     - **优先标准 `Assets.xcassets`，同时兼容旧工程 `Images.xcassets`**。
     - **智能图层清洗与规范化**：自动过滤 `Vector`、`Group` 等无意义名并继承父容器语义，中文 UI 词汇自动翻译为英文，自动补齐 `ic_`/`btn_`/`img_`/`bg_` 前缀。
     - **非系统字体与描边艺术字自动识别**：遇到 `fontFamily != PingFang/System` 或 `strokes.length > 0`（描边艺术字）自动标记为 `IMAGE` 切图导出。
     - **支持 `--dry-run` 预览审查** 与 **`--rename-map` / `--rename-file` 自定义精准重命名**。
  4. 新增单节点 RenderBounds 相对坐标与 Masonry 约束生成器 (`extract_node_spec.py`)：
     - **自动检测突破父容器的溢出元素**，输出带有负边距（如 `make.top.equalTo(superview).offset(-8.0)`）的高精度 Objective-C Masonry 约束代码。
  5. 新增全 App 页面大纲扫描器 (`scan_app_screens.py`) 与全局 Design Tokens 自动导出器 (`export_design_tokens.py`)。
  6. 强化 Objective-C + Masonry 与 SwiftUI 的项目技术栈自动嗅探与组件解耦能力。

---

## 💡 最佳开发实践建议

1. **先全局后局部**：大型项目先运行【场景 4】提取全局 Token 并创建基础库，再逐步落地具体页面。
2. **切图按模块归类**：运行【场景 2】自动切图并指定 `--module <ModuleName>`，Xcode 会自动以命名空间隔离管理。
3. **保持组件解耦**：每个独立视图组件保持职责单一，通过 Delegate / Block 与主控制器通信。
