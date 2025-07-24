# Update WordPress Version Action

A composite action that updates WordPress version requirements in plugin files and workflows. This action helps maintain compatibility by updating "tested up to" versions and optionally adjusting minimum required versions.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `tested-up-to` | WordPress version to set as "tested up to" version (e.g. 6.8.1) | Yes | - |
| `update-min-version` | Update minimum required version to 2 minor versions behind tested version? | No | `no` |
| `gh-bot-token` | GitHub bot token for authentication | No | `${{ github.token }}` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `pull-request-url` | URL of the created pull request | String |
| `pull-request-number` | Number of the created pull request | String |
| `tested-version` | The tested up to version that was set | String |
| `min-version` | The minimum required version that was calculated/set | String |
| `files-updated` | List of files that were updated | Array |

## Usage

### Basic usage

```yaml
- name: Update WordPress version requirements
  uses: the-events-calendar/actions/.github/actions/update-wp-version@main
  with:
    tested-up-to: '6.8.1'
    update-min-version: 'yes'
    gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}
```

### Complete workflow example

```yaml
name: Update WordPress Version
on:
  workflow_dispatch:
    inputs:
      tested_up_to:
        description: 'WordPress version to set as "tested up to"'
        required: true
        type: string
      update_min_version:
        description: 'Update minimum required version?'
        required: true
        type: choice
        options:
          - 'yes'
          - 'no'
        default: 'no'

jobs:
  update-wp-version:
    runs-on: ubuntu-latest
    steps:
      - name: Update WordPress version requirements
        id: update
        uses: the-events-calendar/actions/.github/actions/update-wp-version@main
        with:
          tested-up-to: ${{ github.event.inputs.tested_up_to }}
          update-min-version: ${{ github.event.inputs.update_min_version }}
          gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}

      - name: Display results
        run: |
          echo "Tested Version: ${{ steps.update.outputs.tested-version }}"
          echo "Min Version: ${{ steps.update.outputs.min-version }}"
          echo "PR URL: ${{ steps.update.outputs.pull-request-url }}"
```

### Update tested version only

```yaml
- name: Update tested version only
  uses: the-events-calendar/actions/.github/actions/update-wp-version@main
  with:
    tested-up-to: '6.8.1'
    update-min-version: 'no'
```

### Update both tested and minimum versions

```yaml
- name: Update both versions
  uses: the-events-calendar/actions/.github/actions/update-wp-version@main
  with:
    tested-up-to: '6.8.1'
    update-min-version: 'yes'  # Will set minimum to 6.6
```

## Features

### Version Management
- **Tested Up To**: Updates the maximum WordPress version tested
- **Minimum Required**: Optionally updates minimum version (2 minor versions behind)
- **Smart Calculation**: Automatically calculates appropriate minimum versions
- **Safety Boundaries**: Ensures minimum version never goes below WordPress 5.0

### File Updates
- **readme.txt**: Updates both tested and minimum versions
- **Plugin PHP**: Updates minimum version in main plugin file
- **Workflow Files**: Updates WP-CLI version commands in GitHub Actions
- **Multi-File Support**: Updates all relevant files in a single operation

### Automation Features
- **Pull Request Creation**: Automatically creates PRs with detailed descriptions
- **Branch Management**: Creates temporary branches for changes
- **Skip Flags**: Includes appropriate skip flags for automated PRs

## Version Calculation Logic

### Tested Version
The "tested up to" version is set exactly as provided:
```yaml
Input: 6.8.1
Output: "Tested up to: 6.8.1"
```

### Minimum Version Calculation
When `update-min-version` is `yes`, the minimum is calculated as 2 minor versions behind:

```bash
# Examples:
Tested: 6.8.1 → Minimum: 6.6
Tested: 6.2.0 → Minimum: 6.0
Tested: 6.1.0 → Minimum: 5.11 (if 5.11 exists)
Tested: 6.0.0 → Minimum: 5.10 (if 5.10 exists)

# Safety boundary:
Any calculated minimum < 5.0 → Minimum: 5.0
```

## File Processing

### readme.txt
Updates standard WordPress plugin readme format:
```txt
Tested up to: 6.8.1
Requires at least: 6.6
```

### Plugin PHP File
Updates the main plugin file header (detected via `.puprc`):
```php
/**
 * Requires at least: 6.6
 */
```

### Workflow Files
Updates WP-CLI commands in GitHub Actions workflows:
```yaml
# Before:
- run: wp core update --version=6.4

# After:
- run: wp core update --version=6.6
```

