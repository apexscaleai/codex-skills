# ApexScaleAI Codex Skills

This repo contains reusable Codex skills under `.codex/skills/` for:

- `repo-standards`: formatting/lint/typecheck/test consistency checks
- `perf-profiling`: benchmark/profiling workflow
- `secure-by-default`: security review workflow
- `a11y-review`: accessibility review workflow
- `design-system-enforcer`: design system and token consistency
- `prod-readiness-review`: production readiness checklist

## Use In Codex (App or CLI)

Codex will automatically discover repo skills when you run it from a clone of this repo.

## Optional: Install Globally

To make these skills available across all Codex sessions, copy the folders into your `$CODEX_HOME/skills` directory (often `~/.codex/skills`).
