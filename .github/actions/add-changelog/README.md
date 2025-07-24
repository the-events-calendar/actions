# Add Changelog Action

A composite action that creates new changelog entries using the Jetpack Changelogger tool. This action automatically installs dependencies and generates changelog files with the specified configuration.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `file` | Filename for the changelog entry | Yes | `'action-generated'` |
| `significance` | Changelog significance level | Yes | `'patch'` |
| `type` | Type of changelog entry | Yes | - |
| `entry` | The changelog entry content | Yes | - |
| `comment` | Additional comment for the changelog entry | No | `''` |
| `extra-arguments` | Extra arguments to pass to the changelogger command | No | `'--filename-auto-suffix'` |

### Significance Levels
- `patch` - Patch-level changes (bug fixes)
- `minor` - Minor version changes (new features)
- `major` - Major version changes (breaking changes)

### Changelog Types
- `version` - Version changes
- `feat` - New features
- `tweak` - Minor improvements
- `fix` - Bug fixes
- `performance` - Performance improvements
- `security` - Security fixes
- `accessibility` - Accessibility improvements
- `compatibility` - Compatibility updates
- `deprecated` - Deprecation notices
- `language` - Language/translation updates

## Usage

### Basic usage

```yaml
- name: Add changelog entry
  uses: the-events-calendar/actions/.github/actions/add-changelog@main
  with:
    type: fix
    entry: "Fixed issue with event display on mobile devices"
```

### With custom significance and file

```yaml
- name: Add feature changelog
  uses: the-events-calendar/actions/.github/actions/add-changelog@main
  with:
    file: "feature-new-calendar-view"
    significance: minor
    type: feat
    entry: "Added new calendar view with enhanced filtering options"
    comment: "Implements user-requested feature from issue #123"
```

### Complete workflow example

```yaml
name: Add Changelog Entry
on:
  workflow_dispatch:
    inputs:
      entry_type:
        description: 'Type of changelog entry'
        required: true
        type: choice
        options:
        - fix
        - feat
        - tweak
        - performance
      significance:
        description: 'Significance level'
        required: true
        type: choice
        options:
        - patch
        - minor
        - major
      entry_text:
        description: 'Changelog entry text'
        required: true

jobs:
  add-changelog:
    runs-on: ubuntu-latest
    steps:
      - name: Add changelog entry
        uses: the-events-calendar/actions/.github/actions/add-changelog@main
        with:
          type: ${{ github.event.inputs.entry_type }}
          significance: ${{ github.event.inputs.significance }}
          entry: ${{ github.event.inputs.entry_text }}
          file: "manual-entry-${{ github.run_number }}"
```

### Integration with other actions

```yaml
- name: Analyze changes
  id: analyze
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main

- name: Add filter changelog
  if: steps.analyze.outputs.has-filters-added == 'true'
  uses: the-events-calendar/actions/.github/actions/add-changelog@main
  with:
    type: tweak
    significance: patch
    entry: "Added filters: ${{ steps.analyze.outputs.filters-added }}"
    file: "filters-added-${{ github.sha }}"
```

## Features

### Automatic Dependency Management
- **Composer Caching**: Caches Composer dependencies for faster runs
- **Auto-installation**: Automatically installs required PHP dependencies
- **Platform Requirements**: Ignores platform requirements for compatibility

### Changelogger Integration
- **Jetpack Changelogger**: Uses the industry-standard Jetpack Changelogger tool
- **Flexible Configuration**: Supports all changelogger options and arguments
- **Non-interactive Mode**: Runs in non-interactive mode for CI/CD compatibility

### File Management
- **Auto-suffix**: Automatically adds suffixes to prevent filename conflicts
- **Custom Naming**: Supports custom filename patterns
- **Organized Storage**: Stores changelog entries in the standard `changelog/` directory

## Requirements

### Project Setup
Your project must have:
- `composer.json` with `automattic/jetpack-changelogger` dependency
- `changelog/` directory in the repository root
- Proper Changelogger configuration (typically in `.changelogger.yml`)

### Example composer.json
```json
{
  "require-dev": {
    "automattic/jetpack-changelogger": "^3.0"
  }
}
```

### Example .changelogger.yml
```yaml
changelog: changelog.md
changes-dir: changelog
ordering: semver
types:
  feat: Features
  fix: Bug Fixes
  tweak: Tweaks
  performance: Performance
  security: Security
  accessibility: Accessibility
  compatibility: Compatibility
  deprecated: Deprecated
  language: Language
```

## Output Files

The action generates files in the `changelog/` directory:

```text
changelog/
├── .gitkeep
├── feature-new-view.md
├── fix-mobile-display.md
└── action-generated-abc123.md
```

Each file contains structured changelog data:

```markdown
Significance: patch
Type: fix

Fixed issue with event display on mobile devices
```

## Troubleshooting

### Common Issues

#### Composer Dependencies Not Found
```
Error: Could not find changelogger command
```
**Solution**: Ensure `automattic/jetpack-changelogger` is in your `composer.json`

#### Permission Denied
```
Error: Permission denied when writing changelog file
```
**Solution**: Check repository permissions and ensure the workflow has write access

#### Invalid Changelog Type
```
Error: Unknown changelog type
```
**Solution**: Use one of the supported types listed above

### File Naming Conflicts
The action uses `--filename-auto-suffix` by default to prevent conflicts. If you need custom naming:

```yaml
- name: Add changelog with custom naming
  uses: the-events-calendar/actions/.github/actions/add-changelog@main
  with:
    file: "my-custom-name"
    extra-arguments: ""  # Disable auto-suffix
    type: fix
    entry: "Custom changelog entry"
```

## Migration from Manual Process

### Before (Manual)
```bash
./vendor/bin/changelogger add \
  --filename="fix-mobile-bug" \
  --significance="patch" \
  --type="fix" \
  --entry="Fixed mobile display issue"
```

### After (Action)
```yaml
- uses: the-events-calendar/actions/.github/actions/add-changelog@main
  with:
    file: "fix-mobile-bug"
    significance: patch
    type: fix
    entry: "Fixed mobile display issue"
```

## Best Practices

### Entry Content
- Use clear, descriptive language
- Start with action verbs (Fixed, Added, Updated, etc.)
- Reference relevant issues or PRs when applicable
- Keep entries concise but informative

### File Naming
- Use descriptive filenames that indicate the change
- Include issue numbers when relevant: `fix-mobile-bug-123`
- Use consistent naming conventions across your project

### Significance Levels
- **Patch**: Bug fixes, minor tweaks, documentation updates
- **Minor**: New features, significant improvements
- **Major**: Breaking changes, major refactors

## Integration with Release Process

This action works seamlessly with the changelog processing workflow:

```yaml
jobs:
  add-changelog:
    runs-on: ubuntu-latest
    steps:
      - name: Add changelog entry
        uses: the-events-calendar/actions/.github/actions/add-changelog@main
        with:
          type: feat
          entry: "New feature implementation"

  process-changelog:
    needs: add-changelog
    runs-on: ubuntu-latest
    steps:
      - name: Process changelog for release
        uses: the-events-calendar/actions/.github/actions/process-changelog@main
```
