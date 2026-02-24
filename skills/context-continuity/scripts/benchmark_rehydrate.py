#!/usr/bin/env python3
"""Benchmark rehydration coverage vs token budget and recommend an efficient default."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from memory_store import append_event, detect_repo_root, memory_root_for_repo


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def extract_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    lines = markdown.splitlines()
    in_section = False
    out: list[str] = []
    for line in lines:
        if line.strip() == marker:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            out.append(line)
    return "\n".join(out).strip()


def parse_list_items(section_text: str) -> list[str]:
    out: list[str] = []
    for line in section_text.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        item = s[2:].strip().strip("`").strip()
        if item:
            out.append(item)
    return out


def parse_criteria(section_text: str) -> list[str]:
    return [line.strip() for line in section_text.splitlines() if line.strip().startswith("- [")]


@dataclass
class BudgetResult:
    budget: int
    returncode: int
    stdout: str
    stderr: str
    tokens_used: int
    headings: set[str]
    key_path_hits: int
    key_path_total: int
    criteria_hits: int
    criteria_total: int
    event_lines: int
    coverage_score: int
    efficiency_score: float
    omitted: str


def parse_tokens_used(output: str) -> int:
    m = re.search(r"Approx tokens used: `(\d+)`", output)
    return int(m.group(1)) if m else 0


def parse_omitted(output: str) -> str:
    m = re.search(r"Blocks omitted by budget: `(.*)`", output)
    return m.group(1).strip() if m else ""


def parse_headings(output: str) -> set[str]:
    return set(re.findall(r"^## (.+)$", output, flags=re.MULTILINE))


def run_rehydrate(
    *,
    script_path: Path,
    repo_root: Path,
    budget: int,
    query: str,
    task: str,
    max_events: int,
    max_decisions: int,
) -> tuple[int, str, str]:
    cmd = [
        "python3",
        str(script_path),
        "--repo",
        str(repo_root),
        "--budget-tokens",
        str(budget),
        "--max-events",
        str(max_events),
        "--max-decisions",
        str(max_decisions),
        "--no-write",
    ]
    if query.strip():
        cmd.extend(["--query", query.strip()])
    if task.strip():
        cmd.extend(["--task", task.strip()])
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return cp.returncode, cp.stdout, cp.stderr


def compute_coverage_score(
    *,
    headings: set[str],
    key_hits: int,
    key_total: int,
    criteria_hits: int,
    criteria_total: int,
    event_lines: int,
) -> int:
    score = 0
    if "Active Objective" in headings:
        score += 20
    if "Acceptance Criteria" in headings:
        score += 15
    if "Constraints / Non-Goals" in headings:
        score += 10
    if "Current Status" in headings:
        score += 10
    if "Key Paths" in headings:
        score += 10
    if "Ranked Events" in headings:
        score += 5

    key_ratio = (key_hits / key_total) if key_total else 1.0
    criteria_ratio = (criteria_hits / criteria_total) if criteria_total else 1.0
    score += int(round(20.0 * key_ratio))
    score += int(round(10.0 * criteria_ratio))
    score += min(event_lines, 3) * 3
    return score


def pick_recommended(results: list[BudgetResult]) -> BudgetResult:
    successful = [r for r in results if r.returncode == 0]
    if not successful:
        return results[0]
    successful.sort(
        key=lambda r: (
            r.coverage_score >= 75,
            r.coverage_score,
            r.efficiency_score,
            -r.tokens_used,
            -r.budget,
        ),
        reverse=True,
    )
    top = successful[0]
    # If similar quality (within 2 points), prefer lower tokens.
    peers = [r for r in successful if abs(r.coverage_score - top.coverage_score) <= 2]
    peers.sort(key=lambda r: (r.tokens_used, -r.efficiency_score))
    return peers[0]


def render_report(
    *,
    repo_root: Path,
    mem_root: Path,
    query: str,
    task: str,
    results: list[BudgetResult],
    recommended: BudgetResult,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = []
    lines.append("# Rehydrate Benchmark")
    lines.append("")
    lines.append(f"- Generated: `{ts}`")
    lines.append(f"- Repo root: `{repo_root}`")
    lines.append(f"- Memory root: `{mem_root}`")
    lines.append(f"- Query: `{query or 'none'}`")
    lines.append(f"- Task: `{task or 'none'}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Budget | Return | Tokens | Coverage | Efficiency | Key Paths | Criteria | Events |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        key_cov = f"{r.key_path_hits}/{r.key_path_total or 0}"
        crit_cov = f"{r.criteria_hits}/{r.criteria_total or 0}"
        lines.append(
            f"| {r.budget} | {r.returncode} | {r.tokens_used} | {r.coverage_score} | {r.efficiency_score:.2f} | {key_cov} | {crit_cov} | {r.event_lines} |"
        )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(
        f"- Recommended budget: `{recommended.budget}` (coverage `{recommended.coverage_score}`, approx tokens `{recommended.tokens_used}`)"
    )
    lines.append(f"- Omitted blocks at recommended budget: `{recommended.omitted or 'none'}`")
    lines.append("")
    lines.append("## Why")
    lines.append("")
    lines.append(
        "- Selected for highest practical coverage with lower token usage to keep prompt context efficient."
    )
    lines.append(
        "- Coverage score weights objective/criteria/status/constraints/key paths and evidence presence."
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--budgets",
        default="400,700,1000,1400,1800",
        help="Comma-separated token budgets to benchmark.",
    )
    ap.add_argument("--query", default="", help="Focus query to pass into rehydrate.")
    ap.add_argument("--task", default="", help="Task key to pass into rehydrate.")
    ap.add_argument("--max-events", default=25, type=int, help="Passed to rehydrate.")
    ap.add_argument("--max-decisions", default=6, type=int, help="Passed to rehydrate.")
    ap.add_argument(
        "--record-event",
        action="store_true",
        help="Record a benchmark result event in events.jsonl.",
    )
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    mem_root = memory_root_for_repo(repo_root)
    rehydrate_script = (Path(__file__).resolve().parent / "rehydrate.py").resolve()

    active_task = read_text(mem_root / "ACTIVE_TASK.md")
    key_paths = parse_list_items(extract_section(active_task, "Key Paths"))
    criteria = parse_criteria(extract_section(active_task, "Acceptance Criteria"))

    budgets: list[int] = []
    for raw in args.budgets.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            budgets.append(int(raw))
        except ValueError:
            raise SystemExit(f"Invalid budget value: {raw}")
    if not budgets:
        raise SystemExit("No valid budgets supplied.")

    results: list[BudgetResult] = []
    for budget in budgets:
        rc, stdout, stderr = run_rehydrate(
            script_path=rehydrate_script,
            repo_root=repo_root,
            budget=budget,
            query=args.query,
            task=args.task,
            max_events=args.max_events,
            max_decisions=args.max_decisions,
        )
        headings = parse_headings(stdout)
        key_hits = sum(1 for p in key_paths if p and p in stdout)
        criteria_hits = sum(1 for c in criteria if c and c in stdout)
        tokens_used = parse_tokens_used(stdout)
        omitted = parse_omitted(stdout)
        event_lines = len(re.findall(r"^- E\d+\s", stdout, flags=re.MULTILINE))
        coverage = compute_coverage_score(
            headings=headings,
            key_hits=key_hits,
            key_total=len(key_paths),
            criteria_hits=criteria_hits,
            criteria_total=len(criteria),
            event_lines=event_lines,
        )
        efficiency = (coverage * 100.0 / tokens_used) if tokens_used else 0.0
        results.append(
            BudgetResult(
                budget=budget,
                returncode=rc,
                stdout=stdout,
                stderr=stderr,
                tokens_used=tokens_used,
                headings=headings,
                key_path_hits=key_hits,
                key_path_total=len(key_paths),
                criteria_hits=criteria_hits,
                criteria_total=len(criteria),
                event_lines=event_lines,
                coverage_score=coverage,
                efficiency_score=efficiency,
                omitted=omitted,
            )
        )

    recommended = pick_recommended(results)
    report = render_report(
        repo_root=repo_root,
        mem_root=mem_root,
        query=args.query.strip(),
        task=args.task.strip(),
        results=results,
        recommended=recommended,
    )
    print(report)

    bench_dir = mem_root / "rehydrated" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    out_path = bench_dir / f"{ts}--benchmark.md"
    latest = bench_dir / "latest.md"
    out_path.write_text(report, encoding="utf-8")
    latest.write_text(report, encoding="utf-8")
    print(f"written: {out_path}")
    print(f"written: {latest}")

    if args.record_event:
        events_path = mem_root / "events" / "events.jsonl"
        append_event(
            events_path=events_path,
            repo_root=repo_root,
            repo_id_value=mem_root.name,
            kind="benchmark",
            status="success",
            summary=(
                f"rehydrate benchmark recommended budget {recommended.budget} "
                f"(coverage {recommended.coverage_score}, tokens {recommended.tokens_used})"
            ),
            source="benchmark",
            task=args.task.strip() or "rehydrate-benchmark",
            paths=[str(out_path)],
            payload={
                "budgets": budgets,
                "recommended": {
                    "budget": recommended.budget,
                    "coverage": recommended.coverage_score,
                    "tokens": recommended.tokens_used,
                },
            },
        )
        print(f"event_recorded: {events_path}")


if __name__ == "__main__":
    main()
