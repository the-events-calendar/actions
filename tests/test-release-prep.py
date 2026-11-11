#!/usr/bin/env python3
"""Pin the release prep wiring between the template, our wrapper and the plugin repos.

Run: python3 tests/test-release-prep.py
"""

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
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
        for action in ("push-translations", "generate-pot", "add-changelog", "analyze-hooks"):
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
                     "- name: Import common's changelog entries", "- name: Add the hook and view changelog entries",
                     "- name: Generate the POT file", "- name: Add the language changelog entry"):
            self.assertLess(workflow.index(step), prep, step)

    def test_the_language_entry_is_written_after_the_others(self):
        """The changelogger sorts one write by type; a second write appends, so Language lands last."""
        workflow = WORKFLOW.read_text()
        write = workflow.index("- name: Write the changelog before the language entry")
        self.assertLess(workflow.index("- name: Import common's changelog entries"), write)
        self.assertLess(workflow.index("- name: Add the hook and view changelog entries"), write)
        self.assertLess(write, workflow.index("- name: Add the language changelog entry"))
        self.assertRegex(workflow, r"uses: stellarwp/changelogger@[0-9a-f]{40}\b")

    def step_script(self, name):
        """The run script of a template step, found by its name."""
        step = WORKFLOW.read_text().split("- name: " + name, 1)[1].split("\n      - name:", 1)[0]
        return re.search(r"run: \|\n((?:\s{10}.*\n?)+)", step).group(1)

    def test_the_changelog_date_takes_a_date_today_or_tomorrow(self):
        """The toolbox only takes YYYY-MM-DD; forms GNU date reads as another day are refused."""
        script = self.step_script("Resolve the changelog date")
        # The runner's date is GNU; on macOS run the script against coreutils' gdate.
        env = dict(os.environ)
        gdate = shutil.which("gdate")
        if gdate:
            bin_dir = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, bin_dir)
            os.symlink(gdate, os.path.join(bin_dir, "date"))
            env["PATH"] = bin_dir + os.pathsep + env["PATH"]
        elif subprocess.run(["date", "--version"], capture_output=True).returncode != 0:
            self.skipTest("needs GNU date")

        def day(when):
            return subprocess.check_output(["date", "-u", "-d", when, "+%F"], text=True, env=env).strip()

        def run(given):
            out = tempfile.NamedTemporaryFile("r")
            summary = tempfile.NamedTemporaryFile("r")
            self.addCleanup(out.close)
            self.addCleanup(summary.close)
            result = subprocess.run(["bash", "-e", "-c", script], capture_output=True, text=True,
                                    env={**env, "RELEASE_DATE": given, "GITHUB_OUTPUT": out.name,
                                         "GITHUB_STEP_SUMMARY": summary.name})
            return result, out.read(), summary.read()

        today, tomorrow = day("today"), day("tomorrow")
        for given, expected in (("", today), ("today", today), ("tomorrow", tomorrow), ("2026-01-02", "2026-01-02")):
            result, output, summary = run(given)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.strip(), "date=" + expected, repr(given))
            self.assertIn(expected, summary, repr(given))
        # US mm/dd, a bare number read as an hour, a typo, an impossible day, a version.
        for given in ("02/01/2026", "12", "next friday", "tomorow", "2026-02-30", "6.18.3"):
            result, output, _ = run(given)
            self.assertNotEqual(result.returncode, 0, repr(given))
            self.assertEqual(output, "", repr(given))

    def test_the_changelog_date_is_resolved_before_anything_is_written(self):
        """It can fail, so it runs before GlotPress, and both writes share its one date."""
        workflow = WORKFLOW.read_text()
        resolve = workflow.index("- name: Resolve the changelog date")
        for step in ("- name: Update the WordPress version", "- name: Push the POT file to GlotPress"):
            self.assertLess(resolve, workflow.index(step), step)
        # The changelogger write and the toolbox write share one date, even across UTC midnight.
        self.assertEqual(workflow.count("date: ${{ steps.changelog-date.outputs.date }}"), 2)
        self.assertNotIn("date: ${{ inputs.date }}", workflow)

    def test_the_version_check_refuses_a_tagged_version(self):
        """The toolbox refuses it too, but only after the POT push."""
        script = self.step_script("Check the version")
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        for args in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "init"], ["tag", "6.18.3"]):
            subprocess.run(["git", *args], cwd=repo, check=True, env=git_env)
        for version, code in (("6.18.3", 1), ("6.18.4", 0)):
            result = subprocess.run(["bash", "-e", "-c", script], cwd=repo, capture_output=True, text=True,
                                    env={**git_env, "VERSION": version, "TESTED_UP_TO": "", "UPDATE_MIN_VERSION": ""})
            self.assertEqual(result.returncode, code, version)

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
        self.assertIn("-I'X-Generator:'", workflow)

    def test_plugin_repos_receive_the_workflow(self):
        """common and every plugin are prepared the same way."""
        sync = (ROOT / ".github/sync.yml").read_text()
        plugins_group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release-prep.yml", plugins_group)
        self.assertIn("the-events-calendar/tribe-common@main", plugins_group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
