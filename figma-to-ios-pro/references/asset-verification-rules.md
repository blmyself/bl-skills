# Asset Verification Rules

Use this reference when mapping Figma icons/images to repo assets.

## Core Rule

Do not choose an asset by name alone if more than one local asset is plausible.

## Preferred Verification Order

1. Figma MCP screenshot
2. Figma-exported asset
3. existing repo asset visual compare
4. ask for the exact asset when confidence is still low

## Repo-Grounded Fallback

If MCP is unavailable:

- inspect the candidate xcasset folders
- compare actual image files visually
- prefer the asset the developer explicitly names over inferred naming

## XIB Integrity

After swapping an icon:

- update the `image="..."` reference on the image view
- update the corresponding XIB `<resources>` entry
- verify the asset exists in xcassets
- run `ibtool`
