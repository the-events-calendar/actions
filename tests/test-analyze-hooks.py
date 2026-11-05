#!/usr/bin/env python3
"""Run the analyze-hooks action's script (Node, TypeScript) against a real git repository.

Run: python3 tests/test-analyze-hooks.py   (needs Node 22.18+, which runs .ts files as they are)
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / ".github/actions/analyze-hooks/analyze-hooks.ts"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}

BEFORE = """<?php
$a = apply_filters( 'tec_kept', $a );
$b = apply_filters( 'tec_removed_filter', $b );
do_action( 'tec_removed_action' );
$c = apply_filters( 'tec_moved', $c );
"""
AFTER = """<?php
$a = apply_filters( 'tec_kept', $a );
do_action( "tec_added_action", $x );
$d = apply_filters( 'tec_added_b', $d ) . apply_filters( 'tec_added_a', $d );
$e = apply_filters( "tec_{$dynamic}_filter", $e );
$f = apply_filters( $variable, $f );
do_action_ref_array( 'tec_added_ref', [ $x ] );
$c = apply_filters( 'tec_moved', $c, 1 );
"""


class AnalyzeHooksTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.write("src/Tribe/Main.php", BEFORE)
        self.write("src/views/v2/list.php", "<?php // list\n")
        self.write("src/views/v2/day.php", "<?php // day\n")
        self.commit("release")
        self.git("tag", "6.18.2")
        self.git("tag", "ft-002")
        self.write("src/Tribe/Main.php", AFTER)
        self.write("src/views/v2/list.php", "<?php // list, changed\n")
        self.commit("work")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV}).stdout

    def write(self, name, body):
        (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / name).write_text(body)

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def run_script(self):
        return subprocess.run(["node", str(SCRIPT)], cwd=self.repo, capture_output=True, text=True,
                              env={**os.environ, "GITHUB_STEP_SUMMARY": os.devnull})

    def entries(self):
        return {p.name: p.read_text() for p in sorted((self.repo / "changelog").glob("*.yaml"))}

    @staticmethod
    def entry(text):
        return f'significance: patch\ntype: tweak\nentry: "{text}"\n'

    def test_added_and_removed_hooks_and_changed_views_are_each_one_entry(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.entries(), {
            "analyze-hooks-added-actions.yaml": self.entry("Added actions: `tec_added_action`, `tec_added_ref`"),
            "analyze-hooks-added-filters.yaml": self.entry("Added filters: `tec_added_a`, `tec_added_b`"),
            "analyze-hooks-removed-actions.yaml": self.entry("Removed actions: `tec_removed_action`"),
            "analyze-hooks-removed-filters.yaml": self.entry("Removed filters: `tec_removed_filter`"),
            "analyze-hooks-changed-views.yaml": self.entry("Changed views: `v2/list`"),
        })

    def test_a_hook_that_only_moved_or_has_a_dynamic_name_is_not_listed(self):
        self.run_script()
        listed = "".join(self.entries().values())
        for name in ("tec_moved", "tec_kept", "dynamic", "variable"):
            self.assertNotIn(name, listed)

    def test_a_name_built_by_concatenation_is_not_a_hook(self):
        self.write("src/Tribe/Concat.php", "<?php\n$a = apply_filters( 'tec_' . $name, $a );\n")
        self.commit("concat")
        self.run_script()
        self.assertNotIn("`tec_`", "".join(self.entries().values()))

    def test_a_hook_with_another_call_left_in_src_is_neither_added_nor_removed(self):
        """The diff shows one occurrence; the whole tree decides."""
        self.write("src/Tribe/Twin.php", "<?php\n$a = apply_filters( 'tec_twin', $a );\n")
        self.commit("twin")
        self.git("tag", "6.18.3")
        self.write("src/Tribe/Twin.php", "<?php\n")
        self.write("src/Tribe/Main.php", AFTER + "$g = apply_filters( 'tec_twin', $g );\n")
        self.commit("move the twin")
        self.run_script()
        self.assertNotIn("tec_twin", "".join(self.entries().values()))

    def test_an_entry_from_an_earlier_run_is_removed_when_its_change_is_reverted(self):
        self.run_script()
        self.assertIn("analyze-hooks-added-actions.yaml", self.entries())
        self.write("src/Tribe/Main.php", BEFORE)
        self.commit("revert")
        self.run_script()
        self.assertEqual(set(self.entries()), {"analyze-hooks-changed-views.yaml"})

    def test_it_compares_with_the_last_release_tag_not_another_tag(self):
        """ft-002 is not a release; a later release tag shortens the range."""
        self.git("tag", "6.18.3")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.entries(), {})

    def test_nothing_changed_writes_nothing(self):
        self.git("tag", "6.19.0")
        self.run_script()
        self.assertEqual(self.entries(), {})

    def test_running_twice_leaves_the_same_files(self):
        self.run_script()
        first = self.entries()
        self.run_script()
        self.assertEqual(self.entries(), first)

    def test_an_entry_the_changelog_or_another_pending_file_has_is_not_written_again(self):
        self.write("changelog.md", "= [6.18.2] =\n\n* Tweak - Changed views: `v2/list`\n")
        self.write("changelog/by-hand.yaml", 'significance: patch\ntype: tweak\nentry: "Removed actions: `tec_removed_action`"\n')
        self.run_script()
        self.assertNotIn("analyze-hooks-changed-views.yaml", self.entries())
        self.assertNotIn("analyze-hooks-removed-actions.yaml", self.entries())
        self.assertIn("analyze-hooks-added-actions.yaml", self.entries())

    def test_no_release_tag_is_an_error(self):
        self.git("tag", "-d", "6.18.2")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No release tag", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
