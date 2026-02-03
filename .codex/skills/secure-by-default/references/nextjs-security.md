# Next.js Security Checklist (Practical)

Use this to review Next.js apps for common, high-impact issues. Mark items PASS/FAIL/UNKNOWN and cite evidence.

## Server Boundaries

- API routes / server actions validate input server-side (PASS/FAIL/UNKNOWN):
- Authorization enforced at every server boundary (PASS/FAIL/UNKNOWN):
- Cookie-based auth has CSRF posture (PASS/FAIL/UNKNOWN):

## Secrets

- Secrets are server-only (no `NEXT_PUBLIC_` secrets) (PASS/FAIL/UNKNOWN):
- Server-only SDKs (admin keys) not imported into client components (PASS/FAIL/UNKNOWN):

## Redirects & SSRF

- Redirect targets are allowlisted (PASS/FAIL/UNKNOWN):
- Server-side fetch of user-provided URLs uses allowlists / URL parsing (PASS/FAIL/UNKNOWN):

## Headers (If Applicable)

- Frame protection / clickjacking mitigations present (PASS/FAIL/UNKNOWN):
- HSTS and content-type sniffing protections present (PASS/FAIL/UNKNOWN):
- CSP considered for the app’s threat model (PASS/FAIL/UNKNOWN):

## Abuse Resistance

- Public endpoints have rate limiting or equivalent controls (PASS/FAIL/UNKNOWN):
- Request size/timeouts bounded for expensive operations (PASS/FAIL/UNKNOWN):

