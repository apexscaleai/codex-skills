---
name: design-system-enforcer
description: Enforce design system usage, tokens, and UI consistency across React Native and Next.js.
metadata:
  short-description: Design system enforcement
---

# Design System Enforcer

Use this skill to ensure UI changes adhere to the repo's design system, component library, and design tokens.

## Workflow

1. Locate the design system.
- Identify shared UI packages, component folders, or token files.
- Look for docs under `docs/` or `packages/` that describe UI standards.

2. Audit component usage.
- Prefer shared components over custom one-offs.
- Ensure colors, typography, spacing, and radii use tokens or theme helpers.
- Flag hard-coded styles that bypass tokens.

3. Check interaction consistency.
- Buttons, inputs, and navigation should match existing patterns.
- State styles (hover/pressed/disabled/error) should be consistent.

4. Report deviations.
- Provide exact locations and suggest the canonical component or token.

## Output Format

Provide:
- Summary
- Deviations (with file references)
- Suggested Fixes (preferred components/tokens)
- Consistency Risks (areas likely to drift)

## Notes

- Do not refactor UI without a request.
- If the design system is missing, recommend creating a minimal token source of truth.
