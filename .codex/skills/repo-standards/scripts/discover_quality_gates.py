#!/usr/bin/env python3
"""
Print likely quality-gate commands for a JS/TS repo without guessing beyond repo evidence.

It prefers:
- package.json:packageManager
- lockfile presence
- package.json scripts
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path.cwd()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def detect_pm(pkg: dict) -> str:
    pm = pkg.get("packageManager")
    if isinstance(pm, str) and pm:
        # e.g. "pnpm@9.12.0" -> "pnpm"
        return pm.split("@", 1)[0]
    if (ROOT / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (ROOT / "yarn.lock").exists():
        return "yarn"
    if (ROOT / "package-lock.json").exists():
        return "npm"
    return "pnpm"  # most common in monorepos; treat as suggestion, not fact


def main() -> None:
    pj = ROOT / "package.json"
    if not pj.exists():
        print("package.json not found in cwd")
        return

    pkg = read_json(pj)
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    pm = detect_pm(pkg)

    print(f"repo_root: {ROOT}")
    print(f"package_manager: {pm}")
    print()

    gates = ["lint", "format", "typecheck", "test", "build", "ci"]
    present = [g for g in gates if g in scripts]

    print("scripts_present:")
    for g in present:
        print(f"  - {g}: {scripts[g]}")
    if not present:
        print("  (none of lint/format/typecheck/test/build/ci found)")
    print()

    def cmd(script: str) -> str:
        if pm == "pnpm":
            return f"pnpm run {script}"
        if pm == "yarn":
            return f"yarn {script}"
        return f"npm run {script}"

    print("recommended_commands (only if scripts exist):")
    for g in present:
        print(f"  - {cmd(g)}")


if __name__ == "__main__":
    main()

