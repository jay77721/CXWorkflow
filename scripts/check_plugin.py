#!/usr/bin/env python3
"""Self-contained CXWorkflow plugin checker (stdlib only, CI-friendly).

Validates the plugin manifest and skill metadata without depending on the
official plugin-creator skill scripts. Run in CI or locally:

    python3 scripts/check_plugin.py .

Exit code 0 means the plugin is structurally sound.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                       r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
                       r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
                       r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")

REQUIRED_TOP = ("name", "version", "description")
REQUIRED_AUTHOR = ("name",)
REQUIRED_INTERFACE = ("displayName", "shortDescription", "longDescription", "developerName", "category")

ALLOWED_TOP = {
    "id", "name", "version", "description", "skills", "apps", "mcpServers",
    "interface", "author", "homepage", "repository", "license", "keywords",
}

ALLOWED_INTERFACE = {
    "displayName", "shortDescription", "longDescription", "developerName",
    "category", "capabilities", "websiteURL", "privacyPolicyURL",
    "termsOfServiceURL", "brandColor", "composerIcon", "logo", "logoDark",
    "screenshots", "defaultPrompt", "default_prompt",
}


def check_manifest(plugin_root: Path, errors: list[str]) -> None:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        errors.append("missing `.codex-plugin/plugin.json`")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"`.codex-plugin/plugin.json` is invalid JSON: {exc}")
        return
    if not isinstance(manifest, dict):
        errors.append("`.codex-plugin/plugin.json` must be a JSON object")
        return

    for field in REQUIRED_TOP:
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"plugin.json field `{field}` must be a non-empty string")
    version = manifest.get("version", "")
    if not SEMVER_RE.fullmatch(version):
        errors.append(f"plugin.json field `version` must be strict semver, got {version!r}")

    for key in sorted(set(manifest) - ALLOWED_TOP):
        errors.append(f"plugin.json field `{key}` is not accepted")

    author = manifest.get("author")
    if not isinstance(author, dict):
        errors.append("plugin.json field `author` must be an object")
    else:
        for field in REQUIRED_AUTHOR:
            if not isinstance(author.get(field), str) or not author[field].strip():
                errors.append(f"plugin.json field `author.{field}` must be a non-empty string")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin.json field `interface` must be an object")
        return
    for field in REQUIRED_INTERFACE:
        if not isinstance(interface.get(field), str) or not interface[field].strip():
            errors.append(f"plugin.json field `interface.{field}` must be a non-empty string")
    if "defaultPrompt" not in interface and "default_prompt" not in interface:
        errors.append("plugin.json field `interface.defaultPrompt` or `interface.default_prompt` is required")
    for key in sorted(set(interface) - ALLOWED_INTERFACE):
        errors.append(f"plugin.json field `interface.{key}` is not accepted")

    skills = manifest.get("skills")
    if skills is not None and (not isinstance(skills, str) or not skills.strip()):
        errors.append("plugin.json field `skills` must be a non-empty string")


def check_skills(plugin_root: Path, errors: list[str]) -> None:
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        return
    for skill_root in sorted(skills_root.iterdir()):
        if skill_root.name.startswith(".") or not skill_root.is_dir():
            continue
        skill_md = skill_root / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"skill {skill_root.name}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errors.append(f"skill {skill_root.name}: SKILL.md must start with YAML frontmatter")
            continue
        end = text.find("\n---", 3)
        if end < 0:
            errors.append(f"skill {skill_root.name}: SKILL.md frontmatter is not closed")
            continue
        frontmatter = text[3:end]
        if not re.search(r"(?m)^name:\s*\S", frontmatter):
            errors.append(f"skill {skill_root.name}: frontmatter missing `name`")
        if not re.search(r"(?m)^description:\s*\S", frontmatter):
            errors.append(f"skill {skill_root.name}: frontmatter missing `description`")


def check_agents(plugin_root: Path, errors: list[str]) -> None:
    # AGENTS.md is how a fresh Codex learns to bootstrap and use this repo.
    agents = plugin_root / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing AGENTS.md — Codex will not auto-discover this workflow")
        return
    text = agents.read_text(encoding="utf-8")
    for needle in ("bootstrap", "cxwf.py", "SKILL.md", "Event"):
        if needle not in text:
            errors.append(f"AGENTS.md should mention `{needle}`")


def main() -> int:
    plugin_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors: list[str] = []
    check_agents(plugin_root, errors)
    check_manifest(plugin_root, errors)
    check_skills(plugin_root, errors)
    for marker in ("[TODO:", "[TODO ]"):
        for path in plugin_root.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".md"}:
                if marker in path.read_text(encoding="utf-8", errors="ignore"):
                    errors.append(f"placeholder {marker!r} found in {path}")
    if errors:
        print(f"CXWorkflow check FAILED for {plugin_root}:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"CXWorkflow check OK: {plugin_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
