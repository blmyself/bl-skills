#!/usr/bin/env python3
"""
Export Design Tokens from Figma
从 Figma 文件中一键提取颜色、字体、阴影与圆角 Token，并自动输出 Objective-C 与 Swift 两个版本的常量文件。
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List

try:
    from figma_api_client import FigmaAPIClient, run_cli
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient, run_cli


def extract_file_key(url_or_key: str) -> str:
    """从 URL 或裸 Key 中提取 Figma File Key"""
    match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url_or_key)
    if match:
        return match.group(1)
    return url_or_key.strip()


def hex_from_rgba(r: float, g: float, b: float, a: float = 1.0) -> str:
    """浮点 RGBA 转 16 进制字符串"""
    ir, ig, ib = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    return f"0x{ir:02X}{ig:02X}{ib:02X}"


def sanitize_ident(name: str) -> str:
    """清理生成合法变量名"""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or clean[0].isdigit():
        clean = "T_" + clean
    return clean


def main():
    parser = argparse.ArgumentParser(description="从 Figma 提取 Design Tokens")
    parser.add_argument("url", help="Figma 文件 URL 或 File Key")
    parser.add_argument("--out-dir", default="./DesignTokens", help="输出目录 (默认 ./DesignTokens)")
    parser.add_argument("--prefix", default="App", help="类名/宏前缀 (默认 App)")
    args = parser.parse_args()

    file_key = extract_file_key(args.url)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔍 正在连接 Figma API 分析文件 [FileKey: {file_key}]...")
    client = FigmaAPIClient()

    # 1. 获取全局样式元数据 [Tier 3，额度充裕]
    styles_meta = client.get_styles(file_key)
    meta_styles = styles_meta.get("meta", {}).get("styles", [])

    # 2. 仅取文件名 [Tier 3 的 files/:key/meta]
    #    原实现在此处调用 get_file(depth=3)：那是最稀缺的 Tier1 额度 (Pro 仅 10 次/分)，
    #    却只用来读一个 name 字段，纯属浪费，且大文件响应可达数十 MB。
    doc_name = client.get_file_name(file_key, fallback="App Design System")

    colors = []
    typography = []

    for item in meta_styles:
        stype = item.get("style_type")
        sname = item.get("name", "")
        snode = item.get("node_id", "")
        desc = item.get("description", "")

        if stype == "FILL":
            colors.append({"name": sname, "node_id": snode, "desc": desc})
        elif stype == "TEXT":
            typography.append({"name": sname, "node_id": snode, "desc": desc})

    print(f"✨ 发现 {len(colors)} 个颜色样式，{len(typography)} 个字体样式。")

    # 尝试从具体节点拉取颜色值 (get_nodes 内部会自动去重分批，不再静默截断到前 50 个)
    if colors:
        node_ids = [c["node_id"] for c in colors if c["node_id"]]
        if node_ids:
            try:
                nodes_data = client.get_nodes(file_key, node_ids, depth=1).get("nodes", {})
                for c in colors:
                    nid = c["node_id"].replace("-", ":")
                    if nid in nodes_data:
                        doc = nodes_data[nid].get("document", {})
                        fills = doc.get("fills", [])
                        if fills and fills[0].get("type") == "SOLID":
                            clr = fills[0].get("color", {})
                            c["hex"] = hex_from_rgba(clr.get("r", 0), clr.get("g", 0), clr.get("b", 0))
            except Exception as e:
                print(f"⚠️ 解析颜色值异常: {e}", file=sys.stderr)

    # 3. 输出 Markdown 规范表
    md_lines = [
        f"# Design Tokens: {doc_name}",
        "",
        "## 🎨 颜色系统 (Color Tokens)",
        "",
        "| 样式名称 | 标识符 | 描述 / 默认色值 |",
        "| :--- | :--- | :--- |"
    ]
    for c in colors:
        ident = sanitize_ident(c["name"])
        hex_val = c.get("hex", "0x333333")
        md_lines.append(f"| **{c['name']}** | `{ident}` | `{hex_val}` {c.get('desc', '')} |")

    md_lines.extend([
        "",
        "## 🔤 字体系统 (Typography Tokens)",
        "",
        "| 样式名称 | 标识符 | 描述 |",
        "| :--- | :--- | :--- |"
    ])
    for t in typography:
        ident = sanitize_ident(t["name"])
        md_lines.append(f"| **{t['name']}** | `{ident}` | {t.get('desc', '标准字体')} |")

    md_path = out_dir / f"{args.prefix}DesignTokens.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # 4. 输出 Objective-C Header
    objc_lines = [
        f"// {args.prefix}DesignSystem.h",
        "// 自动由 figma-to-ios-pro 提取生成，严禁手动修改",
        "#import <UIKit/UIKit.h>",
        "",
        "#ifndef " + args.prefix + "DesignSystem_h",
        "#define " + args.prefix + "DesignSystem_h",
        "",
        "static inline UIColor *" + args.prefix + "HexColor(NSInteger hex) {",
        "    return [UIColor colorWithRed:((hex >> 16) & 0xFF) / 255.0",
        "                           green:((hex >> 8) & 0xFF) / 255.0",
        "                            blue:(hex & 0xFF) / 255.0",
        "                           alpha:1.0];",
        "}",
        "",
        "// MARK: - Color Tokens"
    ]
    for c in colors:
        ident = sanitize_ident(c["name"])
        hex_val = c.get("hex", "0x333333")
        macro_name = f"{args.prefix}Color_{ident}"
        objc_lines.append(f"#define {macro_name} {args.prefix}HexColor({hex_val}) // {c['name']}")

    objc_lines.extend([
        "",
        "#endif /* " + args.prefix + "DesignSystem_h */",
        ""
    ])
    objc_path = out_dir / f"{args.prefix}DesignSystem.h"
    objc_path.write_text("\n".join(objc_lines), encoding="utf-8")

    # 5. 输出 Swift 常量
    swift_lines = [
        f"// {args.prefix}DesignTokens.swift",
        "// 自动由 figma-to-ios-pro 提取生成",
        "import SwiftUI",
        "",
        f"public enum {args.prefix}DesignTokens {{",
        "    public enum Colors {",
    ]
    for c in colors:
        ident = sanitize_ident(c["name"])
        hex_val = c.get("hex", "0x333333").replace("0x", "#")
        swift_lines.append(f"        /// {c['name']}")
        swift_lines.append(f"        public static let {ident} = Color(hex: \"{hex_val}\")")

    swift_lines.extend([
        "    }",
        "}",
        "",
        "extension Color {",
        "    init(hex: String) {",
        "        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)",
        "        var int: UInt64 = 0",
        "        Scanner(string: hex).scanHexInt64(&int)",
        "        let a, r, g, b: UInt64",
        "        switch hex.count {",
        "        case 3: // RGB (12-bit)",
        "            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)",
        "        case 6: // RGB (24-bit)",
        "            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)",
        "        case 8: // ARGB (32-bit)",
        "            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)",
        "        default:",
        "            (a, r, g, b) = (1, 1, 1, 0)",
        "        }",
        "        self.init(.sRGB, red: Double(r) / 255, green: Double(g) / 255, blue: Double(b) / 255, opacity: Double(a) / 255)",
        "    }",
        "}"
    ])
    swift_path = out_dir / f"{args.prefix}DesignTokens.swift"
    swift_path.write_text("\n".join(swift_lines), encoding="utf-8")

    print(f"\n🎉 Token 导出完成！已写入:")
    print(f"  📄 文档: {md_path}")
    print(f"  🍏 ObjC 常量: {objc_path}")
    print(f"  🐦 Swift 常量: {swift_path}")
    print(f"  {client.usage_summary()}")


if __name__ == "__main__":
    run_cli(main)
