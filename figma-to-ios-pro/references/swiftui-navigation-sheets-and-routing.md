# SwiftUI Navigation, Sheets, and Routing

Start from:

- `design_spec.interactions`
- `design_spec.flow.primary_path`
- `design_spec.flow.secondary_paths`
- `design_spec.flow.terminal_states`

## Ownership rules

- Keep navigation and presentation in the repo's existing owner.
- Keep hosting-controller or bridge ownership with the local owner when the repo uses hosted SwiftUI screens.
- Do not put cross-screen navigation logic inside the SwiftUI view body unless the repo already keeps it there.
- Keep dismissal behavior where the repo already keeps it; do not split dismissal responsibility across layers without evidence.

## Interaction-confidence rule

- `high` confidence interaction -> may drive control choice and ownership directly
- `medium` confidence interaction -> may shape the plan, but should remain an explicit assumption when behavior is not fully specified
- `low` confidence interaction -> should remain an ambiguity or a re-extraction trigger, not invented behavior

## Modern API rule

- For new work, prefer the repo's modern navigation API when the deployment range supports it.
- Do not mix old and new navigation models inside one feature unless the current subsystem already does so.
- Availability-sensitive presentation APIs need explicit gating and fallbacks.

## Sheet rules

- Match the repo's current sheet presentation style before introducing a new one.
- When the repo already uses routing helpers or presentation owners for modal presentation, route through them.
- Keep model-driven or enum-driven presentation where the repo already uses it.
- Prefer item-driven or single-source presentation state over scattered booleans when the local feature already uses a structured sheet model.
- Avoid callback-heavy sheet contracts when the existing feature expects the presented content to own its own local interactions and dismissal.

## Audit checks

- sheet state is not duplicated across multiple layers
- deep-link or parent-origin flows still dismiss or return correctly
- hosted screens still use the same navigation wrapper conventions as nearby features
- modal presentation style has not drifted away from the surrounding subsystem
- availability-sensitive APIs still have valid fallback paths

## Hybrid rule

- If the SwiftUI view lives inside a UIKit host, preserve the host's presentation and dismissal behavior.
- If a UIKit container expects a hosted child, do not change that embedding contract.
- If a router expects `hostedInNavigation()` or a configured hosting controller, preserve that path instead of presenting the raw view.
- If `flow` implies terminal states or multi-step paths the local host repo does not explain, keep them unresolved rather than inventing a route model.
