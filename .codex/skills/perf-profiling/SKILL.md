---
name: perf-profiling
description: Run and interpret performance benchmarks for React Native and Next.js, compare against budgets, and summarize regressions. Use for bundle size, Lighthouse, and runtime profiling checks.
metadata:
  short-description: Performance profiling
---

# Performance Profiling

Use this skill to run the repo’s performance checks (or propose a minimal plan if they don’t exist), compare results to budgets/baselines, and produce an actionable regression summary.

This skill is intentionally strict about “evidence”:
- If you did not measure it, label it as a risk hypothesis.
- If you did measure it, include the exact command and the key output.

## Workflow

1. Discover perf tooling, baselines, and budgets.
- Inspect `package.json` scripts for: `perf`, `benchmark`, `profile`, `lighthouse`, `bundle`, `analyze`, `size`, `stats`.
- Look for tooling/config files:
  - `next.config.*` (bundle/analyze hooks, headers, compression toggles)
  - `lighthouserc.*`, `lighthouse.*`
  - `size-limit.*`, `.size-limit.*`, `bundlesize.*`
  - `webpack.config.*` / analyzer config (if present)
- Check docs under `docs/` (or repo root docs) for perf budgets and release gates.

2. Identify the target surface (pick only what’s relevant).
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

3. Collect metrics (prefer repo scripts, otherwise propose minimal commands).
- Use the repo's scripts; avoid inventing flags or new dependencies.
- If no scripts exist, propose a minimal plan with clear command candidates and expected outputs, but do not run it unless asked.

4. Compare to budgets/baselines.
- If metrics or budgets are defined, compare current results to those numbers.
- If no budgets exist, call out the missing baseline explicitly.

5. Triage regressions (turn numbers into fixes).
- Separate "measurement noise" from real regressions (e.g., CI variance vs consistent deltas).
- Prefer actionable root causes:
  - New dependency / large asset / code path change
  - Unintentional client-side import of server-only code
  - Increased re-rendering due to unstable props/state
  - Missing memoization in list-heavy views (RN)
  - Next.js route accidentally switched from SSG/ISR to SSR
  - Expensive server action / API route missing caching or doing N+1 work

## What “Good” Looks Like (Heuristics)

- Next.js:
  - Avoid pulling large libs into the client for one small feature.
  - Keep per-route client JS growth explainable (new feature weight).
  - Avoid “everything becomes client” migrations (overuse of `use client`).
- React Native:
  - Keep FlatList item renders cheap, stable, and memoized when needed.
  - Avoid decoding huge images on the JS thread.
  - Avoid repeatedly creating functions/objects in render loops if it triggers re-renders.

## Output Format

Provide:
- Metrics Collected (with tool/source)
- Budget Comparison (pass/fail or missing)
- Regressions/Risks (ordered by impact)
- Suspected Causes (if supported by evidence)
- Suggested Follow-ups
 - “Next Action” (the single most valuable fix to try first)

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
