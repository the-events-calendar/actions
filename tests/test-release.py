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
# Each step's text, keyed by its name: the body runs to the next step.
STEPS = {
    m.group(1): m.group(0)
    for m in re.finditer(r"      - name: (.+)\n(?:(?!      - name: ).*\n?)*", WORKFLOW.read_text())
}


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

    def test_nothing_is_merged_back_unless_asked(self):
        """We work with release branches: develop-branch defaults to empty, which skips the second merge."""
        text = WRAPPERS["release-merge"].read_text()
        self.assertRegex(text, r'develop-branch:\n(?:    .*\n)*?    default: ""')

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

    def test_only_release_branches_are_merged(self):
        """The bot token bypasses the branch rules, so any other branch would reach main unreviewed."""
        guard = STEPS["Check that the run is on the release branch it merges"]
        self.assertIn('release/*) ;;', guard)

    def test_version_is_checked_before_anything_reads_it(self):
        guard = STEPS["Check that the run is on the release branch it merges"]
        self.assertIn(r'^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$', guard)

    def test_notes_and_zip_are_checked_before_the_merge(self):
        """A missing changelog or a wrong zip stops the run before main is touched."""
        workflow = WORKFLOW.read_text()
        merge = workflow.index("- name: Merge the release")
        self.assertLess(workflow.index("- name: Read the title, zip name and changelog"), merge)
        self.assertLess(workflow.index("- name: Download and check the zip"), merge)

    def test_checks_read_the_commit_that_is_merged(self):
        checkout = STEPS["Checkout the release branch at the commit the run started on"]
        self.assertIn("ref: ${{ github.sha }}", checkout)

    def test_zip_version_is_read_from_the_main_plugin_file(self):
        """Another PHP file, or no file at all, must not satisfy the check."""
        step = STEPS["Download and check the zip"]
        self.assertNotIn("xargs", step)
        self.assertIn("MAIN_FILE", step)
        self.assertIn("select(test(\"^[^/]+\\\\.php$\"))", STEPS["Read the title, zip name and changelog"])

    def test_zip_name_is_a_plain_file_name(self):
        """It comes from .puprc and becomes a path and a $GITHUB_OUTPUT line."""
        self.assertIn("^[A-Za-z0-9._-]+$", STEPS["Read the title, zip name and changelog"])

    def test_the_release_pull_request_has_to_be_approved_at_this_commit(self):
        """The bot token bypasses main's review rule, so the run checks the approval itself."""
        workflow = WORKFLOW.read_text()
        step = STEPS["Check that the release pull request is approved at this commit"]
        self.assertLess(workflow.index("- name: Check that the release pull request is approved"), workflow.index("- name: Merge the release"))
        self.assertIn(".headRefOid == $sha", step)
        # main keeps an approval after a push: the approval has to be of this very commit.
        self.assertIn('.state == "APPROVED" and .commit_id == $sha', step)
        self.assertIn("group_by(.user.id) | map(last)", step)
        self.assertNotIn("reviewDecision", step)
        # Anyone can approve on a public repository: only the org's people count, never a bot.
        self.assertIn('.user.type != "Bot"', step)
        self.assertIn('IN("OWNER", "MEMBER", "COLLABORATOR")', step)
        self.assertIn("isCrossRepository | not", step)
        self.assertIn("pull-requests: read", workflow)

    def test_a_branch_main_has_moved_past_is_refused(self):
        """Otherwise the merge commit holds code the zip, built from the branch, does not."""
        step = STEPS["Check that the release pull request is approved at this commit"]
        self.assertIn("compare/${BASE}...${SHA}", step)
        self.assertIn('"diverged"', step)

    def test_readme_says_the_zip_is_optional(self):
        self.assertIn("only when `zip-url` is given", (ROOT / "readme.md").read_text())

    def test_zip_stays_inside_the_checkout(self):
        """release-publish reads assets relative to the checkout."""
        self.assertNotIn("RUNNER_TEMP/${ZIP_NAME}", WORKFLOW.read_text())

    def test_plugin_repos_receive_the_workflow(self):
        sync = (ROOT / ".github/sync.yml").read_text()
        group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release.yml", group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
