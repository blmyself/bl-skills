# Shared UIKit/XIB Component Hardening

Use this reference when UIKit/XIB work touches a reused cell, card, row, or section whose anatomy is shared across multiple screens or modes.

## Core rules

1. Build a per-component spec sheet before editing.
2. Separate XIB-owned values from Swift-owned values.
3. Verify semantic tokens against resolved project assets when naming is ambiguous.
4. Keep shared component layout changes reversible across modes and screens.
5. Re-check the final implementation against the spec sheet, not only against memory.

## Workflow

### 1. Build the spec sheet

- Use `component-spec-sheet-template.md`.
- Capture exact values from Figma for:
  - padding
  - gap rhythm
  - radius
  - shadow
  - border rules
  - typography
  - badge, radio, and icon sizes
  - interactive affordances
- Mark each row with its implementation owner:
  - `XIB`
  - `Swift`
  - `Shared token`

If you want a scaffolded file, run:

```bash
python3 scripts/create_component_spec_sheet.py \
  --component "AddressCell" \
  --figma-node "9502:128333,9502:128348" \
  --screens "Checkout Shipping,My Address Book" \
  --out /tmp/address_cell_spec.md
```

### 2. Verify tokens before patching

- Read `token-verification-workflow.md`.
- Do not pick a token by name similarity alone.
- When a value is design-critical and token names are ambiguous:
  - extract the exact Figma value
  - map candidate semantic tokens
  - verify resolved project values
  - choose the token that matches both the design and the component's semantic family

### 3. Patch with reuse in mind

- Keep shared anatomy shared.
- Keep screen-specific behavior screen-specific.
- If the component changes subview arrangement by mode, require a reversible pair such as:
  - `apply<Mode>Layout()`
  - `restoreDefaultLayout()`
- Do not one-way mutate arranged subviews in `awakeFromNib()` for reused cells or views.
- Keep selection, navigation, and business behavior in the owner that already controls them.

### 4. Close with a focused audit

- Re-check the final implementation against the spec sheet.
- Classify any remaining gap as:
  - `XIB`
  - `Swift runtime`
  - `Token`
  - `Reuse`
  - `Behavior`

## When this reference is mandatory

Use it when any of these are true:

- one component is reused by multiple screens
- a shared row has compact and multiline variants
- styling changes are small but regressions keep slipping through
- the component mixes nib structure with runtime Swift styling
- token naming is ambiguous enough to make visual regressions likely
