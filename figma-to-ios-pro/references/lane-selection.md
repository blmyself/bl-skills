# Lane Selection

Use this file first after `figma-mcp`.

## UIKit/XIB lane

Choose `ios-uikit-xib-lane.md` when the touched feature already uses:

- `BaseVC`
- `BasePresenter`
- `.xib`
- `IBOutlet` / `IBAction`
- child `UIViewController` embedding
- runtime XIB diagnosis or `ibtool` checks

Typical signals:

- the screen class ends in `VC`
- the behavior lives in a presenter
- the view is composed with stack views and nib-backed components

## SwiftUI lane

Choose the SwiftUI references when the touched feature already uses:

- a root SwiftUI view such as `Screen.swift` or `View.swift`
- a feature state owner or other observable owner
- a navigation or presentation owner when the repo separates those concerns
- a feature composition root such as a factory, builder, container, or registerer
- a shared screen-state shell or hosted SwiftUI bridge when the repo already has one
- shared SwiftUI design-system primitives, wrappers, or modifiers

Typical signals:

- the screen is resolved from a composition root rather than loaded from a nib
- navigation or presentation ownership is separated from the view body
- the screen is hosted or presented through the repo's existing SwiftUI integration path
- the touched implementation files are a root SwiftUI view, state owner, navigation owner, or feature composition root

Within the SwiftUI lane, classify the task before proposing work:

- generation: no implementation exists yet or a small isolated block is being created
- audit/repair: an implementation exists and must be compared against `design_spec` and screenshot evidence
- hybrid patch: the target sits inside a mixed UIKit/SwiftUI host and only the matching child seam should be changed

## Hybrid rule

When the host screen mixes UIKit and SwiftUI:

- keep the host shell unchanged
- implement only the child seam that already matches the target area
- keep navigation, presentation, and state ownership in the existing layer
- if both UIKit and SwiftUI entrypoints exist in the same feature, choose the lane from the actual touched entrypoint and current resolver path, not from the feature name alone

Do not convert a UIKit root into SwiftUI or a SwiftUI root into UIKit unless the task explicitly requires migration.

## Project-pattern discovery rule

If the selected lane is SwiftUI and the repo's UI patterns are not already obvious:

1. load the general SwiftUI references first
2. run `subskills/project-ui-pattern-memory/SKILL.md`
3. build or refresh a project UI memory brief from the live codebase
4. use that brief as the project-specific adaptation layer

Do not ship hard-coded per-project SwiftUI overlays inside this public skill.
