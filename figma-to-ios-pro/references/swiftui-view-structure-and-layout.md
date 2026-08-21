# SwiftUI View Structure and Layout

Start from:

- `design_spec.layout_tree`
- `design_spec.anatomy.x_axis`
- `design_spec.anatomy.y_axis`
- `design_spec.anatomy.z_axis`
- `design_spec.node.platform_chrome_filtered_nodes`

## Layout translation rules

- Prefer existing shared layout primitives over raw values when the repo already exposes them.
- Preserve the Figma container hierarchy only to the degree needed for correct spacing, grouping, and interaction.
- Extract complex sections into focused subviews early and keep the root screen readable.
- Prefer always-present modifiers over conditional branches when the design expresses state changes on the same view rather than different views.
- Prefer relative layout over screen-size assumptions or hard-coded device math.
- Keep custom views context-agnostic unless the repo deliberately ships screen-specific components.
- Decide the screen shell only after filtered platform chrome has been excluded.

## Reusable structure rules

- Repeated rows, cards, or chips should become reusable subviews.
- One-off decorative wrappers should stay inline only if they have no reuse or state value.
- If a design block already resembles an existing shared component, reuse or extend it instead of cloning the look.
- Extract complex sections into separate subviews instead of large computed view builders when that improves diffing and keeps the root screen readable.
- Prefer small, named subviews over sprawling `@ViewBuilder` helpers once the view starts carrying multiple responsibilities.

## Conditional structure rule

- Use conditional branches only when the design truly introduces different views or optional sections.
- Use modifier-based state changes when the design is changing the same view's appearance or interaction state.
- Avoid conditional modifier helpers that silently change identity or layout ownership.

## Container and action rules

- Let reusable views own their static container structure instead of depending on every caller to recreate padding and alignment correctly.
- Keep heavy action logic out of inline button closures when the repo already routes actions through methods or owners.
- Preserve overlay/background hierarchy intentionally so the tappable and visual layers match the Figma anatomy.

## `design_spec` structure mapping

- Use `layout_tree` as the default source of container and parent-child structure.
- Use `anatomy.x_axis` to understand horizontal anchors, sibling gaps, and width behavior.
- Use `anatomy.y_axis` to understand vertical rhythm, stack cadence, and height behavior.
- Use `anatomy.z_axis` to understand overlays, layering, overlap, and draw-order-sensitive affordances.
- If screenshot intuition conflicts with `layout_tree` or `anatomy`, validate the extraction evidence before continuing.

## Layout audit checks

- repeated layout constants should resolve to shared tokens when equivalents exist
- view identity should remain stable across state changes
- expensive or deeply nested sections should be extracted when drift fixes keep touching the root screen
- overlay/background usage should preserve hierarchy and interaction intent from the design
- frequent geometry reads should have a reason and should not become a layout-thrash source
- custom full-width content should prefer direct frame/alignment intent over spacer-driven scaffolding when the layout is simpler that way

## Fidelity guardrails

- Keep spacing and padding traceable to Figma or repo tokens.
- Prefer stable existing tokens over raw values when they map cleanly.
- When a raw value is required because no token exists, keep it explicit and local to the new component.
- If exact parity conflicts with an existing shared component contract, document the deviation explicitly instead of silently weakening the design.
- If major visual regions visible in the screenshot are absent from `layout_tree`, prefer re-extraction over structural guesswork.
