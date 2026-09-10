#!/usr/bin/env python3
"""Regression checks for the version arithmetic in release-update-wp-version.yml.

The script under test is extracted from the workflow rather than restated here, so
there is only ever one copy of the logic.

Run it with: python3 tests/test-wp-version-math.py
"""

import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "templates/workflows/release-update-wp-version.yml"
STEP = "Calculate and update versions"

WORKFLOW_FIXTURE = """\
name: tests
jobs:
  t:
    steps:
      - run: |
          ${SLIC_BIN} wp core update --force --version=6.8
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


def bash_runner():
    """The workflow runs on ubuntu-latest, so the script needs GNU sed.

    Fall back to a container where the host has none, rather than asserting less.
    """
    def probe(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True)
        except (OSError, ValueError):
            return None

    sed = probe("sed", "--version")
    if sed and sed.returncode == 0 and "GNU sed" in sed.stdout:
        return "host"
    docker = probe("docker", "version")
    return "docker" if docker and docker.returncode == 0 else None


RUNNER = bash_runner()

# The plugin file lookup shells out to jq, which is not the logic under test and is not
# present in every base image. Stub it so the checks stay hermetic.
JQ_STUB = "#!/bin/sh\necho test-plugin.php\n"


def run(script: str, tested: str, update_min: str):
    """Execute the extracted script in a throwaway repo, as `bash -e` would on a runner."""
    # tested_up_to reaches the script through the environment so a dispatch input can
    # never be expanded into the shell source; update_min_version is a `choice`.
    script = script.replace("${{ github.event.inputs.update_min_version }}", update_min)

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "readme.txt").write_text("Tested up to: 6.4\nRequires at least: 6.0\n")
        (d / "test-plugin.php").write_text("<?php\n/*\nVersion: 1.2.3\nRequires at least: 6.0\n*/\n")
        (d / ".puprc").write_text('{"paths":{"versions":[{"file":"test-plugin.php"}]}}')
        wf = d / ".github/workflows"
        wf.mkdir(parents=True)
        (wf / "tests-php.yml").write_text(WORKFLOW_FIXTURE)
        (wf / "release-update-wp-version.yml").write_text(WORKFLOW_FIXTURE)

        stub_dir = d / "stub-bin"
        stub_dir.mkdir()
        jq = stub_dir / "jq"
        jq.write_text(JQ_STUB)
        jq.chmod(0o755)

        out, summary = d / "gh_output", d / "gh_summary"
        out.touch(); summary.touch()

        if RUNNER == "host":
            cmd = ["bash", "-e", "-c", script]
            env = {"PATH": f"{stub_dir}:/usr/bin:/bin:/usr/local/bin",
                   "TESTED_UP_TO": tested,
                   "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(summary)}
            proc = subprocess.run(cmd, cwd=d, capture_output=True, text=True, env=env)
        else:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{d}:/w", "-w", "/w",
                 "-e", "PATH=/w/stub-bin:/usr/bin:/bin:/usr/local/bin",
                 "-e", f"TESTED_UP_TO={tested}",
                 "-e", "GITHUB_OUTPUT=/w/gh_output",
                 "-e", "GITHUB_STEP_SUMMARY=/w/gh_summary",
                 "debian:stable-slim", "bash", "-e", "-c", script],
                capture_output=True, text=True,
            )

        outputs = dict(
            line.split("=", 1) for line in out.read_text().splitlines() if "=" in line
        )
        files = {p.name: p.read_text() for p in [d / "readme.txt", wf / "tests-php.yml",
                                                 wf / "release-update-wp-version.yml"]}
        files["__present__"] = "\n".join(sorted(p.name for p in d.iterdir()))
        return proc, outputs, files


def main() -> int:
    if RUNNER is None:
        print("needs GNU sed or docker; skipping")
        return 0
    print(f"running the workflow snippet via: {RUNNER}\n")
    script = extract_run_block()
    failures = []

    def check(label, cond):
        if not cond:
            failures.append(label)
        print(f"{'ok  ' if cond else 'FAIL'} {label}")

    # A normal bump resolves two minors back and publishes the result.
    proc, outputs, files = run(script, "6.8.1", "yes")
    check("6.8.1 succeeds", proc.returncode == 0)
    check("6.8.1 -> MIN_VERSION=6.6", outputs.get("MIN_VERSION") == "6.6")
    check("readme.txt tested up to bumped", "Tested up to: 6.8.1" in files["readme.txt"])
    check("readme.txt minimum bumped", "Requires at least: 6.6" in files["readme.txt"])
    check("tests-php.yml wp core update rewritten",
          "wp core update --force --version=6.6" in files["tests-php.yml"])
    check("tests-php.yml kept its ${SLIC_BIN} prefix",
          "${SLIC_BIN} wp core update" in files["tests-php.yml"])
    check("workflow does not rewrite itself",
          "--version=6.8" in files["release-update-wp-version.yml"])

    # A two-segment version is a legal input.
    proc, outputs, _ = run(script, "6.8", "yes")
    check("6.8 -> MIN_VERSION=6.6", proc.returncode == 0 and outputs.get("MIN_VERSION") == "6.6")

    # Crossing a major has no defined answer; it must stop rather than invent one.
    for bad in ("7.0", "6.1.0", "7.1"):
        proc, outputs, _ = run(script, bad, "yes")
        check(f"{bad} is rejected, not turned into a negative minor",
              proc.returncode != 0 and "-" not in outputs.get("MIN_VERSION", ""))

    # Garbage in must not reach the plugin headers.
    for bad in ("banana", "6", ""):
        proc, _, _ = run(script, bad, "yes")
        check(f"{bad!r} is rejected", proc.returncode != 0)

    # A dispatch input reaches the script through the environment, so shell metacharacters
    # are data. Expanded into the source instead, the payload would run before the pattern
    # below ever sees it.
    for payload in ('6.8"; touch INJECTED; #', "6.8$(touch INJECTED)", "6.8`touch INJECTED`"):
        proc, _, files = run(script, payload, "yes")
        check(f"{payload!r} is rejected", proc.returncode != 0)
        check(f"{payload!r} executes nothing", "INJECTED" not in files["__present__"])

    # Leaving the minimum alone still bumps "tested up to".
    proc, _, files = run(script, "7.0", "no")
    check("7.0 with update_min_version=no still succeeds", proc.returncode == 0)
    check("7.0 with update_min_version=no bumps tested up to",
          "Tested up to: 7.0" in files["readme.txt"])
    check("7.0 with update_min_version=no leaves minimum alone",
          "Requires at least: 6.0" in files["readme.txt"])

    print()
    if failures:
        print(f"{len(failures)} failing check(s): " + ", ".join(failures))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
