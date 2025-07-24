# Setup Git Action

A utility action that configures Git user settings for GitHub Actions automation. This action consolidates Git configuration logic that was previously duplicated across dozens of actions and workflows.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `git-user-email` | Git user email for commits | No | `'actions@github.com'` |
| `git-user-name` | Git user name for commits | No | `'github-actions'` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `configured` | Whether Git was successfully configured | String (`true`/`false`) |

## Usage

### Basic usage (default automation settings)

```yaml
- name: Setup Git
  uses: the-events-calendar/actions/.github/actions/setup-git@main
```

### Custom Git user settings

```yaml
- name: Setup Git with custom user
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'bot@example.com'
    git-user-name: 'Release Bot'
```

### With verification

```yaml
- name: Configure Git
  id: git-setup
  uses: the-events-calendar/actions/.github/actions/setup-git@main

- name: Verify Git configuration
  if: steps.git-setup.outputs.configured == 'true'
  run: |
    echo "Git configured successfully"
    git config --list | grep user
```

### In release workflow

```yaml
- name: Setup Git for release
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'releases@stellarwp.com'
    git-user-name: 'StellarWP Release Bot'

- name: Commit release changes
  run: |
    git add .
    git commit -m "Release version ${{ steps.version.outputs.version }}"
    git push
```

### Error handling

```yaml
- name: Setup Git
  id: git
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/setup-git@main

- name: Handle Git setup failure
  if: steps.git.outputs.configured != 'true'
  run: |
    echo "Git setup failed, using manual configuration"
    git config user.email "fallback@example.com"
    git config user.name "Fallback User"
```

## Features

### Automatic Configuration

- **Global Settings**: Configures Git user settings globally for the action runner
- **Validation**: Verifies configuration was applied correctly
- **Error Handling**: Provides clear feedback if configuration fails

### GitHub Integration

- **Step Summary**: Displays configuration details in workflow summary
- **Status Reporting**: Reports success/failure through outputs
- **Visual Feedback**: Uses emojis and formatting for clear status

### Flexible Input

- **Default Values**: Sensible defaults for automation scenarios
- **Custom Settings**: Easy override for specific use cases
- **Validation**: Ensures configuration matches expected values

## Step Summary Examples

### Successful Configuration

```text
## ⚙️ Git Configuration
* **Email**: `actions@github.com`
* **Name**: `github-actions`
* **Status**: ✅ Successfully configured
```

### Configuration Failure

```text
## ❌ Git Configuration Failed
* **Expected Email**: `actions@github.com`
* **Actual Email**: `user@example.com`
* **Expected Name**: `github-actions`
* **Actual Name**: `Different User`
```

## Migration Benefits

This action eliminates duplicated Git configuration logic found in multiple actions:

### Before (Duplicated Code)

```yaml
# In process-changelog action
- name: Set up Git configuration
  run: |
    git config --global user.email "actions@github.com"
    git config --global user.name "github-actions"

# In replace-tbd-entries action
- name: Set up Git configuration
  run: |
    git config --global user.email "actions@github.com"
    git config --global user.name "github-actions"

# In sync-translations action
- name: Configure Git
  run: |
    git config --global user.email "actions@github.com"
    git config --global user.name "github-actions"
```

### After (Modularized)

```yaml
# In any action
- name: Setup Git
  uses: the-events-calendar/actions/.github/actions/setup-git@main
```

## Common Use Cases

### Release Automation

```yaml
name: Release Process
jobs:
  release:
    steps:
      - name: Configure Git for release
        uses: the-events-calendar/actions/.github/actions/setup-git@main
        with:
          git-user-email: 'releases@company.com'
          git-user-name: 'Release Automation'

      - name: Create release commit
        run: |
          git add changelog.md readme.txt
          git commit -m "Release ${{ github.event.inputs.version }}"
          git tag "v${{ github.event.inputs.version }}"
          git push origin main --tags
```

### Pull Request Automation

