# ApexScaleAI Codex Skills

Practical, opinionated skills for shipping production-grade React Native + Next.js apps with high standards for code quality, security, performance, UI/UX, and infrastructure readiness.

## What’s Inside

This repo contains reusable skills under `.codex/skills/`:

- `repo-standards`: formatting/lint/typecheck/test consistency checks
- `perf-profiling`: benchmark/profiling workflow
- `secure-by-default`: security review workflow
- `a11y-review`: accessibility review workflow
- `design-system-enforcer`: design system and token consistency
- `prod-readiness-review`: production readiness checklist
- `infra-optimization`: CI/CD, caching, deploy safety, observability, and cost optimization
- `modern-ui-ux`: modern aesthetics + UX baseline, with checklists and review templates

Each skill follows the same structure:

- `SKILL.md` (required)
- `references/` (checklists, templates)
- `scripts/` (lightweight helpers; no dependencies)
- `assets/` (report templates)

## Use In Codex (Desktop App or CLI)

Codex discovers repo skills automatically when you run Codex from a clone of this repo.

Example prompts:

```text
Use repo-standards to review these changes for PR readiness. Run the repo’s lint/typecheck/test gates if available and report findings with evidence.
```

```text
Use infra-optimization to audit our CI/CD and caching, then propose 5 ROI-ordered improvements with verification and rollback steps.
```

## Optional: Install Globally

To make these skills available across all Codex sessions, copy the skill folders into your Codex skills directory:

- Default on macOS: `~/.codex/skills/`

Example:

```bash
mkdir -p ~/.codex/skills
cp -R .codex/skills/* ~/.codex/skills/
```

## Philosophy (Why These Work Better Than Vague Checklists)

- Evidence-first: discover the repo’s real scripts/configs before recommending changes.
- Actionable output: every finding should include a concrete fix and a verification step.
- Minimal dependencies: helper scripts are intentionally simple and portable.
