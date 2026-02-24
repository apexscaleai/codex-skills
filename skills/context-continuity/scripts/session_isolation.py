#!/usr/bin/env python3
"""Per-session git worktree isolation for concurrent Codex agents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from memory_store import (
    append_event,
    codex_home,
    detect_repo_root,
    ensure_dir,
    memory_root_for_repo,
    sh,
    slugify,
    stable_json,
    utc_now_iso,
)

SESSION_SCHEMA = "context-continuity-session-isolation-v1"


def _is_git_repo(repo_root: Path) -> bool:
    code, out = sh(repo_root, ["git", "rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip().lower() == "true"


def _git_worktrees(repo_root: Path) -> list[dict[str, Any]]:
    code, out = sh(repo_root, ["git", "worktree", "list", "--porcelain"])
    if code != 0:
        raise RuntimeError(out or "git worktree list failed")

    rows: list[dict[str, Any]] = []
    row: dict[str, Any] = {}
    for raw in (out.splitlines() + [""]):
        line = raw.strip()
        if not line:
            if row:
                rows.append(row)
                row = {}
            continue
        key, _space, value = line.partition(" ")
        value = value.strip()
        if key == "worktree":
            row["worktree_path"] = value
        elif key == "branch":
            row["branch_ref"] = value
            row["branch"] = value.removeprefix("refs/heads/")
        elif key == "HEAD":
            row["head"] = value
        elif key == "detached":
            row["detached"] = True
        elif key == "locked":
            row["locked"] = True
    return rows


def _worktree_indexes(repo_root: Path) -> tuple[dict[Path, dict[str, Any]], dict[str, Path]]:
    by_path: dict[Path, dict[str, Any]] = {}
    by_branch: dict[str, Path] = {}
    for row in _git_worktrees(repo_root):
        raw_path = str(row.get("worktree_path") or "").strip()
        if not raw_path:
            continue
        p = Path(raw_path).expanduser().resolve()
        by_path[p] = row
        branch = str(row.get("branch") or "").strip()
        if branch:
            by_branch[branch] = p
    return by_path, by_branch


def _branch_exists(repo_root: Path, branch: str) -> bool:
    code, _out = sh(repo_root, ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return code == 0


def _resolve_base_ref(repo_root: Path, explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    code, out = sh(repo_root, ["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
    if code == 0 and out.strip():
        return out.strip()
    code, out = sh(repo_root, ["git", "rev-parse", "HEAD"])
    if code == 0 and out.strip():
        return out.strip()
    raise RuntimeError("Unable to resolve base ref (pass --base-ref explicitly).")


def _normalize_branch_prefix(prefix: str) -> str:
    parts = [slugify(part) for part in prefix.split("/") if part.strip()]
    filtered = [part for part in parts if part and part != "-"]
    if not filtered:
        return "codex/session"
    return "/".join(filtered)


def _session_id(explicit: str) -> tuple[str, str]:
    raw = explicit.strip()
    if raw:
        return raw, "arg:session-id"

    env_order = [
        "CODEX_THREAD_ID",
        "CODEX_SESSION_ID",
        "SESSION_ID",
        "ITERM_SESSION_ID",
        "TERM_SESSION_ID",
    ]
    for key in env_order:
        value = os.environ.get(key, "").strip()
        if value:
            return value, f"env:{key}"

    fallback = (
        f"manual-{utc_now_iso().replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')}"
        f"-{uuid.uuid4().hex[:8]}"
    )
    return fallback, "generated"


def _session_slug(session_id: str) -> str:
    base = slugify(session_id.lower())
    if len(base) <= 48:
        return base
    digest = hashlib.sha1(session_id.encode("utf-8")).hexdigest()[:10]
    return f"{base[:36]}-{digest}"


def _branch_name(prefix: str, session_slug: str) -> str:
    merged = f"{prefix}/{session_slug}"
    if len(merged) <= 120:
        return merged
    digest = hashlib.sha1(merged.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}/{session_slug[:80]}-{digest}"


def _mapping_path(mem_root: Path) -> Path:
    return mem_root / "automation" / "session-isolation.json"


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_mapping(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_iso8601(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _render_json(obj: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in obj.items():
        print(f"{key}: {value}")


def _ensure_session(
    *,
    repo_root: Path,
    mem_root: Path,
    args: argparse.Namespace,
) -> tuple[int, dict[str, Any]]:
    if not _is_git_repo(repo_root):
        return 2, {
            "status": "failed",
            "reason": "not-a-git-repo",
            "repo_root": str(repo_root),
        }

    session_id, session_source = _session_id(args.session_id)
    session_slug = _session_slug(session_id)
    branch_prefix = _normalize_branch_prefix(args.branch_prefix)
    branch = _branch_name(branch_prefix, session_slug)
    base_ref = _resolve_base_ref(repo_root, args.base_ref)

    root_override = args.worktrees_root.strip()
    if root_override:
        worktrees_root = Path(root_override).expanduser().resolve()
    else:
        worktrees_root = (codex_home() / "worktrees" / "context-continuity" / mem_root.name).resolve()

    target_worktree = (worktrees_root / session_slug).resolve()

    mapping_file = _mapping_path(mem_root)
    mapping = _load_mapping(mapping_file)
    sessions = mapping.get("sessions") if isinstance(mapping.get("sessions"), dict) else {}
    previous = sessions.get(session_id) if isinstance(sessions.get(session_id), dict) else {}

    if previous:
        prev_branch = str(previous.get("branch") or "").strip()
        prev_path = str(previous.get("worktree_path") or "").strip()
        if prev_branch:
            branch = prev_branch
        if prev_path:
            target_worktree = Path(prev_path).expanduser().resolve()

    by_path, by_branch = _worktree_indexes(repo_root)

    created_branch = False
    created_worktree = False

    branch_path = by_branch.get(branch)
    if branch_path:
        final_worktree = branch_path
    else:
        existing = by_path.get(target_worktree)
        if existing:
            existing_branch = str(existing.get("branch") or "").strip()
            if existing_branch and existing_branch != branch:
                return 2, {
                    "status": "failed",
                    "reason": "worktree-path-occupied",
                    "repo_root": str(repo_root),
                    "session_id": session_id,
                    "session_slug": session_slug,
                    "target_worktree": str(target_worktree),
                    "expected_branch": branch,
                    "found_branch": existing_branch,
                }
            final_worktree = target_worktree
        else:
            ensure_dir(target_worktree.parent)
            if target_worktree.exists() and not target_worktree.is_dir():
                return 2, {
                    "status": "failed",
                    "reason": "target-path-not-directory",
                    "target_worktree": str(target_worktree),
                }
            if target_worktree.exists() and any(target_worktree.iterdir()):
                return 2, {
                    "status": "failed",
                    "reason": "target-directory-not-empty",
                    "target_worktree": str(target_worktree),
                }

            if _branch_exists(repo_root, branch):
                code, out = sh(repo_root, ["git", "worktree", "add", str(target_worktree), branch])
            else:
                code, out = sh(
                    repo_root,
                    ["git", "worktree", "add", "-b", branch, str(target_worktree), base_ref],
                )
                created_branch = code == 0

            if code != 0:
                return 2, {
                    "status": "failed",
                    "reason": "git-worktree-add-failed",
                    "repo_root": str(repo_root),
                    "target_worktree": str(target_worktree),
                    "branch": branch,
                    "git_output": out,
                }

            created_worktree = True
            final_worktree = target_worktree

    sessions[session_id] = {
        "session_id": session_id,
        "session_source": session_source,
        "session_slug": session_slug,
        "branch": branch,
        "worktree_path": str(final_worktree),
        "base_ref": base_ref,
        "created_at": str(previous.get("created_at") or utc_now_iso()),
        "last_seen_at": utc_now_iso(),
    }

    mapping_payload = {
        "schema": SESSION_SCHEMA,
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "updated_at": utc_now_iso(),
        "sessions": sessions,
    }
    _save_mapping(mapping_file, mapping_payload)

    topology_changed = (
        not previous
        or str(previous.get("branch") or "") != branch
        or str(previous.get("worktree_path") or "") != str(final_worktree)
    )
    should_record = (
        args.record_event == "always"
        or (
            args.record_event == "on-change"
            and (created_branch or created_worktree or topology_changed)
        )
    )

    if should_record:
        if created_worktree:
            summary = f"session isolation created worktree {final_worktree.name} on {branch}"
        elif topology_changed:
            summary = f"session isolation remapped session {session_slug} to existing worktree"
        else:
            summary = f"session isolation verified existing worktree for {session_slug}"
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="session-isolation",
            status="success",
            summary=summary,
            source="session-isolation",
            task="session-isolation",
            paths=[str(final_worktree)],
            payload={
                "session_id": session_id,
                "session_source": session_source,
                "session_slug": session_slug,
                "branch": branch,
                "worktree_path": str(final_worktree),
                "created_branch": created_branch,
                "created_worktree": created_worktree,
            },
        )

    payload = {
        "status": "ok",
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "mapping_file": str(mapping_file),
        "session_id": session_id,
        "session_source": session_source,
        "session_slug": session_slug,
        "branch": branch,
        "worktree_path": str(final_worktree),
        "created_branch": created_branch,
        "created_worktree": created_worktree,
        "switch_command": f"cd {final_worktree}",
    }
    return 0, payload


def _list_sessions(
    *,
    repo_root: Path,
    mem_root: Path,
    as_json: bool,
) -> tuple[int, dict[str, Any]]:
    mapping_file = _mapping_path(mem_root)
    mapping = _load_mapping(mapping_file)
    sessions = mapping.get("sessions") if isinstance(mapping.get("sessions"), dict) else {}

    by_path, _by_branch = ({}, {})
    if _is_git_repo(repo_root):
        by_path, _by_branch = _worktree_indexes(repo_root)

    rows: list[dict[str, Any]] = []
    for session_id in sorted(sessions.keys()):
        row = sessions.get(session_id)
        if not isinstance(row, dict):
            continue
        worktree_path = Path(str(row.get("worktree_path") or "")).expanduser()
        resolved = worktree_path.resolve() if str(worktree_path) else worktree_path
        active_branch = ""
        active = False
        if resolved and resolved in by_path:
            active = True
            active_branch = str(by_path[resolved].get("branch") or "")
        rows.append(
            {
                "session_id": session_id,
                "session_slug": str(row.get("session_slug") or ""),
                "branch": str(row.get("branch") or ""),
                "worktree_path": str(worktree_path),
                "exists": worktree_path.exists() if str(worktree_path) else False,
                "active_in_git": active,
                "active_branch": active_branch,
                "last_seen_at": str(row.get("last_seen_at") or ""),
            }
        )

    payload = {
        "status": "ok",
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "mapping_file": str(mapping_file),
        "session_count": len(rows),
        "sessions": rows,
    }

    if not as_json:
        print(f"repo_root: {repo_root}")
        print(f"memory_root: {mem_root}")
        print(f"mapping_file: {mapping_file}")
        print(f"session_count: {len(rows)}")
        for row in rows:
            print(
                "- "
                + stable_json(
                    {
                        "session_id": row["session_id"],
                        "branch": row["branch"],
                        "worktree_path": row["worktree_path"],
                        "exists": row["exists"],
                        "active_in_git": row["active_in_git"],
                    }
                )
            )
    return 0, payload


def _path_for_session(*, repo_root: Path, mem_root: Path, args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    _code, payload = _list_sessions(repo_root=repo_root, mem_root=mem_root, as_json=True)
    session_id, _source = _session_id(args.session_id)

    for row in payload.get("sessions") or []:
        if str(row.get("session_id") or "") == session_id:
            result = {
                "status": "ok",
                "session_id": session_id,
                "worktree_path": str(row.get("worktree_path") or ""),
                "branch": str(row.get("branch") or ""),
            }
            return 0, result

    if args.strict:
        return 2, {
            "status": "failed",
            "reason": "session-not-found",
            "session_id": session_id,
        }
    return 0, {"status": "ok", "session_id": session_id, "worktree_path": "", "branch": ""}


def _prune_sessions(
    *,
    repo_root: Path,
    mem_root: Path,
    stale_days: int,
    record_event: str,
) -> tuple[int, dict[str, Any]]:
    if not _is_git_repo(repo_root):
        return 2, {
            "status": "failed",
            "reason": "not-a-git-repo",
            "repo_root": str(repo_root),
        }

    sh(repo_root, ["git", "worktree", "prune"])
    by_path, _by_branch = _worktree_indexes(repo_root)

    mapping_file = _mapping_path(mem_root)
    mapping = _load_mapping(mapping_file)
    sessions = mapping.get("sessions") if isinstance(mapping.get("sessions"), dict) else {}

    now = datetime.now(timezone.utc)
    deadline = now - timedelta(days=max(0, stale_days))
    removed: list[dict[str, str]] = []

    kept: dict[str, Any] = {}
    for session_id, row in sessions.items():
        if not isinstance(row, dict):
            continue
        path_text = str(row.get("worktree_path") or "").strip()
        worktree_path = Path(path_text).expanduser().resolve() if path_text else None

        should_drop = False
        if not worktree_path or worktree_path not in by_path:
            should_drop = True

        if stale_days > 0 and not should_drop:
            last_seen_raw = str(row.get("last_seen_at") or "")
            last_seen = _parse_iso8601(last_seen_raw)
            if last_seen and last_seen < deadline:
                should_drop = True

        if should_drop:
            removed.append(
                {
                    "session_id": session_id,
                    "branch": str(row.get("branch") or ""),
                    "worktree_path": str(row.get("worktree_path") or ""),
                }
            )
            continue

        kept[session_id] = row

    mapping_payload = {
        "schema": SESSION_SCHEMA,
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "updated_at": utc_now_iso(),
        "sessions": kept,
    }
    _save_mapping(mapping_file, mapping_payload)

    if removed and record_event in {"always", "on-change"}:
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="session-isolation",
            status="info",
            summary=f"session isolation pruned {len(removed)} stale session mappings",
            source="session-isolation",
            task="session-isolation",
            payload={"removed": removed, "stale_days": stale_days},
        )

    return 0, {
        "status": "ok",
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "mapping_file": str(mapping_file),
        "removed_count": len(removed),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--action",
        default="ensure",
        choices=["ensure", "path", "list", "prune"],
        help="Operation to run.",
    )
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument("--session-id", default="", help="Explicit session id (defaults to CODEX_THREAD_ID).")
    ap.add_argument(
        "--branch-prefix",
        default="codex/session",
        help="Branch prefix for generated per-session branches.",
    )
    ap.add_argument(
        "--base-ref",
        default="",
        help="Base ref when creating a new session branch (default: current HEAD branch/commit).",
    )
    ap.add_argument(
        "--worktrees-root",
        default="",
        help="Optional root directory for per-session worktrees.",
    )
    ap.add_argument(
        "--record-event",
        default="on-change",
        choices=["off", "on-change", "always"],
        help="Write continuity event entries for isolation operations.",
    )
    ap.add_argument(
        "--stale-days",
        default=0,
        type=int,
        help="With --action prune, remove session mappings older than N days.",
    )
    ap.add_argument("--strict", action="store_true", help="With --action path, fail if session is missing.")
    ap.add_argument("--json", action="store_true", help="Print JSON output.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)

    if args.action == "ensure":
        code, payload = _ensure_session(repo_root=repo_root, mem_root=mem_root, args=args)
    elif args.action == "path":
        code, payload = _path_for_session(repo_root=repo_root, mem_root=mem_root, args=args)
    elif args.action == "list":
        code, payload = _list_sessions(repo_root=repo_root, mem_root=mem_root, as_json=args.json)
        if not args.json:
            raise SystemExit(code)
    else:
        code, payload = _prune_sessions(
            repo_root=repo_root,
            mem_root=mem_root,
            stale_days=args.stale_days,
            record_event=args.record_event,
        )

    _render_json(payload, args.json)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
