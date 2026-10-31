#!/usr/bin/env python3
"""Regression checks for release-publish.yml: the title, the zip name and the changelog it reads.

The script under test is extracted from the workflow rather than restated here, so
there is only ever one copy of the logic.

Run: python3 tests/test-release-publish.py
"""

from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/release-publish.yml"
STEP = "Read the title, zip name and changelog"

README = """\
=== The Events Calendar ===

== Changelog ==

= [6.18.31] 2026-11-30 =

* Fix - Not this one.

= [6.18.3] 2026-10-29 =

* Language - 0 new strings added, 34 updated, 0 fuzzied, and 0 obsoleted.\r
* Security - Hardened how Event details are saved.

* Fix - A second group after a blank line.


= [6.18.2] 2026-10-15 =

* Fix - Not this one either.
"""


def extract_run_block() -> str:
    """Pull the `run: |` body out of the named step."""
    text = WORKFLOW.read_text()
    start = text.index(f"- name: {STEP}")
    body = text[text.index("run: |", start) + len("run: |\n"):]
    lines, indent = [], None
    for line in body.splitlines():
        if line.strip() == "":
            lines.append("")
            continue
        current = len(line) - len(line.lstrip())
        if indent is None:
            indent = current
        elif current < indent:
            break
        lines.append(line[indent:])
    assert lines, "could not extract the run block"
    return "\n".join(lines)


class PrepareTests(unittest.TestCase):
    def run_step(self, version="6.18.3", readme=README, puprc='{\n\t"zip_name": "events-calendar-pro"\n}\n'):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            if readme is not None:
                (tmp / "readme.txt").write_text(readme)
            if puprc is not None:
                (tmp / ".puprc").write_text(puprc)
            output = tmp / "output"
            output.touch()
            env = {
                **os.environ,
                "TYPE": "Maintenance",
                "VERSION": version,
                "GITHUB_OUTPUT": str(output),
                "GITHUB_REPOSITORY": "the-events-calendar/events-pro",
                "RUNNER_TEMP": str(tmp),
            }
            result = subprocess.run(["bash", "-c", extract_run_block()], cwd=tmp, env=env, capture_output=True, text=True)
            outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
            notes = (tmp / "notes.md").read_text() if (tmp / "notes.md").exists() else None
            return result, outputs, notes

    def test_reads_the_version_section_as_release_notes(self):
        """Only this version's entries, bulleted with "-" like the releases so far, no stray blank lines."""
        result, outputs, notes = self.run_step()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            notes,
            "- Language - 0 new strings added, 34 updated, 0 fuzzied, and 0 obsoleted.\n"
            "- Security - Hardened how Event details are saved.\n"
            "\n"
            "- Fix - A second group after a blank line.\n",
        )
        self.assertEqual(outputs["title"], "Maintenance Release 6.18.3")
        self.assertEqual(outputs["zip-name"], "events-calendar-pro")

    def test_zip_name_falls_back_to_the_repository_name(self):
        """A repository without .puprc names its zip after itself."""
        result, outputs, _ = self.run_step(puprc=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs["zip-name"], "events-pro")

    def test_a_version_missing_from_the_changelog_fails(self):
        """A release with empty notes means release prep did not run on that branch."""
        result, _, _ = self.run_step(version="6.18.4")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("6.18.4", result.stdout)

    def test_a_malformed_version_fails(self):
        """The version becomes a tag that the tag ruleset will not let anyone delete."""
        for version in ("v6.18.3", "6.18", "6.18.3 ", "6.18.3-beta"):
            with self.subTest(version=version):
                result, _, _ = self.run_step(version=version)
                self.assertNotEqual(result.returncode, 0)


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text()

    def test_inputs_never_reach_a_shell_directly(self):
        """Inputs are free text: they go through env or with, never interpolated into a script."""
        for line in self.workflow.splitlines():
            if "${{ inputs." in line:
                self.assertRegex(line, r"^\s+[\w-]+: ", line)

    def test_publishes_with_the_bot_token(self):
        """The tag ruleset blocks tag creation for everyone off its bypass list, github.token included."""
        self.assertIn("GH_TOKEN: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}", self.workflow)

    def test_plugin_repos_receive_the_workflow(self):
        sync = (ROOT / ".github/sync.yml").read_text()
        plugins_group = sync.split("  # Active Plugin Repositories\n", 1)[1].split("  # Promoter\n", 1)[0]
        self.assertIn("dest: .github/workflows/release-publish.yml", plugins_group)


if __name__ == "__main__":
    unittest.main(verbosity=2)
