#!/usr/bin/env python3
"""
Heuristic scan for "design drift" patterns: hex colors, rgba, and ad hoc spacing.

This is intentionally simple and will produce false positives. Use it to direct review attention.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\s*\(")
PX = re.compile(r"\b\d+px\b")


def should_scan(path: Path) -> bool:
    if path.is_dir():
        return False
    if any(part in {"node_modules", ".git", "dist", "build", ".next"} for part in path.parts):
        return False
    return path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings: list[str] = []
    if HEX_COLOR.search(text):
        findings.append("hex_color")
    if RGBA.search(text):
        findings.append("rgba")
    if PX.search(text):
        findings.append("px_literal")
    return findings


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    root = root.resolve()
    print(f"scan_root: {root}")
    print()

    hits = 0
    for path in root.rglob("*"):
        if not should_scan(path):
            continue
        kinds = scan_file(path)
        if not kinds:
            continue
        hits += 1
        print(f"{path}: {', '.join(kinds)}")

    print()
    print("notes:")
    print("  - 'hex_color'/'rgba' are often drift if the repo uses tokens.")
    print("  - 'px_literal' may be fine in CSS, but flag it if the repo uses scales/tokens.")
    return 0 if hits == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

