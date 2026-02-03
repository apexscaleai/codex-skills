---
name: design-system-enforcer
description: Enforce design system usage, tokens, and UI consistency across React Native and Next.js. Use to reduce one-off UI and keep components aligned with tokens.
metadata:
  short-description: Design system enforcement
---

# Design System Enforcer

Use this skill to keep UI consistent by enforcing the repo’s design system, components, and tokens (web + mobile).

This skill is strongest when it acts like a “diff gate”:
- New UI should use existing components.
- New styles should use tokens/theme helpers, not ad hoc values.
- New patterns should match existing interaction/empty/error/loading conventions.

## Workflow

1. Locate the design system.
- Identify shared UI packages, component folders, or token files (often under `packages/`).
- Look for styling infrastructure:
  - `tailwind.config.*`, `postcss.config.*`
  - theme files (`theme.ts`, `tokens.ts`, `colors.ts`, etc.)
  - CSS variables / token maps
- Look for docs under `docs/` or `packages/` that describe UI standards.

2. Audit component usage.
- Prefer shared components over custom one-offs.
- Ensure colors, typography, spacing, and radii use tokens or theme helpers.
- Flag hard-coded styles that bypass tokens.
- Flag duplicated components (new button/input variants) when a canonical component exists.

3. Check interaction consistency.
- Buttons, inputs, and navigation should match existing patterns.
- State styles (hover/pressed/disabled/error) should be consistent.
- Loading/empty/error states should follow established UX patterns.

4. Report deviations.
- Provide exact locations and suggest the canonical component or token.

## Concrete “Don’t Drift” Checks

- Color drift:
  - flag hex colors and `rgba(...)` in new code when the repo uses tokens
- Spacing drift:
  - flag magic numbers for padding/margin when spacing scale exists
- Typography drift:
  - flag ad hoc font sizes/weights when typography tokens exist
- Component drift:
  - flag hand-rolled buttons/inputs when canonical components exist

## Output Format

Provide:
- Summary
- Deviations (with file references)
- Suggested Fixes (preferred components/tokens)
- Consistency Risks (areas likely to drift)
 - “What To Standardize Next” (optional, if drift is systemic)

## Notes

- Do not refactor UI without a request.
- If the design system is missing, recommend creating a minimal token source of truth.
