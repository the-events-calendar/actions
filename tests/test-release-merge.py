#!/usr/bin/env python3
"""Run .github/actions/release-merge/merge.sh against a stubbed gh.

Run: python3 tests/test-release-merge.py
"""

from pathlib import Path
import json
import os
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".github/actions/release-merge/merge.sh"
REPO = "the-events-calendar/tribe-common"
TIP = "a" * 40
BASE_TIP = "b" * 40
MERGE = "c" * 40

# Answers `gh api` from ROUTES ("METHOD path" -> [status, body]), applies --jq with the real jq, and
# logs every call to LOG.
STUB = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, subprocess, sys
    args = sys.argv[2:]
    method, fields, jq, silent, path = "GET", {}, None, False, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-X": method = args[i + 1]; i += 2; continue
        if a == "-f": k, v = args[i + 1].split("=", 1); fields[k] = v; i += 2; continue
        if a == "--jq": jq = args[i + 1]; i += 2; continue
        if a == "--silent": silent = True; i += 1; continue
        path = a; i += 1
    with open(os.environ["LOG"], "a") as log:
        log.write(json.dumps([method, path, fields]) + "\\n")
    status, body = json.load(open(os.environ["ROUTES"])).get(f"{method} {path}", [404, {"message": "Not Found"}])
    if status >= 400:
        # As gh does: the body on stdout, the message on stderr.
        sys.stdout.write(json.dumps(body))
        sys.stderr.write(f"gh: {body.get('message', '')} (HTTP {status})\\n")
        sys.exit(1)
    if silent or status == 204:
        sys.exit(0)
    text = json.dumps(body)
    if jq:
        text = subprocess.run(["jq", "-r", jq], input=text, capture_output=True, text=True, check=True).stdout
    sys.stdout.write(text)
''')


def routes(**extra):
    base = {
        f"GET repos/{REPO}/git/ref/heads/release/M26.raichu.2": [200, {"object": {"sha": TIP}}],
        f"GET repos/{REPO}/git/ref/heads/main": [200, {"object": {"sha": BASE_TIP}}],
        f"POST repos/{REPO}/merges": [201, {"sha": MERGE}],
    }
    base.update(extra)
    return base


class MergeTests(unittest.TestCase):
    def run_merge(self, routes_map, **env):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "gh").write_text(STUB)
            (tmp / "gh").chmod(0o755)
            (tmp / "routes.json").write_text(json.dumps(routes_map))
            out = tmp / "output"
            out.touch()
            full = {
                "PATH": f"{tmp}:{os.environ['PATH']}",
                "ROUTES": str(tmp / "routes.json"),
                "LOG": str(tmp / "log"),
                "GITHUB_OUTPUT": str(out),
                "GITHUB_REPOSITORY": REPO,
                "GH_TOKEN": "x",
                "BRANCH": "release/M26.raichu.2",
                "HEAD": TIP,
                "VERSION": "6.14.0.1",
                "BASE": "main",
                "DEVELOP": "",
            }
            full.update(env)
            result = subprocess.run(["bash", str(SCRIPT)], env=full, capture_output=True, text=True)
            log = [json.loads(l) for l in (tmp / "log").read_text().splitlines()] if (tmp / "log").exists() else []
            return result, out.read_text(), log

    def merges(self, log):
        return [fields for method, path, fields in log if method == "POST"]

    def test_four_part_release_merges_without_reading_any_version_file(self):
        result, output, log = self.run_merge(routes())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"base-sha={MERGE}", output)
        self.assertIn("version=6.14.0.1", output)
        self.assertEqual(self.merges(log), [{"base": "main", "head": TIP, "commit_message": "Merge branch 'release/M26.raichu.2' into main"}])
        self.assertFalse([p for _, p, _ in log if "contents/" in p], "no file is read")

    def test_merges_the_commit_the_run_started_on_not_the_branch_name(self):
        _, _, log = self.run_merge(routes())
        self.assertEqual(self.merges(log)[0]["head"], TIP)

    def test_a_branch_that_moved_is_refused(self):
        result, output, log = self.run_merge(routes(), HEAD="d" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("moved after the run started", result.stdout)
        self.assertEqual(self.merges(log), [])
        self.assertEqual(output, "")

    def test_a_tag_from_an_earlier_release_is_refused(self):
        result, _, log = self.run_merge(routes(**{
            f"GET repos/{REPO}/git/ref/tags/6.14.0.1": [200, {}],
            f"GET repos/{REPO}/compare/6.14.0.1...{TIP}": [200, {"status": "diverged"}],
        }))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("was released before", result.stdout)
        self.assertEqual(self.merges(log), [])

    def test_a_repeated_run_passes(self):
        """The tag holds the branch and main already holds it: the merge is a no-op."""
        result, output, _ = self.run_merge(routes(**{
            f"GET repos/{REPO}/git/ref/tags/6.14.0.1": [200, {}],
            f"GET repos/{REPO}/compare/6.14.0.1...{TIP}": [200, {"status": "behind"}],
            f"POST repos/{REPO}/merges": [204, {}],
        }))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"base-sha={BASE_TIP}", output)

    def test_a_conflict_fails_with_its_message(self):
        result, output, _ = self.run_merge(routes(**{f"POST repos/{REPO}/merges": [409, {"message": "Merge conflict"}]}))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::release/M26.raichu.2 conflicts with main", result.stdout)
        self.assertEqual(output, "")

    def test_develop_gets_the_base_when_set(self):
        result, _, log = self.run_merge(routes(), DEVELOP="develop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.merges(log)[1], {"base": "develop", "head": MERGE, "commit_message": "Merge branch 'main' into develop"})

    def test_bad_inputs_are_refused_before_any_call(self):
        for env in ({"VERSION": "6.14.0-beta.1"}, {"VERSION": "6.14.0.1\nx=1"}, {"BRANCH": "refs/heads/x"},
                    {"BRANCH": "main"}, {"HEAD": "abc"}, {"BRANCH": "release/$(id)"}):
            result, _, log = self.run_merge(routes(), **env)
            self.assertNotEqual(result.returncode, 0, env)
            self.assertEqual(log, [], env)


if __name__ == "__main__":
    unittest.main(verbosity=2)
