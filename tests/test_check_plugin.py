"""Tests for the self-contained plugin checker."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_plugin.py"

MINIMAL_MANIFEST = {
    "name": "demo",
    "version": "0.1.0",
    "description": "demo",
    "author": {"name": "demo"},
    "interface": {
        "displayName": "Demo",
        "shortDescription": "d",
        "longDescription": "d",
        "developerName": "demo",
        "category": "Productivity",
        "defaultPrompt": ["demo"],
    },
}


class CheckPluginTests(unittest.TestCase):
    def run_checker(self, plugin_root):
        return subprocess.run(
            [sys.executable, str(CHECKER), str(plugin_root)],
            capture_output=True, text=True,
        )

    def test_real_repo_passes(self):
        result = self.run_checker(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_missing_agents_md_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                json.dumps(MINIMAL_MANIFEST), encoding="utf-8"
            )
            result = self.run_checker(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AGENTS.md", result.stdout)

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_checker(Path(tmp))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(".codex-plugin", result.stdout)

    def test_bad_version_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("ok\n", encoding="utf-8")
            (root / ".codex-plugin").mkdir()
            manifest = dict(MINIMAL_MANIFEST)
            manifest["version"] = "not-semver"
            (root / ".codex-plugin" / "plugin.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = self.run_checker(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("strict semver", result.stdout)


if __name__ == "__main__":
    unittest.main()
