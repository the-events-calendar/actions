#!/usr/bin/env python3
"""Pin the release prep wiring between the template, our wrapper and the plugin repos.

Run: python3 tests/test-release-prep.py
"""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/release-prep.yml"
WRAPPER = ROOT / ".github/actions/release-prep/action.yml"


class ReleasePrepTests(unittest.TestCase):
    def test_template_commits_with_the_bot_token(self):
        """release/* requires pull requests, and github.token starts no workflow run on its commit."""
        self.assertIn("token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}", WORKFLOW.read_text())

    def test_template_checks_out_the_submodules(self):
        """TEC and ET scan common/src for TBDs, and pup fails on a directory that is not there."""
        self.assertIn("submodules: recursive", WORKFLOW.read_text())

    def test_template_calls_our_wrapper(self):
        """The toolbox ref is pinned in one place, the wrapper, not in every product repo."""
        workflow = WORKFLOW.read_text()
        self.assertIn("uses: the-events-calendar/actions/.github/actions/release-prep@main", workflow)
        self.assertNotIn("stellarwp/plugin-toolbox", workflow)

    def test_wrapper_pins_the_toolbox_action_to_a_commit(self):
        """The bot token reaches this code, so it must not be a ref that can move under us."""
        self.assertRegex(WRAPPER.read_text(), r"uses: stellarwp/plugin-toolbox/\.github/actions/release-prep@[0-9a-f]{40}\b")

    def test_plugin_repos_receive_the_workflow(self):
        """common and every plugin are prepared the same way."""
        sync = (ROOT / ".github/sync.yml").read_text()
        plugins_group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release-prep.yml", plugins_group)
        self.assertIn("the-events-calendar/tribe-common@main", plugins_group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
