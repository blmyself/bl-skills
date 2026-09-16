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
1. **拉取节点数据、渲染截图与 RenderBounds 相对约束**：
    ```bash
    python3 scripts/extract_node_spec.py "<Figma_Node_URL>" --out-dir "/tmp/figma_spec"
    ```
    - 自动获取该 Node 的完整树形 JSON 与 2x/3x 高清截图。
    - **RenderBounds 相对坐标换算**：自动计算子节点相对父容器的相对坐标，并自动输出带有**突破父容器溢出负边距**（如 `make.top.equalTo(superview).offset(-8.0)`）的 Masonry 代码到 `masonry_constraints_*.m`。
2. **切图提取与规范重命名 (Asset Export & Renaming)**：
    - 在生成 UI 代码前，运行切图脚本将页面所需的切图/图标导出至 Xcode Assets：
    ```bash
    # 审查模式：预览并检查命名是否规范
    python3 scripts/export_assets_to_xcassets.py "<Figma_Node_URL>" --module "<ModuleName>" --dry-run

    # 导出模式 (支持自动中文翻译/无意义默认名清洗/自定义重命名映射)：
    python3 scripts/export_assets_to_xcassets.py "<Figma_Node_URL>" --module "<ModuleName>" --rename-map '{"node_id": "ic_nav_back"}'
    ```
    - **艺术字/描边文本自动转切图**：当遇到 `type == "TEXT"` 且 `fontFamily != PingFang/System` 或 `strokes.length > 0`（描边艺术字）时，自动将其标记为 `IMAGE` 资产导出，避免在 iOS 端以普通 UILabel 强行硬编码。
    - 强制规范：图标统一 `ic_`，按钮统一 `btn_`，插画统一 `img_`，背景统一 `bg_`，杜绝 `Vector`、`Group` 等无意义图层名。
3. **识别目标工程技术栈**：
    - 检测当前 Xcode 工程风格（如本项目中的 `Objective-C + Masonry`，或 `SwiftUI`，或 `UIKit + XIB`）。
    - 绝不生搬硬套 Web/React 样式，严格转换为 iOS 原生约束与组件。
4. **组件化拆分原则 (Component Decomposition)**：
    - 严禁将几百行代码全堆在一个 ViewController 中！
    - 按照 Figma 逻辑层级将页面解耦为独立的可复用组件（如 `HeaderSegmentView`、`OddsGridView`、`FeedCardView`、`CustomTabBarView` 等）。
5. **绑定全局 Design Tokens 与切图资产**：
    - 优先引用模式 1 生成的颜色宏 / Token，坚决避免硬编码十六进制色值。
    - 图片资源严格使用第 2 步规范命名导入的 Assets（如 `[UIImage imageNamed:@"ModuleName/ic_back"]` 或 `Image("ModuleName/ic_back")`）。
6. **工程注册与语法校验**：
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
2. **Skill 本地配置文件**：读取 [`.env`](.env)。
3. **本地 MCP 服务**：如果开启了 Figma Desktop，支持通过本地 `127.0.0.1:3845` 零 Token 直接读取选中图层。

---

## 🚦 API 配额与限流纪律 (必读)

Figma 自 2025-11-17 起对 REST API 采用**分级漏桶配额**，最贵的 Tier 1 极其稀缺：

| Tier | 接口 | Full/Dev 座位 (Pro→Org→Ent) | Viewer/Collab 座位 |
| :--- | :--- | :--- | :--- |
| **1** | `GET file`、`GET file nodes`、`GET image` | **10 → 15 → 20 次/分** | **6 次/月** |
| 2 | image fills、comments、variables、version history | 25 → 50 → 100 次/分 | 5 次/分 |
| 3 | file **meta**、components、styles、users | 50 → 100 → 150 次/分 | 10 次/分 |

`scripts/figma_api_client.py` 已内置防护，**所有 Figma 请求必须经由该客户端**，禁止在任何脚本里直接 `curl` 或 `urllib` 打 `api.figma.com`：
- **主动限速**：跨进程持久化令牌桶，宁可本地排队也不触发 429（默认只用官方额度的 80%）。
- **429 智能处置**：读取 `Retry-After` 与 `X-Figma-Rate-Limit-Type`；`type=low`（Viewer 座位）或等待超过 120s 时**立刻失败并给出处置建议**，绝不盲等或连打导致封禁延长。
- **共享冷却期**：一个脚本吃到 429 后落盘冷却时间，其余脚本自动避让；**写下冷却期的进程自己同样遵守**。
- **月度硬计数**：`FIGMA_PLAN=view|starter`（Viewer/Collab 座位）时额外记账 Tier 1「6 次/月」，用完直接快速失败，不会被一次批量切图烧干。
- **持久化缓存**：默认 `~/.cache/figma-to-ios-pro`（7 天 TTL），重跑同一设计稿零请求；渲染出的 PNG 按「渲染 URL 指纹」命名，设计稿更新后自动换新文件，不会复用过期切图。

实操纪律：
1. **一次全量、多次复用**：`scan_app_screens.py` 与 `export_design_tokens.py` 每个文件只跑一次，后续按 `node-id` 用 `extract_node_spec.py` 精确取单页，不要反复整文件扫描。
2. **禁止无 `depth` 的整文件拉取**；只想拿文件名请用 Tier 3 的 `client.get_file_name()`。
3. **批量合并**：多节点一次性传入 `get_nodes` / `get_images`（客户端自动去重分批），严禁 for 循环里逐个请求。
4. **吃到配额错误时**：不要重试脚本，先检查 Token 座位类型（`type=low` 说明该 Token 是 Viewer/Collab 座位，Tier 1 全月只有 6 次），改用 Full/Dev 座位 Token 或切换 Figma Desktop MCP 通道。

Token 作用域需同时包含 `file_content:read` 与 `file_metadata:read`（后者是 Tier 3 的 `files/:key/meta` 所需；缺失时只能退回更贵的 Tier 1 取文件名）。可用 `python3 scripts/figma_api_client.py --diagnose` 自检 Token 与当前冷却状态。

常用环境变量：`FIGMA_PLAN=pro|org|enterprise|view|starter`（校准限速档位，`view/starter` 启用月度硬计数）、`FIGMA_RATE_SAFETY=0.8`（安全系数）、`FIGMA_CACHE_TTL`（秒；`0` = 不读缓存，负数 = 永不过期）、`FIGMA_OFFLINE=1`（仅用缓存，零网络请求）、`FIGMA_NO_CACHE=1`（强制刷新 JSON 与 PNG）。

---

## 📚 规范参考库 (References)

按需查阅 `references/` 目录下的专业指南：
- [**Objective-C & Masonry 规范**](references/ios-uikit-xib-lane.md)
- [**SwiftUI 状态流与数据绑定**](references/swiftui-state-and-data-flow.md)
- [**SwiftUI 视图拆分与布局**](references/swiftui-view-structure-and-layout.md)
- [**复用组件防爆盾与极端变体处理**](references/shared-uikit-component-hardening.md)
- [**实施后保真度验证流程**](references/post-implementation-validation-and-learning.md)
