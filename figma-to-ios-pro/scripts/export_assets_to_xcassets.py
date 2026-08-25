#!/usr/bin/env python3
"""
Export Figma Icons and Images directly to Xcode Asset Catalog (Assets.xcassets / Images.xcassets)
支持按模块 Namespace 自动归类存储、@2x/@3x 多倍图切图生成、智能图层名清洗、中文语义转换、
垃圾默认名继承父级上下文、防重名消歧、自定义 --rename-map / --rename-file 与 --dry-run 审查模式。
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional

try:
    from figma_api_client import FigmaAPIClient, run_cli
except ImportError:
    from scripts.figma_api_client import FigmaAPIClient, run_cli


# 常用中文 UI 词汇到英文语义标准词典
ZH_TO_EN_DICT = {
    "返回": "back",
    "关闭": "close",
    "搜索": "search",
    "设置": "settings",
    "主页": "home",
    "首页": "home",
    "用户": "user",
    "我的": "mine",
    "个人": "profile",
    "删除": "delete",
    "编辑": "edit",
    "修改": "edit",
    "添加": "add",
    "增加": "add",
    "新建": "create",
    "分享": "share",
    "更多": "more",
    "提示": "info",
    "帮助": "help",
    "警告": "warning",
    "错误": "error",
    "成功": "success",
    "失败": "fail",
    "收藏": "favorite",
    "点赞": "like",
    "评论": "comment",
    "通知": "notification",
    "消息": "message",
    "刷新": "refresh",
    "下载": "download",
    "上传": "upload",
    "箭头": "arrow",
    "向左": "arrow_left",
    "向右": "arrow_right",
    "向上": "arrow_up",
    "向下": "arrow_down",
    "左": "left",
    "右": "right",
    "上": "up",
    "下": "down",
    "勾选": "check",
    "选中": "selected",
    "未选": "unselected",
    "默认": "default",
    "金币": "coin",
    "钱包": "wallet",
    "充值": "recharge",
    "提现": "withdraw",
    "支付": "pay",
    "购物车": "cart",
    "订单": "order",
    "筛选": "filter",
    "排序": "sort",
    "日历": "calendar",
    "时间": "time",
    "相机": "camera",
    "拍照": "camera",
    "相册": "album",
    "图片": "image",
    "视频": "video",
    "音频": "audio",
    "语音": "voice",
    "播放": "play",
    "暂停": "pause",
    "停止": "stop",
    "眼睛": "eye",
    "可见": "visible",
    "隐藏": "hidden",
    "锁": "lock",
    "解锁": "unlock",
    "复制": "copy",
    "扫码": "scan",
    "二维码": "qrcode",
    "占位图": "placeholder",
    "缺省图": "placeholder",
    "背景": "bg",
    "底图": "bg",
    "卡片": "card",
    "头像": "avatar",
    "角标": "badge",
    "徽章": "badge",
    "标签": "tag",
    "按钮": "btn",
    "图标": "ic",
    "星星": "star",
    "心": "heart",
    "男女": "gender",
    "男": "male",
    "女": "female",
    "位置": "location",
    "定位": "location",
    "地址": "address",
    "电话": "phone",
    "邮件": "email",
    "密码": "password",
    "验证码": "verify_code",
    "等级": "level",
    "皇冠": "crown",
    "钻石": "diamond",
    "礼物": "gift",
    "排行榜": "rank",
}

# Figma 常见无语义默认图层名模式
GENERIC_NAME_PATTERN = re.compile(
    r"^(vector|group|frame|rectangle|ellipse|union|subtract|intersect|exclude|line|polygon|star|component|layer|shape|path|image|mask)[\s_\-\d]*$",
    re.IGNORECASE
)


def parse_figma_url(url: str) -> Tuple[str, str]:
    file_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url)
    node_match = re.search(r"node-id=([a-zA-Z0-9%:\-_]+)", url)
    
    file_key = file_match.group(1) if file_match else url
    node_id = node_match.group(1) if node_match else ""
    node_id = node_id.replace("%3A", ":").replace("-", ":")
    return file_key, node_id


def camel_to_snake(name: str) -> str:
    """将 camelCase / PascalCase 转换为 snake_case"""
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def translate_chinese_terms(text: str) -> str:
    """将文本中的常见中文 UI 词汇翻译为英文语义"""
    res = text
    # 按长度降序替换，优先匹配更长词组 (如 '向左' 优于 '左')
    sorted_terms = sorted(ZH_TO_EN_DICT.items(), key=lambda x: len(x[0]), reverse=True)
    for zh, en in sorted_terms:
        if zh in res:
            res = res.replace(zh, f"_{en}_")
    return res


def sanitize_asset_name(
    raw_name: str,
    parent_names: Optional[List[str]] = None,
    width: float = 0,
    height: float = 0,
    has_image_fill: bool = False
) -> str:
    """
    智能化清洗并规范化 Asset 名称：
    1. 剥离路径层级、去除尺寸/版本/拷贝脏后缀
    2. 中文词汇语义翻译
    3. 若为 Vector/Group 等无语义默认名，自动借用有意义的父节点语义
    4. 规范化转为 snake_case 并补全标准前缀 (ic_ / btn_ / img_ / bg_)
    """
    clean = raw_name.strip()

    # 1. 剥离路径前缀 (如 "Icon/24/arrow_left" -> "arrow_left")
    if "/" in clean:
        clean = clean.split("/")[-1].strip()

    # 2. 去除脏后缀与修饰 (如 "(Copy)", "Copy of", "_v2", "_final", "@2x", ".png")
    clean = re.sub(r"\(copy\d*\)", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^copy\s+of\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"_(v\d+|final|new|copy\d*)$", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"@(2|3)x$", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\.(png|jpg|jpeg|svg|webp)$", "", clean, flags=re.IGNORECASE)

    # 3. 剥离无意义尺寸前缀 (如 "24_arrow_left" -> "arrow_left", "size_24_" -> "")
    clean = re.sub(r"^(size_)?\d{1,3}[\s_\-]+", "", clean, flags=re.IGNORECASE)

    # 4. 检查是否是无意义默认名 (如 Vector, Group 12, Frame 4)
    is_generic = bool(GENERIC_NAME_PATTERN.match(clean.strip()))
    if is_generic and parent_names:
        # 向上寻找第一个有意义的父容器名称
        meaningful_parent = ""
        for p in reversed(parent_names):
            p_clean = p.split("/")[-1].strip()
            if not GENERIC_NAME_PATTERN.match(p_clean):
                meaningful_parent = p_clean
                break
        if meaningful_parent:
            clean = meaningful_parent

    # 5. 中文词汇翻译
    clean = translate_chinese_terms(clean)

    # 6. 转 snake_case 并清理非英数字符
    clean = camel_to_snake(clean)
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")

    # 7. 补全标准前缀 (ic_, btn_, img_, bg_)
    is_icon_sized = (width > 0 and height > 0 and width <= 80 and height <= 80)
    has_type_prefix = any(clean.startswith(p) for p in ["ic_", "btn_", "img_", "bg_", "icon_"])

    if not has_type_prefix:
        if has_image_fill or width > 120 or height > 120:
            if "bg" in clean or "background" in clean:
                clean = "bg_" + clean
            else:
                clean = "img_" + clean
        elif "btn" in clean or "button" in clean:
            clean = "btn_" + clean
        elif is_icon_sized or "icon" in clean or "arrow" in clean or "ic" in clean:
            clean = "ic_" + clean
        else:
            clean = "ic_" + clean

    # 统一将 icon_ 前缀规范为 ic_
    if clean.startswith("icon_"):
        clean = "ic_" + clean[5:]

    # 清理多余的前后冗余类型词
    if clean.startswith("ic_"):
        clean = re.sub(r"(_ic|_icon)$", "", clean)
    elif clean.startswith("btn_"):
        clean = re.sub(r"(_btn|_button)$", "", clean)
    elif clean.startswith("img_"):
        clean = re.sub(r"(_img|_image|_pic|_picture)$", "", clean)
    elif clean.startswith("bg_"):
        clean = re.sub(r"(_bg|_background)$", "", clean)

    # 兜底：若纯数字或为空
    if not clean or clean.replace("_", "").isdigit():
        clean = f"ic_asset_{clean}" if clean else "ic_asset"

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


# 标准 iOS 系统字体清单 (不需转切图，可通过标准 UILabel 渲染)
STANDARD_SYSTEM_FONTS = {
    "pingfang", "pingfang sc", "pingfang tc", "pingfang hk",
    "system", "system font", ".applesystemuifont",
    "sf pro", "sf pro text", "sf pro display", "sf pro rounded",
    "san francisco", "sf compact", "sf compact text", "sf compact display",
    "helvetica", "helvetica neue", "apple color emoji"
}


def is_custom_or_artistic_text(node: Dict[str, Any]) -> Tuple[bool, str]:
    """
    检查 TEXT 节点是否应作为切图导出：
    1. fontFamily != PingFang/System 等标准系统字体（使用了特殊艺术字体/商用非系统字体）
    2. strokes 数量 > 0（即设置了描边、描边艺术字效果）
    3. 包含渐变填充 (GRADIENT_LINEAR 等)
    返回: (是否需要导出, 原因说明)
    """
    if node.get("type") != "TEXT":
        return False, ""

    style = node.get("style") or {}
    font_family = str(style.get("fontFamily") or style.get("fontPostScriptName") or "").strip().lower()

    # 检查字体是否属于标准系统字体
    is_standard_font = any(
        font_family == f or font_family.startswith(f + " ") or font_family.startswith(f + "-") or font_family.startswith(f + "_")
        for f in STANDARD_SYSTEM_FONTS
    )

    # 检查描边 (strokes)
    strokes = [s for s in (node.get("strokes") or []) if s.get("visible", True) is not False]
    has_strokes = len(strokes) > 0

    # 检查渐变填充
    has_gradient_fill = any(
        f.get("type") in ["GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "IMAGE"]
        and f.get("visible", True) is not False
        for f in (node.get("fills") or [])
    )

    if not is_standard_font and font_family:
        raw_family = style.get("fontFamily") or font_family
        return True, f"特殊/艺术字体 ({raw_family})"
    if has_strokes:
        return True, f"描边艺术字 (strokes={len(strokes)})"
    if has_gradient_fill:
        return True, "渐变填充艺术字"

    return False, ""


def collect_asset_nodes(
    node: Dict[str, Any],
    assets: List[Dict[str, Any]],
    visited_ids: Set[str],
    parent_chain: Optional[List[str]] = None
):
    """递归遍历节点树，智能识别图标与切图元素，并记录父节点上下文"""
    if parent_chain is None:
        parent_chain = []

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
    is_icon_name = any(k in nname.lower() for k in [
        "icon", "ic_", "logo", "avatar", "badge", "btn_", "arrow", "tab_", "chevron", "close", "back"
    ])
    is_icon_sized = (8 <= w <= 80) and (8 <= h <= 80)
    has_export_settings = bool(node.get("exportSettings"))

    # 3. 检查是否为特殊艺术字体 / 描边文本
    is_art_text, art_reason = is_custom_or_artistic_text(node)

    # 识别为切图资产的条件
    should_export = False
    if nid not in visited_ids:
        if has_image_fill:
            should_export = True
        elif is_art_text:
            should_export = True
        elif has_export_settings:
            should_export = True
        elif is_icon_name and is_icon_sized:
            should_export = True
        elif ntype == "INSTANCE" and is_icon_sized:
            should_export = True
        elif ntype in ["VECTOR", "BOOLEAN_OPERATION"] and is_icon_sized and (is_icon_name or len(parent_chain) <= 2):
            should_export = True

    if should_export and w > 4 and h > 4:
        visited_ids.add(nid)
        # 如果是艺术字，优先以文字内容或图层名规范化
        text_content = node.get("characters", "").strip() if is_art_text else ""
        raw_naming = f"text_{text_content}" if (text_content and len(text_content) <= 16) else nname
        auto_name = sanitize_asset_name(
            raw_name=raw_naming,
            parent_names=parent_chain,
            width=w,
            height=h,
            has_image_fill=has_image_fill
        )
        if is_art_text and not (auto_name.startswith("img_") or auto_name.startswith("ic_")):
            auto_name = "img_art_" + auto_name

        assets.append({
            "id": nid,
            "name": auto_name,
            "orig_name": nname,
            "parent_chain": list(parent_chain),
            "type": ntype,
            "width": w,
            "height": h,
            "has_image_fill": has_image_fill,
            "is_art_text": is_art_text,
            "art_reason": art_reason
        })
        return

    # 继续递归子节点，将当前有意义节点名加入父级链
    current_chain = list(parent_chain)
    if nname and not GENERIC_NAME_PATTERN.match(nname):
        current_chain.append(nname)

    for child in node.get("children", []):
        collect_asset_nodes(child, assets, visited_ids, current_chain)


def load_rename_map(map_arg: Optional[str], file_arg: Optional[str]) -> Dict[str, str]:
    """加载自定义重命名映射表 (支持 JSON 字符串或文件路径)"""
    rename_map: Dict[str, str] = {}
    if file_arg:
        fpath = Path(file_arg).resolve()
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    rename_map.update({str(k): str(v) for k, v in data.items()})
            except Exception as e:
                print(f"⚠️ 解析 --rename-file 失败: {e}", file=sys.stderr)
        else:
            print(f"⚠️ 指定的 --rename-file 文件不存在: {fpath}", file=sys.stderr)

    if map_arg:
        try:
            # 如果是直接传的 JSON 字符串
            data = json.loads(map_arg)
            if isinstance(data, dict):
                rename_map.update({str(k): str(v) for k, v in data.items()})
        except Exception:
            # 兼容 key=val,key2=val2 格式
            for item in map_arg.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    rename_map[k.strip()] = v.strip()
                elif ":" in item:
                    k, v = item.split(":", 1)
                    rename_map[k.strip()] = v.strip()

    return rename_map


def apply_rename_and_deduplicate(
    assets: List[Dict[str, Any]],
    rename_map: Dict[str, str],
    prefix: str = ""
) -> List[Dict[str, Any]]:
    """应用重命名映射并处理重名消歧"""
    used_names: Dict[str, int] = {}
    processed: List[Dict[str, Any]] = []

    for a in assets:
        nid = a["id"]
        orig_name = a["orig_name"]
        auto_name = a["name"]

        # 匹配优先级：1. 节点 ID -> 2. 原始图层名 -> 3. 自动清洗名
        custom_name = rename_map.get(nid) or rename_map.get(orig_name) or rename_map.get(auto_name)
        
        base_name = custom_name if custom_name else auto_name
        base_name = camel_to_snake(base_name)
        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", base_name).strip("_")

        if prefix and not base_name.startswith(prefix):
            final_name = f"{prefix}{base_name}"
        else:
            final_name = base_name

        # 重名消歧处理
        if final_name in used_names:
            used_names[final_name] += 1
            final_name = f"{final_name}_{used_names[final_name]}"
        else:
            used_names[final_name] = 1

        item = dict(a)
        item["final_name"] = final_name
        item["is_custom_renamed"] = bool(custom_name)
        processed.append(item)

    return processed


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
    parser.add_argument("--rename-map", default=None, help="自定义重命名映射 JSON 字符串 (如 '{\"123:456\": \"ic_nav_back\"}')")
    parser.add_argument("--rename-file", default=None, help="自定义重命名映射 JSON 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览识别出的切图及其规范重命名，不下载和写入文件")
    args = parser.parse_args()

    file_key, node_id = parse_figma_url(args.url)
    client = FigmaAPIClient()

    # 1. 确定 xcassets 路径
    xcassets_path = Path(args.xcassets).resolve() if args.xcassets else find_xcassets_dir(Path.cwd())
    if not xcassets_path or not xcassets_path.exists():
        if not args.dry_run:
            default_dir = Path.cwd() / "Assets.xcassets"
            default_dir.mkdir(parents=True, exist_ok=True)
            (default_dir / "Contents.json").write_text(
                json.dumps({"info": {"author": "xcode", "version": 1}}, indent=2), encoding="utf-8"
            )
            xcassets_path = default_dir
            print(f"ℹ️ 工程中未找到已有 Asset Catalog，已自动创建标准: {xcassets_path}")
        else:
            xcassets_path = Path.cwd() / "Assets.xcassets"

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

    # 加载重命名映射并消歧
    rename_map = load_rename_map(args.rename_map, args.rename_file)
    processed_assets = apply_rename_and_deduplicate(asset_nodes, rename_map, args.prefix)

    print(f"\n✨ 发现 {len(processed_assets)} 个切图/图标资产：")
    print("-" * 90)
    print(f"{'Node ID':<12} | {'Figma 原名':<24} | {'导出规范名称 (Assets)':<30} | {'尺寸':<8} | {'备注'}")
    print("-" * 90)
    for a in processed_assets:
        custom_flag = "🏷️自定义" if a.get("is_custom_renamed") else ""
        note = a.get("art_reason") or custom_flag or "标准切图"
        print(f"{a['id']:<12} | {a['orig_name'][:22]:<24} | {a['final_name']:<30} | {a['width']:.0f}x{a['height']:.0f:<5} | {note}")
    print("-" * 90)

    # 如果是 Dry-run 模式，仅输出建议的映射模板并退出
    if args.dry_run:
        print("\n🔎 [Dry Run 模式] 未进行网络下载与文件写入。")
        sample_map = {a["id"]: a["final_name"] for a in processed_assets}
        print("\n📋 建议的重命名映射表 (可修改后通过 --rename-map 传入):")
        print(json.dumps(sample_map, ensure_ascii=False, indent=2))
        return

    # 4. 批量请求 @2x 和 @3x 渲染图
    node_ids = [a["id"] for a in processed_assets]
    print(f"\n⚡ 正在请求 Figma API 渲染 @2x 与 @3x 切图...")
    img_urls_2x = client.get_images(file_key, node_ids, scale=2, fmt="png")
    img_urls_3x = client.get_images(file_key, node_ids, scale=3, fmt="png")

    # 5. 创建 Namespace 模块目录
    module_folder = create_namespace_folder(xcassets_path, args.module)

    # 6. 下载并生成 .imageset
    downloaded_count = 0
    generated_assets = []
    failed: List[str] = []

    for a in processed_assets:
        nid = a["id"]
        url_2x = img_urls_2x.get(nid)
        url_3x = img_urls_3x.get(nid)
        final_name = a["final_name"]

        if not url_2x or not url_3x:
            failed.append(f"{final_name} (Figma 未返回渲染 URL)")
            continue

        try:
            p2x = client.download_image(
                url_2x, client.image_cache_path(file_key, nid, 2, url_2x), skip_if_exists=True)
            p3x = client.download_image(
                url_3x, client.image_cache_path(file_key, nid, 3, url_3x), skip_if_exists=True)

            create_imageset(module_folder, final_name, p2x.read_bytes(), p3x.read_bytes())
            downloaded_count += 1
            generated_assets.append({
                "name": final_name,
                "namespaced_name": f"{args.module}/{final_name}"
            })
            print(f"  ✅ 已写入: {args.module}/{final_name}.imageset (@2x, @3x)")
        except Exception as e:
            failed.append(f"{final_name}: {e}")
            print(f"  ❌ 下载 {final_name} 失败: {e}", file=sys.stderr)

    print(f"\n🎉 切图全部完成！共导出 {downloaded_count} 组高清资产到:")
    print(f"  📂 目录: {module_folder}")
    print(f"  {client.usage_summary()}")
    if failed:
        print(f"  ⚠️ {len(failed)} 个资产未导出，重跑本命令即可续传 (已成功的走本地缓存):")
        for f in failed[:10]:
            print(f"     - {f}")
    print("\n💡 iOS 代码使用方式:")
    for ga in generated_assets:
        print(f"  • Objective-C: [UIImage imageNamed:@\"{ga['namespaced_name']}\"] (或 @\"{ga['name']}\")")
        print(f"  • SwiftUI:     Image(\"{ga['namespaced_name']}\")")


if __name__ == "__main__":
    run_cli(main)
