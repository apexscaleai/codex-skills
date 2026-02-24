#!/usr/bin/env python3
"""Create/print a global per-repo memory store for continuity across sessions.

This intentionally does NOT write to the repo. It writes to:
  $CODEX_HOME/memory/context-continuity/<repo-id>/

Run from the repo root (or any subdir). It's idempotent.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from memory_store import detect_repo_root, ensure_dir, memory_root_for_repo
from memory_store import canonical_repo_identity_root
from memory_store import sh


@dataclass(frozen=True)
class CreateResult:
    path: Path
    created: bool


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_file(path: Path, content: str) -> CreateResult:
    if path.exists():
        return CreateResult(path=path, created=False)
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    return CreateResult(path=path, created=True)


PROJECT_MEMORY = """# Project Memory (Durable)

Keep this small and stable. Facts that should remain true across many tasks.

## Repo

- Purpose:
- Primary packages/apps:

## Architecture

- Data flow:
- Key services:
- Invariants:

## Conventions

- Naming:
- Testing:
- Tooling:

## Canonical Commands

```bash
# Fill in: dev/lint/typecheck/test/build
```
"""


ACTIVE_TASK = """# Active Task

This is the fastest rehydration entrypoint after chat compaction.

## Current Capsule

- Capsule: task-capsules/YYYY-MM-DD--slug.md

## Objective

- ...

## Acceptance Criteria

- [ ] ...

## Constraints / Non-Goals

- ...

## Key Paths

- ...

## Commands / Verification

```bash
# Exact commands + results
```

## Current Status

- Next step:
- Blockers:
- Notes:
"""


DECISIONS = """# Decisions (ADR-Light)

Each entry: date, decision, alternatives, consequences.

## Template

### YYYY-MM-DD: <Title>

- Context:
- Decision:
- Alternatives:
- Consequences:
"""


PLANNING_ACTIVE = """# Active Plan

Keep this small. Execution checklist for the current task.

## Plan

- [ ] Update ACTIVE_TASK.md + capsule
- [ ] Implement changes
- [ ] Run verification commands
- [ ] Record decisions
- [ ] Snapshot at milestones
- [ ] Verify memory integrity
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo",
        default=".",
        help="Repo directory to key memory by (defaults to cwd; git toplevel is used if present).",
    )
    args = ap.parse_args()

    start = Path(args.repo).expanduser()
    repo_root = detect_repo_root(start)
    repo_identity_root = canonical_repo_identity_root(repo_root)
    root = memory_root_for_repo(repo_root)

    ensure_dir(root / "task-capsules")
    ensure_dir(root / "snapshots")
    ensure_dir(root / "planning")
    ensure_dir(root / "events")
    ensure_dir(root / "rehydrated")
    ensure_dir(root / "rehydrated" / "benchmarks")
    ensure_dir(root / "automation")

    results: list[CreateResult] = []
    results.append(ensure_file(root / "PROJECT_MEMORY.md", PROJECT_MEMORY))
    results.append(ensure_file(root / "ACTIVE_TASK.md", ACTIVE_TASK))
    results.append(ensure_file(root / "DECISIONS.md", DECISIONS))
    results.append(ensure_file(root / "planning" / "ACTIVE.md", PLANNING_ACTIVE))
    results.append(
        ensure_file(
            root / "REPO_POINTER.txt",
            f"repo_root: {repo_root}\nrepo_identity_root: {repo_identity_root}\n",
        )
    )
    results.append(
        ensure_file(
            root / "events" / "events.jsonl",
            "",
        )
    )

    created = [r.path for r in results if r.created]

    print(f"repo_root: {repo_root}")
    print(f"repo_identity_root: {repo_identity_root}")
    print(f"memory_root: {root}")
    if created:
        print("created:")
        for p in created:
            print(f"  - {p}")
    code, inside = sh(repo_root, ["git", "rev-parse", "--is-inside-work-tree"])
    if os.environ.get("CODEX_THREAD_ID", "").strip() and code == 0 and inside.strip().lower() == "true":
        session_script = (Path(__file__).resolve().parent / "session_isolation.py").resolve()
        print("session_isolation_hint:")
        print(
            "  "
            + f"python3 {session_script} --action ensure --repo {repo_root} "
            + '--session-id "${CODEX_THREAD_ID:-}"'
        )


if __name__ == "__main__":
    main()
