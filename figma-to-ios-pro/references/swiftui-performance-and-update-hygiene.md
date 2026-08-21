# SwiftUI Performance and Update Hygiene

Use this reference when the design introduces repeated content, scroll effects, derived formatting, or visually rich compositions that could amplify update churn.

## Core rule

Keep view updates intentional and local. Figma fidelity should not introduce avoidable rendering churn.

## State and dependency rules

- Avoid redundant state writes when the new value is unchanged.
- Pass only the data each view actually needs.
- Keep heavy derived work out of `body`.
- Do not create new objects in `body`.
- Keep fast-changing values out of broad shared dependency surfaces unless the subsystem already requires that shape.

## Collection and scroll rules

- Use stable identities for repeated content.
- Preserve lazy containers when the local feature already uses them for long or variable lists.
- Move expensive filtering, sorting, and formatting upstream where practical.
- Keep scroll-driven visual effects bounded so they do not trigger unnecessary full-screen updates.

## Optional optimizations

Consider these when the screen is already hot or clearly performance-sensitive:

- extracting expensive rows into focused subviews
- `Equatable` or finer-grained dependencies for truly expensive views
- update-debug helpers when unexpected re-rendering is suspected

## Audit checks

- no heavy computation or object creation moved into `body`
- repeated content remains stable and cheap to update
- new visual effects do not create obvious update thrash
- performance findings are presented as real risks, not generic micro-optimization advice
