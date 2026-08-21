# SwiftUI Accessibility and Inclusive Design

Use this reference when the Figma-driven UI includes interactive elements, dynamic text, grouped content, or custom controls.

## Core rules

- Use semantic controls such as `Button` for tappable elements whenever possible.
- Keep typography and spacing compatible with Dynamic Type.
- Treat accessibility as part of fidelity, not a post-pass.

## Text and scaling

- Prefer Dynamic Type-aware text styles or the repo's equivalent typography wrappers.
- Use scalable metrics for custom spacing or icon sizes when they should scale with text.
- Avoid layouts that depend on single-line assumptions unless the design and product both require that behavior.

## Semantics

- Mark decorative imagery as decorative or hidden from accessibility.
- Group related content intentionally so VoiceOver reads the screen in a sensible order.
- Provide explicit labels, values, or hints when the visible content is not descriptive enough on its own.
- Use accessibility representations for custom controls when their visual structure is not self-describing.

## Motion and interaction

- Make sure custom gestures still expose an accessible action or semantic control path.
- Keep tap targets large enough for the surrounding subsystem's accessibility expectations.
- Respect Reduce Motion when animation is prominent in the feature.

## Audit checks

- tappable elements are semantic controls or have a justified custom interaction model
- grouped content reads naturally with assistive technologies
- text still works with longer strings and larger sizes
- decorative content is not creating noise
- accessibility changes were not lost while chasing pixel parity
