# SwiftUI Scroll, List, and Identity

## Repeated content

- Translate repeated Figma blocks into stable `ForEach` structures.
- Use stable identity from the underlying model; do not use positional identity for dynamic content.
- Keep the number of rendered child views per item structurally stable.
- Avoid inline filtering or reshaping inside the render loop when the same result can be prepared earlier in the view model or derived data layer.
- Avoid `AnyView` or ad hoc type erasure in hot row paths unless a real abstraction boundary requires it.

## Scroll translation

- Prefer the repo's shared scroll wrapper when one exists.
- Keep scroll ownership with the outermost screen or container that already manages it.
- Do not nest competing scroll systems unless the existing repo already does so.
- Use programmatic scrolling only when the feature behavior requires it and the subsystem already supports it.
- Use stable IDs and explicit animation when programmatic scrolling is part of the feature behavior.

## Performance guardrails

- Use extracted subviews for complex repeated rows.
- Keep expensive formatting or derived computations out of the hot row body when possible.
- Preserve lazy containers when the repo already uses them for long or variable lists.
- Keep scroll-effect state updates bounded so they do not thrash view updates.

## Audit checks

- repeated content uses stable IDs
- list rows have not lost dynamic content because of identity drift
- shared scroll wrappers are still used where expected
- nested scroll or lazy containers still match the original interaction model from the design
- inline filtering, sorting, or expensive transformations have not migrated into the render loop
