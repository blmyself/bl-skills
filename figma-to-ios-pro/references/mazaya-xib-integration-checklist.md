# Mazaya XIB Integration Checklist

Use this reference when changing or extracting UIKit/XIB sections inside Mazaya.

## When Adding A New XIB-Backed Child VC

Verify all of these:

1. new `.xib` added to `project.pbxproj` resources
2. new Swift files added to `project.pbxproj` sources
3. DI registration added when resolved through `Resolver`
4. parent VC has a host container outlet
5. parent VC embeds the child deterministically
6. presenter/business contract remains unchanged unless the task explicitly changes behavior

## When Refactoring A Fragile Section Out Of A Parent XIB

Prefer extraction when:

- repeated small patches are not stabilizing runtime layout
- the section has its own layout/state complexity
- isolating the view is safer than continuing to mutate the parent XIB

Keep the extraction narrow:

- move only the section UI
- keep existing presenter/use-case ownership
- forward interactions back to the existing parent/presenter flow

## Mazaya Checkout/Shipping Guardrails

Protect:

- presenter ownership of business state
- method/address/pickup payload mapping
- proceed-button gating
- guest vs logged-in branching
- payment-step assumptions

Treat the child VC as a display/interactions host unless the repo already uses a different proven pattern.
