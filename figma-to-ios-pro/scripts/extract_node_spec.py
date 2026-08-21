#!/usr/bin/env python3
"""
Extract Node Spec and Screenshot from Figma
拉取单个或多个 Node 的详细布局属性，并下载渲染截图。
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

try:
    from figma_api_client import FigmaAPIClient
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient


def parse_figma_url(url: str):
    file_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url)
    node_match = re.search(r"node-id=([a-zA-Z0-9%:\-_]+)", url)
    
    file_key = file_match.group(1) if file_match else url
    node_id = node_match.group(1) if node_match else ""
    node_id = node_id.replace("%3A", ":").replace("-", ":")
    return file_key, node_id


def main():
    parser = argparse.ArgumentParser(description="提取 Figma Node 详细布局与截图")
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

    json_path = out_dir / f"node_{node_id.replace(':', '_')}.json"
    json_path.write_text(json.dumps(nodes_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. 拉取渲染截图
    img_urls = client.get_images(file_key, [node_id], scale=2, fmt="png")
    img_url = img_urls.get(node_id)
    img_path = None
    if img_url:
        img_path = out_dir / f"screenshot_{node_id.replace(':', '_')}.png"
        client.download_image(img_url, img_path)

    print(f"\n🎉 提取成功！")
    print(f"  📄 节点数据 JSON: {json_path}")
    if img_path:
        print(f"  🖼️ 渲染截图 PNG: {img_path}")


if __name__ == "__main__":
    main()
