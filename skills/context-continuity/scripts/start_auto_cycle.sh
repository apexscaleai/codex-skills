#!/usr/bin/env bash
set -euo pipefail

# Starts context-continuity auto-cycle in watch mode with low-noise defaults.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${CONTEXT_CONTINUITY_REPO:-/Users/leo}"
TOKEN_BUDGET="${CONTEXT_CONTINUITY_BUDGET:-1000}"
INTERVAL_SECONDS="${CONTEXT_CONTINUITY_INTERVAL_SECONDS:-120}"
SNAPSHOT_MIN_SECONDS="${CONTEXT_CONTINUITY_SNAPSHOT_MIN_SECONDS:-1800}"
QUERY="${CONTEXT_CONTINUITY_QUERY:-}"
TASK="${CONTEXT_CONTINUITY_TASK:-}"

mkdir -p "$HOME/.codex/log"

args=(
  --repo "$REPO_ROOT"
  --budget-tokens "$TOKEN_BUDGET"
  --interval-seconds "$INTERVAL_SECONDS"
  --snapshot-min-seconds "$SNAPSHOT_MIN_SECONDS"
  --watch
)

if [[ -n "$QUERY" ]]; then
  args+=(--query "$QUERY")
fi
if [[ -n "$TASK" ]]; then
  args+=(--task "$TASK")
fi

exec /usr/bin/python3 -u "$SCRIPT_DIR/auto_cycle.py" "${args[@]}"
