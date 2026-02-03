# React Native Security Checklist (Practical)

Use this to review React Native apps for common, high-impact issues. Mark items PASS/FAIL/UNKNOWN and cite evidence.

## Token & Secret Storage

- Access tokens are not stored in plain AsyncStorage (PASS/FAIL/UNKNOWN):
- Refresh token strategy is well-defined (PASS/FAIL/UNKNOWN):
- No API keys intended to be secret are shipped in the app bundle (PASS/FAIL/UNKNOWN):

## Deep Links

- Deep links are validated and cannot trigger arbitrary navigation/commands (PASS/FAIL/UNKNOWN):
- Link parameters are validated before use (PASS/FAIL/UNKNOWN):

## WebViews (If Present)

- WebView navigation is restricted/allowlisted (PASS/FAIL/UNKNOWN):
- Untrusted content is not granted broad JS/native bridge access (PASS/FAIL/UNKNOWN):

## Network

- TLS is used for all backend calls (PASS/FAIL/UNKNOWN):
- Certificate pinning only if required and implemented safely (PASS/FAIL/UNKNOWN):

## Privacy

- Sensitive screens prevent screenshots if required by policy (PASS/FAIL/UNKNOWN):
- PII is not logged (PASS/FAIL/UNKNOWN):

