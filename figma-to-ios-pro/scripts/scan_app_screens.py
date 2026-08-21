#!/usr/bin/env python3
"""
Scan App Structure from Figma
扫描整个 Figma 文件中的所有页面、主画板（Screens）与通用母版组件，输出整套 App 的架构脑图与开发清单。
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List

try:
    from figma_api_client import FigmaAPIClient
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient


def extract_file_key(url_or_key: str) -> str:
    match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url_or_key)
    if match:
        return match.group(1)
    return url_or_key.strip()


def main():
    parser = argparse.ArgumentParser(description="扫描 Figma 文件生成 App 页面清单")
    parser.add_argument("url", help="Figma 文件 URL 或 File Key")
    parser.add_argument("--out", default="AppStructure_Roadmap.md", help="输出 Markdown 文件路径")
    args = parser.parse_args()

    file_key = extract_file_key(args.url)
    print(f"🔍 正在扫描 Figma 文件 [FileKey: {file_key}] 结构与组件清单...")
    client = FigmaAPIClient()

    file_data = client.get_file(file_key, depth=2)
    doc = file_data.get("document", {})
    doc_name = file_data.get("name", "App Design")

    # 1. 扫描组件
    comps_data = client.get_components(file_key)
    components = comps_data.get("meta", {}).get("components", [])

    # 2. 遍历 Canvas 和 Top-level Frames (Screens)
    pages = []
    for canvas in doc.get("children", []):
        if canvas.get("type") != "CANVAS":
            continue
        page_name = canvas.get("name", "Page")
        screens = []
        for frame in canvas.get("children", []):
            fname = frame.get("name", "")
            ftype = frame.get("type", "")
            fid = frame.get("id", "")
            bb = frame.get("absoluteBoundingBox") or {}
            w = bb.get("width", 0)
            h = bb.get("height", 0)

            # 过滤明显不是手机界面的过小元素或图例
            is_screen = (w >= 300 and h >= 500) or ("view" in fname.lower() or "page" in fname.lower() or "screen" in fname.lower())
            screens.append({
                "name": fname,
                "type": ftype,
                "id": fid,
                "width": w,
                "height": h,
                "is_screen": is_screen
            })
        pages.append({"name": page_name, "screens": screens})

    # 3. 输出 Markdown 报告
    lines = [
        f"# 📱 App 页面架构与清单: {doc_name}",
        "",
        f"> **Figma 文件 Key**: `{file_key}`  ",
        f"> **生成时间**: 自动由 `figma-to-ios-pro` 扫描生成",
        "",
        "---",
        "",
        "## 🧭 页面与界面清单 (Screens Roadmap)",
        ""
    ]

    total_screens = 0
    for p in pages:
        screen_list = [s for s in p["screens"] if s["is_screen"]]
        total_screens += len(screen_list)
        lines.append(f"### 📄 画布/模块: {p['name']} ({len(screen_list)} 个界面)")
        lines.append("")
        lines.append("| 序号 | 界面/画板名称 | Node ID | 尺寸 (WxH) | 单独实现指令 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for idx, s in enumerate(screen_list, 1):
            cmd = f"`@figma-to-ios-pro 实现 https://www.figma.com/design/{file_key}?node-id={s['id'].replace(':', '-')}`"
            lines.append(f"| {idx} | **{s['name']}** | `{s['id']}` | {s['width']:.0f}x{s['height']:.0f} | {cmd} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        f"## 🧩 全局通用组件清单 (Master Components: 共 {len(components)} 个)",
        "",
        "| 组件名称 | 组件 Node ID | 描述 |",
        "| :--- | :--- | :--- |"
    ])
    for c in components:
        lines.append(f"| **{c.get('name', '')}** | `{c.get('node_id', '')}` | {c.get('description') or '通用母版组件'} |")

    out_path = Path(args.out).resolve()
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n🎉 扫描完成！共发现 {len(pages)} 个画布，{total_screens} 个业务界面，{len(components)} 个全局通用组件。")
    print(f"📄 架构清单已输出至: {out_path}")


if __name__ == "__main__":
    main()
