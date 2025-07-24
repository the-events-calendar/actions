# Prepare Branch Action

A composite action that creates release branches and performs version bumps for WordPress plugin releases. This action automates the process of preparing new release branches with proper version increments based on semantic versioning.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `new-branch` | Name of the new branch (e.g. release/T24.centaur) | Yes | - |
| `version-bump-type` | Type of version bump (major, feature, maintenance, hotfix) | Yes | - |
| `gh-bot-token` | GitHub bot token for authentication | No | `${{ github.token }}` |

### Version Bump Types

| Type | Description | Example | Effect |
|------|-------------|---------|--------|
| `major` | Breaking changes | `1.0.0` → `2.0.0` | Increments major, resets minor and patch |
| `feature` | New features | `1.0.0` → `1.1.0` | Increments minor, resets patch |
| `maintenance` | Bug fixes | `1.0.0` → `1.0.1` | Increments patch |
| `hotfix` | Critical fixes | `1.0.0` → `1.0.0.1` | Adds/increments hotfix number |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `pull-request-url` | URL of the created pull request | String |
| `pull-request-number` | Number of the created pull request | String |
| `new-version` | The new version that was applied | String |
| `branch-created` | Whether the branch was created or already existed | String (`true`/`false`) |

## Usage

### Basic usage

```yaml
- name: Prepare release branch
  uses: the-events-calendar/actions/.github/actions/prepare-branch@main
  with:
    new-branch: release/T25.feature-name
    version-bump-type: feature
    gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}
```

### Complete workflow example

```yaml
name: Prepare Release Branch
on:
  workflow_dispatch:
    inputs:
      new-branch:
        description: 'Name of the new branch'
        required: true
        default: 'release/T25.release-name'
      version-bump-type:
        description: 'Type of version bump'
        required: true
        type: choice
        options:
          - major
          - feature
          - maintenance
          - hotfix

jobs:
  prepare-branch:
    runs-on: ubuntu-latest
    outputs:
      new-version: ${{ steps.prepare.outputs.new-version }}
      pr-url: ${{ steps.prepare.outputs.pull-request-url }}
    steps:
      - name: Prepare release branch
        id: prepare
        uses: the-events-calendar/actions/.github/actions/prepare-branch@main
        with:
          new-branch: ${{ github.event.inputs.new-branch }}
          version-bump-type: ${{ github.event.inputs.version-bump-type }}
          gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}

      - name: Display results
        run: |
          echo "New version: ${{ steps.prepare.outputs.new-version }}"
          echo "PR URL: ${{ steps.prepare.outputs.pull-request-url }}"
```

### Integration with other actions

```yaml
- name: Prepare release branch
  id: prepare
  uses: the-events-calendar/actions/.github/actions/prepare-branch@main
  with:
    new-branch: release/T25.major-release
    version-bump-type: major

- name: Merge changes forward
  uses: the-events-calendar/actions/.github/actions/merge-forward@main
  with:
    forward-branch: ${{ inputs.new-branch }}
    gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}
```

## Features

### Intelligent Branch Management
- **Branch Detection**: Checks if the release branch already exists
- **Automatic Creation**: Creates new branches when needed
- **Existing Branch Handling**: Uses existing branches without conflicts

### Version Bump Logic
- **Semantic Versioning**: Follows standard semantic versioning principles
- **Multiple File Support**: Updates versions in multiple files simultaneously
- **Hotfix Special Handling**: Skips package.json updates for hotfix releases
- **Regex-Based Updates**: Uses configurable regex patterns for flexible file formats

### Integration Features
- **Auto-Detection**: Uses detect-version action for current version discovery
- **Pull Request Creation**: Automatically creates PRs with detailed information
- **Step Summaries**: Provides comprehensive progress reporting

## Version Bump Process

### 1. Branch Preparation
- Validates input parameters
- Detects current version from project files
- Creates or checks out the target release branch

### 2. Version Calculation
Based on the bump type and current version:

```bash
# Current version: 1.2.3
major    → 2.0.0     # Breaking changes
feature  → 1.3.0     # New features
maintenance → 1.2.4  # Bug fixes
hotfix   → 1.2.3.1   # Critical patches
```

### 3. File Updates
- Reads version configuration from `.puprc`
- Updates all configured version files
- Uses regex patterns for precise replacements
- Provides detailed update summaries

