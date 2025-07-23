# Sync Translations Action

This composite action manages translation file synchronization and GlotPress integration for WordPress plugins. It generates POT files, pushes them to translation services, and creates changelog entries for translation updates.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `target-branch` | Target branch for the workflow | No | `'main'` |
| `additional-inputs` | Additional inputs to pass through (JSON string) | No | `'{}'` |
| `translations-deploy-host` | Host for translation deployment | Yes | - |
| `translations-deploy-user` | User for translation deployment | Yes | - |
| `translations-deploy-ssh-key` | SSH key for translation deployment | Yes | - |
| `translations-deploy-pot-location` | Location for POT file deployment | Yes | - |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `translation-summary` | Summary of translation changes | String |
| `changes-made` | Whether any changes were made | Boolean |

## Usage

### Basic usage

```yaml
- name: Sync translations
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### In a release workflow

```yaml
name: Release Process
on:
  push:
    branches: [release/*, main]

jobs:
  sync-translations:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/release/')
    steps:
      - name: Sync translations
        id: translations
        uses: the-events-calendar/actions/.github/actions/sync-translations@main
        with:
          translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
          translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
          translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

      - name: Report results
        run: |
          echo "Translation sync completed!"
          echo "Summary: ${{ steps.translations.outputs.translation-summary }}"
```

### With conditional execution

```yaml
- name: Check if release branch
  id: check-branch
  run: |
    if [[ "${{ github.ref }}" =~ ^refs/heads/(main|master|release/) ]]; then
      echo "should-sync=true" >> $GITHUB_OUTPUT
    else
      echo "should-sync=false" >> $GITHUB_OUTPUT
    fi

- name: Sync translations
  if: steps.check-branch.outputs.should-sync == 'true'
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### Complete translation workflow

```yaml
name: Translation Management
on:
  push:
    branches: [main, release/*]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  translations:
    runs-on: ubuntu-latest
    steps:
      - name: Sync translations
        id: sync
        uses: the-events-calendar/actions/.github/actions/sync-translations@main
        with:
          translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
          translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
          translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

      - name: Notify team
        if: steps.sync.outputs.changes-made == '1'
        run: |
          echo "Translation files updated and pushed to GlotPress"
          echo "Summary: ${{ steps.sync.outputs.translation-summary }}"
```

## Features

### Automatic Branch Detection
The action automatically determines if translations should be synced based on the branch:
- **Main/Master branches**: Always sync
- **Release branches** (`release/*`): Always sync
- **Other branches**: Skip sync (POT generation only)

### Plugin Configuration
Reads plugin configuration from `.puprc` file:
```json
{
  "i18n": [
    {
      "url": "https://translations.stellarwp.com",
      "slug": "the-events-calendar"
    }
  ]
}
```

### POT File Generation
- Automatically generates translation template (POT) files
- Uses the plugin's text domain and translatable strings
- Stores POT files in the `lang/` directory

### GlotPress Integration
- Pushes POT files to translation management system
- Updates existing translations with new strings
- Provides status feedback on translation updates

### Changelog Integration
- Automatically creates changelog entries for translation updates
- Uses the `add-changelog` action for consistent formatting
- Includes GlotPress result information

## Branch Behavior

### Release/Main Branches
When running on `main`, `master`, or `release/*` branches:
1. Generates POT file
2. Pushes translations to GlotPress
3. Creates changelog entry
4. Sets `changes-made` to `1`

### Development Branches
When running on other branches:
1. Generates POT file only
2. Skips GlotPress push
3. Skips changelog entry
4. Sets `changes-made` to `0`

## Required Secrets

### Translation Deployment Secrets
Configure these secrets in your repository:

```yaml
# Repository Settings > Secrets and variables > Actions
TRANSLATIONS_HOST: "translations.stellarwp.com"
TRANSLATIONS_USER: "deploy-user"
TRANSLATIONS_SSH_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...private key content...
  -----END OPENSSH PRIVATE KEY-----
TRANSLATIONS_POT_LOCATION: "/path/to/translations/"
```

## Configuration Requirements

### .puprc File
The repository must contain a `.puprc` file with translation configuration:

```json
{
  "i18n": [
    {
      "url": "https://translations.stellarwp.com",
      "slug": "the-events-calendar"
    }
  ]
}
```

### Directory Structure
Expected directory structure:
```
plugin-root/
├── .puprc                    # Plugin configuration
├── lang/                     # Translation files directory
│   └── plugin-name.pot      # Generated POT file
├── src/                      # Source code with translatable strings
└── plugin-name.php          # Main plugin file
```

## Example Output

### Successful Sync
```yaml
translation-summary: "POT file updated with 150 strings, pushed to GlotPress successfully"
changes-made: "1"
```

### Skipped Sync (Development Branch)
```yaml
translation-summary: "No translation sync performed (not a release branch)"
changes-made: "0"
```

## Integration Examples

### With Other Release Actions
```yaml
name: Complete Release Process
on:
  push:
    branches: [release/*]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Setup environment
        uses: the-events-calendar/actions/.github/actions/basic-setup@main

      - name: Replace TBD entries
        uses: the-events-calendar/actions/.github/actions/replace-tbd-entries@main

      - name: Analyze changes
        uses: the-events-calendar/actions/.github/actions/analyze-changes@main

      - name: Sync translations
        uses: the-events-calendar/actions/.github/actions/sync-translations@main
        with:
          translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
          translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
          translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

      - name: Process changelog
        uses: the-events-calendar/actions/.github/actions/process-changelog@main
```

### Scheduled Translation Updates
```yaml
name: Weekly Translation Sync
on:
  schedule:
    - cron: '0 8 * * 1'  # Monday at 8 AM UTC
  workflow_dispatch:

jobs:
  sync-translations:
    runs-on: ubuntu-latest
    steps:
      - name: Sync translations
        uses: the-events-calendar/actions/.github/actions/sync-translations@main
        with:
          target-branch: 'main'
          translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
          translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
          translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

## Migration from Reusable Workflow

This action replaces the `sync-translations.yml` reusable workflow.

### Before (Reusable Workflow)
```yaml
uses: ./.github/workflows/reusable/release-process/sync-translations.yml
with:
  target-branch: 'main'
secrets:
  TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
  TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
  TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
  TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### After (Composite Action)
```yaml
uses: the-events-calendar/actions/.github/actions/sync-translations@main
with:
  target-branch: 'main'
  translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
  translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
  translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
  translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### Key Differences
1. **Secrets → Inputs**: Translation secrets are now passed as inputs
2. **Usage**: Direct action call instead of workflow call
3. **Setup**: Uses `basic-setup` action instead of workflow

## Dependencies

### Required Actions
This action depends on:
- `the-events-calendar/actions/.github/actions/basic-setup@main`
- `the-events-calendar/actions/.github/actions/generate-pot@main`
- `the-events-calendar/actions/.github/actions/push-translations@main`
- `the-events-calendar/actions/.github/actions/add-changelog@main`

### System Requirements
- **jq**: For JSON parsing (.puprc file)
- **Git**: For repository operations
- **SSH**: For secure translation file deployment

## Best Practices

### Secret Management
```yaml
# Use environment-specific secrets
- name: Sync translations (Production)
  if: github.ref == 'refs/heads/main'
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.PROD_TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.PROD_TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.PROD_TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.PROD_TRANSLATIONS_POT_LOCATION }}

- name: Sync translations (Staging)
  if: startsWith(github.ref, 'refs/heads/release/')
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.STAGING_TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.STAGING_TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.STAGING_TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.STAGING_TRANSLATIONS_POT_LOCATION }}
```

### Error Handling
```yaml
- name: Sync translations
  id: sync-translations
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

- name: Handle translation failure
  if: steps.sync-translations.outcome == 'failure'
  run: |
    echo "Translation sync failed, notifying team..."
    # Send notification or create issue
```

### Conditional Execution
```yaml
- name: Check if translations needed
  id: check-translations
  run: |
    if git diff --name-only HEAD~1 | grep -E '\.(php|js|jsx|ts|tsx)$'; then
      echo "has-translatable-changes=true" >> $GITHUB_OUTPUT
    else
      echo "has-translatable-changes=false" >> $GITHUB_OUTPUT
    fi

- name: Sync translations
  if: steps.check-translations.outputs.has-translatable-changes == 'true'
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

## Troubleshooting

### Missing .puprc File
```
Error: .puprc file not found or invalid
```
**Solution**: Ensure `.puprc` exists in repository root with valid translation configuration.

### SSH Connection Issues
```
Error: Could not connect to translation server
```
**Solutions**:
- Verify SSH key format and permissions
- Check host and user credentials
- Ensure server is accessible from GitHub Actions

### POT Generation Failure
```
Error: Failed to generate POT file
```
**Solutions**:
- Check for translatable strings in source code
- Verify source file paths and structure
- Ensure proper text domain usage

### GlotPress Push Failure
```
Error: Failed to push translations to GlotPress
```
**Solutions**:
- Verify deployment path exists and is writable
- Check GlotPress server status
- Ensure proper file permissions on target server

### Plugin Slug Detection
```
Warning: Could not determine plugin slug
```
**Solution**: Verify `.puprc` file contains valid `i18n` configuration with translation URL and slug.
