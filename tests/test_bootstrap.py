"""Tests for the self-install bootstrap script."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.py"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill_dir = Path(self._tmp.name) / "codex-skills"

    def tearDown(self):
        self._tmp.cleanup()

    def run_bootstrap(self, *extra):
        return subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--repo-root", str(ROOT), "--skill-dir", str(self.skill_dir), *extra],
            capture_output=True,
            text=True,
        )

    def test_installs_skill_into_temp_dir(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.skill_dir / "cxworkflow" / "SKILL.md").is_file())

    def test_idempotent_second_run(self):
        self.run_bootstrap()
        first = (self.skill_dir / "cxworkflow" / "SKILL.md").read_text(encoding="utf-8")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        second = (self.skill_dir / "cxworkflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertIn("already up to date", result.stdout)

    def test_with_plugin_flag_skips_when_updater_missing(self):
        # A repo with the skill but no scripts/updater: skill install succeeds
        # and the plugin sync is skipped instead of failing.
        fake = Path(self._tmp.name) / "fake"
        (fake / "skills" / "cxworkflow").mkdir(parents=True)
        (fake / "skills" / "cxworkflow" / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--repo-root", str(fake),
             "--skill-dir", str(self.skill_dir), "--with-plugin"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skip", result.stdout)

    def test_missing_skill_source_gives_clear_error(self):
        bare = Path(self._tmp.name) / "bare"
        bare.mkdir()
        result = subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--repo-root", str(bare),
             "--skill-dir", str(self.skill_dir)],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Skill source not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
