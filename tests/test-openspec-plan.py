#!/usr/bin/env python3
"""Run the actual composite-action scripts against fixture GitHub responses.

Requires OpenSpec 1.12.0 on PATH. Run: python3 tests/test-openspec-plan.py
Only GitHub is simulated: missing private resources and transient API failures
cannot be reproduced reliably or safely by changing the shared remote store.
The OpenSpec validator is real, including its parsing and failure exit codes.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ROOT / ".github/actions/verify-openspec-plan"
ACTION = ACTION_DIR / "action.yml"
REPO = "repos/the-events-calendar/plans"
CHANGE = "openspec/changes/soft-1234"
REVISION = "a" * 40
SPEC = """\
## Purpose

Ensure pull requests have complete plans before implementation can be merged.

## ADDED Requirements

### Requirement: Validate the plan
The check SHALL validate the active plan before reporting success.

#### Scenario: Valid plan
- **WHEN** a complete and valid plan is present
- **THEN** the check succeeds
"""
FILES = {
    "proposal.md": "## Why\n\nMissing plans must block PRs.\n\n## What Changes\n\n- Validate plans.\n",
    "design.md": "## Decisions\n\nValidate plan artifacts with OpenSpec.\n",
    "tasks.md": "## 1. Validation\n\n- [ ] 1.1 Validate the plan and verify the tests pass.\n",
    "specs/plan-check/spec.md": SPEC,
}


def run_block(step):
    """Extract executable code, matching the repository's existing test convention."""
    source = ACTION.read_text()
    start = source.index(f"- name: {step}")
    body = source[source.index("run: |\n", start) + len("run: |\n"):]
    lines = []
    for line in body.splitlines():
        if line.strip() and not line.startswith("        "):
            break
        lines.append(line[8:])
    return "\n".join(lines)


GH_STUB = r'''#!/usr/bin/env python3
import base64
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs

args = sys.argv[1:]
assert args[0] == "api", args
url = urlsplit(args[1])
endpoint = url.path
fixture = json.loads(Path(os.environ["GH_FIXTURE"]).read_text())
with open(os.environ["GH_CALLS"], "a") as log:
    log.write(args[1] + "\n")

def respond(value):
    if "--silent" not in args:
        print(json.dumps(value))
    sys.exit(0)

def fail(status):
    print(f"gh: fixture API failure (HTTP {status})", file=sys.stderr)
    sys.exit(1)

repo = "repos/the-events-calendar/plans"
if endpoint in fixture["errors"]:
    fail(fixture["errors"][endpoint])
if endpoint == repo:
    respond({"default_branch": "main"})
if endpoint == repo + "/commits/HEAD":
    respond({"sha": "a" * 40})
prefix = repo + "/contents/"
assert endpoint.startswith(prefix), endpoint
path = endpoint[len(prefix):]
query = parse_qs(url.query)
if query:
    assert query == {"ref": ["a" * 40]}, query

entries = fixture["entries"]
if path in entries:
    entry = entries[path]
    if isinstance(entry, dict):
        respond(entry)
    respond({"type": "file", "name": path.rsplit("/", 1)[-1], "path": path,
             "encoding": "base64", "content": base64.b64encode(entry.encode()).decode()})

children = {}
for candidate in entries:
    if candidate.startswith(path + "/"):
        tail = candidate[len(path) + 1:]
        name = tail.split("/")[0]
        child = path + "/" + name
        entry = entries.get(child)
        kind = entry.get("type", "file") if isinstance(entry, dict) else ("dir" if "/" in tail else "file")
        children[name] = {"name": name, "path": child, "type": kind}
if children:
    respond(list(children.values()))
fail(404)
'''


class PlanCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("openspec"):
            raise RuntimeError("Install @fission-ai/openspec@1.12.0 before running these tests")
        result = subprocess.run(["openspec", "--version"], capture_output=True, text=True, check=True)
        if result.stdout.strip() != "1.12.0":
            raise RuntimeError(f"Expected OpenSpec 1.12.0, got {result.stdout.strip()}")

    def action(self, *, files=None, branch="fix/SOFT-1234/plan-check", title="Fix plan check",
               ticket="", enforcement="block", errors=None, archived=False):
        entries = {f"{CHANGE}/{name}": content for name, content in (FILES if files is None else files).items()}
        if archived:
            entries = {f"openspec/changes/archive/soft-1234/{name}": content for name, content in FILES.items()}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.json"
            fixture.write_text(json.dumps({"entries": entries, "errors": errors or {}}))
            gh = root / "gh"
            gh.write_text(textwrap.dedent(GH_STUB))
            gh.chmod(0o755)
            output, summary, calls = (root / name for name in ("output", "summary", "calls"))
            for path in (output, summary, calls):
                path.touch()
            env = os.environ | {
                "PATH": f"{root}:{os.environ['PATH']}",
                "GH_FIXTURE": str(fixture), "GH_CALLS": str(calls),
                "HEAD_REF": branch, "PR_TITLE": title, "TICKET_INPUT": ticket,
                "ENFORCEMENT": enforcement, "PLANS_REPO": "the-events-calendar/plans",
                "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary),
                "GITHUB_ACTION_PATH": str(ACTION_DIR), "RUNNER_TEMP": str(root),
                "OPENSPEC_TELEMETRY": "0", "DO_NOT_TRACK": "1",
            }
            resolved = subprocess.run(["bash", "-eo", "pipefail", "-c", run_block("Resolve the ticket id")],
                                      cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
            env["TICKET"] = outputs["ticket_id"]
            result = subprocess.run(["bash", "-eo", "pipefail", "-c", run_block("Verify the plan exists")],
                                    cwd=root, env=env, capture_output=True, text=True)
            outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
            return result, outputs, summary.read_text(), calls.read_text()

    def assert_rejected(self, result, state):
        proc, outputs, summary, _ = result
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(outputs.get("plan_found"), state, summary)
        self.assertIn("::error", proc.stdout)
        self.assertTrue(summary.strip())

    def test_blocking_defaults(self):
        action = ACTION.read_text().split("  enforcement:\n", 1)[1].split("\noutputs:", 1)[0]
        self.assertIn("default: 'block'", action)
        self.assertIn("enforcement: 'block'", (ROOT / "templates/workflows/openspec-plan.yml").read_text())

    def test_ticketless_pr_fails(self):
        result = self.action(branch="automation/update-dependencies", title="Update dependencies")
        self.assert_rejected(result, "invalid")
        self.assertIn("ticket", result[2].lower())
        self.assertEqual(result[3], "")

    def test_explicit_invalid_ticket_fails_before_api(self):
        result = self.action(ticket="../../other")
        self.assert_rejected(result, "invalid")
        self.assertEqual(result[3], "")

    def test_title_fallback_and_case_normalization(self):
        proc, outputs, _, _ = self.action(branch="fix/plan-check", title="[SoFt-1234] Fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(outputs["ticket_id"], "soft-1234")
        self.assertEqual(outputs["plan_found"], "true")

    def test_explicit_ticket_precedes_branch(self):
        proc, outputs, _, _ = self.action(branch="fix/SOFT-9999/wrong", ticket="SOFT-1234")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(outputs["ticket_id"], "soft-1234")

    def test_valid_plan_runs_validator_at_pinned_revision(self):
        proc, outputs, summary, calls = self.action()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(outputs["plan_found"], "true")
        self.assertIn("is valid", proc.stdout)
        self.assertIn(f"?ref={REVISION}", calls)
        self.assertIn("still describes", summary)

    def test_missing_and_blank_required_artifacts_fail(self):
        for artifact in FILES:
            for value in (None, "", " \n\t"):
                with self.subTest(artifact=artifact, value=value):
                    files = FILES.copy()
                    if value is None:
                        del files[artifact]
                    else:
                        files[artifact] = value
                    self.assert_rejected(self.action(files=files), "invalid")

    def test_invalid_spec_is_rejected_by_real_validator(self):
        files = FILES | {"specs/plan-check/spec.md": SPEC.split("#### Scenario:")[0]}
        result = self.action(files=files)
        self.assert_rejected(result, "invalid")
        self.assertIn("scenario", result[2].lower())

    def test_strict_validation_rejects_missing_shall(self):
        files = FILES | {"specs/plan-check/spec.md": SPEC.replace("SHALL", "can")}
        self.assert_rejected(self.action(files=files), "invalid")

    def test_multiple_specs_are_all_validated(self):
        files = FILES | {"specs/other/spec.md": "This is not a delta spec."}
        self.assert_rejected(self.action(files=files), "invalid")

    def test_nested_capability_is_supported(self):
        files = FILES.copy()
        files["specs/ci/plan-check/spec.md"] = files.pop("specs/plan-check/spec.md")
        proc, outputs, _, _ = self.action(files=files)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(outputs["plan_found"], "true")

    def test_nonregular_artifact_is_rejected(self):
        files = FILES | {"proposal.md": {"type": "symlink", "target": "../../elsewhere"}}
        self.assert_rejected(self.action(files=files), "invalid")

    def test_metadata_cannot_skip_required_specs(self):
        files = {name: data for name, data in FILES.items() if not name.startswith("specs/")}
        files[".openspec.yaml"] = "schema: spec-driven\nskip_specs: true\n"
        self.assert_rejected(self.action(files=files), "invalid")

    def test_absent_plan_fails(self):
        self.assert_rejected(self.action(files={}), "false")

    def test_archived_plan_fails(self):
        self.assert_rejected(self.action(archived=True), "archived")

    def test_archive_api_failure_is_unknown(self):
        result = self.action(files={}, errors={f"{REPO}/contents/openspec/changes/archive/soft-1234": 500})
        self.assert_rejected(result, "unknown")

    def test_unreadable_store_fails(self):
        for status in (401, 403, 404, 429, 500):
            with self.subTest(status=status):
                self.assert_rejected(self.action(errors={REPO: status}), "unknown")

    def test_unreadable_artifact_fails(self):
        self.assert_rejected(self.action(errors={f"{REPO}/contents/{CHANGE}/proposal.md": 500}), "unknown")

    def test_unreadable_active_plan_fails(self):
        self.assert_rejected(self.action(errors={f"{REPO}/contents/{CHANGE}": 403}), "unknown")

    def test_unreadable_revision_fails(self):
        self.assert_rejected(self.action(errors={f"{REPO}/commits/HEAD": 500}), "unknown")

    def test_warn_mode_preserves_failure_outcomes(self):
        for kwargs, state in (({"files": {}}, "false"), ({"archived": True}, "archived"),
                              ({"errors": {REPO: 403}}, "unknown")):
            with self.subTest(state=state):
                proc, outputs, _, _ = self.action(enforcement="warn", **kwargs)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(outputs["plan_found"], state)
                self.assertIn("::warning", proc.stdout)

    def test_warn_mode_reports_invalid_without_failing(self):
        for kwargs in ({"files": {"design.md": "Only a design"}}, {"branch": "automation/update", "title": "Update"}):
            with self.subTest(kwargs=kwargs):
                proc, outputs, _, _ = self.action(enforcement="warn", **kwargs)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(outputs["plan_found"], "invalid")
                self.assertIn("::warning", proc.stdout)

    def test_unknown_enforcement_fails_closed(self):
        self.assert_rejected(self.action(enforcement="blok"), "invalid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
