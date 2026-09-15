#!/usr/bin/env python3
"""Download plan artifacts as data and run the pinned OpenSpec CLI.

Exit 1 means invalid/incomplete artifacts; exit 2 means verification was not
possible. The composite action decides whether those results block or warn.
"""

import base64
import binascii
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote


class InvalidPlan(Exception):
    pass


class CannotVerify(Exception):
    pass


def api(endpoint, *, optional=False):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, timeout=60)
    if result.returncode:
        if optional and "(HTTP 404)" in result.stderr:
            return None
        raise CannotVerify(f"Cannot read {endpoint}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise CannotVerify(f"GitHub returned invalid JSON for {endpoint}") from error


def content_file(entry, name):
    if not isinstance(entry, dict) or entry.get("type") != "file":
        raise InvalidPlan(f"{name} must be a regular file.")
    if entry.get("encoding") != "base64":
        raise CannotVerify(f"GitHub did not return readable content for {name}.")
    try:
        content = base64.b64decode("".join(entry["content"].split()), validate=True).decode("utf-8")
    except (KeyError, TypeError, ValueError, binascii.Error) as error:
        raise CannotVerify(f"GitHub returned unreadable content for {name}.") from error
    if not content.strip():
        raise InvalidPlan(f"{name} must not be empty or whitespace-only.")
    return content


def download_plan(repo, ticket, ref, destination):
    # ref is already URL-encoded by the action; a branch name may carry slashes.
    commit = api(f"repos/{repo}/commits/{ref}")
    revision = commit.get("sha", "") if isinstance(commit, dict) else ""
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise CannotVerify("GitHub did not return a valid store revision.")
    prefix = f"repos/{repo}/contents/openspec/changes/{ticket}"

    def get(relative):
        return api(f"{prefix}/{quote(relative, safe='/')}?ref={revision}", optional=True)

    def save(relative):
        entry = get(relative)
        if entry is None:
            raise InvalidPlan(f"Missing required artifact: {relative}.")
        content = content_file(entry, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    for name in ("proposal.md", "design.md", "tasks.md"):
        save(name)

    def specs(relative):
        entries = get(relative)
        if entries is None:
            return 0
        if not isinstance(entries, list):
            raise InvalidPlan(f"{relative} must be a directory of capability specs.")
        count = 0
        for entry in entries:
            name = entry.get("name", "")
            if not isinstance(name, str) or not name or name in (".", "..") or "/" in name or "\\" in name:
                raise InvalidPlan("The specs directory contains an unsafe artifact name.")
            child = f"{relative}/{name}"
            if entry.get("type") == "dir":
                count += specs(child)
            elif name == "spec.md":
                if entry.get("type") != "file":
                    raise InvalidPlan(f"{child} must be a regular file.")
                save(child)
                count += 1
            elif entry.get("type") != "file":
                raise InvalidPlan(f"{child} must be a regular file or directory.")
        return count

    if not specs("specs"):
        raise InvalidPlan("Missing required artifact: specs/<capability>/spec.md.")


def report(title, detail):
    # Validator diagnostics can quote plan content. Prefix log lines and escape
    # summary HTML so content cannot become runner commands or summary markup.
    for line in detail.splitlines():
        print(f"OpenSpec: {line}")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(f"## OpenSpec plan: {title}\n\n<pre>{html.escape(detail)}</pre>\n\n")


def main():
    repo, ticket, ref = sys.argv[1:]
    try:
        with tempfile.TemporaryDirectory(prefix="tec-openspec-") as tmp:
            root = Path(tmp)
            change = root / "openspec/changes" / ticket
            change.mkdir(parents=True)
            (root / "openspec/specs").mkdir()
            (root / "openspec/config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
            # Only the required Markdown is downloaded. Store metadata and custom
            # schemas cannot weaken the gate or cause repository code to execute.
            download_plan(repo, ticket, ref, change)
            result = subprocess.run(
                ["openspec", "validate", ticket, "--type", "change", "--strict", "--no-interactive"],
                cwd=root, capture_output=True, text=True, timeout=120,
                env=os.environ | {"OPENSPEC_TELEMETRY": "0", "DO_NOT_TRACK": "1"},
            )
            detail = (result.stdout + result.stderr).strip()
            if result.returncode:
                raise InvalidPlan(detail or "OpenSpec validation failed.")
            report("validation details", detail)
        return 0
    except InvalidPlan as error:
        report("invalid or incomplete", str(error) + "\nComplete the artifacts in the plans repository and rerun this check.")
        return 1
    except (CannotVerify, OSError, subprocess.TimeoutExpired) as error:
        report("could not be checked", str(error) + "\nCheck store access and validator availability, then rerun this check.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
