# Generate POT File Action 🪴

A composite action that generates POT (Portable Object Template) files from WordPress plugin source code using WP-CLI. This action is essential for internationalization workflows, creating template files that translators use to create localized versions of your plugin.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `plugin_path` | Path to the plugin source code to scan for translatable strings | Yes | - |
| `pot_path` | Output path for the generated POT file | Yes | - |

## Usage

### Basic usage

```yaml
- name: Generate POT file
  uses: the-events-calendar/actions/.github/actions/generate-pot@main
  with:
    plugin_path: ./src
    pot_path: ./languages/my-plugin.pot
```

### Complete translation workflow

```yaml
name: Translation Workflow
on:
  push:
    branches: [main]

jobs:
  generate-translations:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate POT file
        uses: the-events-calendar/actions/.github/actions/generate-pot@main
        with:
          plugin_path: ./
          pot_path: ./languages/the-events-calendar.pot

      - name: Upload POT file
        uses: actions/upload-artifact@v4
        with:
          name: pot-file
          path: ./languages/the-events-calendar.pot
```

### Integration with translation sync

```yaml
- name: Generate POT file
  uses: the-events-calendar/actions/.github/actions/generate-pot@main
  with:
    plugin_path: ./
    pot_path: ./languages/my-plugin.pot

- name: Sync translations
  uses: the-events-calendar/actions/.github/actions/sync-translations@main
  with:
    translations-deploy-host: ${{ secrets.TRANSLATIONS_HOST }}
    translations-deploy-user: ${{ secrets.TRANSLATIONS_USER }}
    translations-deploy-ssh-key: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    translations-deploy-pot-location: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### Multi-plugin repository

```yaml
strategy:
  matrix:
    plugin:
      - name: events-calendar
        path: ./plugins/the-events-calendar
        pot: ./plugins/the-events-calendar/lang/the-events-calendar.pot
      - name: events-pro
        path: ./plugins/events-pro
        pot: ./plugins/events-pro/lang/events-pro.pot

steps:
  - name: Generate POT for ${{ matrix.plugin.name }}
    uses: the-events-calendar/actions/.github/actions/generate-pot@main
    with:
      plugin_path: ${{ matrix.plugin.path }}
      pot_path: ${{ matrix.plugin.pot }}
```

## Features

### WP-CLI Integration
- **Latest WP-CLI**: Downloads and installs the latest stable WP-CLI build
- **i18n Commands**: Uses WP-CLI's built-in internationalization tools
- **WordPress Standards**: Follows WordPress coding standards for POT generation

### Smart File Detection
- **Source Scanning**: Automatically scans PHP files for translatable strings
- **Function Detection**: Finds `__()`, `_e()`, `_n()`, `_x()`, and other i18n functions
- **Exclusion Support**: Respects `.distignore` file for excluding paths

### Optimized Output
- **Skip Audit**: Bypasses time-consuming audit processes for faster generation
- **Custom Headers**: Includes standardized POT file headers
- **Clean Format**: Generates properly formatted POT files

## POT File Generation Process

### 1. WP-CLI Installation
The action automatically:
- Downloads the latest WP-CLI PHAR
- Makes it executable
- Installs it system-wide

### 2. String Extraction
WP-CLI scans for:
- `__( 'text', 'textdomain' )` - Basic translation
- `_e( 'text', 'textdomain' )` - Echo translation
- `_n( 'singular', 'plural', $count, 'textdomain' )` - Plural forms
- `_x( 'text', 'context', 'textdomain' )` - Translation with context
- `esc_html__()`, `esc_attr__()` - Escaped translations

### 3. File Exclusion
Uses `.distignore` file to exclude:
- Build artifacts
- Development files
- Test directories
- Documentation

## File Structure

### Input Structure
```text
plugin/
├── src/
│   ├── Plugin.php
│   └── Views/
│       └── Calendar.php
├── languages/
├── .distignore
└── package.json
```

### Output Structure
```text
plugin/
├── languages/
│   └── my-plugin.pot
└── ...
```

### Generated POT Content
```pot
# Copyright (C) 2024 StellarWP
# This file is distributed under the same license as the My Plugin package.
msgid ""
msgstr ""
"Project-Id-Version: My Plugin\n"
"Report-Msgid-Bugs-To: https://evnt.is/191x\n"
"POT-Creation-Date: 2024-01-15 12:00+0000\n"
"Content-Type: text/plain; charset=UTF-8\n"

#: src/Plugin.php:123
msgid "Event not found"
msgstr ""

#: src/Views/Calendar.php:45
msgid "No events found"
msgstr ""
```

## Configuration

### .distignore File
Create a `.distignore` file to exclude paths from POT generation:

```text
# Build files
/build/
/dist/
/node_modules/

# Development files
/.github/
/tests/
*.md

