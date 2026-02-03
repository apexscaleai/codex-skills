---
name: a11y-review
description: Review accessibility issues for React Native and Next.js UI, including labels, focus, and contrast.
metadata:
  short-description: Accessibility review
---

# Accessibility Review

Use this skill to audit UI accessibility for React Native and Next.js. Focus on meaningful, user-impacting issues and align with existing UI patterns.

## Workflow

1. Identify UI surfaces in scope.
- Screens, pages, shared components, navigation, forms.

2. Web (Next.js) checks.
- Semantic elements for headings, lists, buttons, and forms.
- Keyboard navigation and visible focus states.
- Form labeling (label/aria-label), error messaging, and inline help.
- Image `alt` text and decorative image handling.
- Color contrast and text size support.

3. React Native checks.
- `accessibilityLabel`, `accessibilityRole`, `accessibilityHint` on actionable elements.
- Focus order and grouping (`accessible`, `importantForAccessibility`).
- Dynamic type / font scaling support.
- Touch target sizes for interactive elements.

4. Report only actionable issues.
- Tie each issue to a specific component and expected fix.

## Output Format

Provide:
- Summary
- Findings (ordered by severity and UX impact)
- Suggested Fixes (include component/file references)
- Quick Wins (low-effort improvements)

## Notes

- Do not add new dependencies unless asked.
- If the repo has an accessibility checklist, follow it.
