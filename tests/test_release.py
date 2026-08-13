"""Tests for the release helper."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "scripts" / "release.py"


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".codex-plugin").mkdir()
        (self.repo / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "demo", "version": "0.1.0", "description": "d"}), encoding="utf-8"
        )
        (self.repo / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n- work in progress\n", encoding="utf-8"
        )

    def tearDown(self):
        self._tmp.cleanup()

    def run_release(self, version):
        return subprocess.run(
            [sys.executable, str(RELEASE), version, "--repo-root", str(self.repo)],
            capture_output=True, text=True,
        )

    def test_patch_bump(self):
        result = self.run_release("patch")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.repo / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.1.1")
        changelog = (self.repo / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [0.1.1]", changelog)
        self.assertIn("## [Unreleased]", changelog)

    def test_explicit_version(self):
        result = self.run_release("0.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.repo / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.2.0")

    def test_same_version_rejected(self):
        result = self.run_release("0.1.0")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
