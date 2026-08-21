# SwiftUI Fidelity Validation

## Always validate against these sources

1. `design_spec`
2. extracted tokens
3. screenshot
4. current project conventions
5. the project UI memory brief when one was built

## Validation checklist

### Evidence integrity

- `layout_tree` still accounts for the major visible screen regions
- extracted structure does not materially conflict with screenshot grouping
- token identity does not materially conflict with intended styling
- unresolved critical interaction intent is low enough to support the ownership model

If evidence integrity fails, recommend re-extraction before implementation rather than continuing with guessed interpretation.

- layout hierarchy matches the intended screen anatomy
- spacing rhythm matches Figma or mapped tokens
- typography matches family, size, weight, and line-height intent
- colors and surfaces map to the repo's shared palette correctly
- dynamic regions are implemented as dynamic regions, not frozen snapshots
- tappable areas map to explicit actions and routing destinations
- hosted screens still fit existing ownership and shell behavior
- accessibility semantics, Dynamic Type behavior, and touch targets still make sense
- motion and transition choices do not fight Reduce Motion expectations
- availability-sensitive APIs are gated or aligned with the supported deployment range
- update-heavy regions do not introduce obvious performance footguns in hot paths

## Incremental validation strategy

Use the smallest scope that can prove the feature is correct:

- quick mode for one component or one local patch
- standard mode for one screen or hosted child
- deep mode only when hybrid seams or repeated mismatches require it

Start from:

1. the touched `design_spec` section
2. the screenshot
3. the touched files
4. the project UI memory brief

Only widen the search when a mismatch remains unresolved.

## Learning delta

After validation, capture only the proven delta:

- a confirmed local design-system rule
- a confirmed ownership rule
- a reusable primitive that should be preferred next time
- a failure shield discovered during review

Do not rewrite the whole project UI memory brief unless the current task actually invalidated it.

## Required implementation note

When fidelity cannot be achieved exactly because of an existing project token or component contract, call out the deliberate deviation instead of hiding it.

Also call out unresolved assumptions when:

- design does not fully specify behavior
- runtime data combinations could change the chosen component structure
- host-shell ownership had to be inferred from nearby code rather than explicit documentation
- extraction evidence was incomplete but implementation still proceeded with bounded assumptions
