# SwiftUI Animation and Motion

Use this reference when the Figma design includes transitions, state-driven motion, or animated emphasis.

## Core rules

- Animate meaningfully; do not add motion just because the design is modern.
- Match the repo's existing motion language before inventing a new one.
- Respect Reduce Motion when animation is strong enough to affect comprehension or comfort.

## Choosing motion

- Use state-driven animation when the same view changes appearance.
- Use transitions when views are entering or leaving the hierarchy.
- Keep shared or repeated animations consistent across sibling elements.
- Prefer the smallest motion that communicates the state change clearly.

## Guardrails

- Avoid animations that hide ownership or state bugs.
- Do not let animation choices break stable identity in repeated content.
- Keep cross-screen or cross-host transitions aligned with the surrounding subsystem.
- Use advanced animation APIs only when the deployment range and local codebase already support them cleanly.

## Audit checks

- motion communicates a real state change
- transition choice matches insertion/removal behavior
- Reduce Motion expectations still hold
- animation code does not become the place where layout or state bugs are masked
