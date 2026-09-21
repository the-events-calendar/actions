#!/usr/bin/env python3
"""Pin the conditions under which the changelog check does not run.

Run: python3 tests/test-changelogger.py
The gate is a GitHub expression evaluated by the runner, so what is checked here
is the expression itself: which clauses it carries and that an edited body can
still re-run the check.
"""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/changelogger.yml"


class ChangelogGateTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text()

    def gate(self):
        return self.workflow.split("    if: >-\n", 1)[1].split("    steps:", 1)[0]

    def test_release_machinery_is_exempt(self):
        """The bot and the release branch have no entry to add, so the job never starts."""
        gate = self.gate()
        self.assertIn("!contains(github.event.pull_request.body, '[skip-changelog]')", gate)
        self.assertIn("github.event.pull_request.user.login != 'tec-bot'", gate)
        self.assertIn("!startsWith(github.head_ref, 'release/')", gate)

    def test_every_clause_narrows_the_gate(self):
        """One '||' would let a marker alone exempt everything the other clauses catch."""
        self.assertNotIn("||", self.gate())

    def test_an_edited_body_re_runs_the_check(self):
        """A marker typed after the pull request opened only takes effect on an edit."""
        self.assertIn("edited", self.workflow.split("types:", 1)[1].split("]", 1)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
