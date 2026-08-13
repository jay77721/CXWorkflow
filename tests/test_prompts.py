"""Golden tests: the published one-click prompts must not lose protocol fields.

These guard the README/SKILL.md prompts so a future edit cannot silently drop
the 8-field Secretary message format, the 6 roles, or the pin instruction.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIELDS = [
    "Event", "Source", "Task", "Status", "Severity", "Evidence", "Suggested Next", "Needs Commander",
]
ROLES = ["指挥", "秘书", "开发", "测试", "汇报", "obs"]
STATE_MACHINE = [
    "Planned", "Assigned", "Implementing", "ReadyForTest", "Testing", "Fixing", "Accepted", "Reported",
]


def prompts_from(text):
    """Yield the long and short one-click prompts found in a markdown file."""
    # The long prompt lives in a fenced block containing "1. 指挥".
    blocks = re.findall(r"```([^\n]*)\n(.*?)```", text, flags=re.DOTALL)
    return [content for _, content in blocks]


class PromptGoldenTests(unittest.TestCase):
    def test_readme_prompts_contain_all_fields_and_roles(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = "\n".join(prompts_from(readme))
        for field in FIELDS:
            self.assertIn(field, combined, f"README prompt missing field: {field}")
        for role in ROLES:
            self.assertIn(role, combined, f"README prompt missing role: {role}")
        self.assertIn("pin", combined)
        for state in STATE_MACHINE:
            self.assertIn(state, combined, f"README prompt missing state: {state}")

    def test_skill_prompt_contains_all_fields_and_roles(self):
        skill = (ROOT / "skills" / "cxworkflow" / "SKILL.md").read_text(encoding="utf-8")
        for field in FIELDS:
            self.assertIn(field, skill, f"SKILL.md missing field: {field}")
        for role in ROLES:
            self.assertIn(role, skill, f"SKILL.md missing role: {role}")

    def test_cxwf_prompt_matches_protocol(self):
        import subprocess, sys, json, tempfile

        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "cxwf.py"), "--root", tmp, "init"],
                check=True, capture_output=True,
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "cxwf.py"), "--root", tmp,
                 "prompt", "--level", "3"],
                check=True, capture_output=True, text=True,
            )
        for field in FIELDS:
            self.assertIn(field, result.stdout)
        for role in ROLES:
            self.assertIn(role, result.stdout)
        self.assertIn(".cxworkflow", result.stdout)


if __name__ == "__main__":
    unittest.main()
