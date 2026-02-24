#!/usr/bin/env python3
"""Repair event seq/prev_hash/hash chain in events.jsonl with a backup."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import detect_repo_root, hash_event, memory_root_for_repo, stable_json


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON on line {line_no}: {e}")
            if not isinstance(loaded, dict):
                raise SystemExit(f"Invalid event type on line {line_no}: expected object")
            events.append(loaded)
    return events


def normalize_chain(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev_hash = ""
    seq = 0
    for event in events:
        seq += 1
        normalized = dict(event)
        normalized["seq"] = seq
        if prev_hash:
            normalized["prev_hash"] = prev_hash
        else:
            normalized.pop("prev_hash", None)
        normalized.pop("hash", None)
        new_hash = hash_event(normalized)
        normalized["hash"] = new_hash
        prev_hash = new_hash
        out.append(normalized)
    return out


def write_events(path: Path, events: list[dict[str, Any]]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(stable_json(event) + "\n")
        f.flush()
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--events-file",
        default="",
        help="Optional events file path; defaults to memory_root/events/events.jsonl.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print summary only; do not write.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    events_path = (
        Path(args.events_file).expanduser()
        if args.events_file.strip()
        else mem_root / "events" / "events.jsonl"
    )

    events = load_events(events_path)
    if not events:
        print(f"events_file: {events_path}")
        print("events_count: 0")
        print("status: nothing to repair")
        return

    repaired = normalize_chain(events)
    changed = any(events[i] != repaired[i] for i in range(len(events)))

    print(f"events_file: {events_path}")
    print(f"events_count: {len(events)}")
    print(f"changed: {changed}")

    if args.dry_run or not changed:
        print("status: dry-run complete" if args.dry_run else "status: already consistent")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = events_path.with_name(events_path.name + f".bak.{ts}")
    shutil.copy2(events_path, backup)
    write_events(events_path, repaired)
    print(f"backup: {backup}")
    print("status: repaired")


if __name__ == "__main__":
    main()
