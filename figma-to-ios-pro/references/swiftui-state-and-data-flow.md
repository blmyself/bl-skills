# SwiftUI State and Data Flow

Use this file when translating Figma structure into SwiftUI state and data ownership.

## Core rules

- Keep screen-driving state in the repo's existing owner.
- Use local state only for local visual or ephemeral interaction state.
- Do not push business logic down into view bodies.
- Keep async work and side effects where the repo already expects them.
- Reuse existing shared managers, stores, services, and shells instead of duplicating state from design.
- Use `design_spec.business_assumptions` and `design_spec.unresolved` before inventing missing behavior or ownership.

## Owner selection guide

- Use `@State` for local, view-owned value state.
- Use `@Binding` only when a child must write back to parent-owned state.
- Use the repo's current reference-type ownership pattern for view-owned objects.
- If the repo already uses `@Observable` and `@Bindable`, follow that pattern consistently instead of partially migrating one surface.
- Keep `@FocusState` local to the view that actually owns focus behavior.

## Ownership checklist

- Use private local state only for local visual interaction state.
- Keep domain or screen-driving state in the feature's existing owner.
- Use injected read-only values as passed values, not as re-owned local state.
- Use bindings only when the child must write back to its parent-owned state.

## State ownership checklist

- If the repo already has a canonical feature owner type, extend it instead of introducing a second owner.
- If the screen is driven by a standardized state shell, preserve its loading, error, empty, and success flow instead of bypassing it.
- If the design introduces repeated or dynamic blocks, map them to data-driven collections instead of hardcoded snapshots.
- If the repo already uses observable objects or macros in a stable way, follow that local pattern first instead of importing a new one.

## Passed value rules

- Do not turn passed values into locally owned state unless the screen truly needs to fork them.
- Keep read-only inputs as plain passed values.
- If the view reacts to an external value changing, prefer observing that value over re-owning it.

## Dynamic content rules

- Repeated Figma sections should map to model-driven collections.
- Derived view state should usually be computed from source data, not stored separately.
- If the design suggests conditional sections, confirm whether the existing feature already models those conditions upstream.

## Common drift to catch in audit mode

- a view now owns state that used to be injected
- presentation booleans replace a stronger local ownership model
- dynamic sections are rendered as static snapshots
- loading and error states disappear into optional branches
- business decisions move into the SwiftUI view body because the design looked simple

## Translation guardrails

- Do not turn passed-in values into locally owned state unless the repo pattern already does that.
- Do not invent a new architecture pattern just because the design is clean.
- Do not infer business behavior from visuals alone; record assumptions when the design cannot decide behavior.
- Do not replace an existing shared manager or service with view-local duplicates just because the design introduces a new visual grouping.
- If business intent is missing from `design_spec`, keep it unresolved unless the host repo pattern narrows it safely.
