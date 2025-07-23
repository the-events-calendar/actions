# WordPress Plugin Actions Collection

This repository provides a collection of reusable GitHub Actions specifically designed for WordPress plugin development and release management. These actions replace the previous reusable workflows and offer better modularity and easier integration.

## Available Actions

### 🛠️ Setup and Infrastructure

#### [basic-setup](./basic-setup/)
Sets up a basic environment for CI/CD workflows with PHP and Node.js configuration.

```yaml
- uses: the-events-calendar/actions/.github/actions/basic-setup@main
  with:
    setup-php: 'true'
    setup-node: 'true'
    php-version: '8.1'
```

### 🔧 Utility Actions

#### [detect-version](./detect-version/)
Detects the current version from package.json, PHP files, or .puprc configuration.

```yaml
- uses: the-events-calendar/actions/.github/actions/detect-version@main
  with:
    fallback-version: '1.0.0'
```

#### [check-skip-flag](./check-skip-flag/)
Checks for skip flags in PR descriptions to determine if actions should be skipped.

```yaml
- uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: phpcs
```

#### [detect-branch-type](./detect-branch-type/)
Analyzes Git branch names to determine their type and characteristics for conditional workflow logic.

```yaml
- uses: the-events-calendar/actions/.github/actions/detect-branch-type@main
```

### 🔍 Code Analysis

#### [php-change-detector](./php-change-detector/)
Detects PHP file changes in pull requests and provides conditional execution logic.

```yaml
- uses: the-events-calendar/actions/.github/actions/php-change-detector@main
  with:
    skip-flag: phpcs
```

### 🧪 Testing

#### [slic-test-runner](./slic-test-runner/)
Runs PHP tests using the slic testing framework with WordPress environment setup.

```yaml
- uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
  with:
    suite: unit
    wordpress-version: '6.6'
```

### 📝 Release Management

#### [analyze-changes](./analyze-changes/)
Analyzes git changes to detect WordPress hooks (filters/actions) and view modifications for release documentation.

```yaml
- uses: the-events-calendar/actions/.github/actions/analyze-changes@main
  with:
    compare-commit: ${{ github.event.pull_request.base.sha }}
    output-format: changelog
```

#### [process-changelog](./process-changelog/)
Processes changelogs for plugin releases with automatic version detection and formatting.

```yaml
- uses: the-events-calendar/actions/.github/actions/process-changelog@main
  with:
    release-version: 'figure-it-out'
    action-type: 'generate'
```

#### [replace-tbd-entries](./replace-tbd-entries/)
Finds and replaces TBD placeholders in code files with current version numbers.

```yaml
- uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
```

#### [sync-translations](./sync-translations/)
Syncs translation files and manages GlotPress integration for WordPress plugins.

```yaml
- uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

## Quick Start Guide

### Basic Plugin Workflow

Here's a complete example of how to use these actions in a plugin workflow:

```yaml
name: Plugin CI/CD
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  setup-and-analyze:
    runs-on: ubuntu-latest
    outputs:
      should-test: ${{ steps.php-changes.outputs.should-run }}
      has-changes: ${{ steps.analyze.outputs.changes-detected }}
    steps:
      - name: Setup environment
        uses: the-events-calendar/actions/.github/actions/basic-setup@main
        with:
          setup-php: 'true'
          setup-node: 'true'

      - name: Check PHP changes
        id: php-changes
        uses: the-events-calendar/actions/.github/actions/php-change-detector@main

      - name: Analyze changes for release
        id: analyze
        if: github.event_name == 'push'
        uses: the-events-calendar/actions/.github/actions/analyze-changes@main

  test:
    needs: setup-and-analyze
    if: needs.setup-and-analyze.outputs.should-test == '1'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        suite: [unit, integration, wpunit]
    steps:
      - name: Run tests
        uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
        with:
          suite: ${{ matrix.suite }}

  release:
    needs: [setup-and-analyze, test]
    if: github.event_name == 'push' && needs.setup-and-analyze.outputs.has-changes == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Replace TBD entries
        uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

      - name: Sync translations
        uses: the-events-calendar/actions/.github/actions/sync-translations@main
        with:
          translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
          translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
          translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

      - name: Process changelog
        uses: the-events-calendar/actions/.github/actions/process-changelog@main
        with:
          action-type: 'generate'
```

### Release Workflow

For dedicated release workflows:

```yaml
name: Release Process
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version'
        required: false
        default: 'figure-it-out'

jobs:
  analyze-and-process:
    runs-on: ubuntu-latest
    steps:
      - name: Setup environment
        uses: the-events-calendar/actions/.github/actions/basic-setup@main

      - name: Analyze changes since last release
        id: analyze
        uses: the-events-calendar/actions/.github/actions/analyze-changes@main
        with:
          output-format: changelog

      - name: Process changelog
        uses: the-events-calendar/actions/.github/actions/process-changelog@main
        with:
          release-version: ${{ github.event.inputs.version }}
          action-type: 'generate'
```

## Migration Guide

### From Reusable Workflows

If you're migrating from the previous reusable workflows, here are the key changes:

#### Basic Setup
```yaml
# Before
uses: ./.github/workflows/reusable/basic-setup.yml
with:
  setup-node: true
secrets:
  gh-bot-token: ${{ secrets.BOT_TOKEN }}

