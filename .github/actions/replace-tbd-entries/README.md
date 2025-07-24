# Replace TBD Entries Action

This composite action finds and replaces "TBD" (To Be Determined) placeholders in code files with the current version number. It's commonly used in release processes to update version references across the codebase.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `target-branch` | Target branch for the workflow | No | `'main'` |
| `additional-inputs` | Additional inputs to pass through (JSON string) | No | `'{}'` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `changes-made` | Whether any changes were made | Boolean |
| `current-version` | The current version found | String |

## Usage

### Basic usage

```yaml
- name: Replace TBD entries
  id: replace-tbd
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

- name: Check if changes were made
  if: steps.replace-tbd.outputs.changes-made == 'true'
  run: echo "TBD entries were replaced with version ${{ steps.replace-tbd.outputs.current-version }}"
```

### In a release workflow

```yaml
name: Release Process
on:
  push:
    branches: [release/*]

jobs:
  prepare-release:
    runs-on: ubuntu-latest
    steps:
      - name: Replace TBD entries
        id: replace-tbd
        uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

      - name: Commit changes
        if: steps.replace-tbd.outputs.changes-made == 'true'
        run: |
          git add .
          git commit -m "Replace TBD entries with version ${{ steps.replace-tbd.outputs.current-version }}"
          git push
```

### Conditional processing

```yaml
- name: Replace TBD entries
  id: replace-tbd
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

- name: Create PR if changes made
  if: steps.replace-tbd.outputs.changes-made == 'true'
  run: |
    gh pr create \
      --title "Replace TBD entries with v${{ steps.replace-tbd.outputs.current-version }}" \
      --body "Automated replacement of TBD placeholders"
```

## Features

### Version Detection

The action automatically detects the current version from:

1. **package.json** - Looks for `"version": "x.y.z"` field
2. **PHP Plugin Files** - Searches for `Version: x.y.z` headers in PHP files

### File Type Support

Searches and replaces TBD entries in:

- **PHP files** (*.php)
- **JavaScript files** (*.js,*.jsx, *.ts,*.tsx)
- **CSS files** (*.css,*.pcss)
- **Documentation** (*.md,*.txt)

### Directory Exclusions

Automatically excludes common directories:

- `.git/` - Git repository files
- `.github/` - GitHub workflow files
- `changelog/` - Changelog entries
- `common/` - Common submodule files
- `lang/` - Language/translation files
- `dev/` - Development files
- `src/resources/postcss/utilities/` - PostCSS utilities
- `tests/` - Test files
- `vendor/` - Third-party dependencies

### GitHub Integration

- **Step Summary**: Shows detailed information about found TBD entries
- **File Links**: Creates clickable links to specific lines where TBD was found
- **Change Tracking**: Reports whether any changes were actually made

## Example TBD Usage

Common patterns where TBD is used as a placeholder:

### PHP DocBlocks

```php
/**
 * New feature added in version TBD
 *
 * @since TBD
 * @param string $value The value to process
 */
function new_feature($value) {
    // Implementation
}
```

### JavaScript Comments

```javascript
/**
 * @since TBD
 * @version TBD
 */
const newFeature = () => {
    // Implementation
};
```

### CSS Comments

```css
/* Added in version TBD */
.new-feature {
    display: block;
}
```

### Documentation

```markdown
## Changelog

### TBD
- Added new feature
- Fixed bug in component
```

## Version Detection Logic

### Priority Order

1. **package.json** version (if file exists)
2. **PHP plugin header** version (first found)
3. **Default fallback** (0.0.0)

### Version Formats Supported

- Standard semantic versioning: `1.2.3`
- Extended versioning: `1.2.3.4`
- Version with pre-release info: `1.2.3-beta.1` (extracts `1.2.3`)

## Output Examples

### Step Summary

When TBD entries are found:

```text
### Debugging Information
- Current ref: `release/6.2.0`

## Current Version
* Version: `6.2.0`

## Files Changed
- [`src/views/single-event.php@L25`](https://github.com/org/repo/blob/release/6.2.0/src/views/single-event.php#L25)
- [`assets/js/main.js@L10`](https://github.com/org/repo/blob/release/6.2.0/assets/js/main.js#L10)
```

When no TBD entries found:

```text
### Debugging Information
- Current ref: `main`

## Current Version
* Version: `6.1.5`

## Files Changed
No TBD entries found in the repository.
```

## Workflow Integration

### Pre-Release Automation

```yaml
name: Pre-Release
on:
  push:
    branches: [release/*]

jobs:
  prepare:
    runs-on: ubuntu-latest
    steps:
      - name: Replace TBD entries
        uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

      - name: Run tests
        run: npm test

      - name: Build assets
        run: npm run build
```

### Manual Release Process

```yaml
name: Manual Release Prep
on:
  workflow_dispatch:
    inputs:
      create-pr:
        description: 'Create PR with changes'
        type: boolean
        default: true

jobs:
  prepare:
    runs-on: ubuntu-latest
    steps:
      - name: Replace TBD entries
        id: replace
        uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

      - name: Create PR
        if: github.event.inputs.create-pr == 'true' && steps.replace.outputs.changes-made == 'true'
        run: |
          git checkout -b "update-tbd-${{ steps.replace.outputs.current-version }}"
          git add .
          git commit -m "Replace TBD with v${{ steps.replace.outputs.current-version }}"
          git push origin "update-tbd-${{ steps.replace.outputs.current-version }}"
          gh pr create --title "Replace TBD entries" --body "Auto-generated PR"
```

## Migration from Reusable Workflow

This action replaces the `replace-tbd-entries.yml` reusable workflow.

### Before (Reusable Workflow)

```yaml
uses: ./.github/workflows/reusable/release-process/replace-tbd-entries.yml
with:
  target-branch: 'release/6.2.0'
```

### After (Composite Action)

```yaml
uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
with:
  target-branch: 'release/6.2.0'
```

### Key Differences

1. **Usage**: Direct action call instead of workflow call
2. **Setup**: Uses `base-setup` action instead of workflow
3. **Outputs**: Access through step outputs instead of job outputs

## Best Practices

### Release Branch Usage

```yaml
# Only run on release branches
on:
  push:
    branches: [release/*]

# Or use conditional logic
- name: Replace TBD entries
  if: startsWith(github.ref, 'refs/heads/release/')
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
```

### Error Handling

```yaml
- name: Replace TBD entries
  id: replace-tbd
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

- name: Handle failure
  if: steps.replace-tbd.outcome == 'failure'
  run: echo "TBD replacement failed, proceeding with manual process"
```

### Git Configuration

The action automatically configures Git, but you may want to use a bot account:

```yaml
- name: Configure Git
  run: |
    git config --global user.email "bot@example.com"
    git config --global user.name "Release Bot"

- name: Replace TBD entries
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
```

## Troubleshooting

### No Version Found

If the action outputs version `0.0.0`, ensure:

- `package.json` exists with valid version field
- PHP files contain proper plugin headers with `Version:` field
- Files are in the repository root or accessible path

### Permission Issues

If files can't be modified:

- Check repository permissions
- Ensure the action has write access
- Verify files aren't read-only

### Large Repositories

For repositories with many files:

- The action may take longer to complete
- Consider excluding additional directories if needed
- Monitor action timeout limits

### Troubleshooting Git Configuration

If Git operations fail:

- Ensure Git is properly configured
- Check if the repository allows push operations
- Verify branch protection rules don't prevent automated commits
