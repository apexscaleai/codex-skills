---
name: repo-standards
description: Enforce formatting, lint rules, naming conventions, and review checklist items for this repo's stack (React Native + Next.js).
metadata:
  short-description: Repo standards & consistency
---

# Repo Standards

Use this skill to evaluate consistency and quality against the repo's existing standards, without inventing new rules. Prefer to follow the repo's config and scripts.

## Workflow

1. Detect the package manager and scripts.
- Read `package.json` and lockfiles (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`).
- Prefer the repo's `packageManager` field when present.
- Identify scripts for `lint`, `format`, `typecheck`, `test`, `build`.

2. Identify enforced rules and conventions.
- Read ESLint, Prettier, TypeScript, commitlint, and editor configs if present.
- Note naming conventions (components, hooks, files, folders) from existing code and configs.

3. Evaluate the target scope.
- For the files/changes in scope, check:
  - Formatting and lint compliance.
  - Type safety and lint warnings.
  - Naming conventions and folder placement.
  - Test coverage expectations (if tests exist for similar files).

4. Report findings with evidence.
- Summarize deviations with file references and concrete examples.
- If scripts exist, recommend running them rather than guessing.

## What to Avoid

- Do not add new tooling or configs unless the user asks.
- Do not change existing conventions to match personal preferences.
- Do not run heavy scripts unless requested.

## Output Format

Provide:
- Summary (pass/fail status)
- Checks Run (if any)
- Findings (ordered by severity)
- Suggested Fixes (minimal, aligned to existing standards)

## Example Commands (only when asked to run)

```bash
# Example: pnpm repo
pnpm run lint
pnpm run format
pnpm run typecheck
pnpm run test
```
