# Slic Test Runner Action

This composite action runs PHP tests using the slic testing framework, which is commonly used for WordPress plugin testing. It leverages the [`check-skip-flag`](../check-skip-flag/README.md) action for enhanced skip flag handling.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `suite` | Test suite to run | Yes | - |
| `skip-flag` | Skip flag to check for (e.g., skip-views-core) | No | `''` |
| `wordpress-version` | WordPress version to use | No | `'6.6'` |
| `additional-setup` | Additional setup commands to run before tests | No | `''` |
| `gh-bot-token` | GitHub bot token for checkout | No | - |

## Usage

### Basic usage

```yaml
- name: Run unit tests
  uses: ./.github/actions/slic-test-runner
  with:
    suite: unit
```

### With custom WordPress version

```yaml
- name: Run integration tests
  uses: ./.github/actions/slic-test-runner
  with:
    suite: integration
    wordpress-version: '6.4'
```

### With skip flag

```yaml
- name: Run core tests
  uses: ./.github/actions/slic-test-runner
  with:
    suite: views-core
    skip-flag: views-core
```

### With additional setup

```yaml
- name: Run tests with setup
  uses: ./.github/actions/slic-test-runner
  with:
    suite: wpunit
    additional-setup: |
      ${SLIC_BIN} wp plugin install woocommerce --activate
      ${SLIC_BIN} wp option update timezone_string "America/New_York"
```

### With bot token for private repositories

```yaml
- name: Run tests
  uses: ./.github/actions/slic-test-runner
  with:
    suite: unit
    gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

### Complete workflow example

```yaml
name: PHP Tests
on:
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        uses: ./.github/actions/slic-test-runner
        with:
          suite: unit
          wordpress-version: '6.6'

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run integration tests
        uses: ./.github/actions/slic-test-runner
        with:
          suite: integration
          additional-setup: |
            ${SLIC_BIN} wp plugin install advanced-custom-fields --activate
```

## Features

- **Slic Framework**: Uses the stellarwp/slic testing framework
- **WordPress Integration**: Sets up WordPress with specified version
- **Docker Environment**: Manages Docker containers for testing
- **PHP File Detection**: Automatically skips if no PHP files changed
- **Enhanced Skip Flag Support**: Uses the [`check-skip-flag`](../check-skip-flag/README.md) action for robust skip flag handling
- **Case-Insensitive Skip Detection**: Works with any case combination of skip flags
- **Composer Caching**: Caches composer dependencies for faster runs
- **Chrome Support**: Sets up Chrome container for browser tests
- **Plugin Setup**: Configures The Events Calendar and common plugins
- **Flexible Setup**: Supports additional setup commands before testing
- **Modular Architecture**: Leverages reusable components for better maintainability

## Test Suites

Common test suites you can run:

- `unit` - Unit tests
- `integration` - Integration tests
- `wpunit` - WordPress unit tests
- `functional` - Functional tests
- `views-core` - Views core tests
- `acceptance` - Acceptance tests

## Skip Flag Behavior

This action uses the [`check-skip-flag`](../check-skip-flag/README.md) action internally, which provides enhanced skip flag detection:

### Enhanced Features:
- **Case-Insensitive Detection**: Matches `[skip-views-core]`, `[SKIP-VIEWS-CORE]`, `[Skip-Views-Core]`, etc.
- **Detailed Reporting**: Provides comprehensive step summaries with clear skip reasons
- **Consistent Behavior**: Uses the same skip logic across all actions

### Skip Process:
1. If a `skip-flag` is provided, the action calls `check-skip-flag` to validate the PR body
2. If the skip flag is found, all test execution is skipped
3. If no skip flag is provided or the flag is not found, the test process continues

### Example Skip Flag Usage:
Adding any of these formats to your PR description will skip the views-core test suite:

```markdown
This PR updates documentation only.

[skip-views-core]
[SKIP-VIEWS-CORE]
[Skip-Views-Core]
```

## Environment Variables

The action sets up several environment variables:

- `SLIC_BIN` - Path to the slic binary
- `SLIC_WP_DIR` - WordPress directory path
- `SLIC_WORDPRESS_DOCKERFILE` - Docker file to use
- `SLIC` - Indicates slic environment (set to 1)
- `CI` - Indicates CI environment (set to 1)
- `SSH_AUTH_SOCK` - SSH agent socket path

## WordPress Setup

The action automatically:

1. Updates WordPress to the specified version
2. Installs and activates the Twenty Twenty theme
3. Sets up The Events Calendar and common plugins
4. Configures the Docker environment for testing

## Migration from Reusable Workflow

This action replaces the `slic-test-runner.yml` reusable workflow. The main differences:

1. **Secrets**: The `gh-bot-token` is now passed as an input instead of a secret
2. **Usage**: Called with `uses: ./.github/actions/slic-test-runner` instead of workflow call
3. **Enhanced Skip Logic**: Now uses the dedicated `check-skip-flag` action for improved reliability
4. **Better Reporting**: Enhanced step summaries with visual indicators

### Before (Reusable Workflow)

```yaml
uses: ./.github/workflows/reusable/slic-test-runner.yml
with:
  suite: unit
  skip-flag: views-core
secrets:
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

### After (Composite Action)

```yaml
uses: ./.github/actions/slic-test-runner
with:
  suite: unit
  skip-flag: views-core
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

## Benefits of Modular Architecture

By using the `check-skip-flag` action internally:

- **Consistency**: Skip flag behavior is identical across all actions
- **Maintainability**: Skip logic is centralized and easier to update
- **Reliability**: Enhanced error handling and edge case management
- **Flexibility**: Benefits from improvements to the `check-skip-flag` action automatically

## GitHub Step Summaries

The action provides rich step summaries based on the execution path:

### When Tests Run:
```
## Found PHP file changes, running PHP tests.
```

### When No PHP Changes:
```
## No PHP Files changed, PHP tests automatically pass.
```

### When Skipped:
```
⏭️ Action Skipped
Reason: Found [skip-views-core] in PR body
Flag: views-core
```

## Troubleshooting

### Tests not running

- Check if PHP files have changed in your PR
- Verify the suite name is correct
- Check for skip flags in the PR description

### Docker issues

- Ensure sufficient disk space
- Check Docker daemon is running
- Review slic logs for specific errors

### WordPress version issues

- Verify the WordPress version exists
- Check if the version is compatible with your plugins
- Review WordPress core update logs
