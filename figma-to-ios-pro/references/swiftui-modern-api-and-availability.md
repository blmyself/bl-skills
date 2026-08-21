# SwiftUI Modern API and Availability

Use this reference when choosing between older and newer SwiftUI APIs during implementation or review.

## Core rules

- Prefer modern SwiftUI APIs when they fit the target deployment range and the local codebase conventions.
- Do not force an API migration during a Figma-to-UI task when the surrounding subsystem is intentionally on an older pattern.
- Availability-sensitive APIs need explicit gating and a fallback path.

## Modern defaults

- Prefer the repo's current type-safe navigation model over legacy navigation surfaces when the subsystem already adopted it.
- Prefer model-driven or item-driven presentation over scattered boolean toggles when the local feature already uses that style.
- Prefer modern empty-state surfaces when the deployment target and repo conventions allow them.
- Prefer the repo's current observation model instead of mixing old and new ownership patterns in one feature.

## Availability discipline

- Check the supported deployment range before adopting newer APIs.
- Use `#available` gating when a newer API is the right fit but older OS support still matters.
- Keep the fallback path behaviorally equivalent where practical.
- Avoid mixing multiple generations of the same API family inside one feature unless the local subsystem already does so.

## Audit checks

- deprecated or legacy APIs are left in place only for a clear compatibility or subsystem reason
- newer APIs are not introduced without matching target support
- fallback paths are not missing when newer APIs are gated
- review findings distinguish API drift from layout or token drift
