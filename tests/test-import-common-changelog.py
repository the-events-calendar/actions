#!/usr/bin/env python3
"""Run the import-common-changelog action's script against real git repositories: a common and a
plugin that carries it as a submodule, as TEC and ET do.

Run: python3 tests/test-import-common-changelog.py
"""

from pathlib import Path
import os
import re
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
            self.process_common(files)
        self.bump_common()

    def process_common(self, files):
        """Common's release: the entries are deleted and written into changelog.md, in one commit."""
        for name in files:
            (self.common.path / "changelog" / name).unlink()
        with open(self.common.path / "changelog.md", "a") as f:
            f.write("### release\n")
        self.common.commit("Process changelog")

    def bump_common(self):
        sub = self.plugin.path / "common"
        for args in (("fetch", "-q", "origin"), ("checkout", "-q", "origin/main")):
            subprocess.run(["git", *args], cwd=sub, check=True, env={**os.environ, **GIT_ENV})
        self.plugin.commit("bump common")

    def run_script(self):
        proc = subprocess.run(["bash", str(SCRIPT)], cwd=self.plugin.path, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV})
        return proc

    def pending(self):
        """Pending entries by name, without the common commit an imported name ends in."""
        return {re.sub(r"-[0-9a-f]{8}\.yaml$", ".yaml", p.name): p.read_text()
                for p in (self.plugin.path / "changelog").glob("*.yaml")}

    def pending_contents(self):
        return sorted(p.read_text() for p in (self.plugin.path / "changelog").glob("*.yaml"))

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

    def test_ignores_a_prerelease_tag(self):
        """A 6.18.3-rc1 between the release and HEAD would hide the entries before it."""
        self.advance_common({"fix-license.yaml": FIX})
        self.plugin.git("tag", "6.18.3-rc1")
        self.advance_common({"fix-svul-113.yaml": SECURITY})
        self.run_script()
        self.assertEqual(len(self.pending()), 2)

    def test_imports_an_entry_whose_text_is_part_of_a_longer_one(self):
        """Only the same entry counts as a duplicate, not one that merely starts the same way."""
        self.plugin.write("changelog.md", "# Changelog\n\n### [6.18.2] 2026-10-15\n\n"
                                          "* Security - Hardened author handling in the REST API and admin\n")
        self.plugin.commit("longer entry")
        self.plugin.git("tag", "-f", "6.18.2")
        short = "significance: patch\ntype: security\nentry: Hardened author handling in the REST API\n"
        self.advance_common({"rest.yaml": short})
        self.run_script()
        self.assertEqual(list(self.pending().values()), [short])

    def test_skips_a_folded_entry_already_in_the_changelog(self):
        """An entry the YAML folds over two lines is one line in changelog.md."""
        self.plugin.write("changelog.md", "# Changelog\n\n### [6.18.2] 2026-10-15\n\n"
                                          "* Tweak - Added actions: `tribe_settings_form_element_open`, "
                                          "`tribe_settings_form_element_close`\n")
        self.plugin.commit("folded entry, copied by hand")
        self.plugin.git("tag", "-f", "6.18.2")
        self.advance_common({"tut.yaml": FOLDED})
        self.run_script()
        self.assertEqual(self.pending(), {})

    def test_imports_a_folded_entry_that_only_starts_like_an_existing_one(self):
        self.plugin.write("changelog.md", "# Changelog\n\n### [6.18.2] 2026-10-15\n\n"
                                          "* Tweak - Added actions: `tribe_settings_form_element_open`, `other`\n")
        self.plugin.commit("similar entry")
        self.plugin.git("tag", "-f", "6.18.2")
        self.advance_common({"tut.yaml": FOLDED})
        self.run_script()
        self.assertEqual(list(self.pending().values()), [FOLDED])

    def test_keeps_both_entries_when_common_reuses_a_filename(self):
        """Common released twice in the range, with the same entry filename each time."""
        self.advance_common({"fix-license.yaml": FIX}, process=True)
        self.advance_common({"fix-license.yaml": SECURITY}, process=True)
        self.run_script()
        self.assertEqual(self.pending_contents(), sorted([FIX, SECURITY]))

    def test_imports_entries_released_on_a_merged_branch(self):
        """Common releases on a branch that adds the entries and deletes them, then merges it: with
        the default history simplification git skips that side of the merge entirely."""
        self.common.git("checkout", "-q", "-b", "release/C")
        self.common.write("changelog/fix-license.yaml", FIX)
        self.common.commit("entry")
        self.process_common({"fix-license.yaml": FIX})
        self.common.git("checkout", "-q", "main")
        self.common.write("src/other.php", "<?php\n")
        self.common.commit("unrelated")
        self.common.git("merge", "-q", "--no-ff", "--no-edit", "release/C")
        self.bump_common()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {"common-fix-license.yaml": FIX})

    def test_skips_an_entry_added_on_a_branch_the_merge_discarded(self):
        """git merge -s ours keeps the branch in history and none of its files."""
        self.common.git("checkout", "-q", "-b", "obsolete")
        self.common.write("changelog/fix-license.yaml", FIX)
        self.common.commit("entry on an obsolete branch")
        self.common.git("checkout", "-q", "main")
        self.common.write("changelog/fix-svul-113.yaml", SECURITY)
        self.common.commit("entry")
        self.common.git("merge", "-q", "-s", "ours", "--no-edit", "obsolete")
        self.bump_common()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {"common-fix-svul-113.yaml": SECURITY})

    def test_skips_an_entry_common_reverted(self):
        """A deletion that is not a release means the change never shipped."""
        self.advance_common({"fix-license.yaml": FIX, "fix-svul-113.yaml": SECURITY})
        (self.common.path / "changelog/fix-license.yaml").unlink()
        self.common.commit("Revert the license fix")
        self.bump_common()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {"common-fix-svul-113.yaml": SECURITY})

    def test_warns_when_a_newer_release_tag_is_not_merged_in(self):
        """Two release branches open at once: the older one tagged, not yet merged into the newer."""
        self.advance_common({"fix-license.yaml": FIX})
        self.plugin.git("checkout", "-q", "-b", "release/T25")
        self.plugin.write("src/x.php", "<?php\n")
        self.plugin.commit("6.18.3")
        self.plugin.git("tag", "6.18.3")
        self.plugin.git("checkout", "-q", "main")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("::warning::The newest release tag is 6.18.3", proc.stdout)

    def test_imports_the_last_edit_of_an_entry(self):
        edited = FIX.replace("fataling", "fataling on multisite")
        self.advance_common({"fix-license.yaml": FIX})
        self.advance_common({"fix-license.yaml": edited}, process=True)
        self.run_script()
        self.assertEqual(list(self.pending().values()), [edited])

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


