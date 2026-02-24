#!/usr/bin/env python3
"""Shared helpers for the context-continuity scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fcntl


def codex_home() -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".codex"


def sh(repo_root: Path, cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=repo_root, stderr=subprocess.STDOUT)
        return 0, out.decode("utf-8", errors="replace").strip()
    except subprocess.CalledProcessError as e:
        out = (e.output or b"").decode("utf-8", errors="replace").strip()
        return int(e.returncode), out
    except Exception as e:
        return 1, str(e)


def detect_repo_root(start: Path) -> Path:
    code, out = sh(start, ["git", "rev-parse", "--show-toplevel"])
    if code == 0 and out:
        return Path(out).expanduser().resolve()
    return start.resolve()


def _git_common_dir(repo_root: Path) -> Path | None:
    code, out = sh(repo_root, ["git", "rev-parse", "--git-common-dir"])
    if code != 0 or not out.strip():
        return None
    raw = Path(out.strip()).expanduser()
    if not raw.is_absolute():
        raw = (repo_root / raw).resolve()
    else:
        raw = raw.resolve()
    return raw


def canonical_repo_identity_root(repo_root: Path) -> Path:
    """Return a stable repo identity root shared by all git worktrees."""
    common_dir = _git_common_dir(repo_root)
    if common_dir is None:
        return repo_root.resolve()
    # Normal git repos (including linked worktrees) share a common `.git` dir.
    if common_dir.name == ".git":
        return common_dir.parent.resolve()
    # Bare repos and uncommon layouts: use the common dir path itself.
    return common_dir.resolve()


def repo_id(repo_root: Path) -> str:
    identity_root = canonical_repo_identity_root(repo_root)
    key = str(identity_root)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]
    slug = slugify(identity_root.name or repo_root.name or "repo")
    return f"{slug}--{h}"


def memory_root_for_repo(repo_root: Path) -> Path:
    return codex_home() / "memory" / "context-continuity" / repo_id(repo_root)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def stable_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def hash_event(payload_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(payload_without_hash).encode("utf-8")).hexdigest()


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(stable_json(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())


@contextmanager
def event_file_lock(events_path: Path):
    lock_path = events_path.with_name(events_path.name + ".lock")
    ensure_dir(lock_path.parent)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def read_last_jsonl_obj(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last = ""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    if not last:
        return None
    try:
        loaded = json.loads(last)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def approx_tokens(text: str) -> int:
    # Rough estimate: ~4 chars/token for mixed prose/code.
    return max(1, (len(text) + 3) // 4)


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    value = value.strip("-")
    return value or "entry"


def count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def append_event(
    *,
    events_path: Path,
    repo_root: Path,
    repo_id_value: str,
    kind: str,
    status: str,
    summary: str,
    source: str = "manual",
    task: str | None = None,
    paths: list[str] | None = None,
    symbols: list[str] | None = None,
    commands: list[str] | None = None,
    refs: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with event_file_lock(events_path):
        last_event = read_last_jsonl_obj(events_path)
        prev_hash = (
            str(last_event.get("hash"))
            if isinstance(last_event, dict) and last_event.get("hash")
            else ""
        )
        seq = (
            int(last_event.get("seq")) + 1
            if isinstance(last_event, dict) and isinstance(last_event.get("seq"), int)
            else count_nonempty_lines(events_path) + 1
        )

        event_id = (
            f"{utc_now_iso().replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')}"
            f"-{uuid.uuid4().hex[:8]}"
        )

        event_no_hash: dict[str, Any] = {
            "schema": "context-continuity-event-v1",
            "seq": seq,
            "event_id": event_id,
            "timestamp": utc_now_iso(),
            "repo_root": str(repo_root),
            "repo_id": repo_id_value,
            "kind": kind.strip(),
            "status": status.strip(),
            "summary": summary.strip(),
            "source": source.strip(),
            "task": task.strip() if isinstance(task, str) and task.strip() else None,
            "paths": unique_keep_order([p.strip() for p in (paths or []) if p and p.strip()]),
            "symbols": unique_keep_order([s.strip() for s in (symbols or []) if s and s.strip()]),
            "commands": unique_keep_order([c.strip() for c in (commands or []) if c and c.strip()]),
            "refs": unique_keep_order([r.strip() for r in (refs or []) if r and r.strip()]),
            "payload": payload or {},
            "prev_hash": prev_hash or None,
        }
        event_no_hash = {k: v for k, v in event_no_hash.items() if v not in (None, [], {}, "")}
        event_hash = hash_event(event_no_hash)
        event = dict(event_no_hash)
        event["hash"] = event_hash

        append_jsonl(events_path, event)
        return event
