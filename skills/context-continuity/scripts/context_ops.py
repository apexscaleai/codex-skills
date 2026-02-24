#!/usr/bin/env python3
"""Git-style branch/commit/merge operations for continuity memory state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from memory_store import append_event, detect_repo_root, ensure_dir, memory_root_for_repo, stable_json, utc_now_iso

CTX_SCHEMA = "context-continuity-context-ops-v1"
DEFAULT_TRACKED_FILES = [
    "ACTIVE_TASK.md",
    "PROJECT_MEMORY.md",
    "DECISIONS.md",
    "planning/ACTIVE.md",
    "typed-memory.json",
    "rehydrated/latest.md",
]


def _ctx_root(mem_root: Path) -> Path:
    return mem_root / "context"


def _refs_path(mem_root: Path) -> Path:
    return _ctx_root(mem_root) / "refs.json"


def _commits_dir(mem_root: Path) -> Path:
    return _ctx_root(mem_root) / "commits"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_text(content: str) -> str:
    return _sha256_bytes(content.encode("utf-8"))


def _read_refs(mem_root: Path) -> dict[str, Any]:
    refs_path = _refs_path(mem_root)
    refs = _load_json(refs_path)
    if not refs:
        refs = {
            "schema": CTX_SCHEMA,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "active_branch": "main",
            "branches": {"main": None},
        }
        _save_json(refs_path, refs)
    if not isinstance(refs.get("branches"), dict):
        refs["branches"] = {"main": None}
    if not str(refs.get("active_branch") or "").strip():
        refs["active_branch"] = "main"
    return refs


def _write_refs(mem_root: Path, refs: dict[str, Any]) -> None:
    refs["schema"] = CTX_SCHEMA
    refs["updated_at"] = utc_now_iso()
    _save_json(_refs_path(mem_root), refs)


def _snapshot_files(mem_root: Path, files: list[str]) -> dict[str, Any]:
    snapshots: dict[str, Any] = {}
    for rel in files:
        rel_norm = rel.strip()
        if not rel_norm:
            continue
        p = (mem_root / rel_norm).resolve()
        entry: dict[str, Any] = {
            "path": rel_norm,
            "exists": p.exists(),
        }
        if p.exists() and p.is_file():
            data = p.read_bytes()
            entry["sha256"] = _sha256_bytes(data)
            entry["size_bytes"] = len(data)
        snapshots[rel_norm] = entry
    return snapshots


def _create_commit(
    *,
    mem_root: Path,
    branch: str,
    parents: list[str],
    message: str,
    meta: dict[str, Any],
    tracked_files: list[str],
) -> tuple[str, Path]:
    snapshots = _snapshot_files(mem_root, tracked_files)
    payload = {
        "schema": CTX_SCHEMA,
        "timestamp": utc_now_iso(),
        "branch": branch,
        "parents": parents,
        "message": message.strip() or "context commit",
        "tracked_files": tracked_files,
        "file_snapshots": snapshots,
        "meta": meta,
    }
    digest = _sha256_text(stable_json(payload))[:12]
    commit_id = f"ctx-{payload['timestamp'].replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')}-{digest}"
    payload["commit_id"] = commit_id

    commit_path = _commits_dir(mem_root) / f"{commit_id}.json"
    _save_json(commit_path, payload)
    return commit_id, commit_path


def _resolve_from_ref(refs: dict[str, Any], raw_from: str) -> str | None:
    candidate = raw_from.strip()
    branches = refs.get("branches") or {}
    if not candidate:
        active = str(refs.get("active_branch") or "main")
        return branches.get(active)
    if candidate in branches:
        return branches.get(candidate)
    return candidate


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _parse_meta(meta_json: str) -> dict[str, Any]:
    if not meta_json.strip():
        return {}
    loaded = json.loads(meta_json)
    if not isinstance(loaded, dict):
        raise ValueError("--meta-json must be a JSON object")
    return loaded


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--action",
        default="status",
        choices=["init", "status", "list", "commit", "branch", "switch", "merge"],
        help="Operation to run.",
    )
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument("--name", default="", help="Branch name for --action branch/switch.")
    ap.add_argument(
        "--from",
        dest="from_ref",
        default="",
        help="Start point branch/commit for --action branch.",
    )
    ap.add_argument("--branch", default="", help="Target branch for --action commit.")
    ap.add_argument("--source", default="", help="Source branch for --action merge.")
    ap.add_argument("--target", default="", help="Target branch for --action merge.")
    ap.add_argument("--message", default="", help="Commit/merge message.")
    ap.add_argument("--meta-json", default="", help="Optional JSON metadata for commit/merge.")
    ap.add_argument(
        "--record-event",
        default="on-change",
        choices=["off", "on-change", "always"],
        help="Capture continuity events for operations.",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON output.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    refs = _read_refs(mem_root)

    branches = refs.get("branches") if isinstance(refs.get("branches"), dict) else {}
    refs["branches"] = branches
    active = str(refs.get("active_branch") or "main")
    meta = _parse_meta(args.meta_json)

    event_needed = False
    event_summary = ""
    event_payload: dict[str, Any] = {}

    if args.action == "init":
        _write_refs(mem_root, refs)
        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "refs_file": str(_refs_path(mem_root)),
            "active_branch": refs.get("active_branch"),
            "branch_count": len(branches),
        }
        _emit(payload, args.json)
        raise SystemExit(0)

    if args.action in {"status", "list"}:
        commit_files = list(_commits_dir(mem_root).glob("*.json"))
        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "refs_file": str(_refs_path(mem_root)),
            "active_branch": active,
            "branch_count": len(branches),
            "commit_count": len(commit_files),
            "branches": branches,
        }
        _emit(payload, args.json)
        raise SystemExit(0)

    if args.action == "branch":
        branch_name = args.name.strip()
        if not branch_name:
            print("error: --name is required for --action branch")
            raise SystemExit(2)
        if branch_name in branches:
            print(f"error: branch already exists: {branch_name}")
            raise SystemExit(2)

        from_head = _resolve_from_ref(refs, args.from_ref)
        branches[branch_name] = from_head
        _write_refs(mem_root, refs)

        event_needed = True
        event_summary = f"context branch created {branch_name}"
        event_payload = {"branch": branch_name, "from": args.from_ref.strip() or active, "head": from_head}

        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "active_branch": refs.get("active_branch"),
            "branch": branch_name,
            "head": from_head,
        }
        _emit(payload, args.json)

    elif args.action == "switch":
        branch_name = args.name.strip()
        if not branch_name:
            print("error: --name is required for --action switch")
            raise SystemExit(2)
        if branch_name not in branches:
            print(f"error: branch not found: {branch_name}")
            raise SystemExit(2)
        refs["active_branch"] = branch_name
        _write_refs(mem_root, refs)

        event_needed = branch_name != active
        event_summary = f"context branch switched to {branch_name}"
        event_payload = {"from": active, "to": branch_name}

        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "active_branch": branch_name,
            "head": branches.get(branch_name),
        }
        _emit(payload, args.json)

    elif args.action == "commit":
        branch_name = args.branch.strip() or active
        if branch_name not in branches:
            print(f"error: branch not found: {branch_name}")
            raise SystemExit(2)

        parent = branches.get(branch_name)
        parents = [parent] if parent else []
        message = args.message.strip() or f"context commit on {branch_name}"
        commit_id, commit_path = _create_commit(
            mem_root=mem_root,
            branch=branch_name,
            parents=parents,
            message=message,
            meta=meta,
            tracked_files=DEFAULT_TRACKED_FILES,
        )
        branches[branch_name] = commit_id
        refs["active_branch"] = branch_name
        _write_refs(mem_root, refs)

        event_needed = True
        event_summary = f"context commit {commit_id} on {branch_name}"
        event_payload = {
            "branch": branch_name,
            "commit_id": commit_id,
            "parents": parents,
            "commit_path": str(commit_path),
        }

        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "branch": branch_name,
            "commit_id": commit_id,
            "commit_file": str(commit_path),
        }
        _emit(payload, args.json)

    elif args.action == "merge":
        source = args.source.strip()
        target = args.target.strip() or active
        if not source:
            print("error: --source is required for --action merge")
            raise SystemExit(2)
        if source not in branches:
            print(f"error: source branch not found: {source}")
            raise SystemExit(2)
        if target not in branches:
            print(f"error: target branch not found: {target}")
            raise SystemExit(2)

        source_head = branches.get(source)
        target_head = branches.get(target)
        if not source_head:
            print(f"error: source branch has no head commit: {source}")
            raise SystemExit(2)

        if source_head == target_head:
            payload = {
                "status": "ok",
                "repo_root": str(repo_root),
                "memory_root": str(mem_root),
                "message": "no-op merge (heads already equal)",
                "source": source,
                "target": target,
                "head": target_head,
            }
            _emit(payload, args.json)
            raise SystemExit(0)

        parents = [head for head in [target_head, source_head] if head]
        message = args.message.strip() or f"merge {source} into {target}"
        commit_id, commit_path = _create_commit(
            mem_root=mem_root,
            branch=target,
            parents=parents,
            message=message,
            meta={"source_branch": source, "target_branch": target, **meta},
            tracked_files=DEFAULT_TRACKED_FILES,
        )
        branches[target] = commit_id
        refs["active_branch"] = target
        _write_refs(mem_root, refs)

        event_needed = True
        event_summary = f"context merge {source} -> {target} ({commit_id})"
        event_payload = {
            "source": source,
            "target": target,
            "source_head": source_head,
            "target_prev_head": target_head,
            "merge_commit": commit_id,
            "commit_path": str(commit_path),
        }

        payload = {
            "status": "ok",
            "repo_root": str(repo_root),
            "memory_root": str(mem_root),
            "source": source,
            "target": target,
            "merge_commit": commit_id,
            "commit_file": str(commit_path),
        }
        _emit(payload, args.json)

    else:
        print(f"error: unsupported action {args.action}")
        raise SystemExit(2)

    should_record = args.record_event == "always" or (
        args.record_event == "on-change" and event_needed
    )
    if should_record and event_summary:
        append_event(
            events_path=mem_root / "events" / "events.jsonl",
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="context-op",
            status="success",
            summary=event_summary,
            source="context-ops",
            task="continuity-optimization",
            payload=event_payload,
        )


if __name__ == "__main__":
    main()
