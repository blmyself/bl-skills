# iOS UIKit + XIB Lane

## Dependency Rule

Load `figma-mcp` before this lane reference.

- Use `figma-mcp` to run tool calls and extraction order.
- Use this lane to translate extracted data into UIKit/XIB artifacts.
- Do not generate XIB/Swift until extraction is complete.
- If `figma-mcp` is not loaded yet, load it first.

## Core Implementation Rule

Generate only traceable values.

- Map every UI value to MCP output or token catalog.
- Avoid hardcoded design values when tokenized equivalents exist.
- Stop and re-fetch MCP data when a critical value is missing.

## Input Contract From `figma-mcp`

Require these artifacts before generation:

1. Node hierarchy and IDs from `get_metadata`
2. Token map from `get_variable_defs`
3. Layout/style intent from `get_design_context`
4. Screenshot reference from `get_screenshot`
5. Optional component-map info when available

If any artifact is missing, request a re-run instead of guessing.

## References

Read these only when the situation requires them:

- `references/shared-uikit-component-hardening.md`
  - Read when touching a reused UIKit/XIB component such as a row, card, cell, or section that appears across multiple screens or modes.
- `references/xib-runtime-failure-shields.md`
  - Read when `ibtool` passes but runtime layout is still wrong, when labels disappear, or when a screen renders differently from expected design hierarchy.
- `references/stackview-autolayout-pitfalls.md`
  - Read when debugging `UIStackView` rows, multiline labels, fixed-size icons, hugging/compression conflicts, or arranged-subview collapse.
- `references/mazaya-xib-integration-checklist.md`
  - Read when the target repo is Mazaya and you add or extract XIB-backed subviews, child VCs, DI registrations, or `project.pbxproj` entries.
- `references/asset-verification-rules.md`
  - Read when mapping Figma icons/images to repo assets or when MCP screenshots/assets are unavailable or ambiguous.

## Operating Modes

Choose the mode explicitly before editing files:

1. **Generation mode**
- Use when there is no implementation yet or when replacing a small isolated block from scratch.
- Focus on faithful Figma-to-UIKit/XIB translation.

2. **Audit / patch-assist mode**
- Use when an implementation already exists and needs comparison against Figma or targeted fixes.
- Run the implementation reality pass before proposing edits.

3. **Runtime diagnosis mode**
- Use when `ibtool` passes but the app still renders incorrectly at runtime.
- Focus on Auto Layout ownership, stack-view alignment, resource wiring, and runtime/view-hierarchy evidence before changing text rendering or view-model code.

4. **Extraction / section-refactor mode**
- Use when a local patch keeps failing because the parent XIB has become structurally fragile.
- Extract the section into a dedicated child VC/XIB while preserving presenter/business contracts.

## Runtime Diagnosis Trigger Rules

Switch to runtime diagnosis mode immediately when any of these happen:

- `ibtool` passes but labels, icons, or containers are invisible or clipped at runtime
- text exists in state/accessibility but not on screen
- repeated fixes start targeting `preferredMaxLayoutWidth`, `baselineOffset`, or manual relayout loops without clear evidence
- the bug appears only after a section was extracted into a child XIB/VC

Default runtime diagnosis order:

1. verify the text/data actually exists
2. inspect view hierarchy / stack ownership
3. inspect XIB resource integrity
4. inspect runtime wiring (`project.pbxproj`, DI, hosting, child embedding)
5. only then change text rendering code

## Tailwind-to-UIKit Translation Reference

`get_design_context` returns React+Tailwind. Use this table to extract UIKit values:

| Tailwind class | UIKit equivalent |
|---|---|
| `flex flex-col` | `UIStackView(axis: .vertical)` |
| `flex` (default row) | `UIStackView(axis: .horizontal)` |
| `gap-[16px]` | `stackView.spacing = 16` |
| `px-[20px]` | `layoutMargins.left/right = 20` or leading/trailing constraints |
| `pt-[16px]`, `pb-[20px]` | `layoutMargins.top = 16`, `.bottom = 20` or top/bottom constraints |
| `rounded-[6px]` | `layer.cornerRadius = 6` (UDRA in XIB) |
| `text-[16.5px]` | Font size 16.5pt |
| `leading-[24px]` | Line height 24pt (NSAttributedString in Swift) |
| `text-[#6f6f6f]` | `UIColor` from hex #6F6F6F or named color |
| `text-black` | `UIColor.black` or named "Primary" |
| `font-['IBMPlexSans:SemiBold']` | `UIFont(name: "IBMPlexSans-SemiBold", size:)` |
| `font-['IBMPlexSans:Regular']` | `UIFont(name: "IBMPlexSans-Regular", size:)` |
| `shadow-[0px_0px_32px_0px_rgba(0,0,0,0.04)]` | `layer.shadow*` in Swift (see Shadow section) |
| `bg-white` | `backgroundColor = .white` |
| `overflow-clip` | `clipsToBounds = true` |
| `flex-[1_0_0]` | Content hugging low / fill distribution |
| `shrink-0` | Content compression resistance high |
| `w-full` | Width = superview width (leading + trailing) |
| `items-center` | `stackView.alignment = .center` |
| `items-start` | `stackView.alignment = .leading` |
| `justify-between` | `stackView.distribution = .equalSpacing` |
| `justify-center` | `stackView.distribution = .equalCentering` |

