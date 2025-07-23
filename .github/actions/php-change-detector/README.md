# PHP Change Detector Action

This composite action detects whether PHP files have changed in a pull request and provides outputs to determine if subsequent workflows should run.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `skip-flag` | Skip flag to check for (e.g., skip-phpcs) | No | `''` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `has-php-changes` | Whether PHP files have changed (1 or 0) | String |
| `should-run` | Whether the workflow should run (1 or 0) | String |

## Usage

### Basic usage

```yaml
- name: Check PHP changes
  id: php-changes
  uses: the-events-calendar/actions/.github/actions/php-change-detector@main

- name: Run PHP tests
  if: steps.php-changes.outputs.should-run == '1'
  run: echo "Running PHP tests..."
```

### With skip flag

```yaml
- name: Check PHP changes
  id: php-changes
  uses: the-events-calendar/actions/.github/actions/php-change-detector@main
  with:
    skip-flag: phpcs

- name: Run PHPCS
  if: steps.php-changes.outputs.should-run == '1'
  run: phpcs --standard=WordPress src/
```

### Conditional workflow execution

```yaml
jobs:
  check-changes:
    runs-on: ubuntu-latest
    outputs:
      should-run: ${{ steps.php-changes.outputs.should-run }}
      has-changes: ${{ steps.php-changes.outputs.has-php-changes }}
    steps:
      - name: Check PHP changes
        id: php-changes
        uses: the-events-calendar/actions/.github/actions/php-change-detector@main

  php-tests:
    needs: check-changes
    if: needs.check-changes.outputs.should-run == '1'
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: echo "Running PHP tests..."
```

## Features

- **PHP File Detection**: Automatically detects changes in `.php` files
- **Skip Flag Support**: Allows skipping execution based on PR body tags (e.g., `[skip-phpcs]`)
- **Git Diff Analysis**: Compares against the PR base branch to find changed files
- **GitHub Summary**: Provides clear summary of detected changes in the GitHub UI
- **Conditional Logic**: Outputs boolean-like values (0/1) for easy conditional execution

## Skip Flag Behavior

If a `skip-flag` is provided and the PR body contains `[skip-{flag}]`, the action will:
- Set both outputs to `0`
- Skip the file change detection
- Add a skip message to the GitHub step summary

## Example Skip Flag Usage

To skip PHPCS checks, add `[skip-phpcs]` anywhere in your PR description:

```
This PR updates documentation only.

[skip-phpcs]
```

## Migration from Reusable Workflow

This action replaces the `php-change-detector.yml` reusable workflow. The main differences:

1. **Usage**: Called with `uses: the-events-calendar/actions/.github/actions/php-change-detector@main` instead of workflow call
2. **Outputs**: Access outputs through step outputs instead of job outputs
3. **Skip Logic**: The skip condition logic is now handled internally within the action

### Before (Reusable Workflow)
```yaml
uses: ./.github/workflows/reusable/php-change-detector.yml
with:
  skip-flag: phpcs
```

### After (Composite Action)
```yaml
uses: the-events-calendar/actions/.github/actions/php-change-detector@main
with:
  skip-flag: phpcs
```