# Documentation
/docs/
```

### Custom Headers
The action includes these default headers:
- **Report-Msgid-Bugs-To**: `https://evnt.is/191x`
- **Last-Translator**: Empty (filled by translators)
- **Language-Team**: Empty (filled by translation teams)
- **PO-Revision-Date**: Empty (updated during translation)

## Requirements

### System Requirements
- **PHP**: Available in the runner environment
- **curl**: For downloading WP-CLI
- **Unix utilities**: `chmod`, `mv`, `cat`, `tr`, `sed`

### File Requirements
- **Source files**: PHP files with translatable strings
- **.distignore**: File exclusion patterns (optional but recommended)
- **Output directory**: Must exist or be creatable

## Integration with Translation Services

### GlotPress Integration
```yaml
- name: Generate POT
  uses: the-events-calendar/actions/.github/actions/generate-pot@main
  with:
    plugin_path: ./
    pot_path: ./languages/my-plugin.pot

- name: Upload to GlotPress
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
```

### Translation Platform Workflow
```yaml
- name: Generate and deploy POT
  runs-on: ubuntu-latest
  steps:
    - name: Generate POT file
      uses: the-events-calendar/actions/.github/actions/generate-pot@main
      with:
        plugin_path: ./
        pot_path: ./languages/plugin.pot

    - name: Deploy to translation service
      run: |
        # Upload to your translation service
        curl -X POST "https://translate.example.com/api/upload" \
             -F "file=@./languages/plugin.pot" \
             -H "Authorization: Bearer ${{ secrets.TRANSLATION_TOKEN }}"
```

## Troubleshooting

### Common Issues

#### WP-CLI Download Fails
```
Error: Failed to download WP-CLI
```
**Solutions**:
- Check network connectivity
- Verify GitHub's wp-cli/builds repository is accessible
- Ensure `curl` is available in the runner

#### Permission Denied
```
Error: Permission denied when creating POT file
```
**Solutions**:
- Ensure output directory exists and is writable
- Check file permissions in the runner environment
- Verify the action has write access to the target path

#### No Translatable Strings Found
```
Warning: No translatable strings found
```
**Solutions**:
- Verify your PHP files use WordPress i18n functions
- Check that `plugin_path` points to the correct directory
- Ensure your textdomain is consistent
- Review `.distignore` to ensure source files aren't excluded

#### Invalid POT File Generated
```
Error: Generated POT file is malformed
```
**Solutions**:
- Check for syntax errors in PHP source files
- Verify translatable strings follow WordPress standards
- Review WP-CLI output for specific error messages

### Debug Mode
Add debug output to troubleshoot issues:

```yaml
- name: Generate POT with debug
  uses: the-events-calendar/actions/.github/actions/generate-pot@main
  with:
    plugin_path: ./
    pot_path: ./languages/debug.pot

- name: Show POT contents
  run: |
    echo "=== POT File Contents ==="
    head -20 ./languages/debug.pot
    echo "=== String Count ==="
    grep -c "^msgid" ./languages/debug.pot
```

## Best Practices

### File Organization
```text
plugin/
├── languages/           # Translation files
│   ├── plugin.pot      # Template file
│   ├── plugin-es_ES.po # Spanish translation
│   └── plugin-fr_FR.po # French translation
├── src/                # Source code
└── .distignore        # Exclusion patterns
```

### Textdomain Consistency
Ensure all translatable strings use the same textdomain:

```php
// Good: Consistent textdomain
__( 'Hello World', 'my-plugin' );
_e( 'Welcome', 'my-plugin' );

// Bad: Inconsistent textdomain
__( 'Hello World', 'my-plugin' );
_e( 'Welcome', 'different-domain' );
```

### Translation Function Usage
Use appropriate functions for different contexts:

```php
// Simple translation
$text = __( 'Save Changes', 'my-plugin' );

// Echo translation
_e( 'Loading...', 'my-plugin' );

// Pluralization
$message = _n(
    '%d item selected',
    '%d items selected',
    $count,
    'my-plugin'
);

// Translation with context
$post_status = _x( 'Draft', 'post status', 'my-plugin' );
```

### Automation Best Practices
- **Regular Updates**: Generate POT files on every release
- **Version Control**: Commit POT files to track string changes
- **Quality Checks**: Validate POT files before deployment
- **Notification**: Alert translators when new strings are available

## Performance Considerations

### Large Codebases
For large plugins:
- Use specific `plugin_path` to limit scope
- Optimize `.distignore` to exclude unnecessary files
- Consider splitting large plugins into smaller translation units

### CI/CD Optimization
- **Caching**: Cache WP-CLI downloads between runs
- **Conditional Execution**: Only generate POT when source files change
- **Parallel Processing**: Process multiple plugins simultaneously

```yaml
# Conditional generation
- name: Check for PHP changes
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      php:
        - '**/*.php'

- name: Generate POT
  if: steps.changes.outputs.php == 'true'
  uses: the-events-calendar/actions/.github/actions/generate-pot@main
  with:
    plugin_path: ./
    pot_path: ./languages/plugin.pot
```