## Project Profile Setup

Resolve these project constants first:

- `MODULE_NAME` (for XIB `customModule`)
- `MIN_IOS_VERSION`
- `TARGET_DEVICE_WIDTH` used for initial frame assumptions
- `COLOR_ASSET_CATALOG_PATH`
- `TOKEN_FILE_PATHS` for `UIColor`/`UIFont`/`CGFloat` tokens

### Mazaya defaults (when applicable)

- `MODULE_NAME = Mazaya`
- Use named colors from `Colors.xcassets`
- Prefer MVP boundaries: keep business logic out of views
- Avoid Swift Concurrency patterns when project policy forbids it

## Translation Pipeline

Follow this strict order:

1. Build normalized iOS design model
2. Generate token layer files
3. Generate leaf reusable components
4. Generate composite components
5. Generate screen XIB + controller Swift
6. Apply Swift-only visual properties
7. Validate against screenshot and run XIB checks

## Implementation Reality Pass (Analysis + Patch-Assist)

When an implementation already exists (`.xib` + `.swift`, optional presenter), run this pass before proposing edits:

1. Build implementation snapshot with:
   - `scripts/extract_uikit_impl_snapshot.py`
2. Compare extracted design spec vs implementation snapshot with:
   - `scripts/figma_uikit_audit.py`
3. Classify every finding as:
   - `critical`
   - `major`
   - `minor`
4. Emit patch hints only:
   - XIB constraints/styling suggestions
   - Swift runtime styling/wiring suggestions
5. Optionally mine donor XIB patterns from repo (`--repo-root` + `--donor-out`) to reduce invention.

Guardrails:
- Do not auto-edit project implementation files from audit scripts.
- Do not bypass existing presenter/use-case wiring; patch hints must respect current architecture.
- Keep recommendations deterministic and evidence-backed.

### Review Finding Classification

When producing findings from audit or patch-assist mode, classify each finding explicitly as one of:

- `XIB`
- `Swift runtime`
- `Token`
- `Reuse`
- `Behavior`

Use the type in the finding explanation, not only the severity.

Interpretation rules:

- `XIB`: structure, constraints, stack spacing, fixed view sizing, resource declarations
- `Swift runtime`: shadows, border colors, attributed text, runtime layout switching, state styling
- `Token`: named color/font/token mismatch vs Figma or resolved project values
- `Reuse`: shared-component boundary issues, cross-screen regressions, irreversible mode mutations
- `Behavior`: tap-target mapping, selection ownership, navigation/action contract drift

For reused components, prefer a comparison table with:
- current implementation
- target design
- reused-screen behavior
- finding type
- severity

This reduces false fixes where the visual mismatch lives in one layer but the patch is applied to another.

If audit mode reaches a point where runtime evidence contradicts the initial design-translation theory, escalate to runtime diagnosis mode instead of iterating on typography or spacing guesses.

## Runtime Diagnosis Branch

When runtime diagnosis is active:

1. Confirm whether the bug is:
- data/state missing
- runtime wiring missing
- layout collapse
- resource mismatch

2. Treat this signal as layout-first, not text-first:
- text is present in labels or accessibility
- the visible frame is zero or clipped

3. For rows shaped like `fixed-size radio/icon + multiline text stack`, inspect:
- inner horizontal `UIStackView.alignment`
- fixed height constraints on non-text siblings
- multiline labels with low compression resistance
- hidden arranged subviews affecting stack height

4. Do **not** start with:
- `preferredMaxLayoutWidth`
- `baselineOffset`
- custom relayout loops
- attributed-text measurement tweaks

5. Read:
- `references/xib-runtime-failure-shields.md`
- `references/stackview-autolayout-pitfalls.md`

## Reusable Row Interpretation Heuristics

Use this section when the target is a repeated UIKit/XIB row such as:

- payment method rows
- shipping method rows
- settings rows with optional trailing metadata
- icon + text + trailing disclosure layouts

### 1. Build an object-role map before proposing patches

Classify each visible object into one of these roles:

- selection affordance
- identity affordance
- semantic text block
- disclosure/accessory metadata
- separator/rhythm object

Do not start from outlet names alone. Start from the design anatomy.

### 2. Identify row variants explicitly

For repeated rows, enumerate the real runtime/design variants:

- title only
- title + one-line subtitle
- title + multiline subtitle
- title + trailing logos/accessory
- title + subtitle + trailing logos/accessory
- selected vs unselected
- disabled/loading
- RTL

If the proposed XIB can only satisfy one or two of these, the design model is incomplete.

### 3. Do not reserve proportional width for optional trailing metadata by default

If a row contains optional trailing logos or accessory content:

