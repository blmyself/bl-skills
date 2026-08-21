# Stack View Auto Layout Pitfalls

Use this reference when debugging stack-heavy UIKit/XIB layouts.

## Pitfall 1: Horizontal `.fill` with fixed icon + multiline text

Failure shape:

- horizontal stack
- one child has fixed height (for example icon `24pt`)
- sibling is a vertical text stack with multiline labels
- stack alignment defaults to `.fill`

Effect:

- both children are forced to the same cross-axis height
- the title consumes available height
- the multiline subtitle becomes compressible and can collapse to `0`

Preferred fix:

- set the inner horizontal stack alignment to `.top`

## Pitfall 2: Multiline labels with fixed height

Failure shape:

- `numberOfLines = 0`
- direct height constraint on the label

Effect:

- label clips or never expands

Preferred fix:

- remove the fixed height and let the container own height

## Pitfall 3: Hidden arranged subviews changing stack rhythm

Failure shape:

- multiple labels in a vertical stack
- some are conditionally hidden

Effect:

- spacing or visual collapse can look like missing constraints

Preferred fix:

- reason about the visible arranged-subview set and whether the container still owns the intended height

## Pitfall 4: Design-time rects mistaken for real constraints

Failure shape:

- XIB shows suspicious `<rect>` heights like `0`, `19`, or `30`

Effect:

- easy to over-trust Interface Builder’s design-time geometry

Preferred fix:

- inspect actual constraints, stack behavior, hugging, and compression priorities
- treat `<rect>` values as hints, not proof
