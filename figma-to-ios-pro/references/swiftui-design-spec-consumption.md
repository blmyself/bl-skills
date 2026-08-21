# SwiftUI Design Spec Consumption

Read this file first when the selected lane is SwiftUI.

This reference defines how the SwiftUI lane should consume the `design_spec` artifact produced by `figma-mcp`. Do not start SwiftUI interpretation from screenshot intuition alone when structured extraction evidence already exists.

## Required `design_spec` fields

Read these before implementation reasoning:

- `node.file_key`
- `node.node_id`
- `node.node_name`
- `node.platform_chrome_filtered_nodes`
- `tokens.colors`
- `tokens.typography`
- `tokens.radii`
- `tokens.spacing`
- `tokens.shadows`
- `anatomy.x_axis`
- `anatomy.y_axis`
- `anatomy.z_axis`
- `layout_tree`
- `interactions`
- `flow.primary_path`
- `flow.secondary_paths`
- `flow.terminal_states`
- `business_assumptions`
- `unresolved`

If material fields are missing, treat the extraction as incomplete and avoid confident implementation guidance.

## How the fields map into SwiftUI decisions

### Structure

Use:

- `layout_tree`
- `anatomy.x_axis`
- `anatomy.y_axis`
- `anatomy.z_axis`

to decide:

- screen shell
- section boundaries
- repeated component families
- overlay and depth behavior
- scroll ownership

Do not derive shell or section structure from screenshot impression alone when `layout_tree` and `anatomy` are available.

### Interaction and navigation

Use:

- `interactions`
- `flow.primary_path`
- `flow.secondary_paths`
- `flow.terminal_states`

to classify:

- local visual interaction
- view-model intent
- navigation or presentation ownership
- hosted parent action

Confidence rule:

- high-confidence interaction may drive ownership directly
- medium-confidence interaction may shape the plan, but should remain an explicit assumption when behavior is not fully specified
- low-confidence interaction should remain an ambiguity or a re-extraction trigger, not invented behavior

### Business behavior uncertainty

Use:

- `business_assumptions`
- `unresolved`

to constrain:

- state ownership choices
- behavior interpretation
- open questions that must remain explicit

Do not invent business behavior when the extraction already marks the area as assumption-driven or unresolved.

### Platform chrome filtering

Use:

- `node.platform_chrome_filtered_nodes`

to avoid implementing non-app UI such as:

- status bars
- home indicators
- device mock chrome
- filtered framing layers

If a candidate shell depends on filtered nodes, re-evaluate the shell choice before implementation.

## Evidence precedence

When evidence conflicts, use the same priority as `figma-mcp`:

1. token identity from variable definitions
2. layout and styling intent from design context
3. screenshot as visual confirmation

Rules:

- use token truth over screenshot color guesswork
- use structured layout and anatomy over screenshot-derived numeric inference
- use screenshot to confirm interpretation, not to override cleaner structured evidence without cause

## Re-extract instead of guess

Re-extract when:

- a visible section is absent from `layout_tree` or contradicts screenshot grouping
- node IDs or structure do not match expected anatomy
- token values and intended styling conflict materially
- too many unresolved critical fields remain
- action intent is too ambiguous to assign ownership safely
- required fields for structure, interaction, or uncertainty handling are materially incomplete

You may continue with bounded assumptions only when:

- structure remains trustworthy
- unresolved critical fields are few
- interaction ambiguity does not materially change ownership or flow architecture

Otherwise, prefer re-extraction over implementation.

## Required implementation note

Every SwiftUI implementation brief should identify:

- target node or frame identity used
- structure source from `design_spec`
- token source from `design_spec`
- interaction source from `design_spec`
- unresolved assumptions source from `design_spec`
- whether the evidence was sufficient or whether re-extraction is required