- treat that area as a sibling lane
- make it intrinsic/hugging by default
- measure whether it should align to:
  - top of text block
  - vertical center of row
  - title baseline

Do not assume a width multiplier container is correct unless the design explicitly behaves like one.

### 4. Fixed-shell vs content-driven decision

Before changing constraints, decide which of these the existing component is trying to be:

- fixed-shell row:
  - uniform density
  - stable separator rhythm
  - predictable host list height
- content-driven row:
  - row height follows content
  - variants can grow freely

If the shipped component is clearly fixed-shell, avoid converting it fully to content-driven layout unless the design mismatch requires it. Prefer targeted fixes inside the unstable lane first.

### 5. Text block rule for fixed-size icon/chip rows

If the row is `fixed-size icon/chip + text`:

- let the text stack own semantic height
- inspect the horizontal stack alignment first when multiline text collapses
- do not reach first for:
  - `preferredMaxLayoutWidth`
  - manual relayout loops
  - arbitrary line-height compression

This is especially important for checkout rows where one provider may suddenly ship much longer helper copy than others.

### 6. Audit scripts are necessary but not sufficient

Snapshot/audit scripts can validate:

- token family usage
- outlet/runtime assignment coverage
- some deterministic mismatches

They do not fully prove:

- real row geometry correctness
- runtime width negotiation
- sibling-lane centering intent
- screenshot parity under data-driven combinations

When audit says “aligned” but screenshots still look wrong, trust the geometry evidence and continue analysis.

### 7. Accessibility rule for selectable rows

When the radio is only the visible state indicator and the whole row is the real tap target:

- prefer one coherent accessibility element for the row
- avoid exposing fragmented sub-elements unless the design truly has multiple actions
- keep selected/not-selected state readable without requiring the user to inspect a separate visual-only control

### 8. Senior-first-pass checklist for row components

Before finalizing the first patch, answer all of these:

1. What is the primary lane and what is the secondary lane?
2. Which row variant is structurally hardest?
3. Is the current component fixed-shell or content-driven?
4. Which design state changes are localized vs global?
5. Which mismatches are caused by layout vs resolver/business data?
6. What is the smallest change that fixes the unstable lane without rewriting the component family?

## Section Extraction Escalation

Escalate from local patching to section extraction when:

- a parent XIB section resists multiple targeted fixes
- the section has its own layout/state complexity
- the safest path is to isolate view concerns without changing presenter/business ownership

Extraction rules:

- keep business logic in the existing presenter unless there is a proven contract reason to move it
- extract only the fragile UI section, not adjacent checkout flow logic
- add a host container in the parent XIB/VC
- wire a child VC/XIB under `Subviews/` or repo-equivalent structure
- preserve or adapt DI / `project.pbxproj` / resource registration as required by the repo
- keep the child VC as a thin display/interactions host unless the repo clearly prefers otherwise

## First-Pass Staff-Level Quality Gates

Apply these gates before writing final XIB/Swift output:

1. **Interaction contract gate**
- Build a table for all tappable candidates from Figma extraction:
  - `nodeId`
  - intended action
  - UIKit control (`UIButton`, gesture, accessory tap area, etc.)
  - expected handler name (`@IBAction` or callback)
  - destination flow (screen/modal/bottom-sheet/external URL)
- Do not leave an interactive Figma element without a mapped implementation action.

2. **User-flow gate**
- Describe the expected user journey for this component/screen:
  - entry point
  - primary success path
  - alternate paths
  - interruption/error paths implied by context
- Ensure the generated implementation can support this flow, not just the visual layout.

3. **Business-logic reconciliation gate**
- Inspect nearby presenter/use-case/view-model/repository code before finalizing UI wiring.
- Identify places where design is display-only but behavior is data-driven (lists, counts, dynamic labels, conditional visibility, permissions).
- Emit an explicit assumptions list for logic not inferable from design alone.
- Prefer existing business contracts over inventing new runtime behavior in the view.

4. **Typography fidelity gate**
- Match not only size/weight but also family and text behavior from tokens (`uppercase`, tracking, line-height intent).
- If design token specifies a family not currently used in project defaults, flag it explicitly and avoid silent fallback.

5. **Dynamic content gate**
- Classify each area as static, localized-static, or data-driven.
- For data-driven areas, map implementation to reusable cells/components and configuration APIs rather than hardcoded snapshots.

## Build the Normalized iOS Design Model

For each node, store:

- `nodeId`
- `name`
- `figmaType`
- `frame: {x, y, width, height}`
- `layout: direction, gap, alignment, distribution`
- `padding: top/right/bottom/left`
- `style: bg, border, radius, opacity, shadow`
- `text: font family/size/weight/lineHeight/kern/alignment`
- `assetRef`
- `componentKind`: inline, reusable, mapped-existing
- `anatomy`:
  - `x`: horizontal anchors, sibling gaps, width behavior
  - `y`: vertical anchors, section rhythm, height behavior
  - `z`: layer role, overlap targets, depth cues, tap priority

Reject generation if more than 10% of required properties are unresolved.

