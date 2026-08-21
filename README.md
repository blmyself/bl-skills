# bl-skills 🛠️

跨平台 AI Agent 通用技能库（Skills Repository），一套技能核心规范，无缝适配 **Google Antigravity**、**Anthropic Claude Code**、**ByteDance Trae**、**OpenAI Codex** 及 **Cursor**。

---

## 🌟 仓库技能列表

| 技能标识 (Name) | 展示名称 | 描述 | 适用平台 |
| :--- | :--- | :--- | :--- |
| **`skill-creator`** | Skill 锻造师 | 将原始提示词与需求自动锻造成跨平台标准 Skill | 全平台 |
| **`strategic-advisor`** | 专属战略顾问 | 通过连续深度追问厘清复杂局势，输出可执行详细战略规划 | 全平台 |
| **`figma-to-ios-pro`** | Figma 转 iOS 专家 | 全链路 Figma 转 iOS：全局设计系统提取、整套 App 扫描、单页/组件精细化 UIKit/SwiftUI 代码生成与视觉保真度审计 | 全平台 |

---

## 🚀 跨平台一键部署与同步

仓库内置自动化同步脚本 `scripts/sync_skills.py`，支持将技能一键部署到本地各个 Agent 环境：

```bash
# 1. 查看仓库内所有已注册技能
python scripts/sync_skills.py --list

# 2. 单独安装某个技能（如 strategic-advisor）到全局所有 Agent
python scripts/sync_skills.py strategic-advisor

# 3. 单独安装某个技能到指定 Agent（如仅安装到 Claude Code 或 Antigravity）
python scripts/sync_skills.py strategic-advisor --target claude
python scripts/sync_skills.py strategic-advisor --target antigravity

# 4. 一键全量安装所有技能到本地所有 Agent
python scripts/sync_skills.py --all

# 5. 安装技能到当前项目目录（生成 .agents/、.claude/、.trae/、.cursor/）
python scripts/sync_skills.py strategic-advisor --scope project
```

### 各 Agent 使用方式对照

- **Antigravity**：自动注册在 `~/.gemini/config/skills/`，通过自然语言意图或 `@skill-name` 渐进式唤起。
- **Claude Code**：自动生成为 Slash Command (`~/.claude/commands/*.md`)，在 CLI 中直接输入 `/strategic-advisor` 或 `/skill-creator` 即可使用。
- **OpenAI Codex**：放置在 `~/.codex/skills/`，通过 `$strategic-advisor` 或自然语言触发。
- **Trae**：同步到 `.trae/rules/` 作为项目规则生效，或直接复制规则内容到全局配置。
- **Cursor**：同步为 `.cursor/rules/*.mdc`，在 Cursor 对话中自动匹配生效。

---

## 🛠️ 如何快速创建新 Skill？

当你需要将一个新的提示词或角色想法制作为技能时：

### 方式一：直接在 Agent 中调用 `skill-creator`
在对话中直接唤醒 `skill-creator`（或输入 `/skill-creator`），并提供你的原始提示词或想法：
> *“使用 skill-creator，帮我把这段提示词改成一个‘SQL性能调优专家’的 Skill：[粘贴提示词]”*

`skill-creator` 将自动完成需求分析、编写标准 `SKILL.md`、生成 `agents/openai.yaml` 与适配模板，并写入仓库。

### 方式二：手动编写
参考 `skill-creator/templates/` 目录下的标准模板创建新目录，并运行 `python scripts/sync_skills.py` 完成部署。
