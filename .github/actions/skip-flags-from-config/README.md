# Skip Flags from Config Action

This action reads skip flags configuration from `package.json` and generates skip flags for specific test suites. It allows dynamic configuration of test skip flags based on test suite requirements.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `test-suite-name` | The test suite name to get skip flags for (kebab-case, e.g., "views-full-suite") | Yes | - |
| `package-json-path` | Path to package.json file | No | `package.json` |
| `config-key` | Configuration key path in package.json | No | `tec-actions.skip-flags` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `skip-flags` | Space-separated string of skip flags (e.g., "--skip-some-test --skip-another-test") | String |
| `flag-count` | Number of skip flags generated | String |
| `has-flags` | Whether any skip flags were found (true/false) | String |

## Configuration Format

Add skip flags configuration to your `package.json` under the `tec-actions.skip-flags` key:

```json
{
  "tec-actions": {
    "skip-flags": {
      "views-full-suite": [
        "some-slow-test",
        "another-legacy-feature"
      ],
      "views-core": [
        "unstable-feature",
        "known-flaky-test"
      ],
      "default": [
        "common-fixture"
      ]
    }
  }
}
```

### Configuration Rules

- **Test Suite Names**: Use kebab-case (e.g., `views-full-suite`, `integration-tests`)
- **Flag Suffixes**: Array of strings that will be prefixed with `--skip-`
- **Default Fallback**: Include a `default` array for suites not specifically configured
- **Flag Generation**: Each suffix becomes `--skip-{suffix}` in the output

## Usage Examples

### Basic Usage

```yaml
- name: Get skip flags for views test suite
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: views-full-suite

- name: Run tests with skip flags
  run: |
    npm test ${{ steps.skip-flags.outputs.skip-flags }}
```

### Integration with Test Commands

```yaml
- name: Generate skip flags
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: ${{ matrix.test-suite }}

- name: Run slic tests
  run: |
    SKIP_FLAGS="${{ steps.skip-flags.outputs.skip-flags }}"
    if [ -n "$SKIP_FLAGS" ]; then
      ./vendor/bin/slic run tests $SKIP_FLAGS
    else
      ./vendor/bin/slic run tests
    fi
```

### Conditional Flag Usage

```yaml
- name: Get skip flags
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: views-core

- name: Run tests (with flags if available)
  run: |
    echo "Found ${{ steps.skip-flags.outputs.flag-count }} skip flags"
    if [ "${{ steps.skip-flags.outputs.has-flags }}" = "true" ]; then
      echo "Running with skip flags: ${{ steps.skip-flags.outputs.skip-flags }}"
      npm test ${{ steps.skip-flags.outputs.skip-flags }}
    else
      echo "Running without skip flags"
      npm test
    fi
```

### Matrix Strategy

```yaml
strategy:
  matrix:
    test-suite: [views-core, views-integration, views-full-suite]

steps:
  - name: Get skip flags for current suite
    id: skip-flags
    uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
    with:
      test-suite-name: ${{ matrix.test-suite }}

  - name: Run test suite
    run: |
      echo "Testing ${{ matrix.test-suite }}"
      ./test-runner ${{ matrix.test-suite }} ${{ steps.skip-flags.outputs.skip-flags }}
```

### Custom Package.json Location

```yaml
- name: Get skip flags from custom location
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: integration-tests
    package-json-path: ./custom/package.json
```

## Configuration Examples

### Basic Configuration

```json
{
  "tec-actions": {
    "skip-flags": {
      "unit": ["slow-db-test"],
      "integration": ["external-api", "file-system"],
      "default": ["common-cleanup"]
    }
  }
}
```

### Advanced Configuration

```json
{
  "tec-actions": {
    "skip-flags": {
      "views-full-suite": [
        "legacy-calendar-view",
        "deprecated-event-display",
        "slow-recurring-events"
      ],
      "views-core": [
        "experimental-feature",
        "unstable-timezone-test"
      ],
      "views-integration": [
        "third-party-calendar",
        "external-event-source"
      ],
      "e2e": [
        "browser-specific-test",
        "flaky-ui-interaction"
      ],
      "default": [
        "maintenance-mode-test",
        "debug-only-feature"
      ]
    }
  }
}
```

