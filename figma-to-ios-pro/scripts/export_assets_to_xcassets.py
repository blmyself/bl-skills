#!/usr/bin/env python3
"""
Export Figma Icons and Images directly to Xcode Asset Catalog (Assets.xcassets / Images.xcassets)
支持按模块 Namespace 自动归类存储、@2x/@3x 多倍图切图生成、防重名、自动兼容 Assets.xcassets 与 Images.xcassets。
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional

try:
    from figma_api_client import FigmaAPIClient
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient


def parse_figma_url(url: str) -> Tuple[str, str]:
    file_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url)
    node_match = re.search(r"node-id=([a-zA-Z0-9%:\-_]+)", url)
    
    file_key = file_match.group(1) if file_match else url
    node_id = node_match.group(1) if node_match else ""
    node_id = node_id.replace("%3A", ":").replace("-", ":")
    return file_key, node_id


def sanitize_asset_name(name: str) -> str:
    """标准化 Asset 名称，去除特殊字符"""
    clean = name.strip()
    if "/" in clean:
        clean = clean.split("/")[-1]
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or clean[0].isdigit():
        clean = "img_" + clean
    return clean


def find_xcassets_dir(search_root: Path) -> Optional[Path]:
    """智能多级探测工程中的 Asset Catalog 目录 (优先 Assets.xcassets，兼容 Images.xcassets)"""
    # 1. 优先搜索现代标准 Assets.xcassets (排除 build / Pods / 派生目录)
    candidates = [
        p for p in search_root.glob("**/Assets.xcassets")
        if not any(part.startswith(".") or part in ["build", "DerivedData", "Pods"] for part in p.parts)
    ]
    if candidates:
        return candidates[0]

    # 2. 搜索兼容的 Images.xcassets
    img_candidates = [
        p for p in search_root.glob("**/Images.xcassets")
        if not any(part.startswith(".") or part in ["build", "DerivedData", "Pods"] for part in p.parts)
    ]
    if img_candidates:
        return img_candidates[0]

    # 3. 搜索工程内任意其他 *.xcassets
    any_candidates = [
        p for p in search_root.glob("**/*.xcassets")
        if not any(part.startswith(".") or part in ["build", "DerivedData", "Pods"] for part in p.parts)
    ]
    if any_candidates:
        return any_candidates[0]

    return None


def collect_asset_nodes(node: Dict[str, Any], assets: List[Dict[str, Any]], visited_ids: Set[str]):
    """递归遍历节点树，智能识别图标与切图元素"""
    nid = node.get("id", "")
    ntype = node.get("type", "")
    nname = node.get("name", "")
    bb = node.get("absoluteBoundingBox") or {}
    w = bb.get("width", 0)
    h = bb.get("height", 0)

    # 1. 检查是否有图片填充 (Image Fill)
    has_image_fill = False
    for fill in node.get("fills", []):
        if fill.get("type") == "IMAGE":
            has_image_fill = True
            break

    # 2. 检查名称特征与尺寸特征
    is_icon_name = any(k in nname.lower() for k in ["icon", "ic_", "logo", "avatar", "badge", "btn_", "arrow", "tab_"])
    is_vector_shape = ntype in ["VECTOR", "BOOLEAN_OPERATION", "STAR", "REGULAR_POLYGON"]
    is_icon_sized = (10 <= w <= 80) and (10 <= h <= 80)
    has_export_settings = bool(node.get("exportSettings"))

    # 识别为切图资产的条件
    should_export = False
    if nid not in visited_ids:
        if has_image_fill:
            should_export = True
        elif has_export_settings:
            should_export = True
        elif is_icon_name and is_icon_sized:
            should_export = True
        elif ntype == "INSTANCE" and is_icon_sized and is_icon_name:
            should_export = True

    if should_export and w > 4 and h > 4:
        visited_ids.add(nid)
        assets.append({
            "id": nid,
            "name": sanitize_asset_name(nname),
            "orig_name": nname,
            "type": ntype,
            "width": w,
            "height": h
        })
        return

    # 继续递归子节点
    for child in node.get("children", []):
        collect_asset_nodes(child, assets, visited_ids)


def create_namespace_folder(base_xcassets: Path, module_name: str) -> Path:
    """创建带有 provides-namespace 的模块资产文件夹"""
    folder_path = base_xcassets / module_name
    folder_path.mkdir(parents=True, exist_ok=True)

    contents_json = folder_path / "Contents.json"
    contents_data = {
        "info": {
            "author": "xcode",
            "version": 1
        },
        "properties": {
            "provides-namespace": True
        }
    }
    contents_json.write_text(json.dumps(contents_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder_path


def create_imageset(folder: Path, asset_name: str, p2x_data: bytes, p3x_data: bytes) -> Path:
    """在指定模块目录下创建 .imageset 包含 @2x 和 @3x 图片与 Contents.json"""
    imageset_path = folder / f"{asset_name}.imageset"
    imageset_path.mkdir(parents=True, exist_ok=True)

    file_2x_name = f"{asset_name}@2x.png"
    file_3x_name = f"{asset_name}@3x.png"

    (imageset_path / file_2x_name).write_bytes(p2x_data)
    (imageset_path / file_3x_name).write_bytes(p3x_data)

    contents_data = {
        "images": [
            {
                "idiom": "universal",
                "scale": "1x"
            },
            {
                "filename": file_2x_name,
                "idiom": "universal",
                "scale": "2x"
            },
            {
                "filename": file_3x_name,
                "idiom": "universal",
                "scale": "3x"
            }
        ],
        "info": {
            "author": "xcode",
            "version": 1
        }
    }
    (imageset_path / "Contents.json").write_text(
        json.dumps(contents_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return imageset_path


def main():
    parser = argparse.ArgumentParser(description="从 Figma 批量导出切图至 Xcode Asset Catalog (Assets.xcassets / Images.xcassets)")
    parser.add_argument("url", help="Figma 节点或文件 URL")
    parser.add_argument("--module", default="Common", help="模块 Namespace 文件夹名称 (如 PredictionLeak, Home, User)")
    parser.add_argument("--xcassets", default=None, help="目标 *.xcassets 路径 (默认优先搜索 Assets.xcassets，兼容 Images.xcassets)")
    parser.add_argument("--prefix", default="", help="资源名称前缀 (如 PL_, IC_)")
    args = parser.parse_args()

    file_key, node_id = parse_figma_url(args.url)
    client = FigmaAPIClient()

    # 1. 确定 xcassets 路径
    xcassets_path = Path(args.xcassets).resolve() if args.xcassets else find_xcassets_dir(Path.cwd())
    if not xcassets_path or not xcassets_path.exists():
        # 若工程中均未发现，自动在当前目录创建标准 Assets.xcassets
        default_dir = Path.cwd() / "Assets.xcassets"
        default_dir.mkdir(parents=True, exist_ok=True)
        (default_dir / "Contents.json").write_text(
            json.dumps({"info": {"author": "xcode", "version": 1}}, indent=2), encoding="utf-8"
        )
        xcassets_path = default_dir
        print(f"ℹ️ 工程中未找到已有 Asset Catalog，已自动创建标准: {xcassets_path}")

    print(f"📁 目标 Asset Catalog: {xcassets_path.name} ({xcassets_path})")
    print(f"🏷️  模块 Namespace: {args.module}")

    # 2. 获取节点树
    print(f"🔍 正在检索 Figma 节点树 [File: {file_key}, RootNode: {node_id or 'All'}]...")
    if node_id:
        doc_data = client.get_nodes(file_key, [node_id]).get("nodes", {}).get(node_id, {}).get("document", {})
    else:
        doc_data = client.get_file(file_key, depth=3).get("document", {})

    if not doc_data:
        print("❌ 未获取到有效的节点数据，请检查 URL 或 Token。", file=sys.stderr)
        sys.exit(1)

    # 3. 收集切图候选
    asset_nodes = []
    collect_asset_nodes(doc_data, asset_nodes, set())

    if not asset_nodes:
        print("ℹ️ 该节点下未识别到明显的独立图标或切图元素。")
        return

    print(f"✨ 发现 {len(asset_nodes)} 个切图/图标候选：")
    for a in asset_nodes:
        print(f"  - [{a['id']}] {a['name']} ({a['width']:.0f}x{a['height']:.0f})")

    # 4. 批量请求 @2x 和 @3x 渲染图
    node_ids = [a["id"] for a in asset_nodes]
    print(f"\n⚡ 正在请求 Figma API 渲染 @2x 与 @3x 切图...")
    img_urls_2x = client.get_images(file_key, node_ids, scale=2, fmt="png")
    img_urls_3x = client.get_images(file_key, node_ids, scale=3, fmt="png")

    # 5. 创建 Namespace 模块目录
    module_folder = create_namespace_folder(xcassets_path, args.module)

    # 6. 下载并生成 .imageset
    import urllib.request
    downloaded_count = 0
    generated_assets = []

    for a in asset_nodes:
        nid = a["id"]
        url_2x = img_urls_2x.get(nid)
        url_3x = img_urls_3x.get(nid)

        if not url_2x or not url_3x:
            continue

        raw_name = a["name"]
        final_name = f"{args.prefix}{raw_name}" if args.prefix else raw_name

        try:
            req_2x = urllib.request.Request(url_2x, headers={"User-Agent": "FigmaToIOSPro/2.0"})
            with urllib.request.urlopen(req_2x, timeout=20) as resp:
                data_2x = resp.read()

            req_3x = urllib.request.Request(url_3x, headers={"User-Agent": "FigmaToIOSPro/2.0"})
            with urllib.request.urlopen(req_3x, timeout=20) as resp:
                data_3x = resp.read()

            create_imageset(module_folder, final_name, data_2x, data_3x)
            downloaded_count += 1
            generated_assets.append({
                "name": final_name,
                "namespaced_name": f"{args.module}/{final_name}"
            })
            print(f"  ✅ 已写入: {args.module}/{final_name}.imageset (@2x, @3x)")
        except Exception as e:
            print(f"  ❌ 下载 {final_name} 失败: {e}", file=sys.stderr)

    print(f"\n🎉 切图全部完成！共导出 {downloaded_count} 组高清资产到:")
    print(f"  📂 目录: {module_folder}")
    print("\n💡 iOS 代码使用方式:")
    for ga in generated_assets:
        print(f"  • Objective-C: [UIImage imageNamed:@\"{ga['namespaced_name']}\"] (或 @\"{ga['name']}\")")
        print(f"  • SwiftUI:     Image(\"{ga['namespaced_name']}\")")


if __name__ == "__main__":
    main()
