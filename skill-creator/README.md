# skill-creator 🛠️ Skill 锻造师 (Meta-Skill)

专用于将用户的原始提示词、角色设定、专业工作流或碎片化需求，自动锻造成符合现代 Agent 规范的高性能、跨平台（Codex、Claude Code、Trae、Antigravity、Cursor）标准 Skill 套件。

---

## ⚡ 单独安装本技能

如果你只想单独安装 `skill-creator` 到本地环境：

```bash
# 1. 单独安装到本地所有支持的 Agent (全局目录)
python scripts/sync_skills.py skill-creator

# 2. 仅安装到 Claude Code
python scripts/sync_skills.py skill-creator --target claude

# 3. 仅安装到 Antigravity
python scripts/sync_skills.py skill-creator --target antigravity
```

---

## 🌟 核心价值

1. **结构化与工程化**：拒绝模糊笼统的“提示词”，自动提炼状态机、思考链、执行约束、收敛条件与防失效机制。
2. **单一真实信源 (SSOT)**：以标准 `SKILL.md` 为核心源文件，通过适配层与同步脚本无缝导出到各大 Agent。
3. **渐进式披露 (Progressive Disclosure)**：精心设计 Frontmatter 元数据，确保在上下文有限的 Agent 系统中精准命中激活，且不浪费系统 Token。
4. **内置开箱即用模板**：提供标准规范及各平台（OpenAI、Claude Code、Trae、Cursor）的适配模版。

---

## 🛠️ 各平台调用方式

### 1. Claude Code
在终端 CLI 中使用自定义 Slash Command：
```bash
/skill-creator 帮我把这段提示词改成一个SQL优化专家的Skill：[粘贴你的提示词或想法]
```

### 2. Google Antigravity
在对话中直接自然语言唤起或引用：
- *“使用 skill-creator 帮我创建一个代码重构专家的技能”*
- *“把这段提示词改造成标准的跨平台 Skill：[粘贴提示词]”*
- *“@skill-creator 帮我设计一个 API 安全审查技能”*

### 3. OpenAI Codex
在 Codex 环境中输入：
- `使用 $skill-creator 帮我把以下提示词或需求改造成标准的跨平台 Skill：[提示词]`

### 4. Trae / Cursor
在 IDE 对话框中直接提问：
- *“使用 skill-creator 帮我创建新技能：[需求描述]”*

---

## 📋 目录与模板结构

```text
skill-creator/
├── SKILL.md                   # 🌟 元技能核心定义（工作流、规范与失效模式）
├── README.md                  # 技能使用手册
├── agents/
│   └── openai.yaml            # Codex 界面元数据与默认 Prompt
└── templates/                 # 跨平台标准代码模板库
    ├── template_skill.md      # 标准通用 SKILL.md 模板
    ├── template_openai.yaml   # OpenAI / Codex 配置文件模板
    ├── template_claude_command.md # Claude Code Slash Command 模板
    ├── template_trae_rule.md  # Trae Rules 模板
    └── template_cursor_rule.mdc # Cursor MDC 规则模板
```

---

## 🔄 快速创建并部署新 Skill

1. **调用生成**：唤醒 `skill-creator` 并提供原始需求，生成对应技能目录（如 `sql-optimizer/`）。
2. **一键同步**：运行仓库根目录下的同步脚本（支持单独安装或全量同步）：
   ```bash
   # 单独安装新技能
   python scripts/sync_skills.py <新技能名>
   ```
