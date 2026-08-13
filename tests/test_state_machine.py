"""Unit tests for the CXWorkflow task state machine."""

import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cxwf  # noqa: E402


class TransitionValidationTests(unittest.TestCase):
    def setUp(self):
        self.state = cxwf.empty_state()
        self.state["tasks"]["T001"] = {
            "title": "demo",
            "owner": "developer",
            "status": "Planned",
            "severity": "info",
            "evidence": "",
            "suggested_next": "",
            "needs_commander": False,
            "created_at": "now",
            "history": [],
        }

    def set_status(self, status, by="tester"):
        cxwf.valid_transition(self.state, "T001", status)
        cxwf.apply_transition(self.state, "T001", status, by)

    def test_full_happy_path(self):
        for status in ("Assigned", "Implementing", "ReadyForTest", "Testing", "Accepted", "Reported"):
            self.set_status(status)
        self.assertEqual(self.state["tasks"]["T001"]["status"], "Reported")

    def test_fixing_retest_loop(self):
        self.set_status("Assigned")
        self.set_status("Implementing")
        self.set_status("ReadyForTest")
        self.set_status("Testing")
        self.set_status("Fixing")
        # A fix must be re-tested before acceptance.
        with self.assertRaises(SystemExit):
            self.set_status("Accepted")
        self.set_status("ReadyForTest")
        self.set_status("Testing")
        self.set_status("Accepted")

    def test_skip_is_rejected(self):
        # Cannot jump from Planned straight to Testing.
        with self.assertRaises(SystemExit):
            self.set_status("Testing")

    def test_terminal_state_has_no_outgoing_edges(self):
        self.set_status("Assigned")
        self.set_status("Implementing")
        self.set_status("ReadyForTest")
        self.set_status("Testing")
        self.set_status("Accepted")
        self.set_status("Reported")
        with self.assertRaises(SystemExit):
            self.set_status("Implementing")

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.set_status("Done")

    def test_history_is_recorded(self):
        self.set_status("Assigned", by="commander")
        self.assertEqual(self.state["tasks"]["T001"]["history"][-1]["by"], "commander")
        self.assertEqual(self.state["tasks"]["T001"]["history"][-1]["status"], "Assigned")


if __name__ == "__main__":
    unittest.main()
