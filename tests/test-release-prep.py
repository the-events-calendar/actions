#!/usr/bin/env python3
"""Pin the release prep wiring between the template, our wrapper and the plugin repos.

Run: python3 tests/test-release-prep.py
"""

from pathlib import Path
import re
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

    def test_third_party_actions_on_the_way_to_the_commit_are_pinned(self):
        """They run in the job that hands the bot token to the toolbox, so a tag must not move."""
        for action in ("push-translations", "generate-pot", "add-changelog"):
            text = (ROOT / ".github/actions" / action / "action.yml").read_text()
            for ref in re.findall(r"uses:\s*(\S+)", text):
                if ref.startswith("./") or ref.startswith("the-events-calendar/"):
                    continue
                self.assertRegex(ref, r"@[0-9a-f]{40}$", f"{action}: {ref}")
        self.assertIn("sha512sum -c", (ROOT / ".github/actions/generate-pot/action.yml").read_text())
        self.assertIn('pup-version: "2.0.0"', WRAPPER.read_text())

    def test_the_job_never_writes_with_the_github_token(self):
        """The commit uses the bot token; a write-scoped github.token would reach every step before it."""
        self.assertNotIn("contents: write", WORKFLOW.read_text())

    def test_template_fetches_the_history_the_common_import_reads(self):
        """The import diffs common between the last release tag and HEAD."""
        self.assertIn("fetch-depth: 0", WORKFLOW.read_text())

    def test_every_file_writing_step_runs_before_the_commit(self):
        """The toolbox action commits the working tree; a step after it would be left out."""
        workflow = WORKFLOW.read_text()
        prep = workflow.index("- name: Prepare the release branch")
        for step in ("- name: Check the version", "- name: Update the WordPress version",
                     "- name: Import common's changelog entries",
                     "- name: Generate the POT file", "- name: Add the language changelog entry"):
            self.assertLess(workflow.index(step), prep, step)

    def test_the_version_is_checked_before_anything_is_written(self):
        workflow = WORKFLOW.read_text()
        check = workflow.index("- name: Check the version")
        for step in ("- name: Update the WordPress version", "- name: Push the POT file to GlotPress"):
            self.assertLess(check, workflow.index(step), step)

    def test_the_pot_check_ignores_the_headers_every_run_rewrites(self):
        """make-pot stamps the date and the plugin version; a re-run after the bump changes both."""
        workflow = WORKFLOW.read_text()
        self.assertIn("-I'POT-Creation-Date:'", workflow)
        self.assertIn("-I'Project-Id-Version:'", workflow)

    def test_plugin_repos_receive_the_workflow(self):
        """common and every plugin are prepared the same way."""
        sync = (ROOT / ".github/sync.yml").read_text()
        plugins_group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release-prep.yml", plugins_group)
        self.assertIn("the-events-calendar/tribe-common@main", plugins_group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
