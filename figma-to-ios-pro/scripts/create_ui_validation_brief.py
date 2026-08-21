import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a lightweight UI validation brief scaffold for figma-to-ios-ui."
    )
    parser.add_argument("--lane", required=True, help="UIKit/XIB or SwiftUI")
    parser.add_argument("--mode", required=True, help="quick, standard, or deep")
    parser.add_argument("--node", default="", help="Comma-separated Figma node IDs")
    parser.add_argument("--files", default="", help="Comma-separated touched files")
    parser.add_argument("--out", required=True, help="Output markdown path")
    args = parser.parse_args()

    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# UI Validation Brief

## Scope

- Lane: {args.lane}
- Mode: {args.mode}
- Node IDs: {args.node or '[fill me]'}
- Touched files: {args.files or '[fill me]'}

## Evidence Used

- `design_spec` section:
- Screenshot:
- Project UI memory brief:
- Extra repo examples:

## Checks

- Layout and hierarchy:
- Tokens and design-system mapping:
- Interaction and flow:
- Accessibility and motion:
- Project-convention fit:

## Result

- Pass / fail:
- Remaining deviations:
- Required follow-up:

## Learning Delta

- Confirmed repo rule:
- Rejected assumption:
- New reusable pattern:
- Failure shield:
"""

    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
