#!/usr/bin/env python3
"""
Extract Node Spec, Screenshot, and Masonry Layout Constraints from Figma
拉取单个或多个 Node 的详细布局属性、下载渲染截图，并基于 RenderBounds 相对坐标计算输出
包含突破父容器负边距 (如 make.top.equalTo(superview).offset(-8)) 的 Masonry 代码。
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from figma_api_client import FigmaAPIClient, run_cli
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient, run_cli


def parse_figma_url(url: str):
    file_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url)
    node_match = re.search(r"node-id=([a-zA-Z0-9%:\-_]+)", url)
    
    file_key = file_match.group(1) if file_match else url
    node_id = node_match.group(1) if node_match else ""
    node_id = node_id.replace("%3A", ":").replace("-", ":")
    return file_key, node_id


def get_effective_bounds(node: Dict[str, Any]) -> Dict[str, float]:
    """优先使用 absoluteRenderBounds (真实视觉渲染边界，含描边/投影/负边距)，降级使用 absoluteBoundingBox"""
    bounds = node.get("absoluteRenderBounds") or node.get("absoluteBoundingBox") or {}
    return {
        "x": float(bounds.get("x", 0)),
        "y": float(bounds.get("y", 0)),
        "width": float(bounds.get("width", 0)),
        "height": float(bounds.get("height", 0)),
    }


def to_objc_var_name(name: str, ntype: str) -> str:
    """标准化图层名为 Objective-C 变量名 (如 headerCardView, badgeLabel, avatarImageView)"""
    # 拆分 PascalCase / camelCase / 下划线 / 空格
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s1)
    clean = re.sub(r"[^a-zA-Z0-9_]", " ", s2).strip()
    words = clean.split()
    if not words:
        words = ["subview"]

    # camelCase
    var_name = words[0].lower() + "".join(w.capitalize() for w in words[1:])
    var_name = re.sub(r"[^a-zA-Z0-9]", "", var_name)

    # 规范类型后缀
    if ntype == "TEXT":
        if not var_name.lower().endswith("label"):
            var_name += "Label"
    elif ntype in ["VECTOR", "BOOLEAN_OPERATION", "STAR", "REGULAR_POLYGON"]:
        if not (var_name.lower().endswith("imageview") or var_name.lower().endswith("icon")):
            var_name += "ImageView"
    elif ntype in ["FRAME", "GROUP", "COMPONENT", "INSTANCE"]:
        if not (var_name.lower().endswith("view") or var_name.lower().endswith("container")):
            var_name += "View"

    if var_name and var_name[0].isdigit():
        var_name = "item" + var_name

    return var_name


def calculate_relative_constraints(
    child: Dict[str, Any],
    parent: Dict[str, Any],
    superview_name: str = "self.view"
) -> Dict[str, Any]:
    """
    计算子节点相对父节点的 RenderBounds 坐标，检测溢出与负边距，生成 Masonry 约束代码
    """
    cb = get_effective_bounds(child)
    pb = get_effective_bounds(parent)
    c_name = child.get("name", "Child")
    c_type = child.get("type", "FRAME")
    var_name = to_objc_var_name(c_name, c_type)

    # 相对父节点坐标与边界差
    rel_top = cb["y"] - pb["y"]
    rel_left = cb["x"] - pb["x"]
    rel_bottom_overflow = (cb["y"] + cb["height"]) - (pb["y"] + pb["height"])
    rel_right_overflow = (cb["x"] + cb["width"]) - (pb["x"] + pb["width"])
    rel_trailing = (pb["x"] + pb["width"]) - (cb["x"] + cb["width"])
    rel_bottom_inset = (pb["y"] + pb["height"]) - (cb["y"] + cb["height"])

    # 溢出状态判断
    overflows = []
    is_top_overflow = rel_top < -0.5
    is_left_overflow = rel_left < -0.5
    is_right_overflow = rel_right_overflow > 0.5
    is_bottom_overflow = rel_bottom_overflow > 0.5

    if is_top_overflow:
        overflows.append(f"顶部向上溢出 ({rel_top:.1f}pt 负边距)")
    if is_left_overflow:
        overflows.append(f"左侧向外溢出 ({rel_left:.1f}pt 负边距)")
    if is_right_overflow:
        overflows.append(f"右侧向外溢出 (+{rel_right_overflow:.1f}pt 溢出)")
    if is_bottom_overflow:
        overflows.append(f"底部向外溢出 (+{rel_bottom_overflow:.1f}pt 溢出)")

    # 生成 Masonry 代码
    lines = []
    if overflows:
        lines.append(f"    // ⚠️ 悬浮/溢出元素 [{c_name}]: {', '.join(overflows)}")

    lines.append(f"    [self.{var_name} mas_makeConstraints:^(MASConstraintMaker *make) {{")

    # 垂直方向约束
    if is_top_overflow or (not is_bottom_overflow and rel_top <= (pb["height"] * 0.6)):
        # 优先相对顶部 (支持负边距如 offset(-8))
        lines.append(f"        make.top.equalTo({superview_name}.mas_top).offset({rel_top:.1f});")
    else:
        # 偏靠底部
        if is_bottom_overflow:
            lines.append(f"        make.bottom.equalTo({superview_name}.mas_bottom).offset({rel_bottom_overflow:.1f}); // 底部溢出")
        else:
            lines.append(f"        make.bottom.equalTo({superview_name}.mas_bottom).offset(-{rel_bottom_inset:.1f});")

    # 水平方向约束
    if is_left_overflow or (not is_right_overflow and rel_left <= (pb["width"] * 0.5)):
        # 偏靠左侧 (支持负边距)
        lines.append(f"        make.left.equalTo({superview_name}.mas_left).offset({rel_left:.1f});")
    else:
        # 偏靠右侧
        if is_right_overflow:
            lines.append(f"        make.right.equalTo({superview_name}.mas_right).offset({rel_right_overflow:.1f}); // 右侧溢出")
        else:
            lines.append(f"        make.right.equalTo({superview_name}.mas_right).offset(-{rel_trailing:.1f});")

    # 尺寸约束
    if cb["width"] > 0 and cb["height"] > 0:
        lines.append(f"        make.size.mas_equalTo(CGSizeMake({cb['width']:.1f}, {cb['height']:.1f}));")

    lines.append("    }];")

    return {
        "id": child.get("id"),
        "name": c_name,
        "type": c_type,
        "var_name": var_name,
        "bounds": cb,
        "relative_to_parent": {
            "top_offset": round(rel_top, 2),
            "left_offset": round(rel_left, 2),
            "trailing_offset": round(rel_trailing, 2),
            "bottom_inset": round(rel_bottom_inset, 2),
            "right_overflow": round(rel_right_overflow, 2),
            "bottom_overflow": round(rel_bottom_overflow, 2),
        },
        "overflows": overflows,
        "masonry_snippet": "\n".join(lines),
    }


def generate_layout_masonry_spec(root_node: Dict[str, Any]) -> Dict[str, Any]:
    """递归分析整个节点树，提取所有子节点的 RenderBounds 相对坐标与 Masonry 约束"""
    parent_bounds = get_effective_bounds(root_node)
    root_var_name = to_objc_var_name(root_node.get("name", "Container"), root_node.get("type", "FRAME"))

    constraints = []
    children = root_node.get("children", [])

    for child in children:
        c_spec = calculate_relative_constraints(child, root_node, superview_name=f"self.{root_var_name}")
        constraints.append(c_spec)

    # 组合成完整的 Objective-C 约束方法代码
    code_blocks = [
        f"// MARK: - Auto Generated Masonry Constraints for [{root_node.get('name')}]",
        f"// 基于 RenderBounds 相对坐标精密换算 (含负边距溢出校准)",
        f"- (void)setupSubviewsLayout {{",
        f"    // 1. 容器主视图自身约束",
        f"    [self.{root_var_name} mas_makeConstraints:^(MASConstraintMaker *make) {{",
        f"        make.size.mas_equalTo(CGSizeMake({parent_bounds['width']:.1f}, {parent_bounds['height']:.1f}));",
        f"    }}];",
        "",
        f"    // 2. 子视图约束及溢出负边距",
    ]

    for c in constraints:
        code_blocks.append(c["masonry_snippet"])
        code_blocks.append("")

    code_blocks.append("}")

    return {
        "root_node": {
            "id": root_node.get("id"),
            "name": root_node.get("name"),
            "var_name": root_var_name,
            "bounds": parent_bounds,
        },
        "child_constraints": constraints,
        "objc_masonry_code": "\n".join(code_blocks),
    }


def main():
    parser = argparse.ArgumentParser(description="提取 Figma Node 详细布局、截图及 RenderBounds 相对坐标 Masonry 约束")
    parser.add_argument("url", help="Figma 节点 URL (包含 node-id)")
    parser.add_argument("--out-dir", default="./figma_output", help="输出目录")
    args = parser.parse_args()

    file_key, node_id = parse_figma_url(args.url)
    if not node_id:
        print("❌ URL 中缺少 node-id 参数，请提供具体节点链接 (例如: ...?node-id=123-456)", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔍 正在提取节点数据 [FileKey: {file_key}, NodeID: {node_id}]...")
    client = FigmaAPIClient()

    # 1. 拉取节点 JSON
    nodes_data = client.get_nodes(file_key, [node_id])
    node_dict = nodes_data.get("nodes", {}).get(node_id, {})
    doc = node_dict.get("document", {})

    if not doc:
        print(f"❌ 未能获取到节点 {node_id} 的有效数据，请检查链接或 Token。", file=sys.stderr)
        sys.exit(1)

    json_path = out_dir / f"node_{node_id.replace(':', '_')}.json"
    json_path.write_text(json.dumps(nodes_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. 拉取渲染截图
    img_urls = client.get_images(file_key, [node_id], scale=2, fmt="png")
    img_url = img_urls.get(node_id)
    img_path = None
    if img_url:
        img_path = out_dir / f"screenshot_{node_id.replace(':', '_')}.png"
        client.download_image(img_url, img_path)

    # 3. 计算 RenderBounds 相对坐标与 Masonry 约束 (含负边距溢出)
    layout_spec = generate_layout_masonry_spec(doc)
    layout_json_path = out_dir / f"layout_masonry_{node_id.replace(':', '_')}.json"
    layout_json_path.write_text(json.dumps(layout_spec, ensure_ascii=False, indent=2), encoding="utf-8")

    code_path = out_dir / f"masonry_constraints_{node_id.replace(':', '_')}.m"
    code_path.write_text(layout_spec["objc_masonry_code"], encoding="utf-8")

    print(f"\n🎉 提取与约束计算成功！")
    print(f"  📄 原始节点数据 JSON : {json_path}")
    print(f"  📐 布局与约束规范 JSON : {layout_json_path}")
    print(f"  💻 Masonry 代码生成 .m : {code_path}")
    if img_path:
        print(f"  🖼️ 渲染截图 PNG       : {img_path}")

    # 打印检测到的溢出负边距元素
    overflow_items = [c for c in layout_spec["child_constraints"] if c["overflows"]]
    if overflow_items:
        print(f"\n⚡ 智能检测到 {len(overflow_items)} 个突破父容器的溢出/悬浮元素 (已自动生成负边距约束):")
        for item in overflow_items:
            print(f"  • [{item['name']}] (变量: {item['var_name']}) -> {', '.join(item['overflows'])}")

    print(f"\n{client.usage_summary()}")


if __name__ == "__main__":
    run_cli(main)
