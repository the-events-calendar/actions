#!/usr/bin/env python3
"""Pin the release wiring between the template, our wrappers and the toolbox.

Run: python3 tests/test-release.py
"""

from pathlib import Path
import re
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/release.yml"
WRAPPERS = {a: ROOT / f".github/actions/{a}/action.yml" for a in ("release-merge", "release-publish")}
# Each step's text, keyed by its name: the body runs to the next step.
STEPS = {
    m.group(1): m.group(0)
    for m in re.finditer(r"      - name: (.+)\n(?:(?:        .*)?\n)*", WORKFLOW.read_text())
}


class ReleaseTests(unittest.TestCase):
    def test_publish_pins_the_toolbox_action_to_a_commit(self):
        """The bot token reaches this code, so it must not be a ref that can move under us."""
        self.assertRegex(WRAPPERS["release-publish"].read_text(), r"uses: stellarwp/plugin-toolbox/\.github/actions/release-publish@[0-9a-f]{40}\b")

    def test_merge_is_ours_not_the_toolbox(self):
        """The toolbox's release-merge checks package.json against a four-part version and refuses it."""
        text = WRAPPERS["release-merge"].read_text()
        self.assertNotIn("uses:", text)
        self.assertIn('run: bash "$GITHUB_ACTION_PATH/merge.sh"', text)
        self.assertIn("GH_TOKEN: ${{ inputs.token }}", text)

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

    def test_an_approved_pull_request_releases_without_waiting(self):
        """The bot token bypasses main's review rule: an approval of this very commit lets it through."""
        step = STEPS["Check whether the release pull request is approved at this commit"]
        self.assertIn(".headRefOid == $sha", step)
        # main keeps an approval after a push: the approval has to be of this very commit.
        self.assertIn('.state == "APPROVED" and .commit_id == $sha', step)
        self.assertIn("group_by(.user.id) | map(last)", step)
        self.assertIn('any(.state == "CHANGES_REQUESTED")', step)
        # Anyone can review on a public repository: only people with write access count, never a bot.
        self.assertIn('.user.type != "Bot"', step)
        self.assertIn("collaborators/${login}/permission", step)
        self.assertIn('[ "$permission" = admin ] || [ "$permission" = write ]', step)
        # author_association shows a private org member as a CONTRIBUTOR: it must not decide.
        self.assertNotIn("author_association |", step)
        self.assertIn("isCrossRepository | not", step)
        self.assertIn('echo "approved=true"', step)
        # Nobody approves their own release: the dispatcher and the commit's author and committer.
        self.assertIn("ACTOR: ${{ github.actor }}", step)
        self.assertIn("TRIGGERING_ACTOR: ${{ github.triggering_actor }}", step)
        self.assertIn(".author.login?, .committer.login?", step)
        self.assertIn("(.user.login | IN($self[]) | not)", step)
        self.assertIn("pull-requests: read", WORKFLOW.read_text())

    def test_without_one_the_run_waits_for_an_environment_reviewer(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("    needs: check\n", workflow)
        self.assertIn("environment: ${{ needs.check.outputs.approved != 'true' && 'github-release' || '' }}", workflow)

    def test_an_environment_without_reviewers_is_refused(self):
        """GitHub creates a missing environment unprotected, which would run straight through."""
        workflow = WORKFLOW.read_text()
        step = STEPS["Check that the environment has reviewers"]
        self.assertIn("if: needs.check.outputs.approved != 'true'", step)
        self.assertIn('any(.type == "required_reviewers")', step)
        self.assertIn("ENVIRONMENT: github-release", step)
        self.assertIn("actions: read", workflow)
        self.assertLess(workflow.index("- name: Check that the environment has reviewers"), workflow.index("- name: Merge the release"))

    def test_a_branch_main_has_moved_past_is_refused(self):
        """Otherwise the merge commit holds code the zip, built from the branch, does not."""
        workflow = WORKFLOW.read_text()
        step = STEPS["Check that main has nothing the branch lacks"]
        self.assertIn("compare/${BASE}...${SHA}", step)
        self.assertIn('"diverged"', step)
        self.assertLess(workflow.index("- name: Check that main has nothing the branch lacks"), workflow.index("- name: Merge the release"))

    def test_readme_says_the_zip_is_optional(self):
        self.assertIn("only when `zip-url` is given", (ROOT / "readme.md").read_text())

    def test_every_run_script_is_valid_bash(self):
        """String checks miss a broken line, such as a suggestion applied over an old one."""
        for name, step in STEPS.items():
            if "        run: |\n" not in step:
                continue
            script = textwrap.dedent(step.split("        run: |\n", 1)[1])
            result = subprocess.run(["bash", "-n"], input=script, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")

    def test_zip_stays_inside_the_checkout(self):
        """release-publish reads assets relative to the checkout."""
        self.assertNotIn("RUNNER_TEMP/${ZIP_NAME}", WORKFLOW.read_text())

    def test_plugin_repos_receive_the_workflow(self):
        sync = (ROOT / ".github/sync.yml").read_text()
        group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release.yml", group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
