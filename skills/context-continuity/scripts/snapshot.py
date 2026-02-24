#!/usr/bin/env python3
"""Write a lightweight per-repo snapshot into the global continuity store."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from memory_store import detect_repo_root, memory_root_for_repo, read_last_jsonl_obj, slugify


def sh(repo_root: Path, cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, cwd=repo_root, stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"<error running {' '.join(cmd)}: {e}>"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument("--slug", default="", help="Short label added to filename.")
    ap.add_argument("--note", default="", help="One-line note about the snapshot.")
    args = ap.parse_args()

    start = Path(args.repo).expanduser()
    repo_root = detect_repo_root(start)

    mem_root = memory_root_for_repo(repo_root)
    out_dir = mem_root / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    slug = slugify(args.slug) if args.slug.strip() else ""
    suffix = f"--{slug}" if slug else ""
    out_path = out_dir / f"{ts}{suffix}.md"

    branch = sh(repo_root, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    head = sh(repo_root, ["git", "rev-parse", "HEAD"])
    status = sh(repo_root, ["git", "status", "--porcelain=v1"])
    staged = sh(repo_root, ["git", "diff", "--name-only", "--cached"])
    changed = sh(repo_root, ["git", "diff", "--name-only"])
    stat = sh(repo_root, ["git", "diff", "--stat"])
    events_path = mem_root / "events" / "events.jsonl"

    event_count = 0
    if events_path.exists():
        with events_path.open("r", encoding="utf-8") as f:
            event_count = sum(1 for line in f if line.strip())
    last_event = read_last_jsonl_obj(events_path)
    last_event_seq = ""
    last_event_hash = ""
    if last_event:
        seq = last_event.get("seq")
        ev_hash = str(last_event.get("hash") or "")
        if isinstance(seq, int):
            last_event_seq = str(seq)
        if ev_hash:
            last_event_hash = ev_hash

    note_line = f"- Note: {args.note.strip()}\n" if args.note.strip() else ""
    memory_lines = [
        f"- Events recorded: `{event_count}`",
    ]
    if last_event_seq:
        memory_lines.append(f"- Last event seq/hash: `{last_event_seq}` / `{last_event_hash}`")
    memory_line_block = "\n".join(memory_lines)

    content = (
        f"# Snapshot: {ts}\n\n"
        f"- Repo root: `{repo_root}`\n"
        f"- Branch: `{branch}`\n"
        f"- HEAD: `{head}`\n"
        f"{note_line}\n"
        "## Memory Status\n\n"
        f"{memory_line_block}\n\n"
        "## Working Tree (porcelain)\n\n"
        "```text\n"
        f"{status}\n"
        "```\n\n"
        "## Staged Files\n\n"
        "```text\n"
        f"{staged}\n"
        "```\n\n"
        "## Unstaged Changed Files\n\n"
        "```text\n"
        f"{changed}\n"
        "```\n\n"
        "## Diff Stat (unstaged)\n\n"
        "```text\n"
        f"{stat}\n"
        "```\n"
    )

    out_path.write_text(content, encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
