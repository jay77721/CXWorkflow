#!/usr/bin/env python3
"""One-shot bootstrap: make the CXWorkflow skill available to Codex on this machine.

A fresh Codex that receives this repository can install itself by running:

    python3 scripts/bootstrap.py        # install the skill
    python3 scripts/bootstrap.py --with-plugin   # also sync the local plugin

The essential step copies `skills/cxworkflow` into `~/.codex/skills/` so the
skill is auto-discovered in future Codex sessions (idempotent). With
`--with-plugin` it additionally runs `scripts/update_local_plugin.py` to keep the
personal marketplace and Codex cache aligned.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", default=None, help="Target skills directory (default ~/.codex/skills).")
    parser.add_argument("--with-plugin", action="store_true", help="Also sync the local plugin (marketplace + cache).")
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args()


def skill_installed(skill_dir: Path) -> bool:
    return (skill_dir / "cxworkflow" / "SKILL.md").is_file()


def install_skill(repo_root: Path, skill_dir: Path) -> bool:
    source = repo_root / "skills" / "cxworkflow"
    if not (source / "SKILL.md").is_file():
        raise SystemExit(f"Skill source not found: {source} (is this a CXWorkflow repo?)")
    target = skill_dir / "cxworkflow"
    skill_dir.mkdir(parents=True, exist_ok=True)
    if target.is_dir() and filecmp.dircmp(source, target).same_files and not filecmp.dircmp(source, target).left_only:
        return False  # already up to date
    shutil.copytree(source, target, dirs_exist_ok=True)
    return True


def sync_plugin(repo_root: Path) -> None:
    updater = repo_root / "scripts" / "update_local_plugin.py"
    if not updater.is_file():
        print("  [skip] update_local_plugin.py not found")
        return
    result = subprocess.run([sys.executable, str(updater)], cwd=repo_root)
    if result.returncode != 0:
        raise SystemExit("Plugin sync failed; skill install still succeeded.")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    skill_dir = Path(args.skill_dir) if args.skill_dir else Path.home() / ".codex" / "skills"

    changed = install_skill(repo_root, skill_dir)
    if changed:
        print(f"Installed cxworkflow skill -> {skill_dir / 'cxworkflow'}")
    else:
        print(f"cxworkflow skill already up to date at {skill_dir / 'cxworkflow'}")

    if args.with_plugin:
        print("==> Syncing local plugin")
        sync_plugin(repo_root)

    print()
    print("Bootstrap complete. Open a NEW Codex thread so the cxworkflow skill loads.")
    print("Then ask Codex: '帮我基于当前项目创建 CXWorkflow 多线程开发团队'")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
