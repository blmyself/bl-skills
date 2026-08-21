#!/usr/bin/env python3
"""Compare Figma design spec with UIKit implementation snapshot.

Analysis-only script: emits markdown reports and patch hints without editing project files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}
REQUIRED_TOP_KEYS = [
    "node",
    "tokens",
    "anatomy",
    "layout_tree",
    "interactions",
    "flow",
    "business_assumptions",
    "unresolved",
]


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at {path}: {exc}") from exc


def normalize_family(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    if "bell" in lowered:
        return "bell mt"
    if "ibm" in lowered and "plex" in lowered:
        return "ibm plex sans"
    return lowered.strip()


def infer_family_from_expression(expression: str) -> str | None:
    direct = normalize_family(expression)
    if direct in {"bell mt", "ibm plex sans"}:
        return direct

    style_match = re.search(r"appFont\s*\(\s*style\s*:\s*\.([A-Za-z_]+)", expression)
    if style_match:
        style = style_match.group(1).lower()
        if style in {"heavy", "black"}:
            return "bell mt"
        return "ibm plex sans"

    if "systemfont" in expression.lower():
        return "system"
    return None


def infer_size_from_expression(expression: str) -> float | None:
    match = re.search(r"size\s*:\s*([0-9]+(?:\.[0-9]+)?)", expression)
    if not match:
        return None
    return float(match.group(1))


def safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def add_finding(findings: list[dict[str, Any]], severity: str, title: str, evidence: str, recommendation: str, kind: str) -> None:
    findings.append(
        {
            "severity": severity,
            "title": title,
            "evidence": evidence,
            "recommendation": recommendation,
            "kind": kind,
        }
    )


def build_typography_maps(snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], set[str], bool]:
    outlets = snapshot.get("outlets", {}) if isinstance(snapshot.get("outlets"), dict) else {}
    id_to_outlets: dict[str, list[str]] = {}
    for prop, destination in outlets.items():
        id_to_outlets.setdefault(destination, []).append(prop)

    xib_fonts = safe_list(snapshot.get("typography", {}).get("xib_fonts"))
    runtime_fonts = safe_list(snapshot.get("runtime_overrides", {}).get("font_assignments"))
    attributed_hints = set(safe_list(snapshot.get("typography", {}).get("attributed_text_hints")))
    has_attributed_runtime = bool(attributed_hints.intersection({"NSAttributedString", ".kern", "attributedText"}))

    xib_by_target: dict[str, dict[str, Any]] = {}
    for entry in xib_fonts:
        font = entry.get("font", {})
        family = normalize_family(font.get("family") or font.get("name") or font.get("type"))
        size = font.get("point_size")
        outlets_for_node = safe_list(entry.get("outlet_properties"))
        if not outlets_for_node and entry.get("id"):
            outlets_for_node = id_to_outlets.get(entry["id"], [])
        for outlet in outlets_for_node:
            xib_by_target[outlet] = {
                "family": family,
                "size": size,
                "source": "xib",
            }

    runtime_by_target: dict[str, dict[str, Any]] = {}
    runtime_families: set[str] = set()
    for entry in runtime_fonts:
        target = entry.get("target")
        expression = entry.get("expression", "")
        family = infer_family_from_expression(expression)
        size = infer_size_from_expression(expression)
        if family:
            runtime_families.add(family)
        if target:
            runtime_by_target[target] = {
                "family": family,
                "size": size,
                "source": "runtime",
                "expression": expression,
            }

    return xib_by_target, runtime_by_target, runtime_families, has_attributed_runtime


def effective_font(target: str, xib_by_target: dict[str, Any], runtime_by_target: dict[str, Any]) -> dict[str, Any] | None:
    if target in runtime_by_target:
        runtime_value = dict(runtime_by_target[target])
        fallback = xib_by_target.get(target)
        if fallback:
            if runtime_value.get("size") is None:
                runtime_value["size"] = fallback.get("size")
            if runtime_value.get("family") is None:
                runtime_value["family"] = fallback.get("family")
        return runtime_value
    return xib_by_target.get(target)


def extract_xib_corner_radius(snapshot: dict[str, Any]) -> dict[str, float]:
    outlets = snapshot.get("outlets", {}) if isinstance(snapshot.get("outlets"), dict) else {}
    node_by_id: dict[str, dict[str, Any]] = {}

    for section in ("anatomy",):
        draw_order = safe_list(snapshot.get(section, {}).get("z_axis", {}).get("draw_order"))
        for node in draw_order:
            if isinstance(node, dict) and node.get("id"):
                node_by_id[node["id"]] = node

    # Recover full node details from typography colors is not sufficient. Snapshot does not expose all nodes directly,
    # so we inspect spacing constraints and fallback to outlet IDs only when corner radius is in runtime overrides.
    # To keep extraction deterministic, we check runtime_attributes if available in spacing block extensions.
    # For now we parse from a dedicated node list if present.
    node_list = safe_list(snapshot.get("_nodes"))
    for node in node_list:
        node_id = node.get("id")
        if node_id:
            node_by_id[node_id] = node

    result: dict[str, float] = {}
    for outlet, node_id in outlets.items():
        node = node_by_id.get(node_id)
        if not node:
            continue
        for attr in safe_list(node.get("runtime_attributes")):
            if attr.get("key_path") == "layer.cornerRadius" and isinstance(attr.get("value"), (int, float)):
                result[outlet] = float(attr["value"])
    return result


def extract_runtime_corner_radius(snapshot: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for entry in safe_list(snapshot.get("runtime_overrides", {}).get("corner_radius")):
        target = entry.get("target")
        value = entry.get("value")
        if target and isinstance(value, (int, float)):
            result[target] = float(value)
    return result


def extract_shadow_runtime(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for entry in safe_list(snapshot.get("runtime_overrides", {}).get("shadow_assignments")):
        target = entry.get("target")
        prop = entry.get("property")
        expr = entry.get("expression", "")
        if not target or not prop:
            continue
        result.setdefault(target, {})[prop] = expr
    return result


def parse_numeric(expr: str) -> float | None:
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", expr)
    if not m:
        return None
    return float(m.group(1))


def compare_design_to_impl(design_spec: dict[str, Any], snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    missing_keys = [key for key in REQUIRED_TOP_KEYS if key not in design_spec]
    if missing_keys:
        add_finding(
            findings,
            "major",
            "Design spec is incomplete",
            f"Missing required top-level keys: {', '.join(missing_keys)}",
            "Fill missing keys using templates/design_spec.template.json before trusting audit output.",
            "design_spec_completeness",
        )

    unresolved = safe_list(design_spec.get("unresolved"))
    critical_unresolved = 0
    for item in unresolved:
        if isinstance(item, dict) and item.get("severity") == "critical":
            critical_unresolved += 1
    if critical_unresolved > 0:
        severity = "major" if critical_unresolved <= 2 else "critical"
        add_finding(
            findings,
            severity,
            "Unresolved critical design fields",
            f"Design spec contains {critical_unresolved} unresolved critical fields.",
            "Re-extract only missing child nodes and update design_spec before applying patches.",
            "unresolved_fields",
        )

    xib_by_target, runtime_by_target, runtime_families, has_attributed_runtime = build_typography_maps(snapshot)

    typography_tokens = safe_list(design_spec.get("tokens", {}).get("typography"))
    for token in typography_tokens:
        if not isinstance(token, dict):
            continue
        family_expected = normalize_family(token.get("family"))
        size_expected = token.get("size")
        line_height = token.get("line_height")
        letter_spacing = token.get("letter_spacing")
        usage = token.get("usage", "unknown")

        targets = safe_list(token.get("targets"))
        if not targets and isinstance(token.get("target"), str):
            targets = [token["target"]]

        if not targets:
            if family_expected and family_expected not in runtime_families:
                add_finding(
                    findings,
                    "major",
                    f"Typography family not observed for usage '{usage}'",
                    f"Expected family '{family_expected}' is not visible in runtime font assignments.",
                    "Bind explicit UIFont assignment for the intended labels/buttons and re-check family mapping.",
                    "font_family_coverage",
                )
            continue

        for target in targets:
            target_value = effective_font(target, xib_by_target, runtime_by_target)
            if not target_value:
                add_finding(
                    findings,
                    "critical",
                    f"Missing typography target '{target}'",
                    f"Design token usage '{usage}' expects target '{target}' but no XIB/runtime font mapping was found.",
                    "Wire outlet-to-view mapping and assign the tokenized font in runtime if needed.",
                    "font_target_missing",
                )
                continue

            observed_family = normalize_family(target_value.get("family"))
            observed_size = target_value.get("size")

            if family_expected and observed_family and family_expected != observed_family:
                add_finding(
                    findings,
                    "critical",
                    f"Font family mismatch on '{target}'",
                    f"Usage '{usage}' expects '{family_expected}' but effective implementation resolves '{observed_family}'.",
                    "Update runtime font assignment to the expected family or document intentional deviation.",
                    "font_family_mismatch",
                )

            if isinstance(size_expected, (int, float)) and isinstance(observed_size, (int, float)):
                if abs(float(size_expected) - float(observed_size)) > 0.25:
                    add_finding(
                        findings,
                        "major",
                        f"Font size mismatch on '{target}'",
                        f"Usage '{usage}' expects {size_expected}pt but effective implementation uses {observed_size}pt.",
                        "Align XIB or runtime assignment to exact token size.",
                        "font_size_mismatch",
                    )

            if isinstance(line_height, (int, float)) and line_height > 0 and not has_attributed_runtime:
                add_finding(
                    findings,
                    "major",
                    f"Line-height handling not explicit for '{usage}'",
                    f"Token specifies line-height {line_height} but runtime attributed-text handling was not detected.",
                    "Apply attributed text with paragraph style lineHeight multiple/min/max settings.",
                    "line_height_missing",
                )

            if isinstance(letter_spacing, (int, float)) and abs(float(letter_spacing)) > 0.01 and ".kern" not in safe_list(snapshot.get("typography", {}).get("attributed_text_hints")):
                add_finding(
                    findings,
                    "major",
                    f"Letter-spacing handling not explicit for '{usage}'",
                    f"Token requires letter-spacing {letter_spacing} but no kern handling was detected.",
                    "Use attributed title/text with `.kern` for the affected control/label.",
                    "letter_spacing_missing",
                )

    radii_tokens = safe_list(design_spec.get("tokens", {}).get("radii"))
    runtime_radius = extract_runtime_corner_radius(snapshot)
    xib_radius = extract_xib_corner_radius(snapshot)

    for token in radii_tokens:
        if not isinstance(token, dict):
            continue
        usage = token.get("usage", "radius")
        expected = token.get("value")
        if not isinstance(expected, (int, float)):
            continue
        targets = safe_list(token.get("targets"))
        if not targets and isinstance(token.get("target"), str):
            targets = [token["target"]]
        for target in targets:
            observed = runtime_radius.get(target, xib_radius.get(target))
            if observed is None:
                add_finding(
                    findings,
                    "major",
                    f"Radius target missing on '{target}'",
                    f"Token '{usage}' expects radius {expected} but target has no observed cornerRadius.",
                    "Set `layer.cornerRadius` at runtime or via UDRA in XIB.",
                    "radius_missing",
                )
                continue
            if abs(float(expected) - float(observed)) > 0.1:
                add_finding(
                    findings,
                    "major",
                    f"Radius mismatch on '{target}'",
                    f"Token '{usage}' expects {expected} but effective implementation uses {observed}.",
                    "Align runtime and XIB corner radius to token value.",
                    "radius_mismatch",
                )

    shadows = safe_list(design_spec.get("tokens", {}).get("shadows"))
    shadow_runtime = extract_shadow_runtime(snapshot)
    for token in shadows:
        if not isinstance(token, dict):
            continue
        usage = token.get("usage", "shadow")
        targets = safe_list(token.get("targets"))
        if not targets and isinstance(token.get("target"), str):
            targets = [token["target"]]

        expected_blur = token.get("blur")
        expected_alpha = token.get("alpha")
        expected_radius = float(expected_blur) / 2 if isinstance(expected_blur, (int, float)) else None

        for target in targets:
            observed = shadow_runtime.get(target)
            if not observed:
                add_finding(
                    findings,
                    "major",
                    f"Shadow missing on '{target}'",
                    f"Token '{usage}' expects shadow, but no runtime shadow assignments were detected.",
                    "Add shadowColor, shadowOpacity, shadowOffset, shadowRadius in runtime setup.",
                    "shadow_missing",
                )
                continue

            if expected_radius is not None and "shadowRadius" in observed:
                numeric = parse_numeric(observed["shadowRadius"])
                if numeric is not None and abs(expected_radius - numeric) > 0.5:
                    add_finding(
                        findings,
                        "major",
                        f"Shadow radius mismatch on '{target}'",
                        f"Expected UIKit shadowRadius {expected_radius} (from blur {expected_blur}), observed expression '{observed['shadowRadius']}'.",
                        "Set `shadowRadius = blur / 2` according to token.",
                        "shadow_radius_mismatch",
                    )

            if isinstance(expected_alpha, (int, float)) and "shadowOpacity" in observed:
                numeric = parse_numeric(observed["shadowOpacity"])
                if numeric is not None and abs(float(expected_alpha) - numeric) > 0.02:
                    add_finding(
                        findings,
                        "minor",
                        f"Shadow opacity mismatch on '{target}'",
                        f"Expected opacity {expected_alpha}, observed expression '{observed['shadowOpacity']}'.",
                        "Align `shadowOpacity` with token alpha.",
                        "shadow_opacity_mismatch",
                    )

    for target, runtime_value in runtime_radius.items():
        xib_value = xib_radius.get(target)
        if xib_value is not None and abs(runtime_value - xib_value) > 0.1:
            add_finding(
                findings,
                "major",
                f"Effective value conflict on '{target}'",
                f"XIB radius is {xib_value} while runtime radius is {runtime_value}.",
                "Keep one source of truth or ensure both values are intentionally synchronized.",
                "effective_value_conflict",
            )

    summary = {
        "missing_design_keys": missing_keys,
        "critical_unresolved_count": critical_unresolved,
        "finding_counts": {
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "major": sum(1 for f in findings if f["severity"] == "major"),
            "minor": sum(1 for f in findings if f["severity"] == "minor"),
        },
    }

    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["title"]))
    return findings, summary


def markdown_report(findings: list[dict[str, Any]], summary: dict[str, Any], design_spec_path: Path, impl_path: Path) -> str:
    lines = [
        "# Figma vs UIKit Audit Report",
        "",
        f"- Design spec: `{design_spec_path}`",
        f"- Implementation snapshot: `{impl_path}`",
        "",
        "## Summary",
        "",
        f"- Critical findings: **{summary['finding_counts']['critical']}**",
        f"- Major findings: **{summary['finding_counts']['major']}**",
        f"- Minor findings: **{summary['finding_counts']['minor']}**",
    ]

    if summary.get("missing_design_keys"):
        lines.append(f"- Missing design-spec keys: `{', '.join(summary['missing_design_keys'])}`")

    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings. Implementation aligns with provided design spec.")
        return "\n".join(lines) + "\n"

    for idx, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"{idx}. [{finding['severity'].upper()}] {finding['title']}",
                f"   - Evidence: {finding['evidence']}",
                f"   - Recommendation: {finding['recommendation']}",
                f"   - Kind: `{finding['kind']}`",
                "",
            ]
        )

    return "\n".join(lines)


def markdown_patch_hints(findings: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
    target = snapshot.get("target", {}) if isinstance(snapshot.get("target"), dict) else {}
    xib_path = target.get("xib_path", "<xib>")
    swift_path = target.get("swift_path", "<swift>")

    lines = [
        "# Patch Hints (No Auto-Edit)",
        "",
        "These are suggestion-only hints derived from deterministic checks.",
        "",
        f"- XIB target: `{xib_path}`",
        f"- Swift target: `{swift_path}`",
        "",
        "## Suggested Patches",
        "",
    ]

    if not findings:
        lines.append("No patch hints required.")
        return "\n".join(lines) + "\n"

    for finding in findings:
        kind = finding["kind"]
        severity = finding["severity"].upper()
        if kind in {"font_family_mismatch", "font_size_mismatch", "font_target_missing"}:
            file_hint = swift_path
            action_hint = "Set explicit runtime font assignment to the tokenized family/size for the affected outlet."
        elif kind in {"line_height_missing", "letter_spacing_missing"}:
            file_hint = swift_path
            action_hint = "Use NSAttributedString with paragraph style and kern to match line-height/tracking tokens."
        elif kind in {"radius_mismatch", "radius_missing", "effective_value_conflict"}:
            file_hint = swift_path
            action_hint = "Unify corner radius between XIB UDRA and runtime assignment; keep one effective source of truth."
        elif kind.startswith("shadow"):
            file_hint = swift_path
            action_hint = "Apply tokenized shadow properties (`shadowColor`, `shadowOpacity`, `shadowOffset`, `shadowRadius`)."
        elif kind == "design_spec_completeness":
            file_hint = "design_spec"
            action_hint = "Complete required design_spec keys using the provided template before implementation decisions."
        else:
            file_hint = xib_path
            action_hint = finding["recommendation"]

        lines.extend(
            [
                f"- [{severity}] {finding['title']}",
                f"  - Target file: `{file_hint}`",
                f"  - Why: {finding['evidence']}",
                f"  - Suggested change: {action_hint}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def xib_signature(path: Path) -> dict[str, Any] | None:
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return None

    root = tree.getroot()
    counts = {
        "stackView": 0,
        "label": 0,
        "button": 0,
        "imageView": 0,
        "collectionView": 0,
    }
    spacing_values: list[float] = []

    for element in root.iter():
        name = element.tag.split("}")[-1]
        if name in counts:
            counts[name] += 1
        if name == "stackView":
            spacing = element.get("spacing")
            if spacing is not None:
                try:
                    spacing_values.append(float(spacing))
                except ValueError:
                    pass

    average_spacing = sum(spacing_values) / len(spacing_values) if spacing_values else 0.0
    return {
        "path": str(path),
        "counts": counts,
        "average_stack_spacing": average_spacing,
    }


def target_signature(snapshot: dict[str, Any]) -> dict[str, Any]:
    counts = {"stackView": 0, "label": 0, "button": 0, "imageView": 0, "collectionView": 0}

    draw_order = safe_list(snapshot.get("anatomy", {}).get("z_axis", {}).get("draw_order"))
    for node in draw_order:
        node_type = node.get("type") if isinstance(node, dict) else None
        if node_type in counts:
            counts[node_type] += 1

    spacings = [
        item.get("spacing")
        for item in safe_list(snapshot.get("spacing_and_constraints", {}).get("stack_spacing"))
        if isinstance(item.get("spacing"), (int, float))
    ]
    avg_spacing = sum(spacings) / len(spacings) if spacings else 0.0
    return {"counts": counts, "average_stack_spacing": avg_spacing}


def similarity_score(a: dict[str, Any], b: dict[str, Any]) -> float:
    score = 0.0
    for key in a["counts"]:
        score += abs(float(a["counts"][key]) - float(b["counts"].get(key, 0)))
    score += abs(float(a["average_stack_spacing"]) - float(b.get("average_stack_spacing", 0.0))) / 4.0
    return score


def donor_candidates(snapshot: dict[str, Any], repo_root: Path, limit: int) -> list[dict[str, Any]]:
    target = target_signature(snapshot)
    candidates: list[dict[str, Any]] = []

    for path in repo_root.rglob("*.xib"):
        if any(part in {".git", "DerivedData", "Pods", "build"} for part in path.parts):
            continue
        signature = xib_signature(path)
        if not signature:
            continue
        score = similarity_score(target, signature)
        signature["score"] = round(score, 3)
        candidates.append(signature)

    candidates.sort(key=lambda item: item["score"])
    return candidates[: max(1, limit)]


def markdown_donors(candidates: list[dict[str, Any]], repo_root: Path) -> str:
    lines = [
        "# Donor XIB Candidates",
        "",
        f"Ranked by structural similarity within `{repo_root}`.",
        "",
    ]
    if not candidates:
        lines.append("No donor candidates found.")
        return "\n".join(lines) + "\n"

    for idx, item in enumerate(candidates, start=1):
        lines.extend(
            [
                f"{idx}. `{item['path']}`",
                f"   - Score: {item['score']}",
                f"   - Counts: {item['counts']}",
                f"   - Average stack spacing: {item['average_stack_spacing']:.2f}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Figma design spec against UIKit implementation snapshot.")
    parser.add_argument("--design-spec", required=True, help="Absolute path to design-spec JSON")
    parser.add_argument("--impl-snapshot", required=True, help="Absolute path to implementation snapshot JSON")
    parser.add_argument("--repo-root", help="Optional repo root path for donor XIB mining")
    parser.add_argument("--report-out", required=True, help="Output markdown path for analysis report")
    parser.add_argument("--patch-hints-out", required=True, help="Output markdown path for patch hints")
    parser.add_argument("--donor-out", help="Optional output markdown path for donor candidates")
    parser.add_argument("--donor-limit", type=int, default=5, help="Number of donor candidates (default: 5)")
    args = parser.parse_args()

    design_spec_path = Path(args.design_spec).expanduser().resolve()
    impl_snapshot_path = Path(args.impl_snapshot).expanduser().resolve()
    report_out = Path(args.report_out).expanduser().resolve()
    patch_out = Path(args.patch_hints_out).expanduser().resolve()

    for path in (design_spec_path, impl_snapshot_path):
        if not path.exists():
            eprint(f"ERROR: file not found: {path}")
            return 2

    try:
        design_spec = load_json(design_spec_path)
        impl_snapshot = load_json(impl_snapshot_path)
    except ValueError as exc:
        eprint(f"ERROR: {exc}")
        return 3

    findings, summary = compare_design_to_impl(design_spec, impl_snapshot)

    report_out.parent.mkdir(parents=True, exist_ok=True)
    patch_out.parent.mkdir(parents=True, exist_ok=True)

    report_out.write_text(
        markdown_report(findings, summary, design_spec_path, impl_snapshot_path),
        encoding="utf-8",
    )
    patch_out.write_text(markdown_patch_hints(findings, impl_snapshot), encoding="utf-8")

    print(f"Wrote analysis report: {report_out}")
    print(f"Wrote patch hints: {patch_out}")

    if args.donor_out:
        donor_out = Path(args.donor_out).expanduser().resolve()
        donor_out.parent.mkdir(parents=True, exist_ok=True)
        if not args.repo_root:
            donor_out.write_text("# Donor XIB Candidates\n\n`--repo-root` was not provided.\n", encoding="utf-8")
            print(f"Wrote donor report: {donor_out}")
        else:
            repo_root = Path(args.repo_root).expanduser().resolve()
            if not repo_root.exists():
                eprint(f"ERROR: repo root not found: {repo_root}")
                return 4
            donors = donor_candidates(impl_snapshot, repo_root, args.donor_limit)
            donor_out.write_text(markdown_donors(donors, repo_root), encoding="utf-8")
            print(f"Wrote donor report: {donor_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
