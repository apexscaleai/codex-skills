---
name: perf-profiling
description: Run and interpret performance benchmarks for React Native and Next.js, compare against budgets, and summarize regressions.
metadata:
  short-description: Performance profiling
---

# Performance Profiling

Use this skill to find existing performance tooling, run benchmarks if requested, and summarize regressions or risks. Prefer the repo's existing scripts and budgets.

## Workflow

1. Discover existing perf tooling and budgets.
- Search `package.json` scripts for `perf`, `benchmark`, `profile`, `lighthouse`, `bundle`, `analyze`.
- Look for budget/config files (e.g., `lighthouse`, `bundlesize`, `size-limit`, `perf-budget`).
- Check docs under `docs/` for perf guidance.

2. Identify target surface.
- Next.js: build performance, bundle size, route rendering (SSR/SSG/ISR), client JS size.
- React Native: app start time, JS thread frame drops, memory usage, bundle size.

3. Run only what exists and is requested.
- Use the repo's scripts; avoid inventing flags.
- If no scripts exist, propose a minimal plan rather than running ad hoc commands.

4. Compare to budgets or baselines.
- If metrics or budgets are defined, compare current results to those numbers.
- If no budgets exist, call out the missing baseline explicitly.

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
