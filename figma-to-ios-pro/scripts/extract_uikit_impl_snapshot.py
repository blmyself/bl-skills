#!/usr/bin/env python3
"""Extract a normalized UIKit implementation snapshot from XIB/Swift sources.

This script is analysis-only and does not mutate project files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

VIEW_TAGS = {
    "view",
    "stackView",
    "label",
    "button",
    "imageView",
    "collectionView",
    "tableView",
    "textField",
    "textView",
    "scrollView",
    "switch",
    "segmentedControl",
}

X_ATTRS = {"leading", "trailing", "centerX", "left", "right", "width"}
Y_ATTRS = {"top", "bottom", "centerY", "firstBaseline", "lastBaseline", "height"}


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_rect(element: ET.Element) -> dict[str, float] | None:
    rect = element.find("rect")
    if rect is None:
        return None
    x = parse_float(rect.get("x"))
    y = parse_float(rect.get("y"))
    width = parse_float(rect.get("width"))
    height = parse_float(rect.get("height"))
    if None in (x, y, width, height):
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    ax2 = a["x"] + a["width"]
    ay2 = a["y"] + a["height"]
    bx2 = b["x"] + b["width"]
    by2 = b["y"] + b["height"]
    return not (ax2 <= b["x"] or bx2 <= a["x"] or ay2 <= b["y"] or by2 <= a["y"])


def first_text_from_node(node: ET.Element) -> str | None:
    text_attr = node.get("text")
    if text_attr:
        return text_attr
    state = node.find("state")
    if state is not None and state.get("title"):
        return state.get("title")
    return None


def parse_color_node(color: ET.Element) -> dict[str, Any]:
    result: dict[str, Any] = {
        "key": color.get("key"),
        "name": color.get("name"),
        "red": color.get("red"),
        "green": color.get("green"),
        "blue": color.get("blue"),
        "white": color.get("white"),
        "alpha": color.get("alpha"),
        "color_space": color.get("colorSpace"),
        "custom_color_space": color.get("customColorSpace"),
        "system_color": color.get("systemColor"),
    }
    return {k: v for k, v in result.items() if v is not None}


def collect_nodes(root_view: ET.Element) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    children_by_parent: dict[str, list[str]] = {}
    stack_spacing: list[dict[str, Any]] = []

    def visit(node: ET.Element, parent_id: str | None, depth: int, order: int) -> int:
        tag = local_name(node.tag)
        if tag not in VIEW_TAGS:
            return order

        node_id = node.get("id", "")
        frame = parse_rect(node)
        text = first_text_from_node(node)

        node_entry: dict[str, Any] = {
            "id": node_id,
            "type": tag,
            "user_label": node.get("userLabel"),
            "text": text,
            "parent_id": parent_id,
            "depth": depth,
            "draw_order": order,
            "frame": frame,
            "alpha": parse_float(node.get("alpha")),
            "clips_subviews": node.get("clipsSubviews"),
            "content_mode": node.get("contentMode"),
        }

        font = node.find("fontDescription")
        if font is not None:
            node_entry["font"] = {
                "name": font.get("name"),
                "family": font.get("family"),
                "point_size": parse_float(font.get("pointSize")),
                "type": font.get("type"),
            }

        colors = [parse_color_node(c) for c in node.findall("color")]
        if colors:
            node_entry["colors"] = colors

        runtime_attributes = []
        user_defined = node.find("userDefinedRuntimeAttributes")
        if user_defined is not None:
            for attr in user_defined.findall("userDefinedRuntimeAttribute"):
                value_node = attr.find("*[@key='value']")
                value: Any = None
                if value_node is not None:
                    value = value_node.get("value")
                    parsed = parse_float(value)
                    if parsed is not None:
                        value = parsed
                runtime_attributes.append(
                    {
                        "type": attr.get("type"),
                        "key_path": attr.get("keyPath"),
                        "value": value,
                    }
                )
        if runtime_attributes:
            node_entry["runtime_attributes"] = runtime_attributes

        nodes.append(node_entry)

        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(node_id)

        if tag == "stackView":
            stack_spacing.append(
                {
                    "id": node_id,
                    "spacing": parse_float(node.get("spacing")),
                    "axis": node.get("axis"),
                    "alignment": node.get("alignment"),
                    "distribution": node.get("distribution"),
                }
            )

        next_order = order + 1
        subviews = node.find("subviews")
        if subviews is not None:
            for child in list(subviews):
                next_order = visit(child, node_id, depth + 1, next_order)

        return next_order

    visit(root_view, None, 0, 0)
    return nodes, children_by_parent, stack_spacing


def collect_constraints(document_root: ET.Element) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    for constraint in document_root.iter("constraint"):
        entry = {
            "id": constraint.get("id"),
            "first_item": constraint.get("firstItem"),
            "first_attribute": constraint.get("firstAttribute"),
            "second_item": constraint.get("secondItem"),
            "second_attribute": constraint.get("secondAttribute"),
            "constant": parse_float(constraint.get("constant")),
            "multiplier": constraint.get("multiplier"),
            "priority": parse_float(constraint.get("priority")),
            "relation": constraint.get("relation"),
        }
        constraints.append(entry)
    return constraints


def collect_actions(document_root: ET.Element) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for action in document_root.iter("action"):
        actions.append(
            {
                "selector": action.get("selector"),
                "destination": action.get("destination"),
                "event_type": action.get("eventType"),
                "id": action.get("id"),
            }
        )
    return actions


def collect_outlets(document_root: ET.Element) -> dict[str, str]:
    outlets: dict[str, str] = {}
    for outlet in document_root.iter("outlet"):
        prop = outlet.get("property")
        destination = outlet.get("destination")
        if not prop or not destination:
            continue
        outlets[prop] = destination
    return outlets


def parse_runtime_overrides(swift_text: str) -> dict[str, Any]:
    overrides: dict[str, Any] = {
        "font_assignments": [],
        "corner_radius": [],
        "shadow_assignments": [],
        "attributed_text_hints": [],
        "text_assignments": [],
    }

    for match in re.finditer(r"(?m)^\s*([A-Za-z_][\w\.]*)\.font\s*=\s*(.+)$", swift_text):
        overrides["font_assignments"].append(
            {
                "target": match.group(1),
                "expression": match.group(2).strip(),
            }
        )

    for match in re.finditer(r"(?m)^\s*([A-Za-z_][\w\.]*)\.layer\.cornerRadius\s*=\s*([0-9]*\.?[0-9]+)", swift_text):
        overrides["corner_radius"].append(
            {
                "target": match.group(1),
                "value": float(match.group(2)),
            }
        )

    for match in re.finditer(
        r"(?m)^\s*([A-Za-z_][\w\.]*)\.layer\.(shadowColor|shadowOpacity|shadowOffset|shadowRadius)\s*=\s*(.+)$",
        swift_text,
    ):
        overrides["shadow_assignments"].append(
            {
                "target": match.group(1),
                "property": match.group(2),
                "expression": match.group(3).strip(),
            }
        )

    for keyword in ("NSAttributedString", ".kern", ".underlineStyle", "setUnderlineTitle", "attributedText"):
        if keyword in swift_text:
            overrides["attributed_text_hints"].append(keyword)

    for match in re.finditer(r"(?m)^\s*([A-Za-z_][\w\.]*)\.text\s*=\s*(.+)$", swift_text):
        overrides["text_assignments"].append(
            {
                "target": match.group(1),
                "expression": match.group(2).strip(),
            }
        )

    return overrides


def parse_dynamic_hints(swift_text: str) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    if "UICollectionViewDataSource" in swift_text:
        hints.append({"kind": "collection_view_datasource", "confidence": "high"})
    if "UITableViewDataSource" in swift_text:
        hints.append({"kind": "table_view_datasource", "confidence": "high"})

    number_of_items = re.findall(r"numberOfItemsInSection\s+section:\s*Int\)\s*->\s*Int\s*\{\s*([0-9]+)", swift_text)
    for value in number_of_items:
        hints.append({"kind": "fixed_collection_item_count", "value": int(value), "confidence": "medium"})

    if "safe:" in swift_text:
        hints.append({"kind": "safe_indexing_present", "confidence": "medium"})

    return hints


def parse_wiring_hints(swift_text: str, presenter_text: str | None) -> dict[str, Any]:
    presenter_calls = sorted(set(re.findall(r"presenter\.([A-Za-z_][\w]*)\(", swift_text)))
    resolver_calls = sorted(set(re.findall(r"Resolver\.([A-Za-z_][\w]*)\(", swift_text)))
    navigation_calls = sorted(
        set(
            re.findall(
                r"\b(presentVC|present\(|pushVC|pushViewController|dismiss\(|popViewController)\b",
                swift_text,
            )
        )
    )
    ibaction_methods = sorted(set(re.findall(r"@IBAction\s+private\s+func\s+([A-Za-z_][\w]*)", swift_text)))

    presenter_methods: list[str] = []
    if presenter_text:
        presenter_methods = sorted(set(re.findall(r"(?m)^\s*func\s+([A-Za-z_][\w]*)\(", presenter_text)))

    return {
        "presenter_calls": presenter_calls,
        "resolver_calls": resolver_calls,
        "navigation_calls": navigation_calls,
        "ibaction_methods": ibaction_methods,
        "presenter_methods": presenter_methods,
    }


def build_anatomy(
    nodes: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    children_by_parent: dict[str, list[str]],
) -> dict[str, Any]:
    x_axis = []
    y_axis = []

    for constraint in constraints:
        first_attr = constraint.get("first_attribute")
        second_attr = constraint.get("second_attribute")
        attrs = {first_attr, second_attr}
        if any(attr in X_ATTRS for attr in attrs if attr):
            x_axis.append(constraint)
        if any(attr in Y_ATTRS for attr in attrs if attr):
            y_axis.append(constraint)

    frame_by_id: dict[str, dict[str, float]] = {
        node["id"]: node["frame"]
        for node in nodes
        if node.get("id") and isinstance(node.get("frame"), dict)
    }

    overlaps: list[dict[str, Any]] = []
    for parent_id, child_ids in children_by_parent.items():
        valid_children = [cid for cid in child_ids if cid in frame_by_id]
        for i in range(len(valid_children)):
            for j in range(i + 1, len(valid_children)):
                first_id = valid_children[i]
                second_id = valid_children[j]
                if intersects(frame_by_id[first_id], frame_by_id[second_id]):
                    overlaps.append(
                        {
                            "parent_id": parent_id,
                            "first_id": first_id,
                            "second_id": second_id,
                        }
                    )

    z_axis = {
        "draw_order": [
            {
                "id": node.get("id"),
                "type": node.get("type"),
                "depth": node.get("depth"),
                "draw_order": node.get("draw_order"),
            }
            for node in sorted(nodes, key=lambda n: (n.get("draw_order", 0), n.get("depth", 0)))
        ],
        "overlap_candidates": overlaps,
        "depth_cues": [
            {
                "id": node.get("id"),
                "alpha": node.get("alpha"),
                "clips_subviews": node.get("clips_subviews"),
            }
            for node in nodes
            if node.get("alpha") not in (None, 1.0) or node.get("clips_subviews") == "YES"
        ],
    }

    return {
        "x_axis": x_axis,
        "y_axis": y_axis,
        "z_axis": z_axis,
    }


def build_typography(
    nodes: list[dict[str, Any]],
    runtime_overrides: dict[str, Any],
    outlets: dict[str, str],
) -> dict[str, Any]:
    outlet_by_id: dict[str, list[str]] = {}
    for prop, destination in outlets.items():
        outlet_by_id.setdefault(destination, []).append(prop)

    xib_fonts = []
    for node in nodes:
        font = node.get("font")
        if not font:
            continue
        xib_fonts.append(
            {
                "id": node.get("id"),
                "type": node.get("type"),
                "text": node.get("text"),
                "outlet_properties": sorted(outlet_by_id.get(node.get("id", ""), [])),
                "font": font,
            }
        )

    return {
        "xib_fonts": xib_fonts,
        "runtime_font_assignments": runtime_overrides.get("font_assignments", []),
        "attributed_text_hints": runtime_overrides.get("attributed_text_hints", []),
    }


def build_colors(document_root: ET.Element, nodes: list[dict[str, Any]]) -> dict[str, Any]:
    resource_colors = []
    for named in document_root.iter("namedColor"):
        color_node = named.find("color")
        entry = {
            "name": named.get("name"),
            "color": parse_color_node(color_node) if color_node is not None else None,
        }
        resource_colors.append(entry)

    node_colors = []
    for node in nodes:
        for color in node.get("colors", []):
            node_colors.append(
                {
                    "id": node.get("id"),
                    "type": node.get("type"),
                    "color": color,
                }
            )

    return {
        "resource_named_colors": resource_colors,
        "node_colors": node_colors,
    }


def build_spacing_constraints(
    stack_spacing: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> dict[str, Any]:
    constraint_constants = []
    for item in constraints:
        if item.get("constant") is None and item.get("multiplier") is None:
            continue
        constraint_constants.append(item)

    return {
        "stack_spacing": stack_spacing,
        "constraint_constants": constraint_constants,
    }


def load_text(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract UIKit implementation snapshot from XIB/Swift files.")
    parser.add_argument("--xib", required=True, help="Absolute path to .xib file")
    parser.add_argument("--swift", required=True, help="Absolute path to view/controller .swift file")
    parser.add_argument("--presenter", help="Optional absolute path to presenter .swift file")
    parser.add_argument("--out", required=True, help="Absolute output path for snapshot JSON")
    args = parser.parse_args()

    xib_path = Path(args.xib).expanduser().resolve()
    swift_path = Path(args.swift).expanduser().resolve()
    presenter_path = Path(args.presenter).expanduser().resolve() if args.presenter else None
    out_path = Path(args.out).expanduser().resolve()

    missing = [str(path) for path in (xib_path, swift_path) if not path.exists()]
    if presenter_path and not presenter_path.exists():
        missing.append(str(presenter_path))
    if missing:
        for item in missing:
            eprint(f"ERROR: file not found: {item}")
        return 2

    try:
        tree = ET.parse(xib_path)
        document_root = tree.getroot()
    except ET.ParseError as exc:
        eprint(f"ERROR: unable to parse XIB XML: {exc}")
        return 3

    root_view = None
    for candidate in document_root.iter("view"):
        if candidate.get("id"):
            root_view = candidate
            break

    if root_view is None:
        eprint("ERROR: no root view found in XIB")
        return 4

    nodes, children_by_parent, stack_spacing = collect_nodes(root_view)
    constraints = collect_constraints(document_root)
    actions = collect_actions(document_root)
    outlets = collect_outlets(document_root)

    swift_text = load_text(swift_path) or ""
    presenter_text = load_text(presenter_path)

    runtime_overrides = parse_runtime_overrides(swift_text)
    dynamic_hints = parse_dynamic_hints(swift_text)
    wiring_hints = parse_wiring_hints(swift_text, presenter_text)

    snapshot = {
        "target": {
            "xib_path": str(xib_path),
            "swift_path": str(swift_path),
            "presenter_path": str(presenter_path) if presenter_path else None,
        },
        "anatomy": build_anatomy(nodes, constraints, children_by_parent),
        "typography": build_typography(nodes, runtime_overrides, outlets),
        "colors": build_colors(document_root, nodes),
        "spacing_and_constraints": build_spacing_constraints(stack_spacing, constraints),
        "interactions": {
            "xib_actions": actions,
            "ibaction_methods": wiring_hints.get("ibaction_methods", []),
        },
        "runtime_overrides": runtime_overrides,
        "dynamic_content_hints": dynamic_hints,
        "wiring_hints": wiring_hints,
        "outlets": outlets,
        "_nodes": nodes,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote implementation snapshot: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