# After
uses: the-events-calendar/actions/.github/actions/basic-setup@main
with:
  setup-node: 'true'
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

#### PHP Change Detection
```yaml
# Before
uses: ./.github/workflows/reusable/php-change-detector.yml
with:
  skip-flag: phpcs

# After
uses: the-events-calendar/actions/.github/actions/php-change-detector@main
with:
  skip-flag: phpcs
```

#### Slic Test Runner
```yaml
# Before
uses: ./.github/workflows/reusable/slic-test-runner.yml
with:
  suite: unit
secrets:
  gh-bot-token: ${{ secrets.BOT_TOKEN }}

# After
uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
with:
  suite: unit
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

#### Analyze Changes
```yaml
# Before
uses: ./.github/workflows/reusable/release-process/analyze-changes.yml
with:
  compare-commit: ${{ github.event.pull_request.base.sha }}

# After
uses: the-events-calendar/actions/.github/actions/analyze-changes@main
with:
  compare-commit: ${{ github.event.pull_request.base.sha }}
```

#### Process Changelog
```yaml
# Before
uses: ./.github/workflows/reusable/release-process/process-changelog.yml
with:
  release-version: '6.2.0'

# After
uses: the-events-calendar/actions/.github/actions/process-changelog@main
with:
  release-version: '6.2.0'
```

#### Replace TBD Entries
```yaml
# Before
uses: ./.github/workflows/reusable/release-process/replace-tbd-entries.yml

# After
uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
```

#### Sync Translations
```yaml
# Before
uses: ./.github/workflows/reusable/release-process/sync-translations.yml
secrets:
  TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}

# After
uses: the-events-calendar/actions/.github/actions/sync-translations@main
with:
  translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
  translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
  translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
  translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### Key Differences

1. **Secrets → Inputs**: Bot tokens and other secrets are now passed as inputs
2. **Boolean Values**: Must be passed as strings (`'true'`/`'false'`)
3. **Output Access**: Use step outputs instead of job outputs
4. **Action Reference**: Use `the-events-calendar/actions/.github/actions/{action-name}@main`

## Best Practices

### Action Versioning
Always pin to a specific ref for production workflows:

```yaml
# Recommended for production
uses: the-events-calendar/actions/.github/actions/basic-setup@v1.0.0

# Or use main for latest features (development)
uses: the-events-calendar/actions/.github/actions/basic-setup@main
```

### Conditional Execution
Use outputs for efficient conditional execution:

```yaml
- name: Check changes
  id: changes
  uses: the-events-calendar/actions/.github/actions/php-change-detector@main

- name: Run expensive operation
  if: steps.changes.outputs.should-run == '1'
  run: echo "Only runs when needed"
```

### Error Handling
Use `continue-on-error` for non-critical steps:

```yaml
- name: Analyze changes
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main
```

### Matrix Strategies
Combine with matrix strategies for comprehensive testing:

```yaml
strategy:
  matrix:
    php-version: ['7.4', '8.0', '8.1']
    wordpress-version: ['6.4', '6.5', '6.6']
steps:
  - uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
    with:
      suite: unit
      wordpress-version: ${{ matrix.wordpress-version }}
```

## Common Patterns

### Skip Patterns
Use skip flags to bypass actions when not needed:

```yaml
# In PR description: [skip-tests] [skip-phpcs] [skip-changelog]

- uses: the-events-calendar/actions/.github/actions/php-change-detector@main
  with:
    skip-flag: tests

- uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
  with:
    skip-flag: tests
```

### Dependency Chain
Chain actions with dependencies:

```yaml
jobs:
  analyze:
    steps:
      - id: changes
        uses: the-events-calendar/actions/.github/actions/php-change-detector@main

  test:
    needs: analyze
    if: needs.analyze.outputs.should-run == '1'
    steps:
      - uses: the-events-calendar/actions/.github/actions/slic-test-runner@main

  release:
    needs: [analyze, test]
    if: success()
    steps:
      - uses: the-events-calendar/actions/.github/actions/process-changelog@main
```

## Troubleshooting

### Common Issues

#### Action Not Found
```
Error: Could not resolve to a valid repository
```
**Solution**: Ensure you're using the correct repository reference and the action exists.

#### Permission Denied
```
Error: Resource not accessible by integration
```
**Solution**: Check repository permissions and ensure the action has necessary access.

#### Invalid Input Type
```
Error: The 'setup-node' input should be a string, got boolean
```
**Solution**: Pass boolean values as strings: `'true'` instead of `true`.

### Debugging

Enable debug logging:

```yaml
env:
  ACTIONS_STEP_DEBUG: true
```

Use step outputs for debugging:

```yaml
- name: Debug outputs
  run: |
    echo "Changes detected: ${{ steps.analyze.outputs.changes-detected }}"
    echo "Should run: ${{ steps.php-changes.outputs.should-run }}"
```

## Contributing

When contributing new actions to this repository:

1. Create the action in a new directory under `.github/actions/`
2. Include comprehensive README documentation
3. Follow the established input/output patterns
4. Add usage examples
5. Test with actual plugin workflows

## Support

For issues with these actions:

1. Check the individual action READMEs for specific troubleshooting
2. Review the GitHub Actions logs for detailed error messages
3. Ensure all prerequisites and dependencies are met
4. Verify input parameters match the expected format

## License

These actions are provided under the same license as the WordPress plugins they support.
