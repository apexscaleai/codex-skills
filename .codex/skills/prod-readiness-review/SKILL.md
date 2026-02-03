---
name: prod-readiness-review
description: Check production readiness (rollback, monitoring, SLOs, runbooks, load tests, config sanity, migrations) for React Native + Next.js. Use to gate releases and reduce incident risk.
metadata:
  short-description: Production readiness review
---

# Production Readiness Review

Use this skill to assess release readiness for web and mobile apps with a focus on operational safety. Follow any repo-specific release checklists if present.

## Workflow

1. Identify release artifacts and deployment paths.
- Next.js: build outputs, hosting target, environment config.
- React Native: build pipelines, store release steps, OTA updates.

2. Verify operational readiness.
- Monitoring: logs, metrics, traces, crash reporting (web + mobile).
- Alerting: on-call notifications and severity thresholds.
- Runbooks: incident response and rollback steps.
- SLOs: performance or availability targets.

3. Validate data and config safety.
- Environment variables and secrets are managed securely.
- Feature flags for risky changes.
- Migration safety: backward compatibility and rollback plan.
- Config sanity: required env vars documented, safe defaults, non-prod vs prod behavior is explicit.

4. Check release quality gates.
- CI is green and required tests are present.
- Smoke tests or canary plans exist.
- Versioning and changelog practices are followed.
- For mobile: build numbers/versions incremented; release notes; staged rollout plan if supported.
- For web: cache invalidation strategy (CDN/ISR), and safe deploy order if multiple services.

5. Confirm "break-glass" and recovery.
- Rollback is documented and practical (not theoretical).
- If migrations exist, confirm a rollback or forward-fix plan exists.
- Verify incident owner/on-call path exists (even if lightweight).

## Output Format

Provide:
- Readiness Checklist (pass/fail/unknown)
- Blockers (must fix before release)
- Risks (acceptable with mitigation)
- Recommended Next Steps

## Notes

- Do not invent a release process; use repo evidence.
- If key artifacts are missing, call them out explicitly.
