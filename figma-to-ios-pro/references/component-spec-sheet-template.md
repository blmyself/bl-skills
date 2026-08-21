# Component Spec Sheet Template

Use this file before patching a shared UIKit/XIB component.

## Component

- Name:
- Reused by screens:
- Primary revamp screen:
- Figma node IDs:

## Scope Freeze

- Must not change:
- Screen-specific behavior that stays screen-specific:
- Out of scope:

## Visual Spec Table

| Object | Figma node | Exact value | Implementation owner | Token/source | Mode/screen notes |
|---|---|---|---|---|---|
| Card radius |  |  | XIB or Swift |  |  |
| Card shadow |  |  | Swift |  |  |
| Card border |  |  | Swift |  |  |
| Horizontal padding |  |  | XIB |  |  |
| Vertical padding |  |  | XIB |  |  |
| Inter-item gap |  |  | XIB |  |  |
| Title typography |  |  | Swift |  |  |
| Body typography |  |  | Swift |  |  |
| Badge fill/text |  |  | Swift |  |  |
| Radio/icon size |  |  | XIB or Swift |  |  |
| Edit affordance |  |  | XIB or Swift |  |  |

## Ownership Split

### XIB-owned

- Structure:
- Constraint constants:
- Stack spacing:

### Swift-owned

- Shadow:
- Border color/state:
- Attributed text:
- Runtime colors:
- Mode switching:

## Reuse Risks

- Shared anatomy that must remain shared:
- Layout mutations that must be reversible:
- Modes/screens to retest:

## Validation Matrix

| Scenario | Expected result |
|---|---|
| Primary screen selected |  |
| Primary screen unselected |  |
| Secondary screen mode |  |
| Long multiline content |  |
| RTL |  |
| Rebind/reuse |  |
