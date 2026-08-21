# SwiftUI Lane Overview

This lane translates `design_spec` and related extracted evidence from `figma-mcp` into an existing SwiftUI codebase. It is not a generic “write SwiftUI however you like” guide, and it is intentionally architecture-neutral: preserve the target repo's proven patterns instead of imposing a new one.

Read `swiftui-design-spec-consumption.md` first.

## Core Rules

- Reuse the repo's existing SwiftUI composition pattern instead of inventing one.
- Translate design into the smallest existing SwiftUI seam that can hold it cleanly.
- Keep state, navigation, and presentation in the owners already established by the repo.
- Prefer native SwiftUI APIs over UIKit bridging unless the repo already bridges at that seam or the feature truly needs it.
- Use modern SwiftUI APIs when they fit the target deployment range and local codebase conventions.
- Map Figma tokens to the repo's existing spacing, color, typography, surface, and component primitives.
- If project conventions are unclear, build a project UI memory brief before proposing implementation details.

## Operating Modes

### Generation mode

Use when no implementation exists yet or a small isolated block can be introduced safely.

Focus on:

- matching the existing SwiftUI composition pattern
- mapping `design_spec` into reusable subviews and screen sections
- preserving ownership boundaries
- choosing modern APIs and availability gates deliberately
- mapping design tokens into the local design system

### Audit / repair mode

Use when a SwiftUI implementation already exists and must be compared against `design_spec`, screenshot evidence, and repo conventions.

Focus on:

- identifying drift in layout, tokens, state ownership, presentation ownership, modern API usage, accessibility, and reuse boundaries
- fixing the smallest seam that restores fidelity
- preserving existing feature composition unless there is evidence the seam itself is wrong

### Hybrid patch mode

Use when the target SwiftUI section lives inside a UIKit host or a mixed feature shell.

Focus on:

- preserving the host shell
- updating only the SwiftUI child seam
- respecting existing hosting and dismissal contracts
- respecting the repo's current bridge points and wrapper components

## Default Flow

1. Confirm the active feature seam and implementation mode.
2. Consume the relevant `design_spec` evidence before proposing structure or behavior.
3. Build or refresh a project UI memory brief if the repo patterns are not already known.
4. Find the feature composition root.
5. Confirm how the screen is hosted or presented.
6. Confirm where state is owned.
7. Confirm where navigation or presentation is owned.
8. Inspect shared design-system wrappers, modifiers, button styles, and token surfaces.
9. Map Figma sections into subviews and components that fit the current module.
10. Validate screenshot fidelity, interactive intent, accessibility, and update risks.

## What to inspect before proposing code

- `design_spec.layout_tree`
- `design_spec.anatomy`
- `design_spec.interactions`
- `design_spec.flow`
- `design_spec.business_assumptions`
- `design_spec.unresolved`
- feature composition root such as a factory, container, or registerer
- navigation or presentation owner when the repo separates those concerns
- view model, model store, or other observable owner
- root SwiftUI view such as `Screen.swift` or `View.swift`
- shared SwiftUI primitives and token wrappers
- shared modifiers, styles, surfaces, and accessibility helpers
- any current loading, error, empty, or skeleton-shell patterns
- any current list, scroll, focus, input, or sheet conventions
- any existing child subviews or shared components already used by nearby screens
- any hybrid bridge or hosting-controller layer when the feature is mixed UIKit/SwiftUI

## What this lane should produce

- a SwiftUI implementation plan that fits the repo's actual architecture
- a mapping from Figma structure to SwiftUI views and shared primitives
- a concrete state and presentation ownership model
- a design-system mapping plan
- modern API and availability decisions for the touched surface
- accessibility, motion, and performance checks that matter for the screen
- evidence sufficiency and re-extraction need when relevant
- a screenshot-based fidelity validation pass
- a drift classification when the task is audit/repair

## Topic Router

Load only the topic files needed for the task:

| Topic | Reference |
|---|---|
| Design-spec intake and evidence consumption | `swiftui-design-spec-consumption.md` |
| State ownership and data flow | `swiftui-state-and-data-flow.md` |
| View composition and layout translation | `swiftui-view-structure-and-layout.md` |
| Navigation, sheets, hosted routing | `swiftui-navigation-sheets-and-routing.md` |
| Lists, repeated content, and scrolling | `swiftui-scroll-list-and-identity.md` |
| Design-system mapping | `swiftui-design-system-and-token-mapping.md` |
| Modern API and availability decisions | `swiftui-modern-api-and-availability.md` |
| Accessibility and inclusive design | `swiftui-accessibility-and-inclusive-design.md` |
| Performance and update hygiene | `swiftui-performance-and-update-hygiene.md` |
| Motion and animation | `swiftui-animation-and-motion.md` |
| Existing implementation comparison | `swiftui-audit-and-repair.md` |
| Final parity checks | `swiftui-fidelity-validation.md` |

## Correctness Checklist

Treat these as bugs when violated:

- implementation continues even though the extracted design evidence is internally inconsistent
- screen-driving state is not split away into ad hoc local ownership
- passed values and injected owners are not re-owned locally without a clear reason
- repeated dynamic content does not use unstable identity or frozen snapshots
- navigation or presentation ownership is not duplicated across multiple layers
- primary tappable elements do not fall back to raw tap gestures without a semantic-control reason
- availability-sensitive APIs are not used without target awareness and fallback planning
- loading, error, empty, or skeleton states are not bypassed when the repo already has a screen-state shell
- accessibility and reduce-motion implications are not ignored on interaction-heavy UI

## Topic references

- `swiftui-design-spec-consumption.md`
- `swiftui-state-and-data-flow.md`
- `swiftui-view-structure-and-layout.md`
- `swiftui-navigation-sheets-and-routing.md`
- `swiftui-scroll-list-and-identity.md`
- `swiftui-design-system-and-token-mapping.md`
- `swiftui-modern-api-and-availability.md`
- `swiftui-accessibility-and-inclusive-design.md`
- `swiftui-performance-and-update-hygiene.md`
- `swiftui-animation-and-motion.md`
- `swiftui-audit-and-repair.md`
- `swiftui-fidelity-validation.md`
