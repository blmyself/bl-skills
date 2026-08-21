# XIB Runtime Failure Shields

Use this reference when `ibtool` passes but the UI is still wrong at runtime.

## First Split the Problem

Classify the failure before patching:

1. data/state missing
2. runtime wiring missing
3. layout collapse
4. resource mismatch

Do not start by editing text metrics until this split is clear.

## Strong Runtime-Only Signals

Treat these as layout/resource signals, not presenter signals:

- label text exists in runtime state or accessibility, but is not visible
- a label frame is `0` height or the row height collapses to the title line
- the view hierarchy shows the child VC/XIB is loaded, but its content is clipped or compressed
- the icon is wrong even though the image name looks plausible

## Reliable Debug Order

1. confirm text actually exists
2. inspect view hierarchy frames
3. inspect stack-view alignment and arranged subviews
4. inspect fixed-size siblings and compression priorities
5. inspect XIB `<resources>` image/color declarations
6. inspect repo registration/wiring (`project.pbxproj`, DI, host container, child embedding)
7. only then inspect attributed text or relayout code

## Do Not Start With

These are often false first fixes:

- `preferredMaxLayoutWidth`
- `baselineOffset`
- manual relayout loops
- text-measurement experiments

Those are valid only after layout ownership is proven correct.

## Frequent Failure Shield

For rows shaped like:

- fixed radio or icon
- icon image
- multiline text stack

Inspect the **inner horizontal stack alignment** before anything else.

Default `.fill` can force the text column to the fixed icon height and collapse multiline labels.

Preferred default:

- inner horizontal stack `alignment="top"`

## Resource Integrity Shield

When a XIB compiles but the wrong icon or color appears:

- verify the `image="..."` or named color reference in the XIB
- verify the same name exists in the XIB `<resources>` block
- verify the asset exists in the repo xcassets
- if design certainty is low, verify with MCP screenshot/assets instead of guessing by asset name
