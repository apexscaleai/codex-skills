---
name: secure-by-default
description: Check for common vulnerabilities and enforce safe patterns in React Native and Next.js apps. Use for auth, input validation, secrets handling, and dependency scanning workflows.
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
- Auth:
  - session handling, token storage, cookie flags, logout/invalidation
  - authorization checks at every server boundary (not just UI gating)
  - CSRF posture for cookie-based auth (Next.js forms/actions/APIs)
- Input validation:
  - server-side validation for API routes/server actions
  - schema validation for externally supplied data
  - strict allowlists for enums and identifiers
- Data exposure:
  - logging PII/tokens, leaking stack traces, returning overbroad objects
  - client-side secrets (API keys, service credentials) accidentally bundled
- Injection:
  - SQL/NoSQL injection, unsafe query building
  - SSRF (fetching user-controlled URLs on the server)
  - command execution, unsafe `eval`/`Function`/dynamic imports
- Transport:
  - HTTPS-only assumptions, insecure redirects, mixed content
  - certificate pinning only if the repo already uses it (mobile)
- Abuse resistance:
  - missing rate limiting on public endpoints
  - missing request size limits/timeouts for expensive operations

3. Dependency and configuration review (if tooling exists).
- Look for existing `audit` or security scan scripts.
- Report outdated or vulnerable dependencies only if scan data exists.
- Prefer `pnpm audit` / `npm audit` / `yarn npm audit` only when already used by the repo.

4. React Native specific checks.
- Avoid storing tokens in `AsyncStorage`; prefer secure storage libraries.
- Ensure deep links are validated and routed safely (no arbitrary URL execution).
- Confirm sensitive screens prevent screenshots/screen recording if required by policy.
- Confirm TLS is used for all network calls; avoid custom trust managers unless required and audited.

5. Next.js specific checks.
- Verify security headers (CSP, HSTS, frame protection, content-type sniffing) if configured.
- Ensure server actions/API routes validate input and enforce auth.
- Ensure server-only code is not imported into client bundles (secrets, admin SDKs).
- Ensure environment variables follow Next.js conventions (`NEXT_PUBLIC_` only for non-secrets).

## Output Format

Provide:
- Findings (severity: High/Medium/Low)
- Evidence (file references)
- Recommended Fixes (minimal, aligned to repo patterns)
- Follow-up Checks (if tooling or docs are missing)

## Notes

- Do not introduce new dependencies unless asked.
- If a security policy exists in the repo, follow it.
