---
name: perf-profiling
description: Run and interpret performance benchmarks for React Native and Next.js, compare against budgets, and summarize regressions. Use for bundle size, Lighthouse, and runtime profiling checks.
metadata:
  short-description: Performance profiling
---

# Performance Profiling

Use this skill to find existing performance tooling, run benchmarks if requested, and summarize regressions or risks. Prefer the repo's existing scripts and budgets.

## Workflow

1. Discover perf tooling, baselines, and budgets.
- Inspect `package.json` scripts for: `perf`, `benchmark`, `profile`, `lighthouse`, `bundle`, `analyze`, `size`, `stats`.
- Look for tooling/config files:
  - `next.config.*` (bundle/analyze hooks, headers, compression toggles)
  - `lighthouserc.*`, `lighthouse.*`
  - `size-limit.*`, `.size-limit.*`, `bundlesize.*`
  - `webpack.config.*` / analyzer config (if present)
- Check docs under `docs/` (or repo root docs) for perf budgets and release gates.

2. Identify target surface.
- Next.js:
  - Client JS size per route, shared chunks, and third-party bloat.
  - Route rendering mode (SSR/SSG/ISR) and caching behavior.
  - Server execution hotspots (API routes/server actions) and cold starts (if serverless).
  - Lighthouse and Core Web Vitals (if tracked).
- React Native:
  - App start time and bundle load.
  - JS thread responsiveness (dropped frames) and expensive renders.
  - Memory pressure and large images/lists.
  - Bundle size and source map size (release artifacts).

3. Run only what exists and is requested.
- Use the repo's scripts; avoid inventing flags or new dependencies.
- If no scripts exist, propose a minimal plan with clear command candidates and expected outputs, but do not run it unless asked.

4. Compare to budgets or baselines.
- If metrics or budgets are defined, compare current results to those numbers.
- If no budgets exist, call out the missing baseline explicitly.

5. Triage regressions.
- Separate "measurement noise" from real regressions (e.g., CI variance vs consistent deltas).
- Prefer actionable root causes:
  - New dependency / large asset / code path change
  - Unintentional client-side import of server-only code
  - Increased re-rendering due to unstable props/state
  - Missing memoization in list-heavy views (RN)

## Output Format

Provide:
- Metrics Collected (with tool/source)
- Budget Comparison (pass/fail or missing)
- Regressions/Risks (ordered by impact)
- Suspected Causes (if supported by evidence)
- Suggested Follow-ups

## Notes

- Keep results scoped to the repo's existing tooling and documented expectations.
- Do not introduce new dependencies unless asked.

## Example Commands (only when asked to run)

```bash
# Prefer the repo's scripts; these are examples only.

# Next.js (common patterns)
pnpm run build
pnpm run lint

# If the repo already has these scripts/configs:
pnpm run analyze
pnpm run lighthouse
pnpm run size
```
