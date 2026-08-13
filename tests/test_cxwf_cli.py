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
            encoding="utf-8",
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


    def test_message_records_valid_block(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "z")
        self.run_cxwf("task", "set", "T001", "--status", "Assigned", "--by", "commander")
        self.run_cxwf("task", "set", "T001", "--status", "Implementing", "--by", "developer")
        block = (
            "Event: TaskFinished\n"
            "Source: Developer\n"
            "Task: T001\n"
            "Status: ReadyForTest\n"
            "Severity: info\n"
            "Evidence: all tests pass\n"
            "Suggested Next: schedule tester\n"
            "Needs Commander: no\n"
        )
        self.run_cxwf("message", "--text", block)
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["tasks"]["T001"]["status"], "ReadyForTest")
        log = (self.store / "events.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log), 1)
        self.assertEqual(json.loads(log[0])["event"], "TaskFinished")

    def test_message_missing_field_fails(self):
        self.run_cxwf("init")
        self.run_cxwf("message", "--text", "Event: Blocked\nSource: Developer\n", expect_fail=True)

    def test_message_forwarding_requires_suggested_next(self):
        self.run_cxwf("init")
        block = (
            "Event: Blocked\nSource: Developer\nTask: T1\nStatus: \n"
            "Severity: blocking\nEvidence: x\nSuggested Next: \nNeeds Commander: yes\n"
        )
        self.run_cxwf("message", "--text", block, expect_fail=True)

    def test_level_set(self):
        self.run_cxwf("init")
        self.run_cxwf("level", "set", "3")
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["load_level"], 3)
        self.assertFalse(state["paused"])

    def test_rate_limit_downgrades(self):
        self.run_cxwf("init")
        self.run_cxwf("level", "set", "3")
        self.run_cxwf("rate-limit", "--count", "1")
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["load_level"], 2)
        self.run_cxwf("rate-limit", "--count", "5")
        state = json.loads((self.store / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["load_level"], 0)
        self.assertTrue(state["paused"])

    def test_prompt_out_writes_file(self):
        self.run_cxwf("init")
        out = self.store.parent / "prompt.md"
        self.run_cxwf("prompt", "--level", "2", "--out", str(out))
        self.assertTrue(out.is_file())
        self.assertIn("开发", out.read_text(encoding="utf-8"))


    def test_version(self):
        result = subprocess.run(
            [sys.executable, str(CXWF), "--version"], capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("cxwf", result.stdout)

    def test_task_list_table(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "甲")
        self.run_cxwf("task", "add", "--title", "乙")
        result = self.run_cxwf("task", "list")
        self.assertIn("T001", result.stdout)
        self.assertIn("甲", result.stdout)
        self.assertIn("Planned", result.stdout)

    def test_status_dashboard(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "x")
        result = self.run_cxwf("status")
        self.assertIn("Load level", result.stdout)
        self.assertIn("Tasks      : 1 total", result.stdout)

    def test_status_json(self):
        self.run_cxwf("init")
        result = self.run_cxwf("status", "--json")
        data = json.loads(result.stdout)
        self.assertIn("load_level", data)
        self.assertIn("paused", data)
        self.assertIn("task_counts", data)

    def test_check_json_ok(self):
        self.run_cxwf("init")
        result = self.run_cxwf("check", "--json")
        self.assertEqual(json.loads(result.stdout)["ok"], True)

    def test_check_json_fails_on_bad_load_level(self):
        self.run_cxwf("init")
        state_path = self.store / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["load_level"] = 9
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_cxwf("check", "--json", expect_fail=True)
        data = json.loads(result.stdout)
        self.assertFalse(data["ok"])
        self.assertTrue(any("load_level" in e for e in data["errors"]))

    def test_root_auto_discovery_from_subdir(self):
        self.run_cxwf("init")
        self.run_cxwf("task", "add", "--title", "deep")
        nested = self.repo / "a" / "b" / "c"
        nested.mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(CXWF), "status"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(nested),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Tasks      : 1 total", result.stdout)


if __name__ == "__main__":
    unittest.main()
