# SwiftUI Audit and Repair

Use this reference when a SwiftUI implementation already exists and must be compared against `design_spec`, screenshot evidence, and project conventions.

Require the same `design_spec` fields as the implementation lane:

- `layout_tree`
- `anatomy`
- `interactions`
- `flow`
- `business_assumptions`
- `unresolved`

## Review modes

### Visual drift review

Use when the implementation renders, but does not match the design.

Check:

- spacing rhythm
- hierarchy and section grouping
- typography and color token mapping
- missing or extra visual regions
- state-specific visual drift

### Structural drift review

Use when the implementation technically works but the seam no longer matches repo conventions.

Check:

- state ownership moved into the wrong layer
- navigation moved from router into the view body
- reusable blocks became ad hoc copies
- a hosted child was turned into a root rewrite

### Behavioral drift review

Use when taps, sheets, or dynamic content no longer behave like the design or local subsystem.

Check:

- tappable regions map to explicit actions
- sheet and push flows still match the local navigation and presentation contract
- repeated content is data-driven
- loading, error, and empty states still exist where expected

### API and design-system drift review

Use when the screen renders acceptably but implementation choices are now stale or out of family.

Check:

- newer APIs should replace older ones only when the target range and repo conventions allow it
- token mapping still matches the repo's semantic palette, typography, and spacing wrappers
- shared modifiers, button styles, surfaces, and accessibility wrappers are still being reused where appropriate

## Drift classification

Classify findings as one or more of:

- `Extraction evidence mismatch`
- `Layout`
- `Token`
- `State ownership`
- `Presentation ownership`
- `API / Availability`
- `Accessibility`
- `Performance`
- `Reuse`
- `Behavior`

## Repair sequence

1. confirm the selected SwiftUI lane and project UI memory brief are correct
2. compare current implementation structure against `design_spec`
3. compare visible output against screenshot evidence
4. compare design-system mapping and modern API choices against local conventions
5. identify the smallest seam that can restore fidelity
6. preserve repo conventions while patching that seam
7. record any deliberate deviations that remain
8. if extraction evidence itself is inconsistent, stop and request re-extraction rather than classifying it as ordinary implementation drift

## Repair guardrails

- do not rewrite a whole SwiftUI feature when the drift is localized to one child section
- do not convert a hybrid host into a pure SwiftUI flow during a fidelity fix
- do not replace owner-driven presentation with ad hoc local presentation state
- do not treat a token mismatch as a layout rewrite problem until token mapping is verified
- do not assume a repo-specific overlay exists; learn the repo from code if the current pattern is unclear
- do not patch around extraction evidence mismatch as if it were ordinary layout or behavior drift