## Anatomical Translation (X/Y/Z Layers)

Translate design anatomy explicitly, not implicitly:

### X-axis (horizontal anatomy)

- Map horizontal anchors to `leading`, `trailing`, `centerX`, and width constraints.
- Preserve measured horizontal spacing between siblings from Figma extraction.
- Keep width intent explicit:
  - `fixed` width when truly fixed
  - edge-pinned fill when fluid
  - intrinsic/hugging when text-driven

### Y-axis (vertical anatomy)

- Map vertical anchors to `top`, `bottom`, `centerY`, baseline, and height constraints.
- Preserve vertical rhythm (section gaps and intra-block cadence) exactly from extracted values.
- Keep height intent explicit:
  - fixed heights for strict controls
  - intrinsic heights for text blocks
  - content-driven expansion for multiline areas

### Z-axis (depth anatomy)

- Use subview order in XIB as the default draw-order mechanism.
- Handle overlaps deliberately:
  - model front/back relationships from Figma overlap evidence
  - ensure intended view receives interaction (hit-testing precedence)
- Separate shadow and clipping hosts when both are required:
  - outer view for shadow
  - inner content view for clipping/corners
- Avoid `layer.zPosition` unless overlap cannot be solved with hierarchy order.
- Document any intentional depth deviation in the output brief.

## Figma Node to UIKit Mapping

| Figma node | Condition | UIKit target |
|---|---|---|
| FRAME | Root screen | Root `UIView` in VC XIB |
| FRAME | Auto-layout-like container | `UIStackView` |
| FRAME | Free-positioned container | `UIView` + explicit constraints |
| GROUP | Structural grouping | `UIView` |
| COMPONENT / INSTANCE | Reusable | Custom `UIView` + XIB |
| TEXT | Static text | `UILabel` |
| TEXT | Single-line input | `UITextField` |
| TEXT | Multi-line input | `UITextView` |
| IMAGE / VECTOR | Visual asset | `UIImageView` |
| LINE | Divider | `UIView` with fixed 1px/1pt height |

## Layout Translation Rules

### Container direction

- Map vertical flow to `UIStackView.axis = .vertical`.
- Map horizontal flow to `UIStackView.axis = .horizontal`.

### Spacing and padding

- Apply inter-item gaps to `stackView.spacing`.
- Apply container padding with `layoutMargins` plus `isLayoutMarginsRelativeArrangement = true`.
- Use explicit edge constraints when container is not `UIStackView`.

### Alignment and distribution

- Convert cross-axis alignment to `alignment`.
- Convert main-axis behavior to `distribution`.
- Add hugging/compression priorities when fill vs hug behavior is ambiguous.
- For rows containing a fixed-size icon and a multiline text column, prefer `alignment = .top` on the inner horizontal stack unless the design explicitly centers both items.

### Absolute-positioned layouts

When layout is not stack-like:

- Use `x/y/width/height` from metadata as initial constraints.
- Add leading/top/width/height at minimum.
- Prefer leading+trailing over fixed width when design implies stretch.

## Size Behavior Rules

- Use fixed width/height constraints only when design implies fixed size.
- Use greater-than/equal constraints for min-size behavior.
- Use content hugging/compression to preserve intrinsic labels/buttons.

Suggested defaults:

- Hugging high (`251+`) for labels that should not stretch.
- Hugging low (`249`) for fill containers.
- Compression resistance high (`750+`) for critical text.

## Styling Translation Rules

### Color

- Resolve to named tokens first (`UIColor(named:)`).
- Add raw RGBA only when no token exists and token creation is out-of-scope.

### Radius

- Set `cornerRadius` via UDRA when possible.
- Use half-height runtime updates for pill/circle shapes when dynamic size is possible.

### Border

- Set `borderWidth` in XIB/UDRA.
- Set `borderColor` in Swift (`cgColor`) during runtime hook.

### Shadow

Configure shadow in Swift. Standard pattern for card shadows:

```swift
func applyCardShadow(to view: UIView) {
    view.layer.shadowColor = UIColor.black.cgColor
    view.layer.shadowOpacity = 0.04
    view.layer.shadowOffset = .zero
    view.layer.shadowRadius = 16 // Figma blur / 2
    view.layer.masksToBounds = false
}
```

Map from Figma shadow token: `shadow(offset: (x,y), blur: B, spread: S, color: C)`
- `shadowOffset = CGSize(width: x, height: y)`
- `shadowRadius = blur / 2`
- `shadowOpacity = alpha component of color`
- `shadowColor = color without alpha`

Keep `masksToBounds = false` on shadow host view.
Use inner content view for clipping when both shadow and clipping are required.

### Opacity

- Map to `alpha` on view.

## Typography Translation Rules

### Font

- Resolve tokenized typography first.
- Map to `UIFont.systemFont(ofSize:weight:)` or custom font as needed.

### Line height and kerning

- Apply line height and kern with `NSAttributedString` in Swift.
- Do not rely on XIB alone for advanced text metrics.

### Label configuration

