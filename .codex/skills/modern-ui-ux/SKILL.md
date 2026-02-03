---
name: modern-ui-ux
description: Define and enforce modern UI/UX and aesthetics for Next.js and React Native: typography, spacing, motion, states, a11y, and consistency. Use for UI reviews and upgrading generic-looking UIs.
metadata:
  short-description: Modern UI/UX & aesthetics
---

# Modern UI/UX

Use this skill to make UI changes feel modern, intentional, and consistent without drifting from the repo’s design system (if one exists).

This skill complements `frontend-design` (for creating UI) and `design-system-enforcer` (for enforcing tokens/components). Use this skill when you need explicit aesthetic rules, not just “make it nicer”.

## Workflow (Prescriptive)

1. Discover constraints (don’t invent a new system).
- Find existing tokens/theme/components in `packages/`, `components/`, `ui/`, `theme.*`.
- Identify typography scale and spacing scale if present.
- Identify interaction patterns already used (loading/empty/error, dialogs, toasts).

2. Apply the modern UI/UX baseline (use the checklist).
- Use `references/modern-ui-ux-checklist.md`.
- When a design system exists, prefer tokens/components over custom styles.

3. Ensure accessibility is not regressed.
- For web: keyboard + focus + semantics.
- For RN: labels/roles + dynamic type + touch targets.
- If needed, pair with the `a11y-review` skill.

4. Produce a “before/after” improvement plan.
- 3-7 targeted changes that upgrade the feel:
  - typography hierarchy
  - spacing rhythm
  - component states
  - motion restraint
  - color and elevation discipline

## Resources

- Checklist: `references/modern-ui-ux-checklist.md`
- Report template: `assets/modern-ui-ux-review.md`

