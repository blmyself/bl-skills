#!/usr/bin/env python3
import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a shared UIKit/XIB component spec sheet scaffold.")
    parser.add_argument("--component", required=True, help="Component name, e.g. AddressCell")
    parser.add_argument("--figma-node", default="", help="Comma-separated Figma node IDs")
    parser.add_argument("--screens", default="", help="Comma-separated screen names that reuse the component")
    parser.add_argument("--out", required=True, help="Output markdown path")
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# {args.component} Spec Sheet

## Component

- Name: {args.component}
- Reused by screens: {args.screens or '[fill me]'}
- Primary revamp screen: [fill me]
- Figma node IDs: {args.figma_node or '[fill me]'}

## Scope Freeze

- Must not change:
- Screen-specific behavior that stays screen-specific:
- Out of scope:

## Visual Spec Table

| Object | Figma node | Exact value | Implementation owner | Token/source | Mode/screen notes |
|---|---|---|---|---|---|
| Card radius |  |  | XIB or Swift |  |  |
| Card shadow |  |  | Swift |  |  |
| Card border |  |  | Swift |  |  |
| Horizontal padding |  |  | XIB |  |  |
| Vertical padding |  |  | XIB |  |  |
| Inter-item gap |  |  | XIB |  |  |
| Title typography |  |  | Swift |  |  |
| Body typography |  |  | Swift |  |  |
| Badge fill/text |  |  | Swift |  |  |
| Radio/icon size |  |  | XIB or Swift |  |  |
| Edit affordance |  |  | XIB or Swift |  |  |

## Ownership Split

### XIB-owned

- Structure:
- Constraint constants:
- Stack spacing:

### Swift-owned

- Shadow:
- Border color/state:
- Attributed text:
- Runtime colors:
- Mode switching:

## Reuse Risks

- Shared anatomy that must remain shared:
- Layout mutations that must be reversible:
- Modes/screens to retest:

## Validation Matrix

| Scenario | Expected result |
|---|---|
| Primary screen selected |  |
| Primary screen unselected |  |
| Secondary screen mode |  |
| Long multiline content |  |
| RTL |  |
| Rebind/reuse |  |
"""

    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
