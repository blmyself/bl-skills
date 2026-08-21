#!/usr/bin/env python3
"""
Multi-Agent Skills Synchronizer (跨平台 AI Agent 技能同步工具)
用于将 bl-skills 仓库中的技能一键部署/同步到不同的 AI Agent 环境中：
- Google Antigravity (~/.gemini/config/skills/ 或 .agents/skills/)
- Anthropic Claude Code (~/.claude/commands/ 或 .claude/commands/)
- OpenAI Codex (~/.codex/skills/ 或项目内)
- Trae (.trae/rules/)
- Cursor (.cursor/rules/)
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()

# 忽略的非技能目录
IGNORED_DIRS = {".git", ".gemini", ".agents", ".claude", ".trae", ".cursor", "scripts", "scratch", "brain", "node_modules"}


def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """提取 YAML Frontmatter 和正文内容"""
    frontmatter = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        body = match.group(2).strip()

        # 简单无三方依赖的 YAML 键值解析
        for line in yaml_block.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                frontmatter[key] = val

    return frontmatter, body


def parse_openai_yaml(yaml_path: Path) -> Dict[str, str]:
    """读取 agents/openai.yaml 元数据"""
    data = {}
    if not yaml_path.exists():
        return data

    try:
        content = yaml_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                data[k] = v
    except Exception:
        pass
    return data


class Skill:
    def __init__(self, dir_path: Path):
        self.dir = dir_path
        self.name = dir_path.name
        self.skill_md = dir_path / "SKILL.md"
        self.openai_yaml = dir_path / "agents" / "openai.yaml"

        raw_content = self.skill_md.read_text(encoding="utf-8") if self.skill_md.exists() else ""
        self.frontmatter, self.body = parse_frontmatter(raw_content)
        self.openai_meta = parse_openai_yaml(self.openai_yaml)

        self.display_name = self.openai_meta.get("display_name") or self.frontmatter.get("name") or self.name
        self.description = self.openai_meta.get("short_description") or self.frontmatter.get("description") or self.display_name

    def is_valid(self) -> bool:
        return self.skill_md.exists()

    def generate_claude_command(self) -> str:
        """生成 Claude Code 自定义 Slash Command 内容"""
        short_desc = self.description.replace("\n", " ").strip()
        return f"""---
description: {short_desc}
---

# 执行角色：{self.display_name}

请严格遵循以下原则与工作流与用户对话或执行任务：

$ARGUMENTS

---

{self.body}
"""

    def generate_trae_rule(self) -> str:
        """生成 Trae Rule 内容"""
        return f"""# {self.display_name} 行为规范与指引

{self.body}
"""

    def generate_cursor_rule(self) -> str:
        """生成 Cursor MDC Rule 内容"""
        short_desc = self.description.replace("\n", " ").strip()
        return f"""---
description: {short_desc}
globs: *
alwaysApply: false
---

# {self.display_name}

