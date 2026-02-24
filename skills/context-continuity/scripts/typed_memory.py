#!/usr/bin/env python3
"""Build typed memory summaries from continuity artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from memory_store import append_event, detect_repo_root, memory_root_for_repo, stable_json, utc_now_iso


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_events(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _top(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, count in counter.most_common(limit):
        rows.append({"value": key, "count": count})
    return rows


def _extract(events: list[dict[str, Any]], max_items: int) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    successes: list[dict[str, Any]] = []

    task_counter: Counter[str] = Counter()
    path_counter: Counter[str] = Counter()
    symbol_counter: Counter[str] = Counter()
    command_counter: Counter[str] = Counter()

    for ev in events:
        kind = str(ev.get("kind") or "").strip().lower()
        status = str(ev.get("status") or "").strip().lower()
        summary = str(ev.get("summary") or "").strip()
        task = str(ev.get("task") or "").strip()
        ts = str(ev.get("timestamp") or "")
        seq = ev.get("seq")
        hash_short = str(ev.get("hash") or "")[:10]

        if task:
            task_counter[task] += 1

        for path in ev.get("paths") or []:
            text = str(path).strip()
            if text:
                path_counter[text] += 1

        for symbol in ev.get("symbols") or []:
            text = str(symbol).strip()
            if text:
                symbol_counter[text] += 1

        for command in ev.get("commands") or []:
            text = str(command).strip()
            if text:
                command_counter[text] += 1

        snapshot = {
            "seq": seq,
            "timestamp": ts,
            "hash": hash_short,
            "kind": kind,
            "status": status,
            "summary": summary,
            "task": task,
        }

        if kind in {"decision", "adr", "architecture-decision"} or "decision" in summary.lower():
            decisions.append(snapshot)
        if status in {"failure", "warning"} or kind in {"risk", "incident", "bug"}:
            risks.append(snapshot)
        if status == "success":
            successes.append(snapshot)

    typed = {
        "schema": "context-continuity-typed-memory-v1",
        "generated_at": utc_now_iso(),
        "event_count": len(events),
        "decision_count": len(decisions),
        "risk_count": len(risks),
        "success_count": len(successes),
        "top_tasks": _top(task_counter, max_items),
        "top_paths": _top(path_counter, max_items),
        "top_symbols": _top(symbol_counter, max_items),
        "top_commands": _top(command_counter, max_items),
        "recent_decisions": decisions[-max_items:],
        "open_risks": risks[-max_items:],
        "recent_successes": successes[-max_items:],
        "latest_event": events[-1] if events else {},
    }
    return typed


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Typed Memory")
    lines.append("")
    lines.append(f"- Generated: `{payload.get('generated_at', '')}`")
    lines.append(f"- Events analyzed: `{payload.get('event_count', 0)}`")
    lines.append(f"- Open risks: `{payload.get('risk_count', 0)}`")
    lines.append(f"- Decisions: `{payload.get('decision_count', 0)}`")
    lines.append("")

    def section(title: str, key: str) -> None:
        lines.append(f"## {title}")
        items = payload.get(key) or []
        if not items:
            lines.append("- none")
            lines.append("")
            return
        for item in items:
            if isinstance(item, dict) and "value" in item:
                lines.append(f"- {item.get('value')} (count={item.get('count')})")
            elif isinstance(item, dict):
                seq = item.get("seq", "?")
                status = item.get("status", "info")
                summary = str(item.get("summary") or "").strip()
                hash_short = str(item.get("hash") or "")
                lines.append(f"- E{seq} {status}: {summary} | hash:{hash_short}")
            else:
                lines.append(f"- {item}")
        lines.append("")

    section("Top Tasks", "top_tasks")
    section("Top Paths", "top_paths")
    section("Top Symbols", "top_symbols")
    section("Top Commands", "top_commands")
    section("Recent Decisions", "recent_decisions")
    section("Open Risks", "open_risks")
    section("Recent Successes", "recent_successes")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--max-events",
        default=500,
        type=int,
        help="Number of most recent events to analyze.",
    )
    ap.add_argument(
        "--max-items",
        default=12,
        type=int,
        help="Maximum items per typed-memory section.",
    )
    ap.add_argument(
        "--record-event",
        default="on-change",
        choices=["off", "on-change", "always"],
        help="Capture a typed-memory event.",
    )
    ap.add_argument("--no-write", action="store_true", help="Print payload but do not write files.")
    ap.add_argument("--json", action="store_true", help="Print JSON payload.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    events_path = mem_root / "events" / "events.jsonl"
    out_json = mem_root / "typed-memory.json"
    out_md = mem_root / "typed-memory.md"

    events = _load_events(events_path)
    if args.max_events > 0:
        events = events[-args.max_events :]

    payload = _extract(events, max_items=max(1, args.max_items))
    payload["repo_root"] = str(repo_root)
    payload["memory_root"] = str(mem_root)
    payload["events_file"] = str(events_path)

    old_json = _read_text(out_json)
    new_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    changed = old_json != new_json

    if not args.no_write:
        out_json.write_text(new_json, encoding="utf-8")
        out_md.write_text(_render_markdown(payload), encoding="utf-8")

    should_record = (
        args.record_event == "always"
        or (args.record_event == "on-change" and changed)
    )
    if should_record:
        append_event(
            events_path=events_path,
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="typed-memory",
            status="success",
            summary="refreshed typed-memory summary",
            source="typed-memory",
            task="continuity-optimization",
            paths=[str(out_json), str(out_md)],
            payload={
                "event_count": payload.get("event_count", 0),
                "risk_count": payload.get("risk_count", 0),
                "decision_count": payload.get("decision_count", 0),
                "changed": changed,
            },
        )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"repo_root: {repo_root}")
        print(f"memory_root: {mem_root}")
        print(f"events_file: {events_path}")
        print(f"typed_memory_json: {out_json}")
        print(f"typed_memory_md: {out_md}")
        print(f"event_count: {payload.get('event_count', 0)}")
        print(f"risk_count: {payload.get('risk_count', 0)}")
        print(f"decision_count: {payload.get('decision_count', 0)}")
        print(f"changed: {changed}")
        print(f"summary_hash: {hashlib_sha1(stable_json(payload))}")



def hashlib_sha1(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    main()
