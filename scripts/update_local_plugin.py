#!/usr/bin/env python3
"""Update the local CXWorkflow Codex plugin in one step (cross-platform).

Single source of truth for local plugin updates. The PowerShell wrapper
(update-local-plugin.ps1) and the bash wrapper (update-local-plugin.sh) both
delegate to this script.

Flow (mirrors the official plugin-creator update flow):
  1. Read the repo manifest and derive a clean base version (strip any
     pre-existing `+codex.<ts>` cachebuster suffix).
  2. Compute a fresh cachebuster version `base+codex.<utc-timestamp>`.
  3. Ensure the personal marketplace entry at ~/.agents/plugins/marketplace.json.
  4. Copy plugin contents to ~/.agents/plugins/plugins/<name>.
  5. Write a matching cache copy under ~/.codex/plugins/cache/personal/<name>/<version>.
  6. Run the official plugin validator on repo + installed + cached copies when
     it is available.

The repository manifest keeps a clean semver version; cachebusters are only
written to installed/cache copies so the repo diff stays clean.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_TOP_FILES = (
    "README.md",
    "README.en.md",
    "INSTALL.md",
    "CHANGELOG.md",
)
REPO_TOP_DIRS = (".codex-plugin", "skills", "assets")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-name", default="cxworkflow")
    parser.add_argument("--marketplace-name", default="personal")
    parser.add_argument("--repo-root", default=".", help="Path to the plugin repository root.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"Not a JSON object: {path}")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def copy_plugin_contents(source: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in REPO_TOP_DIRS:
        src = source / name
        if src.is_dir():
            shutil.copytree(src, dest / name, dirs_exist_ok=True)
    for name in REPO_TOP_FILES:
        src = source / name
        if src.is_file():
            shutil.copy2(src, dest / name)


def ensure_marketplace_entry(
    marketplace_path: Path, plugin_name: str, marketplace_name: str
) -> None:
    if marketplace_path.is_file():
        marketplace = load_json(marketplace_path)
    else:
        marketplace = {
            "name": marketplace_name,
            "interface": {"displayName": "Personal"},
            "plugins": [],
        }
    marketplace.setdefault("plugins", [])

    entry = next((p for p in marketplace["plugins"] if p.get("name") == plugin_name), None)
    new_entry = {
        "name": plugin_name,
        "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }
    if entry is None:
        marketplace["plugins"].append(new_entry)
    else:
        entry["source"] = new_entry["source"]
        entry["policy"] = new_entry["policy"]
        entry["category"] = new_entry["category"]
    write_json(marketplace_path, marketplace)


def run_validator(validator_path: Path, plugin_path: Path) -> None:
    if not validator_path.is_file():
        print(f"  [skip] validator not found: {validator_path}")
        return
    result = subprocess.run(
        [sys.executable, str(validator_path), str(plugin_path)],
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, end="")
        raise SystemExit(f"Plugin validation failed for {plugin_path}")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    manifest_path = repo_root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing plugin manifest: {manifest_path}")

    manifest = load_json(manifest_path)
    base_version = str(manifest.get("version", "")).split("+")[0]
    if not base_version:
        raise SystemExit(f"Invalid version in manifest: {manifest_path}")

    cachebuster = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    new_version = f"{base_version}+codex.{cachebuster}"

    home = Path.home()
    agents_plugins_root = home / ".agents" / "plugins"
    marketplace_path = agents_plugins_root / "marketplace.json"
    plugin_source_root = agents_plugins_root / "plugins" / args.plugin_name
    cache_root = (
        home / ".codex" / "plugins" / "cache" / args.marketplace_name / args.plugin_name / new_version
    )

    print(f"==> Ensuring personal marketplace entry")
    ensure_marketplace_entry(marketplace_path, args.plugin_name, args.marketplace_name)

    print(f"==> Copying plugin source to personal marketplace")
    copy_plugin_contents(repo_root, plugin_source_root)

    print(f"==> Writing matching Codex plugin cache")
    copy_plugin_contents(plugin_source_root, cache_root)

    validator = (
        home / ".codex" / "skills" / ".system" / "plugin-creator" / "scripts" / "validate_plugin.py"
    )
    print(f"==> Validating repository plugin")
    run_validator(validator, repo_root)
    print(f"==> Validating marketplace source plugin")
    run_validator(validator, plugin_source_root)
    print(f"==> Validating cached plugin")
    run_validator(validator, cache_root)

    print("==> Done")
    print(f"Version: {new_version}")
    print(f"Marketplace: {marketplace_path}")
    print(f"Source: {plugin_source_root}")
    print(f"Cache: {cache_root}")
    print("Open a new Codex thread or restart Codex to reload the plugin.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
