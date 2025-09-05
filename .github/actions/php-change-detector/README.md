# PHP Change Detector Action

This composite action detects whether PHP files have changed in a pull request and provides outputs to determine if subsequent workflows should run. It leverages the [`check-skip-flag`](../check-skip-flag/README.md) action for enhanced skip flag handling.

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
- **Enhanced Skip Flag Support**: Uses the [`check-skip-flag`](../check-skip-flag/README.md) action for robust skip flag handling
- **Case-Insensitive Skip Detection**: Works with any case combination of skip flags
- **Git Diff Analysis**: Compares against the PR base branch to find changed files
- **Rich GitHub Summary**: Provides clear summary with visual indicators in the GitHub UI
- **Conditional Logic**: Outputs boolean-like values (0/1) for easy conditional execution
- **Modular Architecture**: Leverages reusable components for better maintainability

## Skip Flag Behavior

This action uses the [`check-skip-flag`](../check-skip-flag/README.md) action internally, which provides enhanced skip flag detection:

### Enhanced Features:
- **Case-Insensitive Detection**: Matches `[skip-phpcs]`, `[SKIP-PHPCS]`, `[Skip-Phpcs]`, etc.
- **Detailed Reporting**: Provides comprehensive step summaries with clear skip reasons
- **Consistent Behavior**: Uses the same skip logic across all actions

### Skip Process:
1. If a `skip-flag` is provided, the action calls `check-skip-flag` to validate the PR body
2. If the skip flag is found, both outputs are set to `0` and execution is skipped
3. If no skip flag is provided or the flag is not found, PHP change detection proceeds normally

## Example Skip Flag Usage

To skip PHPCS checks, add any of these formats to your PR description:

```markdown
This PR updates documentation only.

[skip-phpcs]
[SKIP-PHPCS]
[Skip-Phpcs]
```

## GitHub Step Summaries

The action provides rich step summaries based on the execution path:

### When PHP Changes Found:
```
## Found PHP file changes
Total changed PHP files: 3
- src/Components/Button.php
- src/Utils/Helper.php
- tests/Unit/ButtonTest.php
```

### When No PHP Changes:
```
## No PHP files changed
Workflow will not run.
```

### When Skipped:
```
⏭️ Action Skipped
Reason: Found [skip-phpcs] in PR body
Flag: phpcs
```

## Integration with Other Actions

This action integrates seamlessly with other workflow management actions:

```yaml
- name: Check for skip flags
  id: skip-check
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: tests

- name: Check PHP changes
  id: php-changes
  if: steps.skip-check.outputs.should-skip != 'true'
  uses: the-events-calendar/actions/.github/actions/php-change-detector@main

- name: Run comprehensive tests
  if: steps.php-changes.outputs.should-run == '1'
  run: composer test
```

## Migration from Reusable Workflow

This action replaces the `php-change-detector.yml` reusable workflow. The main differences:

1. **Usage**: Called with `uses: the-events-calendar/actions/.github/actions/php-change-detector@main` instead of workflow call
2. **Outputs**: Access outputs through step outputs instead of job outputs
3. **Enhanced Skip Logic**: Now uses the dedicated `check-skip-flag` action for improved reliability
4. **Better Reporting**: Enhanced step summaries with visual indicators

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

## Benefits of Modular Architecture

By using the `check-skip-flag` action internally:

- **Consistency**: Skip flag behavior is identical across all actions
- **Maintainability**: Skip logic is centralized and easier to update
- **Reliability**: Enhanced error handling and edge case management
- **Flexibility**: Benefits from improvements to the `check-skip-flag` action automatically

## Troubleshooting

### Common Issues

#### Skip Flag Not Working
- Verify the flag format in your PR body: `[skip-{flag}]`
- Check that the `skip-flag` input matches your PR body text
- Remember that detection is case-insensitive

#### No PHP Changes Detected
- Ensure your changes include `.php` files
- Verify the PR has been properly created with file diffs
- Check that the repository checkout has sufficient depth

#### Action Outputs Not Working
- Verify you're accessing outputs correctly: `steps.{step-id}.outputs.should-run`
- Ensure the condition uses string comparison: `== '1'` not `== 1`
- Check that the step ID matches your YAML configuration
