## What is the Actions repository?

TEC maintains eight WordPress plugins that share a common library (`tribe-common`), plus a handful of services. For a long time each of those repos carried its own copy of the CI workflows and config files, and anything that had to run across several repos lived on an internal Jenkins server. Fixing a workflow meant fixing it eight times, and nobody had a full picture of what ran where.

This repository is the fix. It holds one copy of every shared file and pushes it into the product repos automatically. Most of what Jenkins used to do now runs here as GitHub Actions.

## The two things this repository does

It is a file sync hub. The `templates/` folder holds the canonical copy of each shared file, and a workflow copies those files into the product repos and opens a pull request in each one.

It is also a library of composite actions, under `.github/actions/`. The synced workflows call these with `uses: the-events-calendar/actions/.github/actions/<name>@main`, so the logic lives here and the product repos only carry a thin workflow file that points back.

One thing that trips people up: nothing in `templates/` actually runs here. Those files are inert until they land in a product repo, which is why this repo can hold a `lint.yml` template and have no lint job of its own.

## How file sync works

We use [BetaHuhn/repo-file-sync-action](https://github.com/marketplace/actions/repo-file-sync-action). The configuration is `.github/sync.yml`, and the workflow that runs it is `.github/workflows/sync.yml`.

The sync runs on every push to `main` that touches `templates/**`, `.github/sync.yml`, or the sync workflow itself. You can also kick it off by hand from the Actions tab. For each target repo it checks out the code, copies the listed files to their destination paths, and opens a pull request titled `🔄 synced file(s) with the-events-calendar/actions` as the `tec-bot` user. Someone on the product team reviews and merges that PR like any other. This increases our team productivity by allowing one person to complete these actions instead of waiting for another team member to approve the PR before being able to merge.

The PR body carries `[skip-changelog]`, because a synced file never needs a changelog entry. More on that under [Skip markers](#skip-markers).

### Sync groups

Not every repo gets every file. A WordPress plugin, a Laravel service and a shared library have different needs, and syncing a plugin's release machinery into a service would only give its developers instructions that don't apply. So `sync.yml` defines groups. Each group is a list of files and a list of `owner/repo@branch` targets.

| Group | Targets | What it holds |
|---|---|---|
| Active plugin repositories | `tribe-common`, `the-events-calendar`, `events-pro`, `events-eventbrite`, `events-community`, `events-filterbar`, `event-tickets`, `event-tickets-plus` (all on `main`) | Editor config, license, PR template, `AGENTS.md`, changelog scripts, all release and check workflows |
| Promoter | `promoter@server/production` | PR template and the project-linking workflow only |
| OpenSpec plan check | The eight plugins above plus `advanced-post-manager`, `event-tickets-plus-app`, `event-tickets-seating-service`, `event-tickets-seating-service-auth`, `promoter-auth-connector`, `promoter`, `whodat`, `event-aggregator-site` | One workflow, `openspec-plan.yml` |

The third group is deliberately tiny. Planning is the one thing a plugin, a library and a service all share, so that check goes everywhere. Anything stack specific stays in the first two groups.

### What a sync run looks like from a product repo

Say you work on `event-tickets`. One day a PR from `tec-bot` shows up with a diff of a few template files. You review it, you merge it, done.

What you don't do is edit those files in `event-tickets`. If something in a synced file is wrong, the fix goes into `templates/` here, and the next sync carries it to every repo. Editing a synced file in a product repo works right up until the next sync quietly overwrites it.

## Files we sync

Every path below is relative to the product repo root. The source is the same path under `templates/` here.

### Editor and tooling config

The boring but useful stuff. These keep formatting and lint rules identical across the plugins so a PR doesn't turn into a tabs-versus-spaces argument.

| File | Purpose |
|---|---|
| `.editorconfig` | Tabs for code, two spaces for JSON and YAML, LF line endings |
| `.nvmrc` | Node version (currently `18.17.0`), read by the lint and changelog workflows |
| `.browserslistrc` | Browser targets for the CSS and JS build |
| `.eslintignore` | Paths ESLint skips |
| `.stylelintrc.json` | Stylelint config, WordPress SCSS rules plus alphabetical property order |
| `.gitattributes` | Marks minified and generated files so GitHub collapses them in diffs |
| `license.txt` | GPL license text |

### GitHub files

| File | Purpose |
|---|---|
| `.github/pull_request_template.md` | The PR template |
| `AGENTS.md` | Guidance for AI coding agents |

The PR template has sections for the ticket, the OpenSpec plan, a description, artifacts, a checklist, and an AI disclosure block.

`AGENTS.md` is read by Claude Code, Codex, Cursor and Copilot. Each repo also keeps a `CLAUDE.md` symlink pointing at it. That symlink is created once by hand and is never synced, because the sync action can't copy a symlink over an identical one and fails the whole group when it tries. We learned that the hard way.

### Changelog tooling

We use [@stellarwp/changelogger](https://www.npmjs.com/package/@stellarwp/changelogger). The idea is simple: each PR adds a small YAML file under `changelog/`, and at release time a workflow folds those files into `changelog.md` and `readme.txt`. No more merge conflicts on the changelog.

| File | Purpose |
|---|---|
| `changelog/.gitkeep` | Keeps the directory present when there are no pending entries |
| `bin/check-changelog.sh` | The PR check. Fails when no entry was added |
| `bin/process-changelog.sh` | The release step. Writes pending entries into `changelog.md` and `readme.txt` |
| `bin/tec-changelog-versioning.js` | Teaches changelogger our version format |

A couple of details worth knowing. The check script also rejects any non-YAML file left in `changelog/`, since changelogger silently ignores those and they'd vanish from the release. It also checks that the version bump didn't corrupt the changelogger config in `package.json`, which has happened. The versioning script exists because TEC versions are `x.y.z` with an optional fourth hotfix component, `x.y.z.h`, and stock semver doesn't know what to do with that.

## Workflows we sync

All of these land in `.github/workflows/` of the product repo.

### Pull request checks

These run on every pull request and are what a developer sees most often.

| Workflow | Trigger | What it does |
|---|---|---|
| `changelogger.yml` | PRs into `main` or `release/**` | Runs `bin/check-changelog.sh` against the target branch |
| `phpcs.yml` | Every PR | Runs PHP CodeSniffer, but only if a PHP file changed |
| `lint.yml` | PRs touching JS under `src/` or PostCSS files | `npm ci` then `npm run lint` |
| `openspec-plan.yml` | Every PR | Requires a valid, active OpenSpec plan for the PR's ticket |
| `link-project.yml` | Every PR | Adds PRs targeting a `release/*` branch to the matching GitHub Project board |

`phpcs.yml` does its "did PHP change" check through the `check-php-changes` action, then hands off to the shared `phpcs.yml` reusable workflow in `stellarwp/github-actions`. The changelog check skips PRs that only touch `.github/**`. The OpenSpec check is the most TEC-flavoured of the bunch, see [Which parts are TEC policy](#which-parts-are-tec-policy-and-which-are-reusable). The project link workflow creates the board from a template if it doesn't exist yet.

### Release workflows

These only matter when you're owning a release. They're all started by hand from the Actions tab, and they run in roughly this order: prepare the branch, replace the TBDs, sync translations, process the changelog, and after shipping, merge forward.

Each one creates a branch, makes its change, and opens a `[BOT]` pull request for a human to merge. None of them push straight to a release branch, so there's always a diff to look at before anything lands.

| Workflow | Inputs | What it does |
|---|---|---|
| `release-prepare-branch.yml` | New branch name, bump type | Creates the release branch and bumps the version everywhere |
| `release-replace-tbd-entries.yml` | None | Swaps every `TBD` for the current version |
| `release-sync-translations.yml` | None | Regenerates the `.pot` file and pushes it to GlotPress |
| `release-process-changelog.yml` | Version, date, generate or amend | Writes the pending changelog entries into `changelog.md` and `readme.txt` |
| `release-merge-forward.yml` | Target branch | Merges the current branch forward into the target through a PR |
| `release-update-wp-version.yml` | Tested-up-to version, whether to raise the minimum | Updates the WordPress version requirements |

Some notes on each:

- Prepare Branch offers four bump types: major, feature, maintenance and hotfix. It reads the list of files that carry the version number from `.puprc`, so it works on any plugin with that file set up. It opens the version-bump PR into the new release branch.
- Replace TBD Entries exists because developers write `@since TBD` in docblocks during development. Nobody knows the version number until release day.
- Sync Translations only pushes to translations.stellarwp.com when run on `main` or a release branch. On any other branch it just regenerates the `.pot` file. When it does push, it also imports into GlotPress and adds a `language` changelog entry with the import result.
- Process Changelog can figure out the version on its own from `.puprc`. Run it again with `amend` if more entries land after the first pass.
- Merge Forward creates the target branch if it doesn't exist yet. The usual use is a release branch back into `main`.
- Update WordPress Version is independent of the release cycle. Run it whenever WordPress ships and the tested-up-to value needs to move. It updates `readme.txt`, the plugin header, and any workflow that installs a pinned WordPress version.

### Skip markers

A bot PR shouldn't be blocked by checks meant for humans. Putting one of these strings anywhere in the PR body turns the matching check off:

| Marker | Skips |
|---|---|
| `[skip-changelog]` | `changelogger.yml` |
| `[skip-phpcs]` | `phpcs.yml` |
| `[skip-lint]` | `lint.yml` |

The release workflows and the sync PR add these for you. The checks re-run when a PR body is edited, so adding or removing a marker takes effect straight away. There's no skip marker for the OpenSpec check, and that's on purpose.

## Composite actions

You'll come here when a workflow does something you don't understand and the interesting part turns out to live in `.github/actions/`. Product repos reference these at `@main`, so a change here is live everywhere the moment it merges.

| Action | Used by | What it does |
|---|---|---|
| `check-php-changes` | `phpcs.yml` | Outputs whether any PHP file changed in the PR |
| `process-changelog` | `release-process-changelog.yml` | Wraps `bin/process-changelog.sh` |
| `add-changelog` | `release-sync-translations.yml` | Writes a changelog YAML file |
| `generate-pot` | `release-sync-translations.yml` | Runs `wp i18n make-pot` |
| `push-translations` | `release-sync-translations.yml` | Uploads the `.pot` file and imports it into GlotPress |
| `smart-checkout` | Test workflows in product repos | Checks out a second repo at a matching branch |
| `verify-openspec-plan` | `openspec-plan.yml` | Checks the shared plans repo for a valid plan |

A few of these deserve a sentence more. `process-changelog` switches to amend mode on its own when the changelog directory is empty and `package.json` already carries the release version, which is what happens on the last test package before a release. `generate-pot` downloads WP-CLI on the fly and excludes everything in `.distignore`. `push-translations` rsyncs the file up, runs the import over SSH, and returns the output so the changelog entry can quote it. `smart-checkout` tries the PR's branch first, then the base branch, then the default branch, which is how a `the-events-calendar` PR gets tested against the matching `tribe-common` branch when one exists. `verify-openspec-plan` works out the ticket ID from the branch name or PR title, then checks that the plan is complete, valid, and not archived yet.

## What a product repo needs before it can be synced

This is the section to read when you're adding a repo to `sync.yml` for the first time. The synced workflows assume a few things about the target, and a missing piece gives you a failing run rather than a helpful error.

First, `tec-bot` needs to be a collaborator with write access, or the sync action can't open PRs.

Second, secrets. The release workflows and the OpenSpec check use `GHA_BOT_TOKEN_MANAGER` to open PRs and read the private plans repo. `phpcs.yml` uses `GH_BOT_TOKEN`. Translation sync needs four more: `TRANSLATIONS_DEPLOY_HOST`, `TRANSLATIONS_DEPLOY_USER`, `TRANSLATIONS_DEPLOY_SSH_KEY` and `TRANSLATIONS_DEPLOY_POT_LOCATION`.

Third, a `.puprc` file at the root. That's the config for [pup](https://github.com/stellarwp/pup), our packaging tool, and the release workflows lean on it heavily. It needs a `paths.versions` array listing every file that carries the version number with a regex to find it, and an `i18n` entry whose URL contains `translations.stellarwp.com`.

Then a few smaller things: a `package.json` with a `changelogger` section and a `lint` script, a `changelog.md` and `readme.txt` in the format changelogger expects, and a `CLAUDE.md` symlink to `AGENTS.md` created by hand. For the OpenSpec check to actually block anything, branch protection has to require the **OpenSpec Plan** status check. Without that it's a red X that everyone ignores.

## How this repository checks itself

A broken template reaches eight repos before anyone notices, so this repo lints itself harder than most.

`.github/workflows/check-templates.yml` runs on every PR that touches templates, the sync config, or the actions. It copies `templates/workflows/*.yml` into a fake `.github/workflows/` folder and runs [actionlint](https://github.com/rhysd/actionlint) over them, because the templates aren't workflows of this repo and would otherwise never be linted. It fails if any source listed in `sync.yml` is a symlink. It runs `tests/test-wp-version-math.py` against the version arithmetic in the WordPress version workflow. And it installs the pinned OpenSpec CLI and runs `tests/test-openspec-plan.py` against the real action scripts.

## Some "Gotchas"

Things that have bitten us, so they don't have to bite you.

- When a sync run fails, it fails quietly. The product repos just... don't get a PR. Nobody gets pinged. If you pushed a template change and nothing showed up, the Actions tab here is the first place to look.
- One bad file takes down the whole group. The `CLAUDE.md` symlink stopped every plugin sync for a while until it was pulled from the config.
- Sync PRs can sit around. Each product repo has to review and merge its own, and an old one left open will conflict with the next.
- Composite actions are pinned to `@main`. Merge a change to an action here and every product repo is running it immediately, with no PR on their side to warn them. Treat action changes like production deploys.
- The release workflows create and push their working branch before making any changes. If a run dies halfway, you may need to delete a stray `task/...` branch by hand before rerunning.
- Replace TBD Entries does exactly what it says. Every literal `TBD` in matching file types outside `vendor`, `node_modules` and `tests` gets replaced. Read its PR rather than trusting it.

## Which parts are TEC policy and which are reusable

If you're reading this from another team, this is the section for you. Some of what this repo syncs is generic plugin CI you could lift as is. Some of it encodes how TEC works and would need changing, or dropping, in your setup.

Reusable as they are, or with a config change:

- The sync mechanism and group layout.
- The editor and lint config files.
- Changelog checking and processing, as long as you use `@stellarwp/changelogger`.
- Version bumping, TBD replacement, merge forward, and the WordPress version update. All of these are driven by `.puprc` rather than hard-coded paths.
- `check-php-changes` and `smart-checkout`.

TEC specific:

- The OpenSpec plan check and everything around it: the private `the-events-calendar/plans` store, the `tec-plans` naming, and the rule that every PR has a ticket ID in its branch name.
- `AGENTS.md`, which points at TEC skills and TEC repositories.
- The PR template's plan section and AI disclosure block.
- Translation sync, which pushes to translations.stellarwp.com under a `tec/` prefix and reads the plugin slug from `.puprc`.
- The release branch naming (`release/T25.<codename>`) and the project board template used by `link-project.yml`.
- The `tec-bot` account and its tokens.

## Related repositories

- [stellarwp/github-actions](https://github.com/stellarwp/github-actions) holds org-wide reusable workflows. Our synced `phpcs.yml` calls its `phpcs.yml`. It also carries `zip.yml` and `dependency-zip.yml`, which product repos use for packaging.
- [the-events-calendar/plans](https://github.com/the-events-calendar/plans) is the shared OpenSpec store the plan check reads from. It's private.
- [stellarwp/skills-se](https://github.com/stellarwp/skills-se) holds the agent skills `AGENTS.md` refers to.
- [the-events-calendar/gh-action-project-link](https://github.com/the-events-calendar/gh-action-project-link) is the action behind `link-project.yml`.