### 4. Pull Request Creation
- Creates a temporary branch for changes
- Commits version updates with descriptive messages
- Opens PR against the release branch
- Includes comprehensive metadata

## Configuration

### .puprc File Structure

The action requires a `.puprc` file with version configuration:

```json
{
  "paths": {
    "versions": [
      {
        "file": "package.json",
        "regex": "\"version\":\\s*\"([^\"]+)\""
      },
      {
        "file": "plugin.php",
        "regex": "Version:\\s*([\\d\\.]+)"
      },
      {
        "file": "readme.txt",
        "regex": "Stable tag:\\s*([\\d\\.]+)"
      }
    ]
  }
}
```

### Supported File Types

The action can update versions in any text file using regex patterns:

- **package.json**: NPM package files
- **PHP Plugin Headers**: WordPress plugin main files
- **readme.txt**: WordPress plugin readme files
- **Composer.json**: PHP package files
- **Custom Files**: Any file with regex-definable version patterns

## Error Handling

### Common Issues

#### Missing .puprc File
```
❌ .puprc file not found
```
**Solution**: Create a `.puprc` file with version configuration in the repository root.

#### Invalid Version Configuration
```
❌ paths.versions not found in .puprc
```
**Solution**: Add the `paths.versions` array to your `.puprc` configuration.

#### Version Not Found
```
❌ No version found using regex
```
**Solutions**:
- Verify the regex pattern matches your file format
- Check that the target file exists
- Ensure the version follows the expected format

#### Branch Conflicts
```
Error: Could not create branch
```
**Solutions**:
- Check if the branch name is valid
- Verify permissions to create branches
- Ensure no conflicts with existing branches

### Debug Information

The action provides detailed step summaries:

```yaml
## Branch Preparation
- **New Branch**: `release/T25.feature`
- **Version Bump**: `feature`

## Release Branch Setup
✅ Creating new branch `release/T25.feature`

## Version Bump Process
- **Current Version**: `1.2.3`
- **Bump Type**: `feature`

### File Updates
#### `package.json`
- **Found**: `1.2.3`
- **Updated**: `1.3.0`
```

## Best Practices

### Branch Naming
- Use descriptive names: `release/T25.feature-name`
- Include ticket or sprint identifiers
- Follow consistent naming conventions
- Avoid special characters that could cause Git issues

### Version Bump Selection
- **Major**: Breaking API changes, major feature releases
- **Feature**: New functionality, minor API additions
- **Maintenance**: Bug fixes, security patches, minor improvements
- **Hotfix**: Critical fixes that can't wait for regular release cycle

### Workflow Integration

```yaml
# Sequential release preparation
jobs:
  prepare:
    steps:
      - name: Prepare branch
        uses: the-events-calendar/actions/.github/actions/prepare-branch@main

  validate:
    needs: prepare
    steps:
      - name: Run tests on new branch
        run: npm test

  deploy:
    needs: [prepare, validate]
    steps:
      - name: Deploy to staging
        run: deploy-staging.sh
```

## Hotfix Special Behavior

For hotfix releases:
- **package.json**: Skipped (maintains current version for NPM)
- **PHP Files**: Updated with hotfix number (e.g., `1.2.3.1`)
- **readme.txt**: Updated to match PHP version

This allows for WordPress plugin hotfixes without affecting NPM package versioning.

## Integration with Release Process

This action works seamlessly with other release actions:

```yaml
- name: Prepare release branch
  id: prepare
  uses: the-events-calendar/actions/.github/actions/prepare-branch@main
  with:
    new-branch: release/T25.major
    version-bump-type: major

- name: Process changelog
  uses: the-events-calendar/actions/.github/actions/process-changelog@main
  with:
    release-version: ${{ steps.prepare.outputs.new-version }}

- name: Replace TBD entries
  uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main
```

## Troubleshooting

### Version Bump Failures
- Verify `.puprc` configuration is correct
- Check that all target files exist
- Ensure regex patterns match file formats
- Test regex patterns manually

### Permission Issues
- Verify bot token has proper permissions
- Check repository branch protection rules
- Ensure workflow has write access

### Branch Creation Issues
- Check for naming conflicts
- Verify branch doesn't already exist remotely
- Ensure proper Git configuration