class MonorepoImportCommonChangelogTests(unittest.TestCase):
    """The monorepo: common is plugins/packages/tribe-common, linked into the plugin as a symlink, so
    its history is the monorepo's own, and release tags are `<slug>/<version>`."""

    PACKAGE = "plugins/packages/tribe-common"
    PLUGIN = "plugins/the-events-calendar"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self._tmp.name) / "monorepo")
        self.plugin = self.repo.path / self.PLUGIN
        self.repo.write(f"{self.PACKAGE}/changelog/.gitkeep", "")
        self.repo.write(f"{self.PACKAGE}/changelog.md", "# common\n")
        self.repo.write(f"{self.PLUGIN}/changelog/.gitkeep", "")
        self.repo.write(f"{self.PLUGIN}/changelog.md", "# Changelog\n\n### [6.18.2] 2026-10-15\n\n"
                                                       "* Fix - Closed the date picker on an outside click.\n")
        (self.plugin / "common").symlink_to("../packages/tribe-common")
        self.repo.write("plugins/event-tickets/src/x.php", "<?php\n")
        self.repo.commit("release 6.18.2")
        self.repo.git("tag", "the-events-calendar/6.18.2")

    def tearDown(self):
        self._tmp.cleanup()

    def advance_common(self, files, process=False):
        for name, body in files.items():
            self.repo.write(f"{self.PACKAGE}/changelog/{name}", body)
        self.repo.commit("common entries")
        if process:
            for name in files:
                (self.repo.path / self.PACKAGE / "changelog" / name).unlink()
            with open(self.repo.path / self.PACKAGE / "changelog.md", "a") as f:
                f.write("### release\n")
            self.repo.commit("Process common changelog")

    def run_script(self, prefix="the-events-calendar/"):
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.plugin, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV, "TAG_PREFIX": prefix})

    def pending(self):
        return {re.sub(r"-[0-9a-f]{8}\.yaml$", ".yaml", p.name): p.read_text()
                for p in (self.plugin / "changelog").glob("*.yaml")}

    def test_imports_entries_made_only_in_the_package_since_the_plugins_tag(self):
        self.advance_common({"fix-license.yaml": FIX, "fix-svul-113.yaml": SECURITY}, process=True)
        self.advance_common({"pending.yaml": FOLDED})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {"common-fix-license.yaml": FIX, "common-fix-svul-113.yaml": SECURITY,
                                          "common-pending.yaml": FOLDED})
        self.assertFalse((self.repo.path / "changelog").exists())

    def test_leaves_language_and_version_entries_and_reverted_ones_in_common(self):
        self.advance_common({"lang.yaml": LANGUAGE, "assets.yaml": VERSION, "fix-license.yaml": FIX,
                             "fix-svul-113.yaml": SECURITY})
        (self.repo.path / self.PACKAGE / "changelog/fix-svul-113.yaml").unlink()
        self.repo.commit("Revert the svul fix")
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml"})

    def test_skips_an_entry_already_in_the_plugins_changelog(self):
        self.advance_common({"datepicker.yaml": HAND_COPIED, "fix-license.yaml": FIX})
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml"})

    def test_starts_from_the_plugins_own_tag_not_another_plugins_or_a_bare_one(self):
        self.advance_common({"fix-license.yaml": FIX})
        self.repo.git("tag", "event-tickets/6.20.0")
        self.repo.git("tag", "6.19.0")
        self.repo.git("tag", "the-events-calendar/ft-002")
        self.advance_common({"fix-svul-113.yaml": SECURITY})
        self.run_script()
        self.assertEqual(set(self.pending()), {"common-fix-license.yaml", "common-fix-svul-113.yaml"})

    def test_does_nothing_when_only_other_plugins_changed(self):
        self.repo.write("plugins/event-tickets/changelog/et.yaml", FIX)
        self.repo.commit("ET work")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("unchanged", proc.stdout)
        self.assertEqual(self.pending(), {})

    def test_running_it_again_imports_nothing_new(self):
        self.advance_common({"fix-license.yaml": FIX})
        self.run_script()
        first = self.pending()
        self.run_script()
        self.assertEqual(self.pending(), first)

    def test_warns_when_a_newer_tag_of_the_plugin_is_not_merged_in(self):
        self.repo.git("checkout", "-q", "-b", "release/T25")
        self.repo.write(f"{self.PLUGIN}/src/x.php", "<?php\n")
        self.repo.commit("6.18.3")
        self.repo.git("tag", "the-events-calendar/6.18.3")
        self.repo.git("tag", "event-tickets/9.0.0")
        self.repo.git("checkout", "-q", "main")
        proc = self.run_script()
        self.assertIn("::warning::The newest release tag is the-events-calendar/6.18.3", proc.stdout)

    def test_fails_without_a_tag_of_the_plugin(self):
        self.repo.git("tag", "-d", "the-events-calendar/6.18.2")
        self.repo.git("tag", "event-tickets/6.20.0")
        proc = self.run_script()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("fetch-depth: 0", proc.stdout + proc.stderr)

    def test_a_link_to_the_repository_root_or_a_missing_folder_fails_with_a_message(self):
        link = self.plugin / "common"
        for target, message in (("../..", "below the repository root"), ("../packages/nowhere", "not to a folder")):
            with self.subTest(target=target):
                link.unlink()
                link.symlink_to(target)
                self.repo.commit(f"link to {target}")
                proc = self.run_script()
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("::error::", proc.stdout)
                self.assertIn(message, proc.stdout)

    def test_a_plugin_without_the_link_imports_nothing(self):
        (self.plugin / "common").unlink()
        self.repo.commit("no common")
        self.advance_common({"fix-license.yaml": FIX})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.pending(), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
