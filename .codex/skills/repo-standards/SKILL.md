---
name: repo-standards
description: Enforce formatting, lint rules, naming conventions, and review checklist items for this repo's stack (React Native + Next.js). Use for linting/typechecking/formatting consistency and PR review readiness.
metadata:
  short-description: Repo standards & consistency
---

# Repo Standards

Use this skill to evaluate consistency and quality against the repo's existing standards, without inventing new rules. Prefer to follow the repo's config and scripts.

If the repo has a monorepo toolchain (pnpm workspaces, Turborepo), use it rather than running package-level commands ad hoc.

## Workflow

1. Discover "what the repo already enforces".
- Read `package.json` at the repo root (and any app/package `package.json` in scope).
- Determine package manager from `packageManager` and lockfiles: `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`.
- Identify scripts and conventions from:
  - `package.json` scripts: `lint`, `format`, `typecheck`, `test`, `build`, `ci`
  - `pnpm-workspace.yaml` and `turbo.json` (monorepo orchestration)
  - `commitlint.config.*`, `.husky/`, `lint-staged.config.*`
  - `eslint.config.*`, `.eslintrc*`, `prettier.config.*`, `.prettierrc*`, `.editorconfig`
  - `tsconfig*.json` (incl. base configs)

2. Infer conventions from existing code (only if config is unclear).
- Look at 2-3 representative modules similar to the target scope (e.g., existing Next.js routes/components; existing React Native screens/components).
- Capture conventions that are actually present:
  - file naming (`kebab-case`, `PascalCase`, `camelCase`)
  - component naming (exported component names, default vs named exports)
  - hook naming (`useX`)
  - folder structure (e.g. `components/`, `features/`, `screens/`, `app/`, `pages/`)
  - error handling patterns and logging conventions

3. Run the repo's quality gates when requested (preferred) or simulate them via review (fallback).
- Preferred: run existing scripts (root or per-package depending on repo practice).
- Fallback (no running): validate by inspection using the same standards the tooling would enforce.

4. Evaluate the target scope for consistency and correctness.
- Formatting/Prettier compliance (line endings, quotes, imports order if enforced).
- ESLint rules (React hooks rules, unused vars, exhaustive deps, etc.).
- TypeScript: unsafe `any`, missing `return` paths, wrong nullability, inferred vs explicit types when the repo expects explicit.
- Naming and structure: new code should look "native" to the repo.
- Tests: if similar code has tests, new code should include tests in the same style/location.
- Monorepo hygiene: avoid cross-package deep imports unless the repo already does them.

5. Report findings with evidence.
- Summarize deviations with file references and concrete examples.
- If scripts exist and were not run, recommend the exact script(s) to run to confirm.

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
# Prefer the repo's actual scripts; these are examples only.

# pnpm
pnpm run lint
pnpm run format
pnpm run typecheck
pnpm run test

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