- Use `numberOfLines = 0` for multiline text.
- Set `textAlignment` from extracted alignment.
- Keep baseline and wrapping behavior consistent with design intent.
- If multiline text exists but disappears at runtime, inspect stack-view alignment and compression before changing attributed-text logic.

## Tailwind-Like Scale Fallbacks

Use only when `get_design_context` exposes scale-like values and exact pt values are absent.

Spacing fallback map:
- `1=4, 2=8, 3=12, 4=16, 5=20, 6=24, 8=32, 10=40, 12=48, 16=64`

Font fallback map:
- `xs=12, sm=14, base=16, lg=18, xl=20, 2xl=24, 3xl=30, 4xl=36`

Always replace fallback values with explicit values when later extraction provides exact numbers.

## XIB Generation Standards

### Document-level settings

- Enable Auto Layout.
- Enable safe areas.
- Set proper `customClass` and `customModule` on File's Owner.

### Element identity

- Keep stable, unique element IDs.
- Set `userLabel` to readable semantic names.

### Constraint quality

- Fully constrain each non-stack subview.
- Avoid ambiguous layouts.
- Use priority intentionally.

### Reusable component XIBs

- Use File's Owner pattern for reusable views.
- Keep root view plain; assign custom class to owner.
- Add a deterministic nib-loading method in Swift companion.
- When extracting a fragile screen section into a child VC/XIB, add the host container, child embedding, and repo-specific resource registration in the same pass.

### Common XIB XML patterns

**Card with corner radius (shadow applied in Swift):**
```xml
<view contentMode="scaleToFill" translatesAutoresizingMaskIntoConstraints="NO" id="..." userLabel="Card Name">
    <color key="backgroundColor" white="1" alpha="1" colorSpace="custom" customColorSpace="genericGamma22GrayColorSpace"/>
    <userDefinedRuntimeAttributes>
        <userDefinedRuntimeAttribute type="number" keyPath="layer.cornerRadius">
            <integer key="value" value="6"/>
        </userDefinedRuntimeAttribute>
    </userDefinedRuntimeAttributes>
</view>
```

**1pt separator line:**
```xml
<view contentMode="scaleToFill" translatesAutoresizingMaskIntoConstraints="NO" id="..." userLabel="Separator">
    <color key="backgroundColor" name="Border"/>
    <constraints>
        <constraint firstAttribute="height" constant="1" id="..."/>
    </constraints>
</view>
```

**Title + value cell (vertical labels):**
```xml
<stackView opaque="NO" contentMode="scaleToFill" axis="vertical" translatesAutoresizingMaskIntoConstraints="NO" id="..." userLabel="Cell Name">
    <subviews>
        <label text="Title" translatesAutoresizingMaskIntoConstraints="NO" id="...">
            <constraints><constraint firstAttribute="height" constant="20" id="..."/></constraints>
            <fontDescription key="fontDescription" name="IBMPlexSans-Regular" family="IBM Plex Sans" pointSize="13.8"/>
            <color key="textColor" name="Subtitle"/>
        </label>
        <label text="Value" translatesAutoresizingMaskIntoConstraints="NO" id="...">
            <constraints><constraint firstAttribute="height" constant="24" id="..."/></constraints>
            <fontDescription key="fontDescription" name="IBMPlexSans-Regular" family="IBM Plex Sans" pointSize="16.5"/>
            <color key="textColor" name="Primary"/>
        </label>
    </subviews>
</stackView>
```

## Outlet Naming Convention

Use consistent outlet names derived from the Figma node purpose:

| Pattern | Example |
|---|---|
| Value labels | `nameValueLabel`, `emailValueLabel`, `phoneValueLabel` |
| Title labels | `nameTitleLabel`, `sectionTitleLabel` |
| Edit buttons | `profileEditButton`, `emailEditButton`, `passwordEditButton` |
| Card containers | `profileDetailsCardView`, `loginSecurityCardView` |
| Separators | `nameSeparatorView` (only if needed as outlet) |
| Action buttons | `deleteAccountButton`, `saveButton` |

## Localization Key Convention

Follow the pattern: `SCREEN_SECTION_ELEMENT`

Examples:
- `ACCOUNT_SETTINGS_PROFILE_DETAILS_TITLE` → "Profile details"
- `ACCOUNT_SETTINGS_LOGIN_SECURITY_TITLE` → "Login & security"
- `ACCOUNT_SETTINGS_FULL_NAME_TITLE` → "Full name"
- `ACCOUNT_SETTINGS_EDIT_ACTION` → "Edit"
- `ACCOUNT_SETTINGS_DELETE_ACCOUNT_TITLE` → "Delete account"
- `ACCOUNT_SETTINGS_DANGER_ZONE_TITLE` → "Danger zone"

Before creating new keys, search existing localization files for keys that already cover the same string.

## Swift Companion File Standards

### ViewController companion

Include:

- Outlets
- Basic lifecycle hooks
- Runtime-only visual setup (`borderColor`, shadow, attributed text)
- Action handlers
- Configuration entry points from presenter/view model layer