```yaml
name: Auto-fix PR
jobs:
  fix:
    steps:
      - name: Setup Git
        uses: the-events-calendar/actions/.github/actions/setup-git@main

      - name: Apply automatic fixes
        run: |
          npm run lint:fix
          git add .
          git commit -m "Auto-fix: Apply linting fixes"
          git push
```

### Translation Updates

```yaml
name: Update Translations
jobs:
  translations:
    steps:
      - name: Configure Git for translations
        uses: the-events-calendar/actions/.github/actions/setup-git@main
        with:
          git-user-email: 'translations@company.com'
          git-user-name: 'Translation Bot'

      - name: Update language files
        run: |
          wp i18n make-pot . languages/plugin.pot
          git add languages/
          git commit -m "Update translation template"
          git push
```

### Branch Management

```yaml
name: Merge Forward
jobs:
  merge:
    steps:
      - name: Setup Git
        uses: the-events-calendar/actions/.github/actions/setup-git@main

      - name: Merge changes forward
        run: |
          git checkout develop
          git merge --no-ff release/v1.0.0
          git push origin develop
```

## Best Practices

### Use Early in Workflows

```yaml
jobs:
  process:
    steps:
      # Setup Git early, before any Git operations
      - name: Configure Git
        uses: the-events-calendar/actions/.github/actions/setup-git@main

      - name: Make changes
        run: ./make-changes.sh

      - name: Commit changes
        run: |
          git add .
          git commit -m "Automated changes"
```

### Environment-Specific Configuration

```yaml
- name: Configure Git for production
  if: github.ref == 'refs/heads/main'
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'production@company.com'
    git-user-name: 'Production Bot'

- name: Configure Git for development
  if: github.ref != 'refs/heads/main'
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'dev@company.com'
    git-user-name: 'Development Bot'
```

### With Error Recovery

```yaml
- name: Setup Git
  id: git-config
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/setup-git@main

- name: Verify or fallback
  run: |
    if [[ "${{ steps.git-config.outputs.configured }}" == "true" ]]; then
      echo "Git configured successfully"
    else
      echo "Using fallback configuration"
      git config user.email "fallback@example.com"
      git config user.name "Fallback User"
    fi
```

## Security Considerations

### Email Privacy

```yaml
# Use noreply email for public repositories
- name: Setup Git with privacy
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'noreply@github.com'
    git-user-name: 'GitHub Actions'
```

### Bot Identification

```yaml
# Clearly identify automated commits
- name: Setup Git with bot identification
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'actions@github.com'
    git-user-name: 'github-actions[bot]'
```

## Troubleshooting

### Configuration Not Applied

If Git configuration fails:

- Check for permission issues in the repository
- Verify the action has access to configure Git globally
- Ensure no conflicting Git configuration exists

### Commits Not Attributed

If commits don't show correct attribution:

- Verify email and name match GitHub user settings
- Check that Git configuration was applied before commits
- Ensure no local Git configuration overrides global settings

### Permission Denied

If Git operations fail after configuration:

- Check repository permissions
- Verify authentication tokens are properly configured
- Ensure branch protection rules allow automated commits

## Output Details

### Success Response

```yaml
configured: "true"
```

### Failure Response

```yaml
configured: "false"
```

The action fails with exit code 1 if configuration cannot be applied or verified.

## Integration Examples

### With Other Actions

```yaml
- name: Setup environment
  uses: ./.github/actions/base-setup@main

- name: Configure Git
  uses: the-events-calendar/actions/.github/actions/setup-git@main

- name: Process changes
  uses: ./.github/actions/process-changelog@main
```

### Conditional Configuration

```yaml
- name: Configure Git for automated changes
  if: github.actor == 'dependabot[bot]' || github.actor == 'github-actions[bot]'
  uses: the-events-calendar/actions/.github/actions/setup-git@main
  with:
    git-user-email: 'automation@company.com'
    git-user-name: 'Automation Bot'
```
