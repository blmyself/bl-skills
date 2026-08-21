---
name: project-ui-pattern-memory
description: Inspect a target iOS codebase and derive a task-local UI pattern memory brief for `figma-to-ios-ui`, covering composition, design system, shared primitives, state ownership, navigation or presentation ownership, and SwiftUI or hybrid seams. Use when the repo needs project-specific adaptation but you do not want to bake static overlays into the public skill.
---

# Project UI Pattern Memory

Use this companion when `figma-to-ios-ui` needs project-specific context for SwiftUI or hybrid adaptation.

## Purpose

Replace hard-coded per-project overlays with live codebase learning.

## Core rules

- Derive facts from repo files, not from product similarity or naming intuition.
- Learn only enough of the active subsystem to implement or review confidently.
- Preserve the repo's existing UI architecture and design system instead of imposing a new one.
- Build a concise memory brief that downstream `figma-to-ios-ui` work can consume directly.
- Refresh the brief when the active subsystem changes or when new evidence contradicts it.
- Prefer incremental refresh over full relearning.

## What to learn

Capture evidence for:

- feature composition roots and entrypoints
- state ownership patterns
- navigation and presentation ownership
- shared SwiftUI primitives, modifiers, surfaces, button styles, and wrappers
- design-system tokens for color, typography, spacing, and icons
- loading, error, empty, and skeleton-shell patterns
- list, scroll, focus, text-input, motion, and accessibility conventions
- SwiftUI and UIKit bridge seams for hybrid features
- feature-local anti-patterns or failure shields that should not be violated

## Workflow

1. Scope the active repo and the touched subsystem.
2. Read the feature entrypoints:
   - app shell
   - feature builders, containers, or registerers
   - root screens and hosting bridges
3. Inspect the state owner and nearby child views.
4. Inspect navigation and presentation ownership.
5. Inspect shared design-system and UI primitives.
6. Inspect nearby features that already solve a similar UI problem.
7. Record the findings in a project UI memory brief using the template.

## Incremental refresh rule

When a project UI memory brief already exists:

1. read the existing brief first
2. inspect only the touched seam and the minimum adjacent evidence needed
3. add or correct only the delta proved by the current task

Do not rescan the full codebase unless the current brief is clearly wrong or too shallow for the task.

## Token-efficiency modes

### Quick refresh

Use for:

- one component
- one screen section
- one clear convention check

Read only:

- touched files
- current brief
- one or two nearby examples if needed

### Standard refresh

Use for:

- one feature
- one hosted child flow
- one meaningful design-system adaptation

Read:

- current brief
- feature entrypoints
- touched files
- nearby shared primitives

### Deep refresh

Use only when:

- the subsystem is hybrid and unclear
- the current brief is contradicted by implementation evidence
- multiple adjacent conventions need to be relearned

## Output contract

Produce a compact project UI memory brief with:

- repo and subsystem identity
- composition and entrypoint summary
- state ownership summary
- navigation and presentation summary
- shared design-system tokens and wrappers
- reusable UI primitives and surfaces
- list and scroll conventions
- accessibility and motion conventions
- hybrid bridge rules
- anti-patterns to avoid
- open questions and confidence notes

When updating an existing brief, also produce a short learning delta with:

- confirmed rule
- corrected assumption
- new reusable primitive or wrapper
- failure shield

## Template

Use:

- `subskills/project-ui-pattern-memory/templates/project_ui_pattern_memory.template.md`
- `subskills/project-ui-pattern-memory/templates/project_ui_learning_delta.template.md`
