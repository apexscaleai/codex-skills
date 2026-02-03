---
name: a11y-review
description: Review accessibility issues for React Native and Next.js UI, including labels, focus management, contrast, and screen reader support.
metadata:
  short-description: Accessibility review
---

# Accessibility Review

Use this skill to audit UI accessibility for React Native and Next.js with concrete, testable checks.

Default posture:
- Prefer fixes that improve both accessibility and UX for all users (keyboard, reduced motion, clear errors).
- Report issues only when you can point to a specific element/component and a specific fix.

## Workflow

1. Identify UI surfaces in scope.
- Screens, pages, shared components, navigation, forms.

2. Web (Next.js) checks (manual + code review).
- Semantic elements for headings, lists, buttons, and forms.
- Keyboard navigation and visible focus states.
- Focus management for dialogs/menus (trap focus, restore focus on close).
- Avoid div/span click handlers when a `<button>` is appropriate (unless the repo has a pattern).
- Form labeling (label/aria-label), error messaging, and inline help.
- Image `alt` text and decorative image handling.
- Table semantics where applicable.
- Color contrast and text size support.

3. React Native checks (screen reader + touch targets).
- `accessibilityLabel`, `accessibilityRole`, `accessibilityHint` on actionable elements.
- `accessibilityState` (disabled/selected/checked) where relevant.
- Focus order and grouping (`accessible`, `importantForAccessibility`).
- Dynamic type / font scaling support.
- Respect reduced motion settings if the repo uses animations.
- Touch target sizes for interactive elements.

4. Minimal manual test plan (when feasible).
- Web:
  - Tab through primary flows; ensure focus is visible and logical.
  - Activate all interactive controls via keyboard only.
  - Trigger validation errors; ensure they are announced or discoverable.
- RN:
  - VoiceOver/TalkBack pass on primary screens.
  - Verify labels are meaningful and not duplicated.
  - Verify all tappable elements meet touch target expectations.

5. Report only actionable issues.
- Tie each issue to a specific component and expected fix.

## Output Format

Provide:
- Summary
- Findings (ordered by severity and UX impact)
- Suggested Fixes (include component/file references)
- Quick Wins (low-effort improvements)
 - “How to Test” (1-3 steps to confirm the fix for each major finding)

## Notes

- Do not add new dependencies unless asked.
- If the repo has an accessibility checklist, follow it.
