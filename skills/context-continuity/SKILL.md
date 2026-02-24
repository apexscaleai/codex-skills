---
name: context-continuity
description: Maintain high-accuracy continuity across compacted/long conversations by writing durable planning + memory artifacts to a global per-repo store under CODEX_HOME (not into the project). Use for multi-session work, large repos, and cross-file changes where details can get lost.
metadata:
  short-description: Persistent memory across sessions
---

# Context Continuity (Global)

This skill prevents quality loss from chat compaction by keeping an external, durable memory store per repo.

## Where Memory Lives

- Default: `$CODEX_HOME/memory/context-continuity/<repo-id>/`
- If `CODEX_HOME` is unset: `~/.codex/memory/context-continuity/<repo-id>/`

The `<repo-id>` is derived from canonical git repo identity (`git common-dir`), so all worktrees for one repo share the same memory.

## Quick Start

Run from the repo you are working in:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/bootstrap_memory.py"
```

For concurrent Codex agents in the same repo, isolate each session to its own git worktree/branch:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/session_isolation.py" \
  --action ensure --repo . --session-id "${CODEX_THREAD_ID:-}"
# then `cd` to the printed worktree_path before doing git operations
```

Inspect or clean session mappings:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/session_isolation.py" --action list --repo .
python3 "$HOME/.codex/skills/context-continuity/scripts/session_isolation.py" --action prune --repo .
```

Capture atomic events as you work:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/capture_event.py" \
  --kind edit --status success \
  --summary "Patched auth timeout retry path" \
  --path src/auth/client.ts --task auth-timeout-fix
```

Compile a token-budgeted rehydration context before responding after compaction:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/rehydrate.py" \
  --budget-tokens 1800 --query "auth timeout retry"
```

Refresh typed memory signals (paths/tasks/risks/decisions) from events:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/typed_memory.py" --repo .
```

Use context branch/commit/merge ops for explicit continuity checkpoints:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/context_ops.py" --action status --repo .
python3 "$HOME/.codex/skills/context-continuity/scripts/context_ops.py" --action commit --repo . --message "checkpoint before risky refactor"
```

Evaluate rehydration quality (coverage + token utilization pass/fail):

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/eval_context.py" --repo .
```

Verify event-chain integrity periodically:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/verify_memory.py"
```

If strict verify fails due seq/hash-chain drift (for example after interrupted concurrent writers), repair with backup:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/repair_events_chain.py" --repo .
python3 "$HOME/.codex/skills/context-continuity/scripts/verify_memory.py" --repo . --strict
```

Install low-noise Git hook automation (post-commit/post-merge by default):

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/install_git_hooks.py" --repo .
```

Benchmark token efficiency vs coverage and choose a default budget:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/benchmark_rehydrate.py" \
  --repo . --query "current task focus" --record-event
```

Run low-noise automation (works even outside git repos):

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/auto_cycle.py" \
  --repo . --budget-tokens 1200 --watch --interval-seconds 120
```

Install as a persistent macOS LaunchAgent:

```bash
bash "$HOME/.codex/skills/context-continuity/scripts/install_auto_cycle_launchagent.sh"
```

Uninstall the LaunchAgent:

```bash
bash "$HOME/.codex/skills/context-continuity/scripts/uninstall_auto_cycle_launchagent.sh"
```

Create a snapshot at milestones or before/after risky changes:

```bash
python3 "$HOME/.codex/skills/context-continuity/scripts/snapshot.py" --slug "short-label" --note "what changed + why"
```

## Durable Artifacts (What To Write)

Inside the repo's memory directory:

- `PROJECT_MEMORY.md`: stable facts about how the repo works.
- `ACTIVE_TASK.md`: current objective, constraints, key paths, verification commands, status.
- `DECISIONS.md`: ADR-light decisions (date, decision, alternatives, consequences).
- `task-capsules/`: per-task capsules with full-fidelity file paths, symbols, edge cases, and exact commands.
- `snapshots/`: grep-friendly state captures.
- `planning/ACTIVE.md`: small execution checklist.
- `events/events.jsonl`: append-only event log with per-event hash + prev-hash.
- `rehydrated/latest.md`: latest token-budgeted context package for prompt injection.
- `rehydrated/traces/latest-trace.json`: retrieval planner trace (why blocks/events were chosen).
- `rehydrated/evals/latest-eval.json`: pass/fail quality report for current rehydrated context.
- `rehydrated/benchmarks/`: budget-vs-coverage reports and recommended default budget.
- `automation/auto-cycle-state.json`: low-noise automation state/fingerprint cache.
- `automation/session-isolation.json`: session-id -> worktree/branch mapping for multi-agent isolation.
- `typed-memory.json`: compact typed signal layer used by rehydration ranking.
- `context/refs.json` + `context/commits/*.json`: branch/head pointers and context commits.

## Rehydration Workflow (After Compaction / New Session)

1. Run bootstrap (safe/idempotent) to print the memory directory.
2. Run `rehydrate.py --budget-tokens <N>` to compile bounded working context.
3. Read `ACTIVE_TASK.md` and linked capsule only if more detail is needed.
4. Use `rg` in the repo to confirm symbols/paths referenced by the rehydrated context.
5. If needed, generate a fresh snapshot.

## Operating Rules

- Canonical details live in capsules, not in chat.
- Keep `ACTIVE_TASK.md` current: key paths, exact commands, and current status.
- Don't paste huge logs into chat; save them into a capsule/snapshot and reference the file path.
- Keep event capture high-frequency and summary text low-noise.
- Run integrity verification before risky changes or handoff.
- Prefer low-noise automation points (commits/merges) over per-command spam.
