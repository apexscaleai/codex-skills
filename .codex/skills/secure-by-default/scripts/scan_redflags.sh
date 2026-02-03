#!/usr/bin/env bash
set -euo pipefail

# Quick, dependency-free scan for common security red flags.
# This is heuristic. Always confirm findings with code review.

ROOT="${1:-.}"

echo "scan_root: ${ROOT}"
echo

echo "== Potential Secrets (heuristic) =="
grep -RIn --exclude-dir=node_modules --exclude-dir=.git \
  -E '(sk_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z\\-_]{20,}|-----BEGIN [A-Z ]+ PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\\-]{10,})' \
  "${ROOT}" || true
echo

echo "== Next.js Public Env Vars (review for secrets) =="
grep -RIn --exclude-dir=node_modules --exclude-dir=.git \
  -E 'NEXT_PUBLIC_[A-Z0-9_]+' \
  "${ROOT}" || true
echo

echo "== Dangerous APIs (review context) =="
grep -RIn --exclude-dir=node_modules --exclude-dir=.git \
  -E '\\beval\\s*\\(|\\bnew\\s+Function\\s*\\(|child_process|\\bexec\\s*\\(|\\bspawn\\s*\\(' \
  "${ROOT}" || true
echo

echo "== Possible Open Redirects (review allowlists) =="
grep -RIn --exclude-dir=node_modules --exclude-dir=.git \
  -E '\\bredirect\\s*\\(|\\bNextResponse\\.redirect\\s*\\(' \
  "${ROOT}" || true
echo

echo "== Possible SSRF (review allowlists) =="
grep -RIn --exclude-dir=node_modules --exclude-dir=.git \
  -E '\\bfetch\\s*\\(.*(req\\.|request\\.|params\\.|query\\.|url\\b|href\\b)' \
  "${ROOT}" || true
echo

echo "notes:"
echo "  - This script intentionally produces false positives."
echo "  - Confirm exploitability and blast radius before recommending changes."