## Lookup Logic

The action follows this precedence order:

1. **Suite-Specific Flags**: Looks for exact match with `test-suite-name`
2. **Default Flags**: Falls back to `default` array if no suite-specific configuration
3. **Empty Result**: Returns empty flags if neither is found

### Example Lookup

Given this configuration:
```json
{
  "tec-actions": {
    "skip-flags": {
      "views-full-suite": ["slow-test", "legacy-feature"],
      "default": ["common-fixture"]
    }
  }
}
```

**Lookups:**
- `views-full-suite` → `--skip-slow-test --skip-legacy-feature`
- `views-core` → `--skip-common-fixture` (uses default)
- `unknown-suite` → `--skip-common-fixture` (uses default)

## Output Examples

### Suite-Specific Flags Found

```
Test Suite: views-full-suite
Generated Flags:
- --skip-some-slow-test
- --skip-another-legacy-feature

Result: Generated 2 skip flag(s) ✅
```

**Outputs:**
```yaml
skip-flags: "--skip-some-slow-test --skip-another-legacy-feature"
flag-count: "2"
has-flags: "true"
```

### Using Default Flags

```
Test Suite: unknown-suite
ℹ️ No specific flags for unknown-suite, using default flags
Generated Flags:
- --skip-common-fixture

Result: Generated 1 skip flag(s) ✅
```

**Outputs:**
```yaml
skip-flags: "--skip-common-fixture"
flag-count: "1"
has-flags: "true"
```

### No Flags Found

```
Test Suite: test-suite
⚠️ No flags found for test-suite or default

Result: No skip flags generated ⚠️
```

**Outputs:**
```yaml
skip-flags: ""
flag-count: "0"
has-flags: "false"
```

## Error Handling

### Missing package.json

```
❌ Error: package.json not found at package.json
```

The action will exit with error code 1 and set all outputs to empty/false.

### Missing Configuration

```
⚠️ Warning: No skip-flags configuration found in tec-actions.skip-flags
```

The action will exit successfully with empty outputs.

### Invalid JSON

If `package.json` contains invalid JSON, the action will fail with a jq parsing error.

## Integration Examples

### With Existing Test Actions

```yaml
- name: Get skip flags
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: views-full-suite

- name: Run slic tests
  uses: the-events-calendar/actions/.github/actions/slic-test-runner@main
  with:
    suite: views-full-suite
    additional-setup: |
      echo "Using skip flags: ${{ steps.skip-flags.outputs.skip-flags }}"
      export SKIP_FLAGS="${{ steps.skip-flags.outputs.skip-flags }}"
```

### Dynamic Test Commands

```yaml
- name: Generate skip flags
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: ${{ github.event.inputs.test-suite }}

- name: Run dynamic test command
  run: |
    BASE_CMD="./vendor/bin/phpunit --testsuite=${{ github.event.inputs.test-suite }}"
    SKIP_FLAGS="${{ steps.skip-flags.outputs.skip-flags }}"

    if [ -n "$SKIP_FLAGS" ]; then
      FULL_CMD="$BASE_CMD $SKIP_FLAGS"
    else
      FULL_CMD="$BASE_CMD"
    fi

    echo "Executing: $FULL_CMD"
    eval $FULL_CMD
```

## Best Practices

### 1. Consistent Naming

Use kebab-case for both test suite names and flag suffixes:

```json
{
  "skip-flags": {
    "views-full-suite": ["slow-db-test", "legacy-ui-component"],
    "api-integration": ["rate-limited-endpoint", "external-service"]
  }
}
```

### 2. Meaningful Flag Names

Choose descriptive names that explain why tests are skipped:

```json
{
  "skip-flags": {
    "e2e": [
      "browser-compatibility-chrome-only",
      "requires-payment-gateway",
      "flaky-in-ci-environment"
    ]
  }
}
```

