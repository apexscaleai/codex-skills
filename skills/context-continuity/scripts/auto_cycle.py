#!/usr/bin/env python3
"""Automatic low-noise continuity cycle runner (works in git and non-git workspaces)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import (
    append_event,
    detect_repo_root,
    memory_root_for_repo,
    sh,
    stable_json,
)


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return cp.returncode, cp.stdout.strip(), cp.stderr.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git_state(repo_root: Path) -> dict[str, str]:
    code, inside = sh(repo_root, ["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0 or inside.strip().lower() != "true":
        return {"git_enabled": "false"}
    _code, head = sh(repo_root, ["git", "rev-parse", "HEAD"])
    _code, branch = sh(repo_root, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    _code, status = sh(repo_root, ["git", "status", "--porcelain=v1"])
    return {
        "git_enabled": "true",
        "git_head": head,
        "git_branch": branch,
        "git_status_hash": sha256_text(status),
    }


def last_material_event_signature(mem_root: Path) -> tuple[str, str]:
    """Return (hash, seq) for the latest non-auto-cycle event."""
    events_path = mem_root / "events" / "events.jsonl"
    if not events_path.exists():
        return "", ""

    last_hash = ""
    last_seq = ""
    with events_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if str(event.get("source") or "") == "auto-cycle":
                continue
            ev_hash = str(event.get("hash") or "")
            ev_seq = event.get("seq")
            last_hash = ev_hash
            last_seq = str(ev_seq) if isinstance(ev_seq, int) else ""
    return last_hash, last_seq


def fingerprint(repo_root: Path, mem_root: Path, budget_tokens: int, query: str, task: str) -> dict[str, str]:
    active_task = read_text(mem_root / "ACTIVE_TASK.md")
    decisions = read_text(mem_root / "DECISIONS.md")
    project_memory = read_text(mem_root / "PROJECT_MEMORY.md")
    typed_memory = read_text(mem_root / "typed-memory.json")
    event_hash, event_seq = last_material_event_signature(mem_root)

    base = {
        "repo_root": str(repo_root),
        "active_task_hash": sha256_text(active_task),
        "decisions_hash": sha256_text(decisions),
        "project_memory_hash": sha256_text(project_memory),
        "typed_memory_hash": sha256_text(typed_memory),
        "event_hash": event_hash,
        "event_seq": event_seq,
        "budget_tokens": str(budget_tokens),
        "query": query.strip(),
        "task": task.strip(),
    }
    base.update(git_state(repo_root))
    base["fingerprint"] = sha256_text(stable_json(base))
    return base


def run_cycle(
    *,
    repo_root: Path,
    mem_root: Path,
    scripts_dir: Path,
    budget_tokens: int,
    query: str,
    task: str,
    snapshot_min_seconds: int,
    state_path: Path,
    force: bool,
) -> tuple[bool, str]:
    # Ensure root memory structure exists.
    rc, out, err = run_cmd(
        ["python3", str(scripts_dir / "bootstrap_memory.py"), "--repo", str(repo_root)]
    )
    if rc != 0:
        return False, f"bootstrap failed: {err or out}"

    fp = fingerprint(repo_root, mem_root, budget_tokens, query, task)
    state = load_state(state_path)
    prev_fp = str(state.get("fingerprint") or "")
    changed = force or (fp.get("fingerprint") != prev_fp)

    # Verify integrity every cycle.
    v_rc, v_out, v_err = run_cmd(
        ["python3", str(scripts_dir / "verify_memory.py"), "--repo", str(repo_root), "--strict"]
    )
    if v_rc != 0:
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="automation",
            status="warning",
            summary="auto-cycle detected verify_memory failure",
            source="auto-cycle",
            task=task or "auto-cycle",
            payload={"verify_stdout": v_out, "verify_stderr": v_err},
        )
        return False, "verify_memory strict failed"

    if not changed:
        state["last_run_at"] = utc_now_iso()
        save_state(state_path, state)
        return True, "no state change; skipped rehydrate/snapshot"

    t_rc, t_out, t_err = run_cmd(
        [
            "python3",
            str(scripts_dir / "typed_memory.py"),
            "--repo",
            str(repo_root),
            "--record-event",
            "off",
        ]
    )
    if t_rc != 0:
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="automation",
            status="warning",
            summary="auto-cycle failed during typed-memory refresh",
            source="auto-cycle",
            task=task or "auto-cycle",
            payload={"typed_memory_stdout": t_out, "typed_memory_stderr": t_err},
        )
        return False, "typed-memory refresh failed"

    r_cmd = [
        "python3",
        str(scripts_dir / "rehydrate.py"),
        "--repo",
        str(repo_root),
        "--budget-tokens",
        str(budget_tokens),
    ]
    if query.strip():
        r_cmd.extend(["--query", query.strip()])
    if task.strip():
        r_cmd.extend(["--task", task.strip()])

    r_rc, r_out, r_err = run_cmd(r_cmd)
    if r_rc != 0:
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="automation",
            status="failure",
            summary="auto-cycle failed during rehydrate",
            source="auto-cycle",
            task=task or "auto-cycle",
            payload={"rehydrate_stdout": r_out, "rehydrate_stderr": r_err},
        )
        return False, "rehydrate failed"

    now_ts = int(time.time())
    last_snapshot_ts = int(state.get("last_snapshot_ts") or 0)
    took_snapshot = False
    if now_ts - last_snapshot_ts >= snapshot_min_seconds:
        s_cmd = [
            "python3",
            str(scripts_dir / "snapshot.py"),
            "--repo",
            str(repo_root),
            "--slug",
            "auto-cycle",
            "--note",
            "Automated snapshot after continuity state change",
        ]
        s_rc, s_out, s_err = run_cmd(s_cmd)
        if s_rc == 0:
            took_snapshot = True
            state["last_snapshot_path"] = s_out
            state["last_snapshot_ts"] = now_ts
        else:
            append_event(
                events_path=mem_root / "events" / "events.jsonl",
                repo_root=repo_root,
                repo_id_value=mem_root.name,
                kind="automation",
                status="warning",
                summary="auto-cycle snapshot failed",
                source="auto-cycle",
                task=task or "auto-cycle",
                payload={"snapshot_stdout": s_out, "snapshot_stderr": s_err},
            )

    append_event(
        events_path=mem_root / "events" / "events.jsonl",
        repo_root=repo_root,
        repo_id_value=mem_root.name,
        kind="automation",
        status="success",
        summary=(
            f"auto-cycle refreshed rehydrated context (budget {budget_tokens})"
            + (" + snapshot" if took_snapshot else "")
        ),
        source="auto-cycle",
        task=task or "auto-cycle",
        payload={
            "budget_tokens": budget_tokens,
            "query": query.strip(),
            "task": task.strip(),
            "snapshot_taken": took_snapshot,
        },
    )

    state.update(fp)
    state["last_run_at"] = utc_now_iso()
    save_state(state_path, state)
    return True, "updated rehydrated context"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo/workspace directory (defaults to cwd).")
    ap.add_argument("--budget-tokens", default=1200, type=int, help="Rehydrate token budget.")
    ap.add_argument("--query", default="", help="Optional rehydrate query.")
    ap.add_argument("--task", default="", help="Optional task key.")
    ap.add_argument(
        "--snapshot-min-seconds",
        default=1800,
        type=int,
        help="Minimum seconds between auto snapshots to prevent noise.",
    )
    ap.add_argument(
        "--interval-seconds",
        default=120,
        type=int,
        help="Loop interval when --watch is used.",
    )
    ap.add_argument("--watch", action="store_true", help="Run continuously until interrupted.")
    ap.add_argument("--force", action="store_true", help="Run cycle even if fingerprint unchanged.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    scripts_dir = Path(__file__).resolve().parent
    state_path = mem_root / "automation" / "auto-cycle-state.json"

    if not args.watch:
        ok, msg = run_cycle(
            repo_root=repo_root,
            mem_root=mem_root,
            scripts_dir=scripts_dir,
            budget_tokens=args.budget_tokens,
            query=args.query,
            task=args.task,
            snapshot_min_seconds=args.snapshot_min_seconds,
            state_path=state_path,
            force=args.force,
        )
        print(f"repo_root: {repo_root}")
        print(f"memory_root: {mem_root}")
        print(f"state_file: {state_path}")
        print(f"status: {'ok' if ok else 'failed'}")
        print(f"message: {msg}")
        raise SystemExit(0 if ok else 2)

    print(f"[auto-cycle] repo_root={repo_root}")
    print(f"[auto-cycle] memory_root={mem_root}")
    print(f"[auto-cycle] state_file={state_path}")
    print(f"[auto-cycle] interval_seconds={args.interval_seconds}")
    while True:
        ok, msg = run_cycle(
            repo_root=repo_root,
            mem_root=mem_root,
            scripts_dir=scripts_dir,
            budget_tokens=args.budget_tokens,
            query=args.query,
            task=args.task,
            snapshot_min_seconds=args.snapshot_min_seconds,
            state_path=state_path,
            force=args.force,
        )
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"[auto-cycle] {stamp} status={'ok' if ok else 'failed'} msg={msg}")
        time.sleep(max(5, args.interval_seconds))


if __name__ == "__main__":
    main()
