#!/usr/bin/env python3
"""
Discover infra/ops surface area in the current repo.

This is intentionally dependency-free. It prints evidence paths rather than guessing a stack.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path.cwd()


def _exists_any(patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pat in patterns:
        found.extend(sorted(ROOT.glob(pat)))
    # De-dupe while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for p in found:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _read_package_json() -> dict:
    pj = ROOT / "package.json"
    if not pj.exists():
        return {}
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    print(f"repo_root: {ROOT}")
    print()

    candidates = {
        "infra_dirs": [
            "infrastructure",
            "infra",
            "terraform",
            "pulumi",
            "k8s",
            "helm",
            "deploy",
            ".github/workflows",
        ],
        "infra_files": [
            "Dockerfile",
            "Dockerfile.*",
            "docker-compose.yml",
            "docker-compose.*.yml",
            "vercel.json",
            "netlify.toml",
            "fly.toml",
            "render.yaml",
            "Procfile",
        ],
        "iac_files": [
            "**/*.tf",
            "**/*.tfvars",
            "**/Pulumi.*",
            "**/*.yaml",
            "**/*.yml",
        ],
        "observability_hints": [
            "**/*sentry*",
            "**/*datadog*",
            "**/*opentelemetry*",
            "**/*otel*",
        ],
    }

    infra_dirs = [ROOT / d for d in candidates["infra_dirs"] if (ROOT / d).exists()]
    infra_files = _exists_any(candidates["infra_files"])

    print("infra_dirs:")
    for p in infra_dirs:
        print(f"  - {p}")
    if not infra_dirs:
        print("  (none found)")
    print()

    print("infra_files:")
    for p in infra_files:
        print(f"  - {p}")
    if not infra_files:
        print("  (none found)")
    print()

    pj = _read_package_json()
    scripts = (pj.get("scripts") or {}) if isinstance(pj.get("scripts"), dict) else {}
    package_manager = pj.get("packageManager") if isinstance(pj.get("packageManager"), str) else ""

    print(f"packageManager: {package_manager or '(unknown)'}")
    print("scripts (filtered):")
    for k in sorted(scripts.keys()):
        if any(x in k.lower() for x in ["deploy", "release", "ci", "build", "start", "lint", "typecheck", "test"]):
            print(f"  - {k}: {scripts[k]}")
    if not scripts:
        print("  (no package.json scripts found)")
    print()

    obs = _exists_any(candidates["observability_hints"])
    print("observability_hints:")
    for p in obs[:50]:
        # keep output bounded
        print(f"  - {p}")
    if not obs:
        print("  (none found)")
    elif len(obs) > 50:
        print(f"  ... +{len(obs) - 50} more")

    print()
    print("lockfiles:")
    for lf in ["pnpm-lock.yaml", "yarn.lock", "package-lock.json"]:
        p = ROOT / lf
        if p.exists():
            print(f"  - {p}")
    print()

    print("notes:")
    print("  - This script is discovery-only; it does not validate correctness.")
    print("  - Use the checklist in references/infra-checklist.md to evaluate PASS/FAIL/UNKNOWN.")


if __name__ == "__main__":
    # Avoid noisy locale issues.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()

