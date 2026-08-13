#!/usr/bin/env python3
"""Bump the CXWorkflow plugin version and update CHANGELOG (keep-a-changelog).

Usage:
    python3 scripts/release.py 0.2.0          # explicit new version
    python3 scripts/release.py patch|minor|major   # bump from current version

The repo manifest keeps a clean semver; local cachebuster versions are only
written to installed/cache copies by scripts/update_local_plugin.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def bump(current: str, kind: str) -> str:
    major, minor, patch = (int(part) for part in current.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"Unknown bump kind: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="New version (e.g. 0.2.0) or bump kind (major|minor|patch).")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    manifest_path = root / ".codex-plugin" / "plugin.json"
    changelog_path = root / "CHANGELOG.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = manifest["version"].split("+")[0]
    if not SEMVER_RE.fullmatch(current):
        raise SystemExit(f"Current version is not clean semver: {current!r}")

    if SEMVER_RE.fullmatch(args.version):
        new_version = args.version
    else:
        new_version = bump(current, args.version)

    if new_version == current:
        raise SystemExit(f"New version {new_version} equals current version")

    manifest["version"] = new_version
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    changelog = changelog_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    if f"## [{new_version}]" in changelog:
        raise SystemExit(f"CHANGELOG already contains [{new_version}]")
    entry = (
        f"\n## [{new_version}] - {today}\n\n"
        f"### Added\n\n- _Describe what was added in {new_version}._\n\n"
        f"### Changed\n\n- _Describe what changed in {new_version}._\n\n"
        f"### Fixed\n\n- _Describe what was fixed in {new_version}._\n"
    )
    changelog = changelog.replace("## [Unreleased]", "## [Unreleased]", 1)
    # Insert after the Unreleased section header block.
    if "## [Unreleased]" in changelog:
        head, _, rest = changelog.partition("## [Unreleased]")
        section_end = rest.find("\n## [")
        if section_end == -1:
            # No released sections yet; append at the end of the Unreleased block.
            changelog = head + "## [Unreleased]" + rest.rstrip() + "\n" + entry
        else:
            unreleased = rest[:section_end]
            released = rest[section_end:]
            changelog = head + "## [Unreleased]" + unreleased + entry + released
    else:
        changelog += "\n## [Unreleased]\n" + entry
    changelog_path.write_text(changelog, encoding="utf-8")

    print(f"Bumped version to {new_version} in {manifest_path}")
    print(f"Updated {changelog_path}")
    print("Edit the new CHANGELOG entry, then tag:  git tag v" + new_version)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
