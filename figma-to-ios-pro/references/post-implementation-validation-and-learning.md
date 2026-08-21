# Post-Implementation Validation and Learning

Use this reference after implementing or repairing a Figma-driven UI surface.

## Core rule

Do not stop at "the code looks right." Validate the implemented UI against the design evidence and feed only proven deltas back into the project UI memory.

## Evidence priority

Validate in this order:

1. `design_spec`
2. screenshot evidence
3. touched implementation files
4. project UI memory brief
5. nearby repo examples only if a mismatch remains unresolved

Do not restart from the full Figma payload or full codebase unless the smaller evidence set fails.

## Validation modes

Choose the smallest mode that can prove correctness.

### 1. Quick mode

Use for:

- one component
- one reusable row or card
- one clearly isolated patch

Inputs:

- affected `design_spec` section
- screenshot for the same section
- touched files only
- existing project UI memory brief if available

### 2. Standard mode

Use for:

- one screen or one hosted child feature
- a meaningful visual revamp with several subviews
- an audit/repair pass with multiple findings

Inputs:

- screen-level `design_spec`
- screenshot
- touched files
- active project UI memory brief
- one or two nearby repo examples if needed

### 3. Deep mode

Use only when:

- the feature is hybrid UIKit/SwiftUI
- runtime behavior contradicts the design theory
- repeated mismatches survive a quick or standard pass

Inputs:

- all standard-mode inputs
- hosting or bridge seam
- owner files for state, navigation, or presentation
- targeted nearby subsystem examples

## Validation checklist

Confirm:

- layout hierarchy still matches the design anatomy
- spacing, typography, surfaces, and tokens match the intended semantics
- dynamic regions are dynamic, not frozen snapshots
- tappable regions map to explicit actions and destinations
- accessibility and motion posture still make sense
- project-convention seams are preserved
- any deliberate deviation is recorded explicitly

## Learning loop

After validation, learn only what was proven.

Capture deltas such as:

- a confirmed shared primitive or modifier family
- a confirmed state or presentation ownership rule
- a confirmed design-system mapping pattern
- a failure shield discovered during validation
- a rejected assumption that should not be repeated

Do not restate the full repo pattern memory after each task.

## Token-efficiency rules

- Start from touched files, not the full feature tree.
- Reuse the existing project UI memory brief instead of rebuilding it.
- Refresh only the section that the task disproved or extended.
- Escalate from quick to standard to deep only when unresolved mismatches remain.
- Record a short learning delta instead of a full narrative when the repo rule was only slightly clarified.

## Required artifacts

Produce at least one of:

- a filled validation brief
- a short learning delta appended to the project UI memory brief

Use:

- `templates/ui_validation_brief.template.md`

If no new learning emerged, say that explicitly and keep the project UI memory unchanged.
