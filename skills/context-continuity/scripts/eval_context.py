#!/usr/bin/env python3
"""Evaluate rehydrated context quality against practical coverage thresholds."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import detect_repo_root, memory_root_for_repo


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_events(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, dict):
                rows.append(loaded)
    return rows


def _extract_section(md: str, heading: str) -> str:
    start = f"## {heading}".strip()
    lines = md.splitlines()
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


def _extract_key_paths(active_task_md: str) -> list[str]:
    section = _extract_section(active_task_md, "Key Paths")
    out: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if line.startswith("`") and line.endswith("`") and len(line) >= 2:
            line = line[1:-1]
        if line:
            out.append(line)
    return out


def _extract_budget(meta_md: str) -> tuple[int, int]:
    budget = 0
    used = 0

    m_budget = re.search(r"Token budget \(approx\):\s*`?(\d+)`?", meta_md)
    if m_budget:
        budget = int(m_budget.group(1))

    m_used = re.search(r"Approx tokens used:\s*`?(\d+)`?", meta_md)
    if m_used:
        used = int(m_used.group(1))

    return budget, used


def _extract_hash_prefixes(md: str) -> set[str]:
    out: set[str] = set()
    for hit in re.findall(r"hash:([a-f0-9]{6,40})", md):
        out.add(hit[:10])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--rehydrated-path",
        default="",
        help="Override rehydrated markdown path (default memory_root/rehydrated/latest.md).",
    )
    ap.add_argument(
        "--risk-window",
        default=25,
        type=int,
        help="Number of most recent warning/failure events to evaluate for coverage.",
    )
    ap.add_argument(
        "--min-path-coverage",
        default=0.8,
        type=float,
        help="Minimum fraction of ACTIVE_TASK key paths present in rehydrated output.",
    )
    ap.add_argument(
        "--min-risk-coverage",
        default=0.75,
        type=float,
        help="Minimum fraction of recent warning/failure event hashes represented in rehydrated output.",
    )
    ap.add_argument(
        "--max-token-utilization",
        default=1.0,
        type=float,
        help="Maximum allowed used/budget token ratio.",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON output.")
    ap.add_argument("--no-write", action="store_true", help="Do not persist eval artifacts.")
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)

    active_task_path = mem_root / "ACTIVE_TASK.md"
    events_path = mem_root / "events" / "events.jsonl"
    rehydrated_path = (
        Path(args.rehydrated_path).expanduser()
        if args.rehydrated_path.strip()
        else mem_root / "rehydrated" / "latest.md"
    )

    active_task_md = _read_text(active_task_path)
    rehydrated_md = _read_text(rehydrated_path)
    events = _load_events(events_path)

    key_paths = _extract_key_paths(active_task_md)
    lower_rehydrated = rehydrated_md.lower()

    matched_paths: list[str] = []
    for path in key_paths:
        if path.lower() in lower_rehydrated:
            matched_paths.append(path)

    path_coverage = 1.0 if not key_paths else len(matched_paths) / len(key_paths)

    risk_events = [
        ev
        for ev in events
        if str(ev.get("status") or "").lower() in {"warning", "failure"}
    ]
    if args.risk_window > 0:
        risk_events = risk_events[-args.risk_window :]

    present_hashes = _extract_hash_prefixes(rehydrated_md)
    covered_risks = [
        ev
        for ev in risk_events
        if str(ev.get("hash") or "")[:10] in present_hashes
    ]

    risk_coverage = 1.0 if not risk_events else len(covered_risks) / len(risk_events)

    budget, used = _extract_budget(rehydrated_md)
    token_utilization = 0.0
    if budget > 0:
        token_utilization = used / budget

    checks = {
        "path_coverage_pass": path_coverage >= args.min_path_coverage,
        "risk_coverage_pass": risk_coverage >= args.min_risk_coverage,
        "token_utilization_pass": (budget == 0) or (token_utilization <= args.max_token_utilization),
        "rehydrated_exists_pass": bool(rehydrated_md.strip()),
    }

    overall_pass = all(checks.values())

    payload = {
        "schema": "context-continuity-eval-v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "repo_root": str(repo_root),
        "memory_root": str(mem_root),
        "rehydrated_path": str(rehydrated_path),
        "events_file": str(events_path),
        "thresholds": {
            "min_path_coverage": args.min_path_coverage,
            "min_risk_coverage": args.min_risk_coverage,
            "max_token_utilization": args.max_token_utilization,
            "risk_window": args.risk_window,
        },
        "metrics": {
            "path_coverage": path_coverage,
            "risk_coverage": risk_coverage,
            "token_budget": budget,
            "token_used": used,
            "token_utilization": token_utilization,
            "key_path_count": len(key_paths),
            "matched_path_count": len(matched_paths),
            "risk_event_count": len(risk_events),
            "covered_risk_count": len(covered_risks),
        },
        "checks": checks,
        "overall_pass": overall_pass,
        "matched_paths": matched_paths,
        "missing_paths": [p for p in key_paths if p not in matched_paths],
        "covered_risks": [
            {
                "seq": ev.get("seq"),
                "hash": str(ev.get("hash") or "")[:10],
                "summary": ev.get("summary"),
            }
            for ev in covered_risks
        ],
    }

    if not args.no_write:
        eval_dir = mem_root / "rehydrated" / "evals"
        eval_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        out_path = eval_dir / f"{ts}--eval.json"
        latest_path = eval_dir / "latest-eval.json"
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        out_path.write_text(rendered, encoding="utf-8")
        latest_path.write_text(rendered, encoding="utf-8")
        payload["eval_output"] = str(out_path)
        payload["latest_eval"] = str(latest_path)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"repo_root: {repo_root}")
        print(f"memory_root: {mem_root}")
        print(f"rehydrated_path: {rehydrated_path}")
        print(f"path_coverage: {path_coverage:.3f}")
        print(f"risk_coverage: {risk_coverage:.3f}")
        if budget > 0:
            print(f"token_utilization: {token_utilization:.3f} ({used}/{budget})")
        else:
            print("token_utilization: n/a")
        print(f"overall_pass: {overall_pass}")
        if "eval_output" in payload:
            print(f"eval_output: {payload['eval_output']}")
            print(f"latest_eval: {payload['latest_eval']}")

    raise SystemExit(0 if overall_pass else 3)


if __name__ == "__main__":
    main()
