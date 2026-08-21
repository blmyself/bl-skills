# SwiftUI Design System and Token Mapping

Use this reference when mapping Figma colors, typography, spacing, surfaces, and component anatomy into an existing SwiftUI codebase.

## Core rule

Prefer the repo's semantic design-system primitives over raw values whenever they map cleanly to the design.

## Discovery checklist

Inspect the active subsystem for:

- color and surface tokens
- typography helpers or custom font wrappers
- spacing and size tokens
- shared button styles, card surfaces, chips, rows, and modifiers
- icon wrappers or asset-loading helpers
- existing nearby screens that solve a visually similar problem

## Mapping priorities

1. Existing semantic tokens and shared primitives already used by nearby screens
2. Existing design-system wrappers that match the design intent
3. Local explicit raw values only when no clean token exists and token creation is out of scope

## Rules

- Do not choose a token by name similarity alone when multiple candidates are plausible.
- Prefer the semantic family already used by sibling controls if the design intent matches.
- Reuse shared components before cloning their appearance into a new local view.
- Keep raw fallback values explicit and local to the component when a token is missing.
- Record deliberate deviations when an existing design-system contract prevents exact Figma parity.

## Audit checks

- color, typography, spacing, and surface choices still match the repo's semantic families
- a shared component was not bypassed just because local custom code was faster to write
- raw values remain isolated to the smallest possible seam
- any deviation from exact parity is documented and justified
