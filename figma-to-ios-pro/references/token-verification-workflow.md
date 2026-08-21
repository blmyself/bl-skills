# Token Verification Workflow

Use this when a Figma value must map to a project token and the token name is not self-evident.

## Goal

Pick the semantically correct token by verified output, not by token-name intuition.

## Steps

1. Capture the exact Figma value.
   - Example: badge fill `#B6E3C1`

2. List the candidate semantic tokens in the project.
   - Example: `lightTertiary`, `selectedGreenBackground`, `tertiary`

3. Verify how the candidates resolve in the repo.
   - Inspect token definitions in the project color/font helpers.
   - If needed, inspect the compiled asset output or the resolved runtime value.

4. Check semantic neighbors.
   - Prefer the token already used by sibling controls when the design intent matches.
   - Example: if the radio fill already uses the correct semantic selection green, the badge may need the same family.

5. Record the decision in the spec sheet.
   - Figma value
   - chosen token
   - rejected tokens
   - reason

## Anti-Patterns

- Do not choose a token just because the name sounds close.
- Do not trust Interface Builder preview when Swift overrides runtime colors or typography.
- Do not silently reuse a screen-specific token on a shared component without checking other screens.

## Minimum Evidence

Before changing a token, capture:

- exact Figma value
- implementation line using the current token
- project token definition or resolved value
- the reason the replacement is a closer semantic match
