# Infra Optimization Checklist (Evidence-Based)

Fill with `PASS` / `FAIL` / `UNKNOWN` and cite repo evidence (file path, CI job name, etc.).

## CI/CD

- CI configured and runs on PRs (PASS/FAIL/UNKNOWN):
- CI has a clear “required checks” gate (PASS/FAIL/UNKNOWN):
- Dependency caching enabled (pnpm/yarn/npm) (PASS/FAIL/UNKNOWN):
- Build cache enabled (turborepo/next cache/remote cache) (PASS/FAIL/UNKNOWN):
- CI separates lint/typecheck/test/build for parallelism (PASS/FAIL/UNKNOWN):
- Secrets are handled via CI secrets store (no plaintext in repo) (PASS/FAIL/UNKNOWN):
- Deploy is automated (not manual steps only) (PASS/FAIL/UNKNOWN):

## Deploy Safety

- Rollback procedure documented and practical (PASS/FAIL/UNKNOWN):
- Canary/staged rollout exists for web deploys (PASS/FAIL/UNKNOWN):
- Feature flags exist for risky changes (PASS/FAIL/UNKNOWN):
- DB migrations are backward compatible OR have a forward-fix plan (PASS/FAIL/UNKNOWN):

## Next.js Runtime

- Hosting target identified (PASS/FAIL/UNKNOWN):
- Caching strategy defined (CDN / ISR / revalidation) (PASS/FAIL/UNKNOWN):
- Error boundaries and logging for server-side failures (PASS/FAIL/UNKNOWN):
- Security headers configured where appropriate (PASS/FAIL/UNKNOWN):
- Image optimization strategy consistent (PASS/FAIL/UNKNOWN):

## Data Layer

- DB connection pooling strategy appropriate for hosting model (PASS/FAIL/UNKNOWN):
- Query performance basics covered (indexes, N+1 avoidance) (PASS/FAIL/UNKNOWN):
- Read/write timeouts and retries are bounded (PASS/FAIL/UNKNOWN):
- Background jobs/queues are monitored (if present) (PASS/FAIL/UNKNOWN):

## Observability

- Web error tracking (Sentry/Datadog/etc.) (PASS/FAIL/UNKNOWN):
- Mobile crash reporting (PASS/FAIL/UNKNOWN):
- Metrics and alerts exist for key flows (PASS/FAIL/UNKNOWN):
- Logs are structured and searchable (PASS/FAIL/UNKNOWN):

## Cost Controls

- Major cost drivers identified (PASS/FAIL/UNKNOWN):
- Budgets/alerts on spend exist (PASS/FAIL/UNKNOWN):
- CDN enabled for static assets (PASS/FAIL/UNKNOWN):
- Large asset delivery optimized (images/video) (PASS/FAIL/UNKNOWN):

## Mobile Release (React Native)

- Build pipeline documented (PASS/FAIL/UNKNOWN):
- Signing credentials managed securely (PASS/FAIL/UNKNOWN):
- Staged rollout supported (Play Store / TestFlight / EAS) (PASS/FAIL/UNKNOWN):
- Crash-free sessions monitored post-release (PASS/FAIL/UNKNOWN):

