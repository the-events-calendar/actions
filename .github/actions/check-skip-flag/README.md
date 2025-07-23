# Check Skip Flag Action

A utility action that checks for skip flags in PR descriptions to determine if subsequent actions should be skipped. This action consolidates skip flag logic that was previously duplicated across multiple actions.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `skip-flag` | Skip flag to check for (e.g., skip-phpcs, skip-tests) | Yes | - |
| `pr-body` | PR body to check (defaults to current PR body) | No | `${{ github.event.pull_request.body }}` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `should-skip` | Whether the action should be skipped | String (`true`/`false`) |
| `skip-reason` | Reason for skipping (if applicable) | String |

## Usage

### Basic usage

```yaml
- name: Check if PHPCS should be skipped
  id: check-skip
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: phpcs

- name: Run PHPCS
  if: steps.check-skip.outputs.should-skip != 'true'
  run: phpcs --standard=WordPress src/
```

### Multiple skip flags

```yaml
- name: Check test skip
  id: check-tests
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: tests

- name: Check linting skip
  id: check-lint
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: lint

- name: Run tests
  if: steps.check-tests.outputs.should-skip != 'true'
  run: npm test

- name: Run linting
  if: steps.check-lint.outputs.should-skip != 'true'
  run: npm run lint
```

### Custom PR body

```yaml
- name: Check skip with custom body
  id: check-skip
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: deployment
    pr-body: ${{ github.event.issue.body }}
```

### Conditional workflow execution

```yaml
jobs:
  check-flags:
    runs-on: ubuntu-latest
    outputs:
      skip-tests: ${{ steps.check-tests.outputs.should-skip }}
      skip-build: ${{ steps.check-build.outputs.should-skip }}
    steps:
      - name: Check test skip
        id: check-tests
        uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
        with:
          skip-flag: tests

      - name: Check build skip
        id: check-build
        uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
        with:
          skip-flag: build

  run-tests:
    needs: check-flags
    if: needs.check-flags.outputs.skip-tests != 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: npm test

  run-build:
    needs: check-flags
    if: needs.check-flags.outputs.skip-build != 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Build assets
        run: npm run build
```

## Features

### Skip Flag Detection

The action looks for flags in the format `[skip-{flag}]` anywhere in the PR body:

```markdown
This PR updates documentation only.

[skip-tests] [skip-phpcs]
```

### Case Insensitive

The action performs case-insensitive matching:

- `[skip-tests]` ✅
- `[SKIP-TESTS]` ✅
- `[Skip-Tests]` ✅

### Multiple Flags

Each flag is checked independently, allowing granular control:

- `[skip-tests]` - Skip test suite
- `[skip-phpcs]` - Skip code style checks
- `[skip-build]` - Skip build process
- `[skip-deployment]` - Skip deployment steps

### GitHub Integration

- **Step Summary**: Displays clear information about skip decisions
- **Detailed Output**: Provides skip reason for debugging
- **Visual Indicators**: Uses emojis for quick visual feedback

## Common Skip Flags

### Testing

- `tests` - Skip all tests
- `unit` - Skip unit tests only
- `integration` - Skip integration tests only
- `e2e` - Skip end-to-end tests

### Code Quality

- `phpcs` - Skip PHP code style checks
- `eslint` - Skip JavaScript linting
- `stylelint` - Skip CSS linting

### Build & Deploy

- `build` - Skip asset building
- `deployment` - Skip deployment steps
- `translations` - Skip translation sync

### Documentation

- `docs` - Skip documentation updates
- `changelog` - Skip changelog processing

## Migration Benefits

This action eliminates duplicated skip flag logic found in:

- `php-change-detector` action (lines 25-32)
- `slic-test-runner` action (lines 25-32)
- Various workflow files with custom skip logic

### Before (Duplicated Code)

```yaml
# In php-change-detector
- name: Check skip condition
  run: |
    if [[ "${{ github.event.pull_request.body }}" == *"[skip-phpcs]"* ]]; then
      echo "should_skip=true" >> $GITHUB_OUTPUT
    fi

# In slic-test-runner
- name: Check skip condition
  run: |
    if [[ "${{ github.event.pull_request.body }}" == *"[skip-tests]"* ]]; then
      echo "should_skip=true" >> $GITHUB_OUTPUT
    fi
```

### After (Modularized)

```yaml
# In any action
- name: Check skip
  id: skip
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: phpcs

- name: Run action
  if: steps.skip.outputs.should-skip != 'true'
  run: echo "Action runs"
```

## Output Examples

### When Flag Found

```yaml
should-skip: "true"
skip-reason: "Found [skip-tests] in PR body"
```

### When Flag Not Found

```yaml
should-skip: "false"
skip-reason: ""
```

## Step Summary Examples

### Skipped Action

```text
## ⏭️ Action Skipped
**Reason**: Found `[skip-tests]` in PR body
**Flag**: `tests`
```

### Action Will Run

```text
## ✅ Action Will Run
No `[skip-tests]` flag found in PR body
```

## Best Practices

### Combine with Conditional Logic

```yaml
- name: Check skip
  id: skip
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: deployment

- name: Deploy to staging
  if: steps.skip.outputs.should-skip != 'true' && github.ref == 'refs/heads/develop'
  run: deploy-staging.sh
```

### Use in Job Conditions

```yaml
jobs:
  check-skip:
    outputs:
      should-skip: ${{ steps.check.outputs.should-skip }}
    steps:
      - id: check
        uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
        with:
          skip-flag: tests

  run-tests:
    needs: check-skip
    if: needs.check-skip.outputs.should-skip != 'true'
    steps:
      - run: npm test
```

### Error Handling

```yaml
- name: Check skip
  id: skip
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: tests

- name: Run tests (skip on error)
  if: steps.skip.outcome == 'success' && steps.skip.outputs.should-skip != 'true'
  run: npm test
```

## Troubleshooting

### Flag Not Recognized

If the skip flag isn't working:

- Verify the flag format: `[skip-{flag}]`
- Check for typos in the flag name
- Ensure brackets are present: `[` and `]`

### Action Still Running

If actions run despite skip flags:

- Check the conditional logic: `if: steps.skip.outputs.should-skip != 'true'`
- Verify the flag matches the input exactly
- Check that PR body is being read correctly

### Using Multiple Flags

When using multiple flags:

- Each flag must be checked separately
- Use different step IDs for each check
- Combine conditions if needed: `if: steps.skip1.outputs.should-skip != 'true' && steps.skip2.outputs.should-skip != 'true'`
