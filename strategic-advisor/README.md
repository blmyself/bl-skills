# strategic-advisor 🎯 专属战略顾问

用于在重大决策、复杂局面、职业抉择、商业战略和项目规划中，通过深度苏格拉底追问击穿问题本质，并制定高颗粒度行动方案的跨平台 AI Agent 技能。

---

## ⚡ 单独安装本技能

如果你只想安装 `strategic-advisor`，而不需要安装仓库中的其他技能，可以在仓库根目录执行：

```bash
# 1. 单独安装到本地所有支持的 Agent (全局目录)
python scripts/sync_skills.py strategic-advisor

# 2. 仅安装到 Claude Code
python scripts/sync_skills.py strategic-advisor --target claude

# 3. 仅安装到 Antigravity
python scripts/sync_skills.py strategic-advisor --target antigravity

# 4. 仅安装到当前项目 (生成 .agents/、.claude/、.trae/ 等)
python scripts/sync_skills.py strategic-advisor --scope project
```

---

## 🛠️ 各平台调用方式

### 1. Claude Code
在终端 CLI 中使用自定义 Slash Command：
```bash
/strategic-advisor 正在考虑是否要从大厂离职创业做AI出海，帮我全面梳理
```

### 2. Google Antigravity
在对话中直接自然语言唤起或引用：
- *“帮我理清思路，我最近在推进一个新业务但遇到了卡点”*
- *“使用 @strategic-advisor 当我的战略顾问，连续追问我直到击穿本质”*

### 3. OpenAI Codex
在 Codex 环境中输入：
- `使用 $strategic-advisor 主动追问我的真实处境，厘清关键矛盾后再制定详细行动规划。`

### 4. Trae / Cursor
在 IDE 对话框中直接提问：
- *“帮我做战略决策分析，理清这个架构演进的取舍和路线图”*

---

## 📋 核心流程
1. **问题重塑**：不盲从初始表述，重塑核心问题定义。
2. **战略底稿**：结构化追踪目标、事实、解释、约束、博弈与风险。
3. **9维追问**：目标、现实、因果、约束、取舍、关系、行为、风险、实验。
4. **收敛快照**：出具“战略判断快照”完成认知对齐。
5. **行动路线图**：输出包含阶段里程碑、行动清单、风险预案与今日即刻动作（Top 3）的完整方案。
