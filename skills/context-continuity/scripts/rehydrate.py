#!/usr/bin/env python3
"""Compile a token-budgeted working context from continuity artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import approx_tokens, detect_repo_root, memory_root_for_repo


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def extract_section(markdown: str, heading: str) -> str:
    start = f"## {heading}".strip()
    lines = markdown.splitlines()
    in_section = False
    out: list[str] = []
    for line in lines:
        if line.strip() == start:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            out.append(line)
    return "\n".join(out).strip()


def parse_capsule_path(active_task_md: str) -> str:
    for line in active_task_md.splitlines():
        if "Capsule:" not in line:
            continue
        m = re.search(r"Capsule:\s*`?([^`]+)`?", line)
        if m:
            return m.group(1).strip()
    return ""


def compact_lines(text: str, *, max_lines: int, max_chars: int) -> str:
    out: list[str] = []
    chars = 0
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("#"):
            continue
        if len(out) >= max_lines:
            break
        if chars + len(line) > max_chars:
            break
        out.append(line)
        chars += len(line)
    return "\n".join(out)


def tail_decision_titles(decisions_md: str, max_items: int) -> list[str]:
    titles = [line.strip() for line in decisions_md.splitlines() if line.startswith("### ")]
    return titles[-max_items:]


def tokenize_terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z0-9_./-]+", text.lower()) if len(w) >= 3}


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, dict):
                events.append(loaded)
    return events


def _kind_bonus(kind: str) -> int:
    if kind in {"risk", "incident", "failure"}:
        return 12
    if kind in {"decision", "typed-memory", "automation"}:
        return 8
    if kind in {"test", "verify", "benchmark"}:
        return 7
    return 0


def event_score(
    event: dict[str, Any],
    *,
    recency_rank: int,
    terms: set[str],
    task_focus: str,
) -> tuple[int, dict[str, Any]]:
    score = max(0, 28 - recency_rank)
    trace: dict[str, Any] = {
        "recency_rank": recency_rank,
        "recency_score": score,
        "status_bonus": 0,
        "kind_bonus": 0,
        "term_hits": [],
        "task_match": False,
    }

    status = str(event.get("status") or "").lower()
    if status == "failure":
        score += 22
        trace["status_bonus"] = 22
    elif status == "warning":
        score += 14
        trace["status_bonus"] = 14
    elif status == "success":
        score += 7
        trace["status_bonus"] = 7

    kind = str(event.get("kind") or "").strip().lower()
    kind_bonus = _kind_bonus(kind)
    score += kind_bonus
    trace["kind_bonus"] = kind_bonus

    haystack = " ".join(
        [
            str(event.get("summary") or ""),
            str(event.get("task") or ""),
            str(event.get("kind") or ""),
            " ".join(str(v) for v in event.get("paths") or []),
            " ".join(str(v) for v in event.get("symbols") or []),
        ]
    ).lower()

    term_hits: list[str] = []
    if terms:
        for term in terms:
            if term in haystack:
                score += 5
                term_hits.append(term)
    trace["term_hits"] = term_hits

    if task_focus and task_focus.lower() in haystack:
        score += 9
        trace["task_match"] = True

    return score, trace


def render_event_line(event: dict[str, Any]) -> str:
    seq = event.get("seq", "?")
    ts = str(event.get("timestamp") or "?")
    kind = str(event.get("kind") or "note")
    status = str(event.get("status") or "info")
    summary = str(event.get("summary") or "").strip()
    event_hash = str(event.get("hash") or "")[:10]
    paths = [str(p) for p in (event.get("paths") or []) if str(p).strip()]

    line = f"- E{seq} [{ts}] {kind}/{status}: {summary}"
    if paths:
        line += f" | paths: {', '.join(paths[:3])}"
    if event_hash:
        line += f" | hash:{event_hash}"
    return line


def typed_memory_blocks(typed_memory: dict[str, Any]) -> tuple[str, str, str, str]:
    if not typed_memory:
        return "", "", "", ""

    def render_counter(rows: Any, limit: int = 8) -> str:
        if not isinstance(rows, list):
            return ""
        out: list[str] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            value = str(row.get("value") or "").strip()
            count = row.get("count")
            if value:
                out.append(f"- {value} (count={count})")
        return "\n".join(out)

    def render_events(rows: Any, limit: int = 8) -> str:
        if not isinstance(rows, list):
            return ""
        out: list[str] = []
        for row in rows[-limit:]:
            if not isinstance(row, dict):
                continue
            seq = row.get("seq", "?")
            status = str(row.get("status") or "info")
            summary = str(row.get("summary") or "").strip()
            hash_short = str(row.get("hash") or "")
            if summary:
                out.append(f"- E{seq} {status}: {summary} | hash:{hash_short}")
        return "\n".join(out)

    top_tasks = render_counter(typed_memory.get("top_tasks"))
    top_paths = render_counter(typed_memory.get("top_paths"))
    open_risks = render_events(typed_memory.get("open_risks"))
    decisions = render_events(typed_memory.get("recent_decisions"))
    return top_tasks, top_paths, open_risks, decisions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--budget-tokens",
        default=1800,
        type=int,
        help="Approximate token budget for compiled context.",
    )
    ap.add_argument("--query", default="", help="Focus query used to rank events.")
    ap.add_argument("--task", default="", help="Task key for prioritization.")
    ap.add_argument("--max-events", default=25, type=int, help="Maximum events to include.")
    ap.add_argument("--max-decisions", default=6, type=int, help="Maximum decision titles to include.")
    ap.add_argument("--typed-memory-path", default="", help="Override typed-memory JSON path.")
    ap.add_argument("--no-typed-memory", action="store_true", help="Ignore typed-memory summaries.")
    ap.add_argument("--no-write", action="store_true", help="Do not write output to disk.")
    ap.add_argument("--no-write-trace", action="store_true", help="Do not write retrieval trace JSON.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    active_task_path = mem_root / "ACTIVE_TASK.md"
    project_memory_path = mem_root / "PROJECT_MEMORY.md"
    decisions_path = mem_root / "DECISIONS.md"
    events_path = mem_root / "events" / "events.jsonl"

    active_task_md = read_text(active_task_path)
    project_memory_md = read_text(project_memory_path)
    decisions_md = read_text(decisions_path)

    capsule_rel = parse_capsule_path(active_task_md)
    capsule_path = mem_root / capsule_rel if capsule_rel else None
    capsule_md = read_text(capsule_path) if capsule_path else ""

    typed_memory_path = (
        Path(args.typed_memory_path).expanduser()
        if args.typed_memory_path.strip()
        else mem_root / "typed-memory.json"
    )
    typed_memory = {} if args.no_typed_memory else read_json(typed_memory_path)

    objective_text = compact_lines(
        extract_section(active_task_md, "Objective"), max_lines=10, max_chars=1600
    )
    criteria_text = compact_lines(
        extract_section(active_task_md, "Acceptance Criteria"), max_lines=12, max_chars=1800
    )
    constraints_text = compact_lines(
        extract_section(active_task_md, "Constraints / Non-Goals"), max_lines=10, max_chars=1400
    )
    key_paths_text = compact_lines(
        extract_section(active_task_md, "Key Paths"), max_lines=14, max_chars=1800
    )
    status_text = compact_lines(
        extract_section(active_task_md, "Current Status"), max_lines=10, max_chars=1400
    )
    commands_text = compact_lines(
        extract_section(active_task_md, "Commands / Verification"), max_lines=10, max_chars=1800
    )

    project_repo_text = compact_lines(
        extract_section(project_memory_md, "Repo"),
        max_lines=8,
        max_chars=1000,
    )
    project_arch_text = compact_lines(
        extract_section(project_memory_md, "Architecture"),
        max_lines=8,
        max_chars=1200,
    )
    decision_titles = tail_decision_titles(decisions_md, args.max_decisions)
    capsule_excerpt = compact_lines(capsule_md, max_lines=26, max_chars=2400)

    top_tasks_text, top_paths_signal_text, open_risks_text, recent_decisions_text = typed_memory_blocks(
        typed_memory
    )

    query_terms = tokenize_terms(
        " ".join(
            [
                args.query,
                args.task,
                objective_text,
                top_tasks_text,
                top_paths_signal_text,
            ]
        )
    )

    events = load_events(events_path)
    scored: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    for idx, event in enumerate(reversed(events)):
        score, trace = event_score(
            event,
            recency_rank=idx,
            terms=query_terms,
            task_focus=args.task.strip(),
        )
        scored.append((score, -idx, event, trace))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected = scored[: args.max_events]
    selected_events = [row[2] for row in selected]
    rendered_events = [render_event_line(event) for event in selected_events]

    trace_ranked_events: list[dict[str, Any]] = []
    for score, _neg_idx, event, trace in scored[: max(args.max_events * 2, 20)]:
        trace_ranked_events.append(
            {
                "seq": event.get("seq"),
                "event_id": event.get("event_id"),
                "hash": str(event.get("hash") or "")[:10],
                "kind": event.get("kind"),
                "status": event.get("status"),
                "summary": event.get("summary"),
                "score": score,
                "trace": trace,
            }
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    header = (
        "# Rehydrated Context\n\n"
        f"- Generated: `{now}`\n"
        f"- Repo root: `{repo_root}`\n"
        f"- Memory root: `{mem_root}`\n"
        f"- Token budget (approx): `{args.budget_tokens}`\n"
        f"- Focus query: `{args.query.strip() or 'none'}`\n"
        f"- Focus task: `{args.task.strip() or 'none'}`\n"
        f"- Typed memory: `{typed_memory_path if typed_memory else 'none'}`\n"
    )

    block_candidates: list[tuple[str, str, int]] = [
        ("Active Objective", objective_text, 100),
        ("Acceptance Criteria", criteria_text, 95),
        ("Constraints / Non-Goals", constraints_text, 90),
        ("Current Status", status_text, 88),
        ("Key Paths", key_paths_text, 87),
        ("Verification Commands", commands_text, 86),
        ("Open Risks (Typed)", open_risks_text, 85),
        ("Top Task Signals (Typed)", top_tasks_text, 84),
        ("Top Path Signals (Typed)", top_paths_signal_text, 83),
        ("Recent Decisions (Typed)", recent_decisions_text, 82),
        ("Project Repo Facts", project_repo_text, 72),
        ("Project Architecture Facts", project_arch_text, 70),
        ("Recent Decisions", "\n".join(f"- {title}" for title in decision_titles), 68),
        (
            "Capsule Pointer",
            f"- Active capsule: `{capsule_rel}`\n- Capsule file exists: `{bool(capsule_md)}`",
            66,
        ),
        ("Capsule Excerpt", capsule_excerpt, 62),
        ("Ranked Events", "\n".join(rendered_events), 58),
    ]
    block_candidates.sort(key=lambda item: item[2], reverse=True)

    selected_blocks: list[str] = [header]
    used_tokens = approx_tokens(header)
    omitted_titles: list[str] = []
    planner_trace: list[dict[str, Any]] = []

    for title, body, priority in block_candidates:
        if not body.strip():
            continue
        block = f"## {title}\n\n{body.strip()}\n"
        block_tokens = approx_tokens(block)
        included = used_tokens + block_tokens <= args.budget_tokens
        planner_trace.append(
            {
                "title": title,
                "priority": priority,
                "approx_tokens": block_tokens,
                "included": included,
            }
        )
        if not included:
            omitted_titles.append(title)
            continue
        selected_blocks.append(block)
        used_tokens += block_tokens

    footer = (
        "## Budget Summary\n\n"
        f"- Approx tokens used: `{used_tokens}`\n"
        f"- Blocks omitted by budget: `{', '.join(omitted_titles) if omitted_titles else 'none'}`\n"
        f"- Evidence source: `{events_path}`\n"
    )
    selected_blocks.append(footer)
    output = "\n".join(selected_blocks).rstrip() + "\n"

    print(output)

    trace_payload = {
        "schema": "context-continuity-rehydrate-trace-v1",
        "generated_at": now,
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "budget_tokens": args.budget_tokens,
        "query": args.query.strip(),
        "task": args.task.strip(),
        "query_terms": sorted(query_terms),
        "selected_block_count": sum(1 for row in planner_trace if row.get("included")),
        "omitted_block_count": sum(1 for row in planner_trace if not row.get("included")),
        "planner_trace": planner_trace,
        "event_ranking": trace_ranked_events,
        "typed_memory_path": str(typed_memory_path) if typed_memory else "",
    }

    if args.no_write:
        return

    out_dir = mem_root / "rehydrated"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    out_path = out_dir / f"{ts}--rehydrated.md"
    latest_path = out_dir / "latest.md"
    out_path.write_text(output, encoding="utf-8")
    latest_path.write_text(output, encoding="utf-8")
    print(f"written: {out_path}")
    print(f"written: {latest_path}")

    if args.no_write_trace:
        return

    trace_dir = out_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / f"{ts}--trace.json"
    latest_trace = trace_dir / "latest-trace.json"
    trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_trace.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"written: {trace_path}")
    print(f"written: {latest_trace}")


if __name__ == "__main__":
    main()
