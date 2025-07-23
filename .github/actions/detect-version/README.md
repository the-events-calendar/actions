# Detect Version Action

A utility action that detects the current version from various sources in WordPress plugin repositories. This action consolidates version detection logic that was previously duplicated across multiple actions.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `fallback-version` | Fallback version if none found | No | `'1.0.0'` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `version` | The detected version | String |
| `source` | Source where version was found | String |

## Usage

### Basic usage

```yaml
- name: Detect current version
  id: version
  uses: the-events-calendar/actions/.github/actions/detect-version@main

- name: Use detected version
  run: echo "Current version is ${{ steps.version.outputs.version }}"
```

### With custom fallback

```yaml
- name: Detect version with fallback
  id: version
  uses: the-events-calendar/actions/.github/actions/detect-version@main
  with:
    fallback-version: '2.0.0'
```

### In a workflow

```yaml
jobs:
  detect-and-process:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.detect.outputs.version }}
      source: ${{ steps.detect.outputs.source }}
    steps:
      - name: Detect version
        id: detect
        uses: the-events-calendar/actions/.github/actions/detect-version@main

  use-version:
    needs: detect-and-process
    runs-on: ubuntu-latest
    steps:
      - name: Process with version
        run: |
          echo "Processing version ${{ needs.detect-and-process.outputs.version }}"
          echo "Source: ${{ needs.detect-and-process.outputs.source }}"
```

## Features

### Multi-Source Detection

The action searches for version information in priority order:

1. **package.json** - Looks for `"version": "x.y.z"` field
2. **PHP Plugin Headers** - Searches for `Version: x.y.z` in PHP files
3. **.puprc Configuration** - Uses project configuration for complex version detection
4. **Fallback** - Uses provided fallback version if none found

### Version Format Support

- Standard semantic versioning: `1.2.3`
- Extended versioning: `1.2.3.4`
- Complex regex patterns via `.puprc` configuration

### Integration Features

- **GitHub Summary**: Displays detected version and source in workflow summary
- **Error Handling**: Graceful fallback when detection fails
- **Configurable**: Supports custom fallback versions

## Version Detection Logic

### package.json Detection

```json
{
  "version": "6.2.0"
}
```

### PHP Plugin Header Detection

```php
<?php
/**
 * Plugin Name: My Plugin
 * Version: 6.2.0
 */
```

### .puprc Configuration Detection

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
      }
    ]
  }
}
```

## Migration Benefits

This action eliminates duplicated version detection logic found in:

- `process-changelog` action (lines 67-88)
- `replace-tbd-entries` action (lines 58-78)
- Any custom workflows that detect versions

### Before (Duplicated Code)

```yaml
# In process-changelog action
- name: Figure out Version
  run: |
    if [ -f "package.json" ]; then
      PACKAGE_VERSION=$(grep -Po '"version":\s*"\K[^"]+' package.json)
    fi
    # ... 20+ more lines of logic

# In replace-tbd-entries action
- name: Check for version files
  run: |
    if [ -f "package.json" ]; then
      PACKAGE_VERSION=$(grep -Po '"version":\s*"\K[^"]+' package.json)
    fi
    # ... 20+ more lines of duplicated logic
```

### After (Modularized)

```yaml
# In any action
- name: Detect version
  id: version
  uses: the-events-calendar/actions/.github/actions/detect-version@main

- name: Use version
  run: echo "Version: ${{ steps.version.outputs.version }}"
```

## Output Examples

### Success (package.json)

```text
Version: 6.2.0
Source: package.json
```

### Success (PHP file)

```text
Version: 6.1.5
Source: php:my-plugin.php
```

### Success (.puprc)

```text
Version: 6.0.0
Source: puprc:package.json
```

### Fallback

```text
Version: 1.0.0
Source: fallback
```

## Troubleshooting

### No Version Found

If the action returns the fallback version:

- Verify `package.json` exists with valid version field
- Check PHP files contain proper `Version:` headers
- Ensure `.puprc` configuration is valid JSON
- Verify file paths and regex patterns in `.puprc`

### Invalid Version Format

The action expects standard version formats:

- `1.2.3` (semantic versioning)
- `1.2.3.4` (extended versioning)
- Versions must contain only digits and dots

### Performance Considerations

- PHP file search is limited to first 10 files for performance
- Excludes common directories (`vendor/`, `node_modules/`, `tests/`)
- Uses efficient regex patterns for extraction
