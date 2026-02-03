---
name: infra-optimization
description: Optimize and harden infrastructure for Next.js + React Native projects (CI/CD, caching, build speed, runtime cost, observability, reliability). Use for infra reviews and production cost/perf improvements.
metadata:
  short-description: Infra optimization
---

# Infra Optimization

Use this skill to improve deployment and runtime infrastructure with a bias toward measurable outcomes: faster builds, cheaper runtime, safer deploys, and better observability.

Do not assume an infra stack. Discover what's actually used in the repo first.

## Quick Start

1. Run discovery to map infra surface area: `scripts/discover_infra.py`.
2. Fill the checklist using repo evidence (PASS/FAIL/UNKNOWN): `references/infra-checklist.md`.
3. Propose 3-5 high ROI changes with expected impact and verification steps.

## Workflow (Prescriptive)

1. Discover the infra surface area (evidence-first).
- Look for infra code: `infrastructure/`, `infra/`, `terraform/`, `pulumi/`, `k8s/`, `helm/`, `docker-compose.yml`, `Dockerfile*`.
- Identify hosting targets:
  - Web: Vercel, Netlify, AWS, GCP, self-hosted, containers, serverless, edge.
  - Mobile: build pipelines (Fastlane/EAS), OTA updates, artifact signing, store release flow.
- Identify CI: GitHub Actions, CircleCI, Buildkite, etc.
- Identify observability: Sentry, Datadog, OpenTelemetry, LogRocket, custom logging.

2. Establish current bottlenecks and budgets.
- Build time (CI minutes) and cache hit rate (if available).
- Bundle size and build output size (web + mobile).
- Runtime cost drivers (serverless invocations, DB queries, bandwidth/CDN).
- Reliability risks (no canary, no rollback plan, missing alerts).

3. Apply the checklist.
- Use `references/infra-checklist.md` and mark each item PASS/FAIL/UNKNOWN with links to files.

4. Recommend improvements (ranked).
- Provide a short list ranked by ROI:
  - Expected impact (time/cost/risk)
  - Complexity (low/med/high)
  - Blast radius
  - Verification steps

5. If asked to implement, do it safely.
- Prefer incremental changes (one deploy pipeline/cache change at a time).
- Include a rollback path for infra changes.

## Resources

- Checklist: `references/infra-checklist.md`
- Report template: `assets/infra-optimization-report.md`
- Discovery script: `scripts/discover_infra.py`

