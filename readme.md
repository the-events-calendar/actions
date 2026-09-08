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
| Active Plugin Repositories | the 8 plugin repos and `tribe-common` | base config, the PR template, changelog tooling, release and lint workflows |
| Promoter | `promoter` | the PR template and project linking |
| OpenSpec plan check | every active product, 16 repos | one workflow, nothing stack specific |

## OpenSpec plan check

Work on TEC products is planned before it is written, and the plan lives in one
shared store — [`the-events-calendar/plans`](https://github.com/the-events-calendar/plans) —
rather than in the product repositories. A feature routinely spans several repos,
so a spec kept in any one of them is invisible from the others.

`templates/workflows/openspec-plan.yml` reports whether the ticket a pull request
belongs to has a plan. It reads the ticket id from the branch name
(`{type}/{task-id}/{short-desc}`), falls back to the PR title, and looks the change
up through `.github/actions/verify-openspec-plan`.

What it reports:

| Situation | Result |
|---|---|
| Plan is active in the store | passes, with a reminder to archive once every repo has merged |
| Plan exists but is already archived | warns — a change is archived once, after the last repo merges |
| No plan for that ticket | warns, and the summary shows the command to create one |
| No ticket id anywhere | skips — not every branch carries a ticket |

**It warns rather than fails.** Set `enforcement: 'block'` in the workflow to make
a missing plan stop the merge. Do that once teams are used to the workflow, not
before: a hard gate on day one produces empty plans written to get CI green, which
looks like coverage and is worse than none.

The check needs `GHA_BOT_TOKEN_MANAGER` to have read access to the `plans`
repository, which is internal.

The `tec-openspec` skill in
[stellarwp/skills-se](https://github.com/stellarwp/skills-se) covers
the workflow itself — creating a change, naming it, and archiving it.
