#!/usr/bin/env python3
"""Heuristic XIB runtime risk scan for stack-heavy UIKit layouts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


@dataclass
class Finding:
    severity: str
    title: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xib", required=True)
    parser.add_argument("--out")
    return parser.parse_args()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def iter_children_named(element: ET.Element, name: str):
    for child in list(element):
        if local_name(child.tag) == name:
            yield child


def has_fixed_height(element: ET.Element) -> bool:
    for constraints in iter_children_named(element, "constraints"):
        for constraint in iter_children_named(constraints, "constraint"):
            if constraint.attrib.get("firstAttribute") == "height":
                return True
    return False


def stack_axis(stack: ET.Element) -> str:
    return stack.attrib.get("axis", "horizontal")


def stack_alignment(stack: ET.Element) -> str:
    return stack.attrib.get("alignment", "fill")


def direct_subviews(container: ET.Element):
    for subviews in iter_children_named(container, "subviews"):
        for child in list(subviews):
            yield child


def multiline_labels(element: ET.Element):
    for child in element.iter():
        if local_name(child.tag) == "label" and child.attrib.get("numberOfLines") == "0":
            yield child


def first_label_text(element: ET.Element) -> str:
    for child in element.iter():
        if local_name(child.tag) == "label":
            return child.attrib.get("text", "<empty>")
    return "<no label>"


def scan_stack_risks(root: ET.Element) -> list[Finding]:
    findings: list[Finding] = []

    for stack in root.iter():
        if local_name(stack.tag) != "stackView":
            continue
        if stack_axis(stack) != "horizontal":
            continue
        if stack_alignment(stack) != "fill":
            continue

        children = list(direct_subviews(stack))
        has_fixed_visual_child = any(
            local_name(child.tag) in {"imageView", "view"} and has_fixed_height(child)
            for child in children
        )
        vertical_text_stacks = [
            child for child in children
            if local_name(child.tag) == "stackView"
            and stack_axis(child) == "vertical"
            and any(True for _ in multiline_labels(child))
        ]

        if has_fixed_visual_child and vertical_text_stacks:
            sample = first_label_text(vertical_text_stacks[0])
            findings.append(
                Finding(
                    severity="major",
                    title="Horizontal stack defaults to .fill beside fixed-height visual child",
                    detail=(
                        f"Stack id `{stack.attrib.get('id', '?')}` can collapse multiline text "
                        f"next to a fixed-height icon/view. Sample text: `{sample}`. "
                        "Prefer `alignment=\"top\"` unless the design explicitly requires equal heights."
                    ),
                )
            )

    return findings


def scan_label_height_risks(root: ET.Element) -> list[Finding]:
    findings: list[Finding] = []

    for label in root.iter():
        if local_name(label.tag) != "label":
            continue
        if label.attrib.get("numberOfLines") != "0":
            continue
        if has_fixed_height(label):
            findings.append(
                Finding(
                    severity="major",
                    title="Multiline label has fixed height constraint",
                    detail=(
                        f"Label id `{label.attrib.get('id', '?')}` text "
                        f"`{label.attrib.get('text', '<empty>')}` is multiline and also has a fixed "
                        "height constraint. Remove the fixed height unless clipping is intentional."
                    ),
                )
            )

    return findings


def scan_resource_risks(root: ET.Element) -> list[Finding]:
    findings: list[Finding] = []

    image_names = {image.attrib.get("name") for image in root.iter() if local_name(image.tag) == "image"}
    color_names = {color.attrib.get("name") for color in root.iter() if local_name(color.tag) == "namedColor"}

    for image_view in root.iter():
        if local_name(image_view.tag) == "imageView":
            image_name = image_view.attrib.get("image")
            if image_name and image_name not in image_names:
                findings.append(
                    Finding(
                        severity="major",
                        title="Image view references asset missing from XIB resources",
                        detail=(
                            f"Image view id `{image_view.attrib.get('id', '?')}` references `{image_name}`, "
                            "but the XIB `<resources>` block does not declare that image."
                        ),
                    )
                )

    for color in root.iter():
        if local_name(color.tag) == "color":
            name = color.attrib.get("name")
            if name and name not in color_names:
                findings.append(
                    Finding(
                        severity="minor",
                        title="Named color used without XIB resource declaration",
                        detail=(
                            f"Color `{name}` is referenced in the XIB, but the `<resources>` block does not "
                            "declare it. Verify whether Interface Builder will inject it or whether the XIB "
                            "needs an explicit namedColor entry."
                        ),
                    )
                )

    return findings


def render_markdown(xib_path: Path, findings: list[Finding]) -> str:
    lines = [f"# XIB Runtime Risk Scan", "", f"- XIB: `{xib_path}`", ""]
    if not findings:
        lines.append("No heuristic runtime-layout risks found.")
        return "\n".join(lines) + "\n"

    for idx, finding in enumerate(findings, start=1):
        lines.append(f"{idx}. **[{finding.severity.upper()}] {finding.title}**")
        lines.append(f"   {finding.detail}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    xib_path = Path(args.xib)
    root = ET.parse(xib_path).getroot()

    findings = []
    findings.extend(scan_stack_risks(root))
    findings.extend(scan_label_height_risks(root))
    findings.extend(scan_resource_risks(root))

    report = render_markdown(xib_path, findings)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