## Configuration

### .puprc Integration
The action uses `.puprc` to identify the main plugin file:

```json
{
  "paths": {
    "versions": [
      {
        "file": "plugin.php",
        "regex": "Version:\\s*([\\d\\.]+)"
      }
    ]
  }
}
```

Only PHP files in the root directory are considered for plugin header updates.

## Error Handling

### Common Issues

#### Invalid Version Format
```
❌ Invalid version format: 6.8
```
**Solution**: Use proper semantic versioning (e.g., `6.8.0` or `6.8.1`).

#### Missing Files
```
⚠️ readme.txt not found
```
**Solution**: Ensure your plugin follows WordPress standards with a `readme.txt` file.

#### Configuration Issues
```
⚠️ Main plugin PHP file not found or .puprc not configured
```
**Solutions**:
- Add `.puprc` file with version configuration
- Ensure main plugin file is in repository root
- Verify `.puprc` paths.versions includes PHP files

### Debug Information

The action provides detailed step summaries:

```yaml
## WordPress Version Updates
- **Tested Up To**: `6.8.1`
- **Update Minimum**: `yes`
- **New Minimum Required**: `6.6`

## File Updates
### `readme.txt`
✅ Updated 'Tested up to' version
✅ Updated 'Requires at least' version

### Plugin PHP File
- **File**: `plugin.php`
✅ Updated 'Requires at least' version

**Total files updated**: 2
```

## Best Practices

### Version Selection
- **Tested Up To**: Use the latest WordPress version you've tested
- **Regular Updates**: Update when new WordPress versions are released
- **Conservative Minimums**: Only update minimum versions when necessary

### Timing
```yaml
# Good: Regular maintenance schedule
- cron: '0 0 1 * *'  # First of each month

# Good: After WordPress releases
on:
  workflow_dispatch:
    inputs:
      tested_up_to:
        description: 'Latest WordPress version'
```

### Integration with Release Process
```yaml
- name: Update WordPress requirements
  uses: the-events-calendar/actions/.github/actions/update-wp-version@main
  with:
    tested-up-to: '6.8.1'
    update-min-version: 'yes'

- name: Run compatibility tests
  run: |
    # Test with minimum version
    wp core update --version=${{ steps.update.outputs.min-version }}
    npm run test

    # Test with tested version
    wp core update --version=${{ steps.update.outputs.tested-version }}
    npm run test
```

## Skip Flags

The action automatically includes skip flags in created PRs:
- `[skip-changelog]` - Skip changelog validation
- `[skip-lint]` - Skip linting checks
- `[skip-phpcs]` - Skip code style checks

These prevent unnecessary CI runs for version requirement updates.

## WordPress Compatibility

### Supported Versions
- **Minimum Boundary**: Never sets requirements below WordPress 5.0
- **Current Support**: Handles all WordPress 5.x and 6.x versions
- **Future Proof**: Automatically adapts to newer WordPress versions

### File Format Support
- **Standard readme.txt**: WordPress.org plugin repository format
- **Plugin Headers**: Standard WordPress plugin file headers
- **Custom Formats**: Configurable via regex patterns

## Troubleshooting

### Version Not Applied
- Check file permissions and formats
- Verify regex patterns match your file structure
- Ensure sed commands are compatible with your file encoding

### PR Creation Failed
- Verify token permissions include pull request creation
- Check branch protection rules
- Ensure repository allows automated PRs

### Workflow Updates Skipped
- Verify workflow files contain WP-CLI core update commands
- Check command syntax matches expected patterns
- Ensure workflow files are in `.github/workflows/` directory

## Integration Examples

### Quarterly Updates
```yaml
name: Quarterly WordPress Update
on:
  schedule:
    - cron: '0 0 1 */3 *'  # Every quarter

jobs:
  update-versions:
    steps:
      - name: Update to latest WordPress
        uses: the-events-calendar/actions/.github/actions/update-wp-version@main
        with:
          tested-up-to: '6.8.1'  # Update to current version
          update-min-version: 'yes'
```

### Release Preparation
```yaml
- name: Prepare for release
  uses: the-events-calendar/actions/.github/actions/update-wp-version@main
  with:
    tested-up-to: ${{ env.WORDPRESS_LATEST }}
    update-min-version: 'yes'

- name: Update changelog
  uses: the-events-calendar/actions/.github/actions/process-changelog@main
```