{self.body}
"""


def discover_skills(repo_root: Path) -> List[Skill]:
    """发现仓库中所有有效的 Skill"""
    skills = []
    for item in repo_root.iterdir():
        if item.is_dir() and item.name not in IGNORED_DIRS and not item.name.startswith("."):
            skill = Skill(item)
            if skill.is_valid():
                skills.append(skill)
    return sorted(skills, key=lambda s: s.name)


def sync_to_antigravity(skill: Skill, scope: str, project_dir: Optional[Path], dry_run: bool):
    """同步到 Antigravity"""
    dest_dirs = []
    if scope in ("global", "both"):
        dest_dirs.append(HOME / ".gemini" / "config" / "skills" / skill.name)
    if scope in ("project", "both") and project_dir:
        dest_dirs.append(project_dir / ".agents" / "skills" / skill.name)

    for dest in dest_dirs:
        print(f"  [Antigravity] -> {dest}")
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        
        # 尝试使用软链接，若跨卷或失败则回退到目录拷贝
        try:
            dest.symlink_to(skill.dir, target_is_directory=True)
        except Exception:
            shutil.copytree(skill.dir, dest)


def sync_to_claude(skill: Skill, scope: str, project_dir: Optional[Path], dry_run: bool):
    """同步到 Claude Code Custom Slash Commands"""
    dest_files = []
    if scope in ("global", "both"):
        dest_files.append(HOME / ".claude" / "commands" / f"{skill.name}.md")
    if scope in ("project", "both") and project_dir:
        dest_files.append(project_dir / ".claude" / "commands" / f"{skill.name}.md")

    content = skill.generate_claude_command()
    for dest in dest_files:
        print(f"  [Claude Code] -> {dest} (命令: /{skill.name})")
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def sync_to_trae(skill: Skill, scope: str, project_dir: Optional[Path], dry_run: bool):
    """同步到 Trae Rules"""
    dest_files = []
    if scope in ("project", "both") and project_dir:
        dest_files.append(project_dir / ".trae" / "rules" / f"{skill.name}.md")
    elif scope == "global":
        # Trae 全局规则提示
        print(f"  [Trae] 提示: Trae 全局规则请在 Trae IDE 设置 -> Rules 中直接粘贴 {skill.skill_md}")
        return

    content = skill.generate_trae_rule()
    for dest in dest_files:
        print(f"  [Trae Rules] -> {dest}")
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def sync_to_cursor(skill: Skill, scope: str, project_dir: Optional[Path], dry_run: bool):
    """同步到 Cursor Rules (.mdc)"""
    dest_files = []
    if scope in ("project", "both") and project_dir:
        dest_files.append(project_dir / ".cursor" / "rules" / f"{skill.name}.mdc")
    if scope in ("global", "both"):
        # Cursor 全局暂支持导出到 ~/.cursorrules_d/ 或记录
        pass

    content = skill.generate_cursor_rule()
    for dest in dest_files:
        print(f"  [Cursor Rules] -> {dest}")
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def sync_to_codex(skill: Skill, scope: str, project_dir: Optional[Path], dry_run: bool):
    """同步到 OpenAI Codex"""
    dest_dirs = []
    if scope in ("global", "both"):
        dest_dirs.append(HOME / ".codex" / "skills" / skill.name)

    for dest in dest_dirs:
        print(f"  [Codex] -> {dest}")
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        try:
            dest.symlink_to(skill.dir, target_is_directory=True)
        except Exception:
            shutil.copytree(skill.dir, dest)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent 技能同步工具 (支持全量同步与单个/指定技能精准安装)",
        epilog="示例:\n"
               "  python scripts/sync_skills.py strategic-advisor               # 单独安装 strategic-advisor 到全局所有平台\n"
               "  python scripts/sync_skills.py strategic-advisor --target claude # 仅安装到 Claude Code\n"
               "  python scripts/sync_skills.py --all                           # 安装全部技能\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("skill_names", nargs="*", default=None, help="可选的位置参数：指定要同步的技能名称（如 strategic-advisor），支持多个")
    parser.add_argument("--list", action="store_true", help="列出仓库中发现的所有技能")
    parser.add_argument("--skills", type=str, default=None, help="指定要同步的技能名称，逗号分隔，例如: strategic-advisor,skill-creator")
    parser.add_argument("--all", action="store_true", help="显式指定同步所有技能")
    parser.add_argument(
        "--target",
        type=str,
        default="all",
        help="目标平台: antigravity, claude, trae, cursor, codex, all (默认 all)",
    )
    parser.add_argument(
        "--scope",
        type=str,
        choices=["global", "project", "both"],
        default="global",
        help="部署范围: global(用户全局目录), project(指定项目目录), both (默认 global)",
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=".",
        help="当 scope 为 project 或 both 时生效的目标工程路径 (默认当前工作目录)",
    )
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅打印计划变更而不实际写入")

    args = parser.parse_args()

    all_skills = discover_skills(REPO_ROOT)

    if args.list:
        print("📦 仓库中已注册的 Skills:")
        for s in all_skills:
            print(f"  - \033[1;36m{s.name}\033[0m: {s.display_name} ({s.description[:50]}...)")
        return

    # 确定要安装/同步的技能集合
    target_skill_names = set()
    if args.skill_names:
        target_skill_names.update(args.skill_names)
    if args.skills:
        target_skill_names.update([n.strip() for n in args.skills.split(",") if n.strip()])

    if target_skill_names:
        selected_skills = [s for s in all_skills if s.name in target_skill_names]
        missing = target_skill_names - {s.name for s in selected_skills}
        if missing:
            print(f"⚠️ 警告: 以下技能未在仓库中找到: {', '.join(missing)}")
    else:
        # 如果未指定任何技能名称，且未指定 --all，默认提示用户选择或全量同步
        selected_skills = all_skills

    if not selected_skills:
        print("❌ 未找到任何匹配的技能。使用 --list 查看可用技能。")
        sys.exit(1)

    # 目标平台
    targets = [t.strip().lower() for t in args.target.split(",")]
    if "all" in targets:
        targets = ["antigravity", "claude", "codex", "trae", "cursor"]

    project_dir = Path(args.project_dir).resolve() if args.project_dir else None

    print(f"🚀 开始同步 {len(selected_skills)} 个技能到目标平台: {', '.join(targets)}")
    print(f"📍 部署范围: {args.scope}" + (f" (项目路径: {project_dir})" if args.scope in ("project", "both") else ""))
    if args.dry_run:
        print("⚠️ 演练模式 (DRY RUN): 不会进行实际文件操作\n")

    for skill in selected_skills:
        print(f"\n⚡ 同步技能: \033[1;32m{skill.name}\033[0m ({skill.display_name})")
        if "antigravity" in targets:
            sync_to_antigravity(skill, args.scope, project_dir, args.dry_run)
        if "claude" in targets:
            sync_to_claude(skill, args.scope, project_dir, args.dry_run)
        if "codex" in targets:
            sync_to_codex(skill, args.scope, project_dir, args.dry_run)
        if "trae" in targets:
            sync_to_trae(skill, args.scope, project_dir, args.dry_run)
        if "cursor" in targets:
            sync_to_cursor(skill, args.scope, project_dir, args.dry_run)

    print("\n✅ 所有指定技能已完成同步与部署！")


if __name__ == "__main__":
    main()
