## What is the Actions repository?

TEC maintains eight WordPress plugins that share a common library (`tribe-common`), plus a handful of services. Before this repository, each product repo carried its own copies of the CI workflows and config files, and anything that had to run across several repos lived in an internal Jenkins server. Fixing a workflow meant fixing it eight times, and nobody had a full picture of what ran where.

This repository holds one copy of every shared file and pushes it into the product repos automatically. Jenkins was retired in favour of GitHub Actions for everything.

## The two things this repository does

1. It is a **file sync hub**. The `templates/` folder holds the canonical copy of each shared file. A workflow in this repo copies those files into the product repos and opens a pull request in each one.
2. It is a **library of composite actions** under `.github/actions/`. The synced workflows call these with `uses: the-events-calendar/actions/.github/actions/<name>@main`, so the logic lives here and the product repos only carry a thin workflow file.

Nothing in `templates/` runs in this repository. Those files only do something once they land in a product repo.

## How file sync works

We use [BetaHuhn/repo-file-sync-action](https://github.com/marketplace/actions/repo-file-sync-action). The configuration is `.github/sync.yml`, and the workflow that runs it is `.github/workflows/sync.yml`.

The sync runs on every push to `main` that touches `templates/**`, `.github/sync.yml`, or the sync workflow itself. It can also be started by hand from the Actions tab. For each target repository it checks out the repo, copies the listed files to their destination paths, and opens a pull request titled `🔄 synced file(s) with the-events-calendar/actions` as the `tec-bot` user. Someone on the product team reviews and merges that PR like any other.

The PR body carries `[skip-changelog]`, because a synced file never needs a changelog entry. See [Skip markers](#skip-markers).

### Sync groups

Not every repo gets every file. A WordPress plugin, a Laravel service and a shared library have different needs, so `sync.yml` defines groups. Each group is a list of files and a list of `owner/repo@branch` targets.

| Group | Targets | What it holds |
|---|---|---|
| Active plugin repositories | `tribe-common`, `the-events-calendar`, `events-pro`, `events-eventbrite`, `events-community`, `events-filterbar`, `event-tickets`, `event-tickets-plus` (all on `main`) | Editor config, license, PR template, `AGENTS.md`, changelog scripts, all release and check workflows |
| Promoter | `promoter@server/production` | PR template and the project-linking workflow only |
| OpenSpec plan check | The eight plugins above plus `advanced-post-manager`, `event-tickets-plus-app`, `event-tickets-seating-service`, `event-tickets-seating-service-auth`, `promoter-auth-connector`, `promoter`, `whodat`, `event-aggregator-site` | One workflow, `openspec-plan.yml` |

The third group is deliberately narrow. Planning is the one thing a plugin, a library and a service all share, so that check goes everywhere. Everything stack specific stays in the first two groups.

### What a sync run looks like from a product repo

A developer on `event-tickets` sees a PR from `tec-bot` appear with a diff of the changed template files. They do not edit those files in the product repo. If something in a synced file is wrong, the fix goes into `templates/` here, and the next sync carries it to every repo. Editing a synced file in a product repo works until the next sync overwrites it.

## Files we sync

Every path below is relative to the product repo root. The source is the same path under `templates/` here unless noted.

### Editor and tooling config

| File | Purpose |
|---|---|
| `.editorconfig` | Tabs for code, two spaces for JSON and YAML, LF line endings |
| `.nvmrc` | Node version (currently `18.17.0`) read by the lint and changelog workflows |
| `.browserslistrc` | Browser targets for the CSS and JS build |
| `.eslintignore` | Paths ESLint skips (vendor, build output, tests, common) |
| `.stylelintrc.json` | Stylelint config, extends the WordPress SCSS config with alphabetical property order |
| `.gitattributes` | Marks minified and generated files so GitHub collapses them in diffs |
| `license.txt` | GPL license text |

### GitHub files

| File | Purpose |
|---|---|
| `.github/pull_request_template.md` | The PR template. Sections for ticket, OpenSpec plan, description, artifacts, a checklist, and an AI disclosure block |
| `AGENTS.md` | Guidance for AI coding agents (Claude Code, Codex, Cursor, Copilot). Each repo keeps a `CLAUDE.md` symlink pointing at it. The symlink is created once by hand and is never synced, because the sync action cannot copy a symlink over an identical one and fails the whole group when it tries |

### Changelog tooling

We use [@stellarwp/changelogger](https://www.npmjs.com/package/@stellarwp/changelogger). Each PR adds a small YAML file under `changelog/`, and a release workflow folds those files into `changelog.md` and `readme.txt`.

| File | Purpose |
|---|---|
| `changelog/.gitkeep` | Keeps the directory present when there are no pending entries |
| `bin/check-changelog.sh` | Fails a PR that adds no changelog entry, rejects any non-YAML leftover in `changelog/`, and checks that the version bump did not corrupt the changelogger config in `package.json` |
| `bin/process-changelog.sh` | Writes pending entries into `changelog.md` and `readme.txt` for a given version and date, or relabels an existing header when there is nothing new to write |
| `bin/tec-changelog-versioning.js` | Tells changelogger how TEC version numbers work: `x.y.z` with an optional fourth hotfix component, `x.y.z.h` |

## Workflows we sync

All of these land in `.github/workflows/` of the product repo.

### Pull request checks

These run on every pull request.

| Workflow | Trigger | What it does |
|---|---|---|
| `changelogger.yml` | PRs into `main` or `release/**`, skipping `.github/**` changes | Runs `bin/check-changelog.sh` against the target branch |
| `phpcs.yml` | Every PR | First checks whether any PHP file changed (via the `check-php-changes` action). If so, calls the shared `phpcs.yml` reusable workflow in `stellarwp/github-actions` |
| `lint.yml` | PRs touching JS under `src/` or PostCSS files | `npm ci` then `npm run lint` |
| `openspec-plan.yml` | Every PR | Requires a valid, active OpenSpec plan for the PR's ticket. See [Which parts are TEC policy](#which-parts-are-tec-policy-and-which-are-reusable) |
| `link-project.yml` | Every PR | Adds PRs targeting a `release/*` branch to the matching GitHub Project board, creating the board from a template if needed |

### Release workflows

These are all started by hand from the Actions tab (`workflow_dispatch`). Each one creates a branch, makes its change, and opens a `[BOT]` pull request for a human to merge. None of them push straight to a release branch.

| Workflow | Inputs | What it does |
|---|---|---|
| `release-prepare-branch.yml` | New branch name, bump type (major, feature, maintenance, hotfix) | Creates the release branch, bumps the version in every file listed in `.puprc`, opens a version-bump PR into it |
| `release-process-changelog.yml` | Version (or "figure it out"), date, generate or amend | Runs the `process-changelog` action and opens a PR with the updated `changelog.md` and `readme.txt` |
| `release-replace-tbd-entries.yml` | None | Finds every `TBD` in source and docs, replaces it with the current version, opens a PR. Used for `@since TBD` docblocks written during development |
| `release-sync-translations.yml` | None | Regenerates the `.pot` file. On `main` or a release branch it also pushes the file to translations.stellarwp.com, imports it into GlotPress, and adds a `language` changelog entry with the import result |
| `release-update-wp-version.yml` | Tested-up-to version, whether to also raise the minimum | Updates `readme.txt`, the plugin header, and any workflow that installs a pinned WordPress version |
| `release-merge-forward.yml` | Target branch | Merges the current branch forward into the target (for example a release branch into `main`) through a PR. Creates the target branch if it does not exist |

### Skip markers

A bot PR should not be blocked by the checks meant for human PRs. Putting one of these strings anywhere in the PR body turns the matching check off:

| Marker | Skips |
|---|---|
| `[skip-changelog]` | `changelogger.yml` |
| `[skip-phpcs]` | `phpcs.yml` |
| `[skip-lint]` | `lint.yml` |

The release workflows and the sync PR add these automatically. The checks re-run when a PR body is edited, so adding or removing a marker takes effect straight away. There is no skip marker for the OpenSpec check.

## Composite actions

These live in `.github/actions/` and are called from the workflows above. Product repos reference them at `@main`, so a change here is live everywhere as soon as it merges.

| Action | Used by | What it does |
|---|---|---|
| `check-php-changes` | `phpcs.yml` | Diffs the PR against its base and outputs whether any PHP file changed |
| `process-changelog` | `release-process-changelog.yml` | Wraps `bin/process-changelog.sh`. Switches to amend mode on its own when the changelog directory is empty and `package.json` already carries the release version |
| `add-changelog` | `release-sync-translations.yml` | Writes a changelog YAML file with a given filename, significance, type and entry |
| `generate-pot` | `release-sync-translations.yml` | Downloads WP-CLI and runs `wp i18n make-pot`, excluding everything in `.distignore` |
| `push-translations` | `release-sync-translations.yml` | Rsyncs the `.pot` file to translations.stellarwp.com, runs the GlotPress import over SSH, and returns the import output |
| `smart-checkout` | Test workflows in product repos | Checks out a second repository on the same branch as the PR if it exists there, falling back to the base branch, then the default branch. Used to pull `tribe-common` or another plugin at a matching branch |
| `verify-openspec-plan` | `openspec-plan.yml` | Works out the ticket ID from the branch name or PR title, then checks the shared plans repository for a complete, valid, unarchived plan |

## What a product repo needs before it can be synced

The synced workflows assume a few things about the target repository. Missing any of these produces a failing run rather than a helpful error.

- `tec-bot` is a collaborator with write access, so the sync action can open PRs.
- These secrets exist in the repo: `GHA_BOT_TOKEN_MANAGER` (used by the release workflows and the OpenSpec check to open PRs and read the private plans repo), `GH_BOT_TOKEN` (used by `phpcs.yml`), and for translation sync `TRANSLATIONS_DEPLOY_HOST`, `TRANSLATIONS_DEPLOY_USER`, `TRANSLATIONS_DEPLOY_SSH_KEY` and `TRANSLATIONS_DEPLOY_POT_LOCATION`.
- A `.puprc` file at the root with a `paths.versions` array listing every file that carries the version number and a regex to find it, and an `i18n` entry whose URL contains `translations.stellarwp.com`. The release workflows read both. `.puprc` is the config file for [pup](https://github.com/stellarwp/pup), our packaging tool.
- `package.json` with a `changelogger` section and a `lint` script.
- `changelog.md` and `readme.txt` in the format changelogger expects.
- A `CLAUDE.md` symlink to `AGENTS.md`, created by hand.
- For the OpenSpec check, branch protection that requires the **OpenSpec Plan** status check, otherwise a failing check does not block a merge.

## How this repository checks itself

`.github/workflows/check-templates.yml` runs on every PR that touches templates, the sync config, or the actions. It:

- copies `templates/workflows/*.yml` into a fake `.github/workflows/` folder and runs [actionlint](https://github.com/rhysd/actionlint) over them, because the templates are not workflows of this repo and would otherwise never be linted;
- fails if any source listed in `sync.yml` is a symlink;
- runs `tests/test-wp-version-math.py` against the version arithmetic in the WordPress version workflow;
- installs the pinned OpenSpec CLI and runs `tests/test-openspec-plan.py` against the real action scripts.

A broken template reaches eight repos before anyone notices, so this check is the last line of defence.

## Some "Gotchas"

- A failed sync run is silent from the product repo's point of view. If a group fails, none of its repos get a PR, and nothing tells them. Check the Actions tab in this repository if a change seems not to have arrived.
- One bad file fails the whole group. The symlink problem with `CLAUDE.md` stopped every plugin sync until it was removed from the config.
- Sync PRs can sit unmerged. Each product repo has to review and merge its own, and an old sync PR left open will conflict with newer ones.
- Composite actions are pinned to `@main`. Merging a change to an action here changes behaviour in every product repo immediately, with no PR on their side.
- The release workflows create the working branch and push it before making changes. If a run fails halfway you may need to delete a `task/...` branch by hand before rerunning.
- `release-replace-tbd-entries.yml` replaces every literal `TBD` in matching file types outside `vendor`, `node_modules` and `tests`. Review its PR rather than trusting it.

## Which parts are TEC policy and which are reusable

Some of what this repository syncs is generic plugin CI. Some of it encodes how TEC works and would need changing, or dropping, in another team's setup.

Reusable as they are, or with a config change:

- The sync mechanism and group layout.
- The editor and lint config files.
- Changelog checking and processing, as long as the target uses `@stellarwp/changelogger`.
- Version bumping, TBD replacement, merge forward, and the WordPress version update, all of which are driven by `.puprc` rather than hard-coded paths.
- `check-php-changes` and `smart-checkout`.

TEC specific:

- The OpenSpec plan check and everything around it: the private `the-events-calendar/plans` store, the `tec-plans` naming, and the requirement that every PR has a ticket ID in its branch name.
- `AGENTS.md`, which points at TEC skills and TEC repositories.
- The PR template's plan section and AI disclosure block.
- Translation sync, which pushes to translations.stellarwp.com with the `tec/` prefix and reads the plugin slug from `.puprc`.
- The release branch naming (`release/T25.<codename>`) and the project board template used by `link-project.yml`.
- The `tec-bot` account and its tokens.

## Related repositories

- [stellarwp/github-actions](https://github.com/stellarwp/github-actions) holds org-wide reusable workflows. Our synced `phpcs.yml` calls its `phpcs.yml`. It also carries `zip.yml` and `dependency-zip.yml`, which product repos use for packaging.
- [the-events-calendar/plans](https://github.com/the-events-calendar/plans) is the shared OpenSpec store the plan check reads from. It is private.
- [stellarwp/skills-se](https://github.com/stellarwp/skills-se) holds the agent skills `AGENTS.md` refers to.
- [the-events-calendar/gh-action-project-link](https://github.com/the-events-calendar/gh-action-project-link) is the action behind `link-project.yml`.
