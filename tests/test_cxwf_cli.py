"""Integration tests for the cxwf CLI against a temporary repository."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CXWF = ROOT / "scripts" / "cxwf.py"


class CxwfCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.store = self.repo / ".cxworkflow"

    def tearDown(self):
        self._tmp.cleanup()

    def run_cxwf(self, *args, expect_fail=False):
        result = subprocess.run(
            [sys.executable, str(CXWF), "--root", str(self.repo), *args],
            capture_output=True,
            text=True,
        )
        if expect_fail:
            self.assertNotEqual(result.returncode, 0, f"expected failure, got: {result.stdout}")
        else:
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result

    def test_init_creates_store(self):
        self.run_cxwf("init")
        for name in ("state.json", "events.log", "README.md", ".gitignore"):
            self.assertTrue((self.store / name).is_file(), name)
        self.assertTrue((self.store / "briefs").is_dir())
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["tasks"], {})
        self.assertEqual(state["version"], 1)

    def test_init_twice_requires_force(self):
        self.run_cxwf("init")
        self.run_cxwf("init", expect_fail=True)
        self.run_cxwf("init", "--force")

    def test_task_lifecycle_via_cli(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "feat", "--owner", "developer")
        self.run_cxwf("task", "set", "T001", "--status", "Assigned", "--by", "commander")
        self.run_cxwf("task", "set", "T001", "--status", "Implementing", "--by", "developer")
        self.run_cxwf("task", "set", "T001", "--status", "ReadyForTest", "--by", "developer")
        self.run_cxwf("task", "set", "T001", "--status", "Testing", "--by", "tester")
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["tasks"]["T001"]["status"], "Testing")
        self.assertEqual(len(state["tasks"]["T001"]["history"]), 5)

    def test_invalid_transition_fails(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "x")
        self.run_cxwf("task", "set", "T001", "--status", "Reported", expect_fail=True)

    def test_event_requires_suggested_next_when_forwarding(self):
        self.run_cxwf("init")
        self.run_cxwf(
            "event", "--event", "Blocked", "--source", "developer",
            "--severity", "blocking", "--needs-commander", "yes", expect_fail=True,
        )

    def test_event_logs_and_check_passes(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "y")
        self.run_cxwf("task", "set", "T001", "--status", "Assigned", "--by", "commander")
        self.run_cxwf("task", "set", "T001", "--status", "Implementing", "--by", "developer")
        self.run_cxwf("event", "--event", "TaskFinished", "--source", "developer",
                      "--task", "T001", "--status", "ReadyForTest",
                      "--evidence", "tests pass", "--suggested-next", "schedule tester")
        self.run_cxwf("check")
        log = (self.store / "events.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log), 1)
        record = json.loads(log[0])
        self.assertEqual(record["event"], "TaskFinished")
        self.assertFalse(record["needs_commander"])

    def test_check_catches_corrupt_events(self):
        self.run_cxwf("init")
        with (self.store / "events.log").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": "Nope", "severity": "urgent"}) + "\n")
        result = self.run_cxwf("check", expect_fail=True)
        self.assertIn("unknown event", result.stdout)
        self.assertIn("unknown severity", result.stdout)

    def test_decision_and_brief(self):
        self.run_cxwf("init")
        self.run_cxwf("decision", "批准阶段二")
        self.run_cxwf("brief", "测试已通过，待指挥验收")
        self.assertIn("批准阶段二", (self.store / "decisions.md").read_text(encoding="utf-8"))
        briefs = list((self.store / "briefs").glob("brief-*.md"))
        self.assertEqual(len(briefs), 1)
        self.assertIn("待指挥验收", briefs[0].read_text(encoding="utf-8"))

    def test_prompt_levels(self):
        self.run_cxwf("init")
        for level, expected in ((0, ["指挥"]), (1, ["指挥", "开发"]), (2, ["指挥", "开发", "测试"])):
            result = self.run_cxwf("prompt", "--level", str(level))
            for role in expected:
                self.assertIn(role, result.stdout)
        level3 = self.run_cxwf("prompt", "--level", "3").stdout
        for role in ("指挥", "秘书", "开发", "测试", "汇报", "obs"):
            self.assertIn(role, level3)
        self.assertIn(".cxworkflow", level3)


if __name__ == "__main__":
    unittest.main()
