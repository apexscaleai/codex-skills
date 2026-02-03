---
name: repo-standards
description: Enforce formatting, lint rules, naming conventions, and review checklist items for this repo's stack (React Native + Next.js). Use for linting/typechecking/formatting consistency and PR review readiness.
metadata:
  short-description: Repo standards & consistency
---

# Repo Standards

Use this skill to make changes that are consistent with the repo's established standards, and to review changes for “PR-ready” quality.

If the repo has a monorepo toolchain (pnpm workspaces, Turborepo), use it rather than running package-level commands ad hoc.

## Quick Start (When You Need A Tight Answer)

1. Identify package manager + orchestrator.
2. Find the repo’s actual quality gates (`lint`, `typecheck`, `test`, `format`, `ci`).
3. Run the gates (preferred) or do a best-effort static review (fallback).
4. Report issues with file references + exact commands to reproduce.

## Workflow (Concrete)

1. Discover what the repo enforces (source-of-truth first).
- Read root `package.json`.
- Determine package manager:
  - `package.json:packageManager` if present.
  - Else lockfile: `pnpm-lock.yaml` > `yarn.lock` > `package-lock.json`.
- Identify orchestrator:
  - `turbo.json` and/or `pnpm-workspace.yaml` implies monorepo orchestration.
  - If neither exists, assume single-package scripts in root `package.json`.
- Identify “quality gate” scripts:
  - Look for `lint`, `typecheck`, `test`, `format`, `ci` in `package.json:scripts`.
  - If a root `ci` exists, prefer that (it usually reflects production gates).
- Identify tooling config files (read them, don’t guess):
  - ESLint: `eslint.config.*`, `.eslintrc*`
  - Prettier: `prettier.config.*`, `.prettierrc*`
  - TS: `tsconfig*.json`
  - commitlint: `commitlint.config.*`
  - editor: `.editorconfig`
  - pre-commit: `.husky/`, `lint-staged.config.*`

2. Determine the scope you are enforcing.
- If reviewing a PR: scope is changed files only.
- If implementing: scope is “new/modified files + touched neighbors” (imports, types, tests).
- Identify whether changes are web (Next.js), mobile (React Native), or shared packages.

3. Infer conventions from code (only when configs don’t fully specify).
- Look at 2-3 existing modules similar to the target area.
- Record conventions that are clearly consistent in the repo:
  - file names (`kebab-case` vs `PascalCase`)
  - exports (default vs named exports)
  - hooks naming (`useX`)
  - folders (e.g., `app/` vs `pages/`, `screens/`, `features/`, `components/`)
  - test placement and naming (`*.test.ts`, `__tests__/`, etc.)

4. Run the repo’s quality gates (preferred).
- Prefer the highest-level orchestrator the repo uses:
  - If `turbo.json` exists and there are scripts like `turbo lint` / `turbo typecheck`, use them.
  - If pnpm workspaces are used, prefer `pnpm -r <script>` or a repo-provided wrapper script.
- If you cannot run commands (or user didn’t ask), do a best-effort static check, but clearly label it as such.

5. Enforce the “PR-ready” checklist (concrete checks).
- Formatting:
  - No mixed quote/spacing style within a file.
  - No manual alignment whitespace.
- Lint/TS:
  - No new lint suppressions unless justified and localized.
  - No new `any` unless it’s the established repo approach.
  - No unsafe non-null assertions unless a guard exists.
- React:
  - Hooks rules respected; dependencies correct.
  - No `useEffect` that should be derived state.
- Next.js:
  - Server/client boundary respected (no secrets in client bundles, no server-only imports in client components).
  - Route conventions align with existing usage (`app/` vs `pages/`).
- React Native:
  - Avoid inline anonymous components in render paths if it causes re-renders.
  - Avoid expensive list item renders (FlatList) without memoization if the repo uses it.
- Tests:
  - If similar code has tests, add/update tests following the same harness.
  - If no tests exist, note the gap and propose the minimal test that would catch regressions.

6. Report findings with evidence.
- Every finding must include:
  - The file path(s)
  - Why it violates the repo’s standard (config or observed pattern)
  - Minimal fix guidance
  - The command(s) that would fail (if applicable)

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
 - “How to Verify” (exact script(s) to run)

## Example Commands (only when asked to run)

```bash
# Prefer the repo's actual scripts; these are examples only.

# pnpm (single package)
pnpm run lint
pnpm run format
pnpm run typecheck
pnpm run test

# pnpm (workspace/monorepo common patterns)
pnpm -r run lint
pnpm -r run typecheck
pnpm -r run test

# yarn
yarn lint
yarn format
yarn typecheck
yarn test

# npm
npm run lint
npm run format
npm run typecheck
npm test
```

## Review Checklist (PR-Ready)

- No new lint/type errors.
- No hard-coded secrets, tokens, or API keys.
- New code matches existing naming + folder patterns.
- If behavior changes, tests updated/added accordingly.
- No dead code, unused exports, or commented-out blocks.
