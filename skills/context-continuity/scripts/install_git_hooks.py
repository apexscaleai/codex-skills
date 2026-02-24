#!/usr/bin/env python3
"""Install/uninstall low-noise git hooks for automatic continuity event capture."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from memory_store import detect_repo_root, sh


MANAGED_MARKER = "# Managed by context-continuity (do not edit manually)"


def hooks_dir(repo_root: Path) -> Path:
    code, out = sh(repo_root, ["git", "rev-parse", "--git-path", "hooks"])
    if code != 0 or not out.strip():
        raise RuntimeError(f"Not a git repo (or hooks path unavailable): {repo_root}")
    p = Path(out.strip())
    if not p.is_absolute():
        p = (repo_root / p).resolve()
    return p


def capture_script_path() -> Path:
    return (Path(__file__).resolve().parent / "capture_event.py").resolve()


def render_hook(hook_name: str, capture_path: Path) -> str:
    cap = str(capture_path)
    common = (
        "#!/bin/sh\n"
        f"{MANAGED_MARKER}\n"
        'repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0\n'
        f'cap="{cap}"\n'
        '[ -f "$cap" ] || exit 0\n'
    )

    if hook_name == "post-commit":
        return common + (
            'sha="$(git rev-parse --short HEAD 2>/dev/null || true)"\n'
            'subject="$(git log -1 --pretty=%s 2>/dev/null || true)"\n'
            'set -- --repo "$repo_root" --kind commit --status success --source git-hook '
            '--task git-history --summary "commit ${sha} ${subject}" --command "git commit"\n'
            "while IFS= read -r p; do\n"
            '  [ -n "$p" ] || continue\n'
            '  set -- "$@" --path "$p"\n'
            "done <<EOF\n"
            '$(git show --name-only --pretty="" HEAD 2>/dev/null | head -n 30)\n'
            "EOF\n"
            'python3 "$cap" "$@" >/dev/null 2>&1 || true\n'
        )

    if hook_name == "post-merge":
        return common + (
            'sha="$(git rev-parse --short HEAD 2>/dev/null || true)"\n'
            'set -- --repo "$repo_root" --kind merge --status success --source git-hook '
            '--task git-history --summary "post-merge at ${sha}" --command "git merge"\n'
            "while IFS= read -r p; do\n"
            '  [ -n "$p" ] || continue\n'
            '  set -- "$@" --path "$p"\n'
            "done <<EOF\n"
            '$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | head -n 30)\n'
            "EOF\n"
            'python3 "$cap" "$@" >/dev/null 2>&1 || true\n'
        )

    if hook_name == "pre-commit":
        return common + (
            "staged_count=$(git diff --name-only --cached 2>/dev/null | wc -l | tr -d ' ')\n"
            '[ "${staged_count:-0}" -eq 0 ] && exit 0\n'
            'set -- --repo "$repo_root" --kind commit-prepare --status info --source git-hook '
            '--task git-history --summary "pre-commit with ${staged_count} staged files" --command "git commit"\n'
            "while IFS= read -r p; do\n"
            '  [ -n "$p" ] || continue\n'
            '  set -- "$@" --path "$p"\n'
            "done <<EOF\n"
            '$(git diff --name-only --cached 2>/dev/null | head -n 30)\n'
            "EOF\n"
            'python3 "$cap" "$@" >/dev/null 2>&1 || true\n'
        )

    if hook_name == "post-checkout":
        return common + (
            '[ "${3:-0}" != "1" ] && exit 0\n'
            'old="$(printf "%s" "${1:-}" | cut -c1-8)"\n'
            'new="$(printf "%s" "${2:-}" | cut -c1-8)"\n'
            'python3 "$cap" --repo "$repo_root" --kind checkout --status info --source git-hook '
            '--task git-history --summary "checkout ${old} -> ${new}" --command "git checkout" >/dev/null 2>&1 || true\n'
        )

    raise ValueError(f"Unsupported hook name: {hook_name}")


def parse_hooks(raw: str, include_pre_commit: bool, include_post_checkout: bool) -> list[str]:
    items = [h.strip() for h in raw.split(",") if h.strip()]
    for mandatory in ("post-commit", "post-merge"):
        if mandatory not in items:
            items.append(mandatory)
    if include_pre_commit and "pre-commit" not in items:
        items.append("pre-commit")
    if include_post_checkout and "post-checkout" not in items:
        items.append("post-checkout")
    allowed = {"pre-commit", "post-commit", "post-merge", "post-checkout"}
    for item in items:
        if item not in allowed:
            raise ValueError(f"Unsupported hook '{item}'. Allowed: {', '.join(sorted(allowed))}")
    return items


def backup_path(target: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(f"{target.name}.bak.context-continuity.{ts}")


def is_managed(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return MANAGED_MARKER in content


def install(repo_root: Path, selected_hooks: list[str], force: bool) -> int:
    hooks = hooks_dir(repo_root)
    hooks.mkdir(parents=True, exist_ok=True)
    cap = capture_script_path()
    written = 0
    skipped = 0

    for hook in selected_hooks:
        target = hooks / hook
        if target.exists() and not is_managed(target):
            if not force:
                print(f"skip: {target} (existing custom hook; use --force to override)")
                skipped += 1
                continue
            bak = backup_path(target)
            target.rename(bak)
            print(f"backup: {target} -> {bak}")

        target.write_text(render_hook(hook, cap), encoding="utf-8")
        target.chmod(0o755)
        print(f"installed: {target}")
        written += 1

    print(f"hooks_dir: {hooks}")
    print(f"installed_count: {written}")
    print(f"skipped_count: {skipped}")
    return 0 if skipped == 0 else 1


def uninstall(repo_root: Path, selected_hooks: list[str]) -> int:
    hooks = hooks_dir(repo_root)
    removed = 0
    skipped = 0
    for hook in selected_hooks:
        target = hooks / hook
        if not target.exists():
            continue
        if not is_managed(target):
            print(f"skip: {target} (not managed by context-continuity)")
            skipped += 1
            continue
        target.unlink()
        print(f"removed: {target}")
        removed += 1
    print(f"hooks_dir: {hooks}")
    print(f"removed_count: {removed}")
    print(f"skipped_count: {skipped}")
    return 0 if skipped == 0 else 1


def status(repo_root: Path, selected_hooks: list[str]) -> int:
    hooks = hooks_dir(repo_root)
    print(f"hooks_dir: {hooks}")
    for hook in selected_hooks:
        target = hooks / hook
        if not target.exists():
            print(f"- {hook}: missing")
            continue
        if is_managed(target):
            print(f"- {hook}: managed")
        else:
            print(f"- {hook}: custom")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo directory (defaults to cwd).")
    ap.add_argument(
        "--action",
        default="install",
        choices=["install", "uninstall", "status"],
        help="Operation to perform.",
    )
    ap.add_argument(
        "--hooks",
        default="post-commit,post-merge",
        help="Comma-separated hooks to manage. Defaults keep signal high and noise low.",
    )
    ap.add_argument(
        "--include-pre-commit",
        action="store_true",
        help="Also manage pre-commit (higher event volume).",
    )
    ap.add_argument(
        "--include-post-checkout",
        action="store_true",
        help="Also manage post-checkout for branch switches.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Override custom hook files by backing them up and installing managed versions.",
    )
    args = ap.parse_args()

    repo_root = detect_repo_root(Path(args.repo).expanduser())
    hooks = parse_hooks(args.hooks, args.include_pre_commit, args.include_post_checkout)

    try:
        if args.action == "install":
            raise SystemExit(install(repo_root, hooks, args.force))
        if args.action == "uninstall":
            raise SystemExit(uninstall(repo_root, hooks))
        raise SystemExit(status(repo_root, hooks))
    except RuntimeError as e:
        print(f"error: {e}")
        print(
            "hint: use this script inside a git repository, or use auto_cycle.py for non-git workspaces."
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
