#!/usr/bin/env python3
"""Run the import-common-changelog action's script against real git repositories: a common and a
plugin that carries it as a submodule, as TEC and ET do.

Run: python3 tests/test-import-common-changelog.py
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / ".github/actions/import-common-changelog/import-common-changelog.sh"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    # The test's common is a local path; git refuses file:// submodules by default.
    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.file.allow", "GIT_CONFIG_VALUE_0": "always",
}

FIX = "significance: patch\ntype: fix\nentry: Stopped the license check from fataling.\n"
SECURITY = "significance: patch\ntype: security\nentry: Hardened author handling in the REST API.\n"
LANGUAGE = "significance: patch\ntype: language\nentry: 3 new strings added.\n"
VERSION = "significance: patch\ntype: version\nentry: Updated stellarwp/assets to 1.5.1.\n"
FOLDED = ("significance: patch\ntype: tweak\nentry: \"Added actions: `tribe_settings_form_element_open`,\n"
          "  `tribe_settings_form_element_close`\"\ntimestamp: 2026-09-30T16:41:42.138Z\n")
HAND_COPIED = "significance: patch\ntype: fix\nentry: Closed the date picker on an outside click.\n"


class Repo:
    def __init__(self, path: Path):
        self.path = path
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.path, check=True, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV}).stdout.strip()

    def write(self, name, body):
        (self.path / name).parent.mkdir(parents=True, exist_ok=True)
        (self.path / name).write_text(body)

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")


class ImportCommonChangelogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)

        self.common = Repo(root / "tribe-common")
        self.common.write("changelog/.gitkeep", "")
        self.released = self.common.commit("common at the plugin's last release")

        self.plugin = Repo(root / "plugin")
        self.plugin.git("submodule", "add", "-q", str(self.common.path), "common")
        self.plugin.write("changelog/.gitkeep", "")
        self.plugin.write("changelog.md", "# Changelog\n\n### [6.18.2] 2026-10-15\n\n"
                                          "* Fix - Closed the date picker on an outside click.\n")
        self.plugin.commit("release 6.18.2")
        self.plugin.git("tag", "6.18.2")

    def tearDown(self):
        self._tmp.cleanup()

    def advance_common(self, files, process=False):
        """Commit entries to common, then optionally run common's own release, which deletes them."""
        for name, body in files.items():
            self.common.write(f"changelog/{name}", body)
        self.common.commit("entries")
        if process:
            for name in files:
                (self.common.path / "changelog" / name).unlink()
            self.common.commit("Process changelog")
        sub = self.plugin.path / "common"
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=sub, check=True, env={**os.environ, **GIT_ENV})
        subprocess.run(["git", "checkout", "-q", "origin/main"], cwd=sub, check=True, env={**os.environ, **GIT_ENV})
        self.plugin.commit("bump common")

    def run_script(self):
        proc = subprocess.run(["bash", str(SCRIPT)], cwd=self.plugin.path, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV})
        return proc

    def pending(self):
        return {p.name: p.read_text() for p in (self.plugin.path / "changelog").glob("*.yaml")}

    def test_imports_entries_common_already_processed(self):
        """Common's release deletes its entries; they are read from its history instead."""
        self.advance_common({"fix-license.yaml": FIX, "fix-svul-113.yaml": SECURITY}, process=True)
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {"common-fix-license.yaml": FIX, "common-fix-svul-113.yaml": SECURITY})

    def test_imports_entries_common_has_not_processed_yet(self):
        self.advance_common({"fix-license.yaml": FIX})
        self.run_script()
        self.assertEqual(self.pending(), {"common-fix-license.yaml": FIX})

    def test_copies_a_folded_entry_verbatim(self):
        self.advance_common({"tut.yaml": FOLDED}, process=True)
        self.run_script()
        self.assertEqual(self.pending(), {"common-tut.yaml": FOLDED})

    def test_leaves_language_and_version_entries_in_common(self):
        self.advance_common({"lang.yaml": LANGUAGE, "assets.yaml": VERSION, "fix-license.yaml": FIX})
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml"})

    def test_skips_an_entry_already_copied_by_hand(self):
        """The plugin's changelog carrying the entry already is how it was done before this step."""
        self.advance_common({"datepicker.yaml": HAND_COPIED, "fix-license.yaml": FIX})
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml"})

    def test_skips_an_entry_a_pending_plugin_entry_repeats(self):
        self.plugin.write("changelog/fix-license-in-tec.yaml", FIX)
        self.plugin.commit("hand-written copy")
        self.advance_common({"fix-license.yaml": FIX})
        self.run_script()
        self.assertEqual(set(self.pending()), {"fix-license-in-tec.yaml"})

    def test_running_it_again_imports_nothing_new(self):
        self.advance_common({"fix-license.yaml": FIX})
        self.run_script()
        first = self.pending()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), first)

    def test_does_nothing_when_common_has_not_moved(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {})

    def test_does_nothing_in_a_plugin_without_common(self):
        """ECP, ETP and the other add-ons ship common through TEC or ET, not themselves."""
        other = Repo(Path(self._tmp.name) / "add-on")
        other.commit("init")
        proc = subprocess.run(["bash", str(SCRIPT)], cwd=other.path, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((other.path / "changelog").exists())

    def test_ignores_a_nearer_tag_that_is_not_a_release(self):
        """Repos carry tags such as ft-002; one after the release would hide the entries before it."""
        self.advance_common({"fix-license.yaml": FIX})
        self.plugin.git("tag", "ft-002")
        self.advance_common({"fix-svul-113.yaml": SECURITY})
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml", "common-fix-svul-113.yaml"})

    def test_fails_without_a_reachable_tag(self):
        """Without the last release there is no range, and guessing one would drop entries."""
        self.plugin.git("tag", "-d", "6.18.2")
        self.advance_common({"fix-license.yaml": FIX})
        proc = self.run_script()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("fetch-depth: 0", proc.stdout + proc.stderr)
        self.assertEqual(self.pending(), {})

    def test_fails_when_the_last_release_common_is_not_in_the_checkout(self):
        """A shallow submodule is missing the old end of the range."""
        self.advance_common({"fix-license.yaml": FIX})
        missing = "1" * 40
        self.plugin.git("checkout", "-q", "6.18.2")
        self.plugin.git("update-index", "--cacheinfo", f"160000,{missing},common")
        self.plugin.git("commit", "-q", "-m", "release with a common the checkout lacks")
        self.plugin.git("tag", "-f", "6.18.2")
        self.plugin.git("checkout", "-q", "main")
        self.plugin.git("merge", "-q", "--no-edit", "-s", "ours", "6.18.2")
        proc = self.run_script()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not in the checkout", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
