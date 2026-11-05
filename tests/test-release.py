#!/usr/bin/env python3
"""Pin the release wiring between the template, our wrappers and the toolbox.

Run: python3 tests/test-release.py
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/release.yml"
WRAPPERS = {a: ROOT / f".github/actions/{a}/action.yml" for a in ("release-merge", "release-publish")}


class ReleaseTests(unittest.TestCase):
    def test_wrappers_pin_the_toolbox_action_to_a_commit(self):
        """The bot token reaches this code, so it must not be a ref that can move under us."""
        for name, path in WRAPPERS.items():
            self.assertRegex(path.read_text(), rf"uses: stellarwp/plugin-toolbox/\.github/actions/{name}@[0-9a-f]{{40}}\b")

    def test_template_calls_our_wrappers_not_the_toolbox(self):
        """The toolbox ref is pinned in one place, the wrappers."""
        workflow = WORKFLOW.read_text()
        for name in WRAPPERS:
            self.assertIn(f"uses: the-events-calendar/actions/.github/actions/{name}@main", workflow)
        self.assertNotIn("stellarwp/plugin-toolbox", workflow)

    def test_the_job_never_writes_with_the_github_token(self):
        self.assertNotIn("contents: write", WORKFLOW.read_text())

    def test_both_toolbox_steps_use_the_bot_token(self):
        """The tag ruleset and the branch rules block github.token."""
        self.assertEqual(WORKFLOW.read_text().count("token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}"), 2)

    def test_the_run_must_be_on_the_branch_it_merges(self):
        workflow = WORKFLOW.read_text()
        self.assertLess(workflow.index("Check that the run is on the release branch"), workflow.index("- name: Merge the release"))
        self.assertIn("head: ${{ github.sha }}", workflow)

    def test_publishes_at_the_merged_commit_after_the_zip_check(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("target: ${{ steps.merge.outputs.base-sha }}", workflow)
        self.assertLess(workflow.index("- name: Download and check the zip"), workflow.index("- name: Publish the GitHub release"))

    def test_zip_stays_inside_the_checkout(self):
        """release-publish reads assets relative to the checkout."""
        self.assertNotIn("RUNNER_TEMP/${ZIP_NAME}", WORKFLOW.read_text())

    def test_plugin_repos_receive_the_workflow(self):
        sync = (ROOT / ".github/sync.yml").read_text()
        group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release.yml", group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
