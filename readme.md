# The Events Calendar: GitHub Actions

This repository contains the code for the Automations using GitHub Actions used by the The Events Calendar team.

Our goal here is to create Actions that will allow us to deprecate the use of our Internal Jenkins for most of the automation tasks.

Before the creation of this repository most of the automation were done with individual GitHub Actions that were scattered across the different repositories. This made it hard to maintain and to have a clear overview of what was happening.

For more global integrations we used Jenkins, but we want to move away from it and use GitHub Actions for everything.

## Synchronization of Files

We are using the [BetaHuhn/repo-file-sync-action](https://github.com/marketplace/actions/repo-file-sync-action) action to enable us to synchronize files across different repositories.

So any files that need to be identical across different repositories can be synchronized using this action, and the original stored in this repository under the `templates` folder.

> [!NOTE]
> If you are using this action, please make sure to include `@tec-bot` user as a collaborator with write permissions in the repository you want to sync the files to.
### Sync groups

The groups in `.github/sync.yml` exist because our repositories are not all the
same kind of thing. A WordPress plugin, a shared library and a Laravel service
have genuinely different needs, and syncing a plugin's release machinery into a
service would only give its developers instructions that do not apply.

| Group | Goes to | Holds |
|---|---|---|
| Active Plugin Repositories | the 8 plugin repos and `tribe-common` | base config, the PR template, `AGENTS.md` (each repo keeps a `CLAUDE.md` symlink to it, seeded by hand and not synced), changelog tooling, release and lint workflows |
| Promoter | `promoter` | the PR template and project linking |
| OpenSpec plan check | every active product, 16 repos | one workflow, nothing stack specific |

## WordPress test matrix

`.github/actions/wp-test-matrix` returns the three most recent WordPress X.Y
releases from the wordpress.org version-check API, newest first, as a JSON array
(for example `["7.1","7.0.4","6.9.7"]`). Test workflows feed it into their matrix:

```yaml
jobs:
  wp-versions:
    runs-on: ubuntu-latest
    outputs:
      versions: ${{ steps.matrix.outputs.versions }}
    steps:
      - id: matrix
        uses: the-events-calendar/actions/.github/actions/wp-test-matrix@main

  test:
    needs: wp-versions
    name: ${{ matrix.suite }} (WP ${{ matrix.wp }})
    strategy:
      fail-fast: false
      matrix:
        suite: [ unit, wpunit ]
        wp: ${{ fromJSON(needs.wp-versions.outputs.versions) }}
    steps:
      - run: ${SLIC_BIN} wp core update --force --version=${{ matrix.wp }}
```

Because the version under test comes from the matrix, `release-update-wp-version.yml`
no longer rewrites any `wp core update` line in the test workflows.

## OpenSpec plan check

Work on TEC products is planned before it is written, and the plan lives in one
shared store — [`the-events-calendar/plans`](https://github.com/the-events-calendar/plans) —
rather than in the product repositories. A feature routinely spans several repos,
so a spec kept in any one of them is invisible from the others.

`templates/workflows/openspec-plan.yml` requires a complete, valid active plan for
the ticket a pull request belongs to. It reads the ticket id from the branch name
(`{type}/{task-id}/{short-desc}`), falls back to the PR title, and looks the change
up through `.github/actions/verify-openspec-plan`. The store is read from a branch
named like the PR branch when one exists there, so a plan still being written can
be checked before it merges; otherwise the store's default branch is used.

What it reports:

| Situation | Result |
|---|---|
| Active plan has nonempty artifacts and passes strict validation | passes, with a reminder to archive once every repo has merged |
| Plan exists but is already archived | fails — a change must remain active until the last repo merges |
| No plan for that ticket | fails, and the summary shows the command to create one |
| No valid ticket id | fails with guidance to add an ID to the branch, title, or action's `ticket-id` input |
| Required artifacts are missing, blank, or invalid | fails with artifact or validation diagnostics |
| Store or artifacts cannot be read | fails because the plan could not be verified |

**Both the action and the synced workflow default to `enforcement: 'block'`.**
Automated PRs also need a ticket and a plan; there is no ticketless skip. An explicit
`ticket-id` takes precedence over the branch, which takes precedence over the title.
IDs are normalized to lower case. Callers can explicitly select `warn` for advisory
results; invalid enforcement values always fail. Outputs distinguish validated
(`true`), missing (`false`), archived, invalid, and unknown results.

Validation requires nonempty `proposal.md`, `design.md`, `tasks.md`, and at least
one `specs/<capability>/spec.md` (nested capability paths are supported). The action
downloads those files at one resolved store commit and runs OpenSpec 1.12.0 with
`validate --type change --strict --no-interactive`. It uses the built-in
spec-driven schema; plan metadata, custom schemas, and `skip_specs` cannot bypass
the required artifacts. Task checkboxes can remain unchecked while implementation
is in progress. The CLI validates spec structure; nonempty prose alone does not
prove quality or agreement with code. Reviewers must still confirm the plan
describes the PR.

The action uses Node 24, Python 3, `gh`, and a pinned OpenSpec installation on the
Ubuntu runner. Plan content is read as data, and telemetry is disabled. Package
installation failures also fail the job.

Changing the action default does not override existing callers that explicitly
select `warn`. After publishing the shared change, the workflow template must land
in each of the 16 repositories through the existing sync process. To prevent merges
with a failing check, the repository's merge rules must require **OpenSpec Plan**.
Editing the generated product workflows directly will be overwritten by sync.

The check needs `GHA_BOT_TOKEN_MANAGER` to have read access to the `plans`
repository, which is internal.

### Testing the check

Install the same validator used in CI, then run the regression suite:

```bash
npm install --prefix /tmp/tec-openspec-cli --ignore-scripts --no-audit --no-fund @fission-ai/openspec@1.12.0
PATH="/tmp/tec-openspec-cli/node_modules/.bin:$PATH" python3 tests/test-openspec-plan.py
```

The tests execute the actual action scripts and real OpenSpec validator. GitHub
responses are simulated to cover missing plans and API failures without changing
remote repositories. `.github/workflows/check-templates.yml` runs these tests and
the existing workflow lint and WordPress version arithmetic checks.

The [`openspec-workflow` skill](https://github.com/stellarwp/skills-se) covers
the workflow itself — writing a proposal worth reviewing and keeping it current —
and its TEC extension, `tec-openspec`, covers the shared store, the ticket-ID
naming, and archiving once (after the last repository merges, not per repo).
