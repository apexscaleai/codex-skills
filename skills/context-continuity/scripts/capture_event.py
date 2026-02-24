#!/usr/bin/env python3
"""Capture an append-only continuity event with hash-chain integrity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory_store import (
    append_event,
    detect_repo_root,
    memory_root_for_repo,
)


def parse_payload(payload_json: str, payload_file: str) -> dict[str, Any]:
    if payload_json and payload_file:
        raise ValueError("Pass only one of --payload-json or --payload-file.")
    if payload_json:
        loaded = json.loads(payload_json)
        if not isinstance(loaded, dict):
            raise ValueError("--payload-json must decode to an object.")
        return loaded
    if payload_file:
        loaded = json.loads(Path(payload_file).expanduser().read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("--payload-file must contain a JSON object.")
        return loaded
    return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument("--kind", default="note", help="Event kind (e.g. edit, test, decision, risk).")
    ap.add_argument(
        "--status",
        default="info",
        choices=["info", "success", "warning", "failure"],
        help="Event status.",
    )
    ap.add_argument("--summary", required=True, help="One-line event summary.")
    ap.add_argument("--task", default="", help="Task key or label to aid retrieval.")
    ap.add_argument("--source", default="manual", help="Event source (manual, hook, script, etc).")
    ap.add_argument("--path", action="append", default=[], help="Relevant path (repeatable).")
    ap.add_argument("--symbol", action="append", default=[], help="Relevant symbol (repeatable).")
    ap.add_argument("--command", action="append", default=[], help="Executed command (repeatable).")
    ap.add_argument("--ref", action="append", default=[], help="Evidence reference (repeatable).")
    ap.add_argument("--payload-json", default="", help="JSON object payload as a string.")
    ap.add_argument("--payload-file", default="", help="Path to JSON object payload file.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    events_path = mem_root / "events" / "events.jsonl"

    payload = parse_payload(args.payload_json.strip(), args.payload_file.strip())
    event = append_event(
        events_path=events_path,
        repo_root=repo_root,
        repo_id_value=mem_root.name,
        kind=args.kind,
        status=args.status,
        summary=args.summary,
        source=args.source,
        task=args.task,
        paths=args.path,
        symbols=args.symbol,
        commands=args.command,
        refs=args.ref,
        payload=payload,
    )

    print(f"memory_root: {mem_root}")
    print(f"events_file: {events_path}")
    print(f"event_id: {event.get('event_id')}")
    print(f"seq: {event.get('seq')}")
    print(f"hash: {event.get('hash')}")


if __name__ == "__main__":
    main()
