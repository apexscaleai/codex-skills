---
name: secure-by-default
description: Check for common vulnerabilities and enforce safe patterns in React Native and Next.js apps.
metadata:
  short-description: Secure-by-default review
---

# Secure-by-Default

Use this skill to review security posture for React Native and Next.js codebases. Focus on practical, high-signal issues and align with existing repo patterns.

## Workflow

1. Identify entry points and trust boundaries.
- Next.js: API routes, server actions, middleware, auth flows, data fetching.
- React Native: network calls, deep links, local storage, push notification handlers.

2. Check common risk areas.
- Auth: session handling, token storage, cookie flags, logout/invalidation.
- Input validation: server-side validation, schema checks, SSR inputs.
- Data exposure: logging PII, client-side secrets, overbroad API responses.
- Injection: SQL/NoSQL, SSRF, command execution, unsafe `eval`.
- Transport: HTTPS-only endpoints, TLS assumptions.

3. Dependency and configuration review (if tooling exists).
- Look for existing `audit` or security scan scripts.
- Report outdated or vulnerable dependencies only if scan data exists.

4. React Native specific checks.
- Avoid storing tokens in `AsyncStorage`; prefer secure storage libraries.
- Ensure deep links are validated.
- Confirm sensitive screens prevent screenshots if required by policy.

5. Next.js specific checks.
- Verify security headers (CSP, HSTS, X-Frame-Options) if configured.
- Ensure server actions/API routes validate input and enforce auth.

## Output Format

Provide:
- Findings (severity: High/Medium/Low)
- Evidence (file references)
- Recommended Fixes (minimal, aligned to repo patterns)
- Follow-up Checks (if tooling or docs are missing)

## Notes

- Do not introduce new dependencies unless asked.
- If a security policy exists in the repo, follow it.
