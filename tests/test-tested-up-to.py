#!/usr/bin/env python3
"""Regression checks for the "Tested up to" check.

The check runs two ways from one file, and both are covered here. The pull request
workflow runs it as a plain script, which is the matrix below; pup runs it as a simple
check registered in .puprc, which is the parity block at the end. Every case builds a
throwaway repository around the real template file.

The current WordPress release is read from the same API the check uses, and the
fixtures are derived from it, so nothing here goes stale on a WordPress release.

Needs php and network access. The pup phar is downloaded once into tests/.cache/.

Run it with: python3 tests/test-tested-up-to.py
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "templates/bin/check-tested-up-to.php"
SLUG = "tested-up-to-is-up-to-date"
API = "https://api.wordpress.org/core/version-check/1.7/"
PUP_URL = "https://github.com/stellarwp/pup/releases/download/1.3.9/pup.phar"
CACHE = ROOT / "tests/.cache"

PUPRC = json.dumps(
    {
        "paths": {"versions": []},
        "checks": {SLUG: {"type": "simple", "file": "bin/check-tested-up-to.php"}},
    }
)

# tribe-common's readme.txt shape: a changelog with no plugin header block at all.
CHANGELOG_ONLY_README = """\
== Changelog ==

= [6.12.3] 2026-09-03 =

* Fix - Added a warning when a Unified license key is entered.
"""


def latest_wp() -> str:
    """The version the check will compare against."""
    with urllib.request.urlopen(API, timeout=30) as response:
        body = response.read().decode("utf-8")
    # The payload carries a raw control character; Python's strict decoder rejects it
    # where PHP's json_decode does not.
    return json.loads(body, strict=False)["offers"][0]["version"]


def pup_phar() -> pathlib.Path:
    """Download the pinned pup once, into an ignored cache directory."""
    CACHE.mkdir(parents=True, exist_ok=True)
    phar = CACHE / "pup.phar"
    if not phar.exists():
        urllib.request.urlretrieve(PUP_URL, phar)
    return phar


def run(readme, base_ref=None, via_pup=False):
    """Run the check in a throwaway repository. Returns (exit code, combined output)."""
    with tempfile.TemporaryDirectory() as directory:
        work = pathlib.Path(directory)
        (work / "bin").mkdir()
        shutil.copy(CHECK, work / "bin/check-tested-up-to.php")
        command = ["php", "bin/check-tested-up-to.php"]
        if via_pup:
            shutil.copy(pup_phar(), work / "bin/pup.phar")
            (work / ".puprc").write_text(PUPRC)
            command = ["php", "bin/pup.phar", f"check:{SLUG}"]
        if readme is not None:
            (work / "readme.txt").write_text(readme)

        env = dict(os.environ)
        env.pop("GITHUB_BASE_REF", None)
        if base_ref is not None:
            env["GITHUB_BASE_REF"] = base_ref

        proc = subprocess.run(
            command, cwd=work, capture_output=True, text=True, env=env,
        )
        return proc.returncode, proc.stdout + proc.stderr


def header(version: str, trailer: str = "") -> str:
    """A readme.txt whose plugin header block is tested up to the given version."""
    return (
        "=== The Events Calendar ===\n"
        "\n"
        "Contributors: theeventscalendar\n"
        "Stable tag: 6.17.1\n"
        "Requires at least: 6.7\n"
        f"Tested up to: {version}\n"
        "Requires PHP: 7.4\n"
        "\n"
        "== Description ==\n"
        f"{trailer}"
    )


def main() -> int:
    if shutil.which("php") is None:
        print("needs php; skipping")
        return 0

    latest = latest_wp()
    branch = ".".join(latest.split(".")[:2])
    major = int(latest.split(".")[0])
    stale = f"{major - 1}.0"
    ahead = f"{major + 1}.0"
    print(f"current WordPress release: {latest} (branch {branch}, stale fixture {stale}, ahead fixture {ahead})\n")

    failures = []

    def check(label, cond):
        if not cond:
            failures.append(label)
        print(f"{'ok  ' if cond else 'FAIL'} {label}")

    # The header matching the current release is the whole point of passing.
    code, out = run(header(latest), "main")
    check(f"header {latest} on main passes", code == 0)

    # The shape every repository in the sync group actually ships: the WordPress branch
    # rather than the patch. Comparing it against the full release would fail a
    # repository that is current.
    code, out = run(header(branch), "main")
    check(f"header {branch} on main passes", code == 0)

    # A trailing header fails, and the message has to name both versions so the fix is
    # obvious from the job log alone. The expected version is the branch, because that
    # is what release-update-wp-version.yml writes into readme.txt verbatim.
    code, out = run(header(stale), "main")
    check(f"header {stale} on main fails", code == 1)
    check("the failure names the version found", stale in out)
    check("the failure names the branch expected", f"tested_up_to: {branch}" in out)

    # A header ahead of the current release is legitimate mid-cycle.
    code, _ = run(header(ahead), "main")
    check(f"header {ahead} passes", code == 0)

    # tribe-common: no plugin header block, and it must not reach the network to say so.
    code, out = run(CHANGELOG_ONLY_README, "main")
    check("a changelog-only readme.txt passes", code == 0)

    # A repository with no readme.txt at all is not an error either.
    code, _ = run(None, "main")
    check("a missing readme.txt passes", code == 0)

    # First match wins: a stale version quoted further down the file must not be read
    # as the header.
    code, _ = run(header(latest, f"Tested up to: {stale} was the previous target.\n"), "main")
    check("a stale version in the body does not shadow the header", code == 0)

    # The guard applies to the branches a release is cut from.
    code, _ = run(header(stale), "release/7.2")
    check(f"header {stale} fails on a release branch", code == 1)

    # And not to anything else.
    code, _ = run(header(stale), "feature/something")
    check(f"header {stale} is skipped on a feature branch", code == 0)

    # A production zip build has no base ref, and the header still has to be current.
    code, _ = run(header(stale), None)
    check(f"header {stale} fails with no base ref", code == 1)

    # The same file under pup, which is how a zip build reaches it once .puprc registers
    # the check. The workflow does not need that entry, so this only guards the contract
    # the file keeps with pup: $output is used, not defined, and the int is the status.
    code, out = run(header(branch), "main", via_pup=True)
    check(f"pup: header {branch} passes", code == 0)
    code, out = run(header(stale), "main", via_pup=True)
    check(f"pup: header {stale} fails", code == 1)
    check("pup: the failure names the branch expected", f"tested_up_to: {branch}" in out)
    code, _ = run(None, "main", via_pup=True)
    check("pup: a missing readme.txt passes", code == 0)

    print()
    if failures:
        print(f"{len(failures)} failing check(s): " + ", ".join(failures))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