### 3. Default Configuration

Always include a `default` array for test suites without specific configuration:

```json
{
  "skip-flags": {
    "default": [
      "debug-only-test",
      "developer-environment-only"
    ]
  }
}
```

### 4. Documentation

Document your skip flags in comments or a separate file:

```json
{
  "skip-flags": {
    "views-full-suite": [
      "legacy-calendar-rendering",  // TODO: Remove after v7.0
      "timezone-dst-edge-case"      // Flaky due to system timezone
    ]
  }
}
```

## Troubleshooting

### No Flags Generated

1. **Check configuration**: Ensure `tec-actions.skip-flags` exists in package.json
2. **Verify test suite name**: Must match exactly (case-sensitive)
3. **Include default**: Add a `default` array as fallback

### Invalid JSON Error

1. **Validate JSON**: Use `jq . package.json` to check syntax
2. **Check quotes**: Ensure all strings are properly quoted
3. **Verify commas**: Check for missing or extra commas

### Wrong Flags Generated

1. **Check suffix format**: Flags should be array of strings
2. **Verify kebab-case**: Use hyphens, not underscores or camelCase
3. **Test locally**: Use `jq` to verify configuration parsing

## Migration from Hardcoded Flags

### Before (Hardcoded)

```yaml
- name: Run tests
  run: |
    phpunit --skip-slow-test --skip-legacy-feature --testsuite=views
```

### After (Dynamic)

```yaml
- name: Get skip flags
  id: skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: views

- name: Run tests
  run: |
    phpunit ${{ steps.skip-flags.outputs.skip-flags }} --testsuite=views
```

### Configuration Migration

```json
{
  "tec-actions": {
    "skip-flags": {
      "views": ["slow-test", "legacy-feature"]
    }
  }
}
```

## Integration with Workflow-Level Skip Flags

This action is designed to work alongside the [`check-skip-flag`](../check-skip-flag/README.md) action, creating a two-tier skipping system:

1. **Workflow-Level**: Skip entire workflows via PR flags (e.g., `[skip-tests]`)
2. **Test-Level**: Skip specific tests within suites via configuration

### Combined Usage Example

```yaml
- name: Check if entire test workflow should be skipped
  id: check-workflow-skip
  uses: the-events-calendar/actions/.github/actions/check-skip-flag@main
  with:
    skip-flag: tests

- name: Get test-specific skip flags for optimization
  if: steps.check-workflow-skip.outputs.should-skip != 'true'
  id: test-skip-flags
  uses: the-events-calendar/actions/.github/actions/skip-flags-from-config@main
  with:
    test-suite-name: views-full-suite

- name: Run optimized tests (if not skipped entirely)
  if: steps.check-workflow-skip.outputs.should-skip != 'true'
  run: |
    echo "Running tests with optimizations..."
    ./vendor/bin/phpunit --testsuite=views-full-suite ${{ steps.test-skip-flags.outputs.skip-flags }}
```

### Skip Level Comparison

| Skip Level | Action | Trigger | Purpose | Example |
|------------|--------|---------|---------|---------|
| **Workflow** | `check-skip-flag` | PR body `[skip-tests]` | Skip entire test workflow | Skip all tests for docs-only PR |
| **Test** | `skip-flags-from-config` | package.json config | Skip specific tests within suite | Skip slow tests for faster CI |

### When to Use Each

#### Use `check-skip-flag` when:
- PR contains only documentation changes
- Testing a specific component that doesn't affect others
- Debugging workflows and need to isolate issues
- Making emergency hotfixes that don't require full test suite

#### Use `skip-flags-from-config` when:
- Tests are running but you want to optimize for speed
- Known flaky tests that shouldn't block CI
- Legacy tests that are being phased out
- Environment-specific tests that don't apply

#### Use both together when:
- You want maximum flexibility in test execution
- Different team members have different testing needs
- CI needs to be both fast and thorough when needed