### UIView component companion

Include:

- Nib-loading bootstrap
- Outlet wiring
- Runtime style setup
- Public `configure(...)` API
- Lightweight state handling (normal/loading/disabled/error) when variants exist

## Runtime-Only Properties Checklist

Always set these in Swift runtime hooks, not purely in XIB:

- `layer.borderColor`
- `layer.shadowColor` / `shadowOffset` / `shadowRadius` / `shadowOpacity`
- Gradient layers (`CAGradientLayer`)
- Attributed text with line-height/kern
- Underlined text (`NSAttributedString` with `.underlineStyle`)
- Any value requiring `cgColor`

Use `awakeFromNib` for fixed setup and `layoutSubviews` for frame-dependent layers.

## Componentization Strategy

Create separate reusable XIB components when:

- Node is a Figma component/instance
- Block appears in more than one screen
- Block has independent states/variants
- Block has visual complexity worth isolation

Keep inline when:

- Container is purely structural
- Block is one-off with no reuse value

## Token File Strategy

Generate and keep synchronized:

- `UIColor+DesignTokens.swift`
- `UIFont+DesignTokens.swift`
- `DesignTokens.swift` for spacing/radius constants
- Color assets in xcassets for token names

Prefer semantic names (`brandPrimary`, `textSecondary`) over raw names.

## Constraint Conversion Patterns

Use these patterns consistently:

- Fill horizontally: leading + trailing
- Fixed size: width + height
- Vertical gap: current.top = previous.bottom + constant
- Centering: centerX/centerY constraints
- Scroll content: pin content view 4 edges + equal width for vertical scrolling

## Translation Validation Rules

Run these checks after extracting Figma data and before generating XIB/Swift. Catches incorrect translations early.

### Non-Negotiable Fidelity Checks

Treat these as hard checks before finalizing:

1. Font family mismatches must be reported (for example Bell MT required but IBM Plex implemented).
2. Radius and shadow values must match tokens exactly unless deviation is explicitly documented.
3. Non-default line-height and letter-spacing must be handled with attributed text runtime logic.
4. Effective value reconciliation is mandatory:
   - compare XIB-declared values with runtime overrides in Swift
   - report conflicts (for example radius in XIB differs from runtime-assigned radius).

### Pre-generation checklist

Before writing any XIB XML, verify:

1. **All colors resolved** — every color from design context maps to either a named color in xcassets or an explicit hex. No `???` or placeholder colors.
2. **All fonts resolved** — every font from design context maps to a font name that exists in the project (check `customFonts` in existing XIBs or Info.plist `UIAppFonts`).
3. **All spacing values extracted** — gaps, paddings, and margins are numeric pt values, not Tailwind scale names.
4. **All text content captured** — every label visible in the screenshot has corresponding text in the extraction brief.
5. **Hidden nodes excluded** — nodes with `hidden="true"` in metadata are not included in the XIB.
6. **Interactive nodes mapped** — every interactive candidate has an explicit UIKit control + action mapping.
7. **Flow intent captured** — primary and secondary user flows are documented for this artifact.
8. **Business assumptions documented** — unresolved behavior details are listed before coding.
9. **Static vs dynamic split done** — repeated/list-like regions are classified as data-driven when appropriate.
10. **Anatomy map complete** — X/Y anchors and Z-layer roles are explicitly mapped for key nodes.

### Runtime diagnosis checklist

When UI is wrong at runtime but extraction values look correct, verify:

1. text exists in the label or accessibility
2. the visible frame is non-zero
3. the row/container height is owned by the intended text stack
4. any inner horizontal stack containing icon + text does not default to problematic `.fill`
5. images/named colors referenced in XIB also exist in the XIB `<resources>` and repo asset catalog
6. extracted XIBs are registered in `project.pbxproj`
7. child VCs/XIBs are embedded and resolved through the repo’s navigation/DI pattern

### Tailwind parsing validation

When extracting values from `get_design_context` Tailwind classes, verify:

| Tailwind pattern | What to check |
|---|---|
| `gap-[Xpx]` | X is a number, not a Tailwind scale token like `gap-4` |
| `text-[Xpx]` | X matches a typography token size from `get_variable_defs` |
| `text-[#hex]` | Hex matches a color token; if not, flag it |
| `leading-[Xpx]` | X matches the lineHeight from a typography token |
| `font-['Family:Style']` | Family and style resolve to a real font file in the project |
| `rounded-[Xpx]` | X is consistent across similar elements (all cards same radius) |
| `px-[X]`, `py-[X]`, `pt-[X]`, `pb-[X]` | Values match padding from the Figma frame, not arbitrary |
| `shadow-[...]` | Offset, blur, color match the shadow token from variable defs |
| `w-[Xpx]` or `h-[Xpx]` | Compare against metadata dimensions for the same node |

### UIKit value mapping validation

After converting Tailwind to UIKit values, verify:

- **Font size in XIB** matches the token (e.g., 16.5pt not rounded to 17pt).
- **Corner radius in UDRA** matches the Tailwind `rounded-[X]` value exactly.
- **Named colors** in XIB reference colors that exist in the project's xcassets. Run `grep -r "colorName" *.xcassets` to confirm.
- **Stack spacing** matches the `gap-[X]` value, not a guess.
- **Constraint constants** match the padding/margin values from Tailwind, not approximations.

### Constraint completeness validation

For every view in the XIB, verify:

- Non-stack views have 4 constraints minimum (position + size).
- Stack arranged subviews rely on the stack for positioning — do not add redundant position constraints.
- Scroll view content has: 4 edge pins to scroll view + width equal to scroll view.
- Labels with dynamic text use `numberOfLines="0"` and do not have a fixed height constraint.
- Separator views have exactly 1 height constraint (1pt) and width from leading+trailing.

### Token-to-XIB named color mapping

Before using a named color in XIB, verify the mapping:

| Figma token | Expected named color | Verify exists |
|---|---|---|
| `Foundation/.../black-500` or `#000000` | "Primary" | Check xcassets |
| `Foundation/.../black-250` or `#6F6F6F` | "Subtitle" | Check xcassets |
| `Foundation/.../black-50` or `#E6E6E6` | "Border" | Check xcassets |
| `Foundation/.../White` or `#FFFFFF` | white (literal) | Built-in |
| `Foundation/.../Red/red-500` or `#BE1E46` | "Error" | Check xcassets |
| Background color | "Background" | Check xcassets |

If a Figma color does not match any existing named color, flag it in the output brief and suggest creating a new xcasset color entry.

### Post-generation XIB validation

After writing the XIB file:

1. **Run ibtool** — `ibtool --errors --warnings --notices file.xib` must return zero errors.
2. **Verify customClass** — File's Owner `customClass` matches the Swift ViewController class name.
3. **Verify customModule** — `customModule` matches the project module (e.g., "Mazaya").
4. **Count outlets** — every outlet referenced in Swift has a corresponding element ID in the XIB.
5. **Count actions** — every `@IBAction` in Swift has a corresponding connection in the XIB.
6. **No orphan constraints** — every constraint references two existing view IDs.
7. **Runtime wiring** — confirm target XIB is added to PBX resources and actually instantiated by DI/navigation path.
8. **Interaction continuity** — confirm each mapped action is wired through presenter/view-model flow (not dead-end UI taps).
9. **Localization resilience** — validate text expansion behavior for long strings and RTL-sensitive alignment zones.
10. **Z-layer correctness** — verify overlap order, shadow host placement, and tap-priority on layered regions.
11. **Resource integrity** — verify all referenced images and named colors are present in both the XIB `<resources>` block and the repo asset catalog.
12. **Runtime risk scan** — run `xib_runtime_risk_scan.py` when the layout includes stack-heavy rows, extracted sections, or multiline label groups.

### Common translation errors to catch

| Error | Symptom | Fix |
|---|---|---|
| Tailwind `leading-[24px]` treated as leading constraint | Label has a left-margin of 24pt instead of line-height 24pt | `leading-[X]` in Tailwind means CSS `line-height`, not Auto Layout leading edge |
| Font size rounded | 16.5pt becomes 17pt in XIB | Use exact `pointSize="16.5"` in fontDescription |
| Shadow blur used directly | `shadowRadius = 32` instead of 16 | Figma blur = UIKit shadowRadius * 2; divide by 2 |
| Color alpha in wrong place | `#0000000A` used as opaque color | Separate into color `#000000` + opacity `0.04` |
| Tailwind `shrink-0` ignored | Label stretches unexpectedly | Set high content compression resistance (750+) |
| `flex-[1_0_0]` ignored | Container does not fill available space | Set low content hugging priority (249) |
| Inner horizontal stack left at default `.fill` | Fixed-size icon row collapses multiline subtitle text to height `0` | Set inner horizontal stack alignment to `.top` so the text column owns row height |
| Asset guessed by name only | Correct-looking XIB but wrong icon vs Figma | Verify with MCP screenshot/assets first; otherwise inspect repo assets and ask for the exact asset when confidence is low |

## Screenshot Validation Protocol

Validate before finalizing:

- Spacing rhythm matches
- Typography scale and weight match
- Radius/border/shadow match
- Alignment and hierarchy match
- Asset cropping/fit mode match
- Scroll behavior match

Record any intentional deviations explicitly.

## Mazaya-Specific Final Checks (When Working In Mazaya)

After changing XIBs, run:

```bash
git diff --name-only -- '*.xib'
git diff --cached --name-only -- '*.xib'
CHANGED_XIBS="$(git diff --name-only -- '*.xib'; git diff --cached --name-only -- '*.xib')"
printf "%s\n" "$CHANGED_XIBS" | sort -u | while IFS= read -r xib; do
  [[ -z "$xib" ]] && continue
  python3 .codex/skills/xib-xml-audit/scripts/xib_xml_static_checks.py "$xib"
  IBTOOL_MODULE="Mazaya" bash .codex/skills/xib-xml-audit/scripts/xib_ibtool_check.sh "$xib"
done
```

