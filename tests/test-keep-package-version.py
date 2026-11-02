#!/usr/bin/env python3
"""Run the release-prep wrapper's keep-package-version.sh against a real git repository, then stage the
way the toolbox does (git add --all) after pup has written the release version everywhere.

Run: python3 tests/test-keep-package-version.py
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / ".github/actions/release-prep/keep-package-version.sh"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}

# The changelogger's "version" type comes after the package's own version, as in ET's package.json.
PACKAGE = '{\n\t"name": "event-tickets",\n\t"version": "%s",\n\t"changelogger": {\n\t\t"types": {\n\t\t\t"version": "Version"\n\t\t}\n\t}\n}\n'


class KeepPackageVersionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self.git("init", "-q", "-b", "release/M26.raichu.1")
        (self.path / "package.json").write_text(PACKAGE % "5.30.3")
        (self.path / "event-tickets.php").write_text(" * Version: 5.30.3\n")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "init")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.path, check=True, capture_output=True, text=True,
                              env={**os.environ, **GIT_ENV}).stdout

    def prepare(self, version):
        """Runs the script, then what the toolbox does: pup writes every version file, git add --all."""
        subprocess.run(["bash", str(SCRIPT)], cwd=self.path, check=True, capture_output=True,
                       env={**os.environ, **GIT_ENV, "VERSION": version})
        (self.path / "package.json").write_text(PACKAGE % version)
        (self.path / "event-tickets.php").write_text(f" * Version: {version}\n")
        self.git("add", "--all")

    def staged(self, name):
        return self.git("show", f":{name}")

    def test_a_four_part_version_commits_its_three_part_start_in_package_json(self):
        self.prepare("5.30.3.1")
        self.assertEqual(self.staged("package.json"), PACKAGE % "5.30.3")
        self.assertEqual(self.staged("event-tickets.php"), " * Version: 5.30.3.1\n")

    def test_a_branch_already_holding_a_four_part_package_version_is_put_back(self):
        """A prep run before this fix committed 5.30.3.1; running the prep again repairs it."""
        (self.path / "package.json").write_text(PACKAGE % "5.30.3.1")
        self.git("commit", "-q", "-am", "broken prep")
        self.prepare("5.30.3.1")
        self.assertEqual(self.staged("package.json"), PACKAGE % "5.30.3")

    def test_a_later_security_release_keeps_the_same_start(self):
        self.prepare("5.30.3.12")
        self.assertEqual(self.staged("package.json"), PACKAGE % "5.30.3")

    def test_a_three_part_version_is_left_to_pup(self):
        self.prepare("5.31.0")
        self.assertEqual(self.staged("package.json"), PACKAGE % "5.31.0")

    def test_a_repository_without_package_json_is_left_alone(self):
        self.git("rm", "-q", "package.json")
        self.git("commit", "-q", "-m", "no package.json")
        subprocess.run(["bash", str(SCRIPT)], cwd=self.path, check=True, capture_output=True,
                       env={**os.environ, **GIT_ENV, "VERSION": "5.30.3.1"})
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
