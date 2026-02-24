#!/usr/bin/env python3
"""Verify continuity memory integrity (event hash chain and basic schema)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_store import detect_repo_root, hash_event, memory_root_for_repo


def parse_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except Exception:
        return False


def resolve_ref(path_text: str, repo_root: Path) -> Path:
    raw = Path(path_text).expanduser()
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--events-file",
        default="",
        help="Optional path to events file. Defaults to memory_root/events/events.jsonl.",
    )
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    events_path = (
        Path(args.events_file).expanduser()
        if args.events_file.strip()
        else mem_root / "events" / "events.jsonl"
    )

    errors: list[str] = []
    warnings: list[str] = []

    if not events_path.exists():
        errors.append(f"Events file missing: {events_path}")
    else:
        previous_hash = ""
        previous_seq = 0
        seen_ids: set[str] = set()
        event_count = 0

        with events_path.open("r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                event_count += 1
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_no}: invalid JSON ({e}).")
                    continue
                if not isinstance(event, dict):
                    errors.append(f"Line {line_no}: event must be a JSON object.")
                    continue

                schema = event.get("schema")
                if schema != "context-continuity-event-v1":
                    warnings.append(f"Line {line_no}: unexpected schema '{schema}'.")

                seq = event.get("seq")
                if not isinstance(seq, int) or seq <= 0:
                    errors.append(f"Line {line_no}: invalid seq '{seq}'.")
                elif seq != previous_seq + 1:
                    errors.append(
                        f"Line {line_no}: non-contiguous seq '{seq}', expected '{previous_seq + 1}'."
                    )
                previous_seq = seq if isinstance(seq, int) else previous_seq

                event_id = event.get("event_id")
                if not isinstance(event_id, str) or not event_id.strip():
                    errors.append(f"Line {line_no}: missing/invalid event_id.")
                elif event_id in seen_ids:
                    errors.append(f"Line {line_no}: duplicate event_id '{event_id}'.")
                else:
                    seen_ids.add(event_id)

                ts = event.get("timestamp")
                if not isinstance(ts, str) or not parse_iso8601(ts):
                    errors.append(f"Line {line_no}: invalid timestamp '{ts}'.")

                prev_hash = str(event.get("prev_hash") or "")
                if previous_hash and prev_hash != previous_hash:
                    errors.append(
                        f"Line {line_no}: prev_hash mismatch, expected '{previous_hash}' got '{prev_hash}'."
                    )
                if not previous_hash and prev_hash:
                    warnings.append(
                        f"Line {line_no}: first event has prev_hash set ('{prev_hash}')."
                    )

                current_hash = event.get("hash")
                if not isinstance(current_hash, str) or not current_hash.strip():
                    errors.append(f"Line {line_no}: missing hash.")
                else:
                    check_payload: dict[str, Any] = dict(event)
                    check_payload.pop("hash", None)
                    computed = hash_event(check_payload)
                    if computed != current_hash:
                        errors.append(
                            f"Line {line_no}: hash mismatch (expected computed '{computed}')."
                        )
                    previous_hash = current_hash

                for ref_key in ("paths", "refs"):
                    refs = event.get(ref_key)
                    if isinstance(refs, list):
                        for ref in refs:
                            if not isinstance(ref, str) or not ref.strip():
                                warnings.append(
                                    f"Line {line_no}: invalid empty reference in '{ref_key}'."
                                )
                                continue
                            resolved = resolve_ref(ref, repo_root)
                            if not resolved.exists():
                                warnings.append(
                                    f"Line {line_no}: referenced path not found '{ref}' ({resolved})."
                                )

        print(f"repo_root: {repo_root}")
        print(f"memory_root: {mem_root}")
        print(f"events_file: {events_path}")
        print(f"events_checked: {event_count}")

    if errors:
        print("errors:")
        for err in errors:
            print(f"  - {err}")
    if warnings:
        print("warnings:")
        for warn in warnings:
            print(f"  - {warn}")

    if errors:
        raise SystemExit(2)
    if warnings and args.strict:
        raise SystemExit(3)
    print("status: ok")


if __name__ == "__main__":
    main()
