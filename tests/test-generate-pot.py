#!/usr/bin/env python3
"""Run the generate-pot action's script with stand-ins for php and wp-cli, and check what make-pot is
asked to skip: .distignore, submodules (a single plugin repository) and symlinked directories (the
monorepo's common/ and postcss utilities), all read from the plugin's folder.

Run: python3 tests/test-generate-pot.py
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / ".github/actions/generate-pot/generate-pot.sh"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


class GeneratePotTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        # php records its arguments; wp only has to exist for `command -v wp`.
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.args = self.tmp / "args"
        (self.bin / "php").write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{self.args}"\n')
        (self.bin / "wp").write_text("#!/bin/sh\n")
        for f in ("php", "wp"):
            (self.bin / f).chmod(0o755)

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, env={**os.environ, **GIT_ENV})

    def write(self, name, body=""):
        (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / name).write_text(body)

    def make_pot(self, plugin):
        proc = subprocess.run(
            ["bash", str(SCRIPT)], cwd=self.repo, capture_output=True, text=True,
            env={**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}",
                 "PLUGIN_PATH": str(self.repo / plugin), "POT_PATH": str(self.repo / plugin / "lang/x.pot")})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        args = self.args.read_text().splitlines()
        self.assertIn("make-pot", args)
        self.assertEqual(args[args.index("make-pot") + 1:][:2], [str(self.repo / plugin), str(self.repo / plugin / "lang/x.pot")])
        exclude = next(a for a in args if a.startswith("--exclude="))
        return [e for e in exclude.removeprefix("--exclude=").split(",") if e]

    def test_single_repository_skips_distignore_and_submodules(self):
        self.write(".distignore", "node_modules\ntests\n")
        self.write(".gitmodules", '[submodule "common"]\n\tpath = common\n\turl = ../tribe-common\n')
        self.write("CLAUDE.md")
        os.symlink("CLAUDE.md", self.repo / "AGENTS.md")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "init")

        self.assertEqual(self.make_pot("."), ["node_modules", "tests", "common"])

    def test_monorepo_plugin_skips_its_linked_directories(self):
        self.write("plugins/packages/tribe-common/src/a.php", "<?php\n")
        self.write("plugins/packages/common-styles/x.pcss")
        self.write("plugins/the-events-calendar/.distignore", "tests\n")
        self.write("plugins/the-events-calendar/AGENTS.md")
        self.write("plugins/the-events-calendar/src/resources/postcss/main.pcss")
        os.symlink("../packages/tribe-common", self.repo / "plugins/the-events-calendar/common")
        os.symlink("../../../../packages/common-styles",
                   self.repo / "plugins/the-events-calendar/src/resources/postcss/utilities")
        os.symlink("AGENTS.md", self.repo / "plugins/the-events-calendar/CLAUDE.md")
        self.write(".distignore", "root-only\n")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "init")

        self.assertEqual(self.make_pot("plugins/the-events-calendar"),
                         ["tests", "common", "src/resources/postcss/utilities"])

    def test_a_link_within_the_plugin_keeps_its_strings(self):
        """Only shared code from outside the plugin's folder has its own POT."""
        self.write("src/views/a.php", "<?php\n")
        self.write("dir with space/b.php", "<?php\n")
        self.write("shared/c.php", "<?php\n")
        os.symlink("src/views", self.repo / "views")
        os.symlink("../shared", self.repo / "src/linked shared")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "init")
        (self.repo / "plugin").mkdir()

        self.assertEqual(self.make_pot("."), [])
        os.symlink("../shared", self.repo / "plugin/out")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "plugin")
        self.assertEqual(self.make_pot("plugin"), ["out"])

    def test_a_folder_outside_git_still_gets_a_pot(self):
        (self.repo / ".git").rename(self.repo / "not-git")
        self.write(".distignore", "tests\n")

        self.assertEqual(self.make_pot("."), ["tests"])

    def test_nothing_to_skip(self):
        self.write("src/a.php", "<?php\n")
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "init")

        self.assertEqual(self.make_pot("."), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