Use this to prevent malformed XIB output before handoff.

If the repo-local `xib-xml-audit` scripts are missing, use this fallback:

```bash
git diff --name-only -- '*.xib'
git diff --cached --name-only -- '*.xib'
CHANGED_XIBS="$(git diff --name-only -- '*.xib'; git diff --cached --name-only -- '*.xib')"
printf "%s\n" "$CHANGED_XIBS" | sort -u | while IFS= read -r xib; do
  [[ -z "$xib" ]] && continue
  ibtool --errors --warnings --notices "$xib"
done
```

If you add a new XIB-backed child VC or extracted section in Mazaya, also verify:

- the new `.xib` is in `project.pbxproj` resources
- the new Swift files are in `project.pbxproj` sources
- DI registration exists if the repo resolves the child via `Resolver`
- the parent VC/XIB contains a host container and embeds the child deterministically
- the presenter contract remains stable unless the task explicitly changes behavior

For Mazaya checkout/shipping work, read `references/mazaya-xib-integration-checklist.md` before extracting a section into `Subviews/`.

## Error Recovery Guide

### Unknown class at runtime

- Verify `customClass` spelling.
- Verify `customModule` matches target module.
- Verify file target membership.

### Nil outlets

- Verify XIB outlet connections.
- Verify File's Owner class.
- Verify reuse of owner vs root custom class pattern.

### Ambiguous constraints

- Ensure each view has deterministic position and size.
- Resolve competing constraints by priority.
- Reduce redundant constraints in stack-managed layouts.

### Visual mismatch vs Figma

- Re-check token mapping first.
- Re-check spacing from design context.
- Re-check content mode and text attributes.
- Use screenshot diff reasoning before changing structure.
- If the mismatch is iconography, read `references/asset-verification-rules.md` and avoid guessing by asset name.

## Output Contract For This Skill

When implementing, return:

- Files created/updated
- Node IDs covered
- Token mappings applied
- Runtime-only properties handled in Swift
- Validation results (including XIB checks where applicable)
- Whether generation mode, audit mode, runtime diagnosis mode, or extraction mode was used
- Known gaps or assumptions

When running audit/patch-assist workflows, also return:

- `analysis_report.md`
- `patch_hints.md`
- `donor_xib_candidates.md` (only when donor mining is requested)
- `xib_runtime_risks.md` (when risk scan is run)

## Collaboration With `figma-mcp`

Keep responsibilities split:

- `figma-mcp`: extraction correctness and tool orchestration
- `figma-to-ios-ui`: UIKit/XIB translation and file generation

Do not bypass `figma-mcp` pipeline when Figma data is incomplete.

## Script Interfaces (Patch-Assist Automation)

`extract_uikit_impl_snapshot.py`

```bash
python3 scripts/extract_uikit_impl_snapshot.py \
  --xib <abs_path_to_xib> \
  --swift <abs_path_to_view_swift> \
  --presenter <abs_path_optional> \
  --out <abs_path_json>
```

Output JSON keys:
- `target`
- `anatomy` (`x_axis`, `y_axis`, `z_axis`)
- `typography`
- `colors`
- `spacing_and_constraints`
- `interactions`
- `runtime_overrides`
- `dynamic_content_hints`
- `wiring_hints`

`figma_uikit_audit.py`

```bash
python3 scripts/figma_uikit_audit.py \
  --design-spec <abs_path_design_spec_json> \
  --impl-snapshot <abs_path_impl_json> \
  --repo-root <abs_repo_root_optional_for_donor_search> \
  --report-out <abs_path_md> \
  --patch-hints-out <abs_path_md> \
  --donor-out <abs_path_md_optional> \
  --donor-limit 5
```

Behavior:
- deterministic comparisons with tolerance rules
- severity classification + rationale
- patch hints only (no file mutation)
- optional donor-XIB ranking

`xib_runtime_risk_scan.py`

```bash
python3 scripts/xib_runtime_risk_scan.py \
  --xib <abs_path_to_xib> \
  [--out <abs_path_md>]
```

Behavior:
- heuristic scan for stack-view runtime risk patterns
- flags likely multiline-label collapse chains
- flags missing XIB resource declarations for referenced images/named colors
- intended for runtime-diagnosis mode, not as a substitute for simulator/view-hierarchy evidence

## Design Spec Template

Use:
- `templates/design_spec.template.json`

Required top-level keys:
- `node`
- `tokens`
- `anatomy`
- `layout_tree`
- `interactions`
- `flow`
- `business_assumptions`
- `unresolved`

## How To Run (Single Command Wrapper)

```bash
bash scripts/run_audit.sh \
  --design-spec /tmp/design_spec.json \
  --xib /absolute/path/View.xib \
  --swift /absolute/path/View.swift \
  --presenter /absolute/path/Presenter.swift \
  --repo-root /absolute/path/repo \
  --out-dir /tmp/figma-uikit-audit
```
