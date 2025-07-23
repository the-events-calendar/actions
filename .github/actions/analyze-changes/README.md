# Analyze Changes Action

This composite action analyzes git changes between commits to automatically detect WordPress plugin hooks (filters and actions) and view modifications. It's designed for release process automation to track API changes and generate appropriate changelog entries.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `compare-commit` | Commit to compare against (default: latest tag) | No | `''` |
| `output-format` | Output format: changelog, list, or html | No | `'changelog'` |
| `additional-inputs` | Additional inputs to pass through (JSON string) | No | `'{}'` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `analysis-summary` | Summary of analyzed changes | String |
| `changes-detected` | Whether any changes were detected | Boolean |
| `filters-added` | List of added filters | String |
| `has-filters-added` | Whether filters were added | Boolean |
| `filters-removed` | List of removed filters | String |
| `has-filters-removed` | Whether filters were removed | Boolean |
| `actions-added` | List of added actions | String |
| `has-actions-added` | Whether actions were added | Boolean |
| `actions-removed` | List of removed actions | String |
| `has-actions-removed` | Whether actions were removed | Boolean |
| `views-changed` | List of changed views | String |
| `has-views-changed` | Whether views were changed | Boolean |

## Usage

### Basic usage (compare against latest tag)

```yaml
- name: Analyze changes
  id: analyze
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main

- name: Check if changes detected
  if: steps.analyze.outputs.changes-detected == 'true'
  run: echo "Changes found!"
```

### Compare against specific commit

```yaml
- name: Analyze changes
  id: analyze
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main
  with:
    compare-commit: ${{ github.event.pull_request.base.sha }}
```

### Different output formats

```yaml
# Changelog format (default)
- name: Analyze for changelog
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main
  with:
    output-format: changelog

# List format
- name: Analyze for list
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main
  with:
    output-format: list

# HTML format
- name: Analyze for HTML
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main
  with:
    output-format: html
```

### Complete release workflow example

```yaml
name: Release Analysis
on:
  pull_request:
    branches: [main]

jobs:
  analyze-changes:
    runs-on: ubuntu-latest
    outputs:
      changes-detected: ${{ steps.analyze.outputs.changes-detected }}
      summary: ${{ steps.analyze.outputs.analysis-summary }}
    steps:
      - name: Analyze changes
        id: analyze
        uses: the-events-calendar/actions/.github/actions/analyze-changes@main

  conditional-steps:
    needs: analyze-changes
    if: needs.analyze-changes.outputs.changes-detected == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Handle detected changes
        run: |
          echo "Summary: ${{ needs.analyze-changes.outputs.summary }}"
```

### Using specific change type outputs

```yaml
- name: Analyze changes
  id: analyze
  uses: the-events-calendar/actions/.github/actions/analyze-changes@main

- name: Handle new filters
  if: steps.analyze.outputs.has-filters-added == 'true'
  run: |
    echo "New filters: ${{ steps.analyze.outputs.filters-added }}"

- name: Handle removed actions
  if: steps.analyze.outputs.has-actions-removed == 'true'
  run: |
    echo "Removed actions: ${{ steps.analyze.outputs.actions-removed }}"
    # Potentially notify about breaking changes

- name: Handle view changes
  if: steps.analyze.outputs.has-views-changed == 'true'
  run: |
    echo "Changed views: ${{ steps.analyze.outputs.views-changed }}"
    # Update template documentation
```

## Features

### Change Detection
- **WordPress Hooks**: Detects `apply_filters()` and `do_action()` calls
- **View Files**: Identifies changes to PHP view templates in `src/views/`
- **Git Diff Analysis**: Compares against specified commit or latest tag
- **Deduplication**: Automatically removes duplicate entries

### Output Formats
- **Changelog**: WordPress-style changelog entries (`* Tweak - Added filters: ...`)
- **List**: Simple bullet-point lists
- **HTML**: Formatted HTML with headings and code samples

### Automatic Changelog Generation
When `output-format` is set to `changelog`, the action automatically:
- Creates individual changelog entries for each change type
- Uses the `add-changelog` action to generate proper entries
- Files are named `task-analyze-changes-{type}-{sha}`

### GitHub Integration
- **Step Summary**: Displays results in GitHub Actions UI
- **Detailed Outputs**: All detected changes available as action outputs
- **Conditional Execution**: Easy integration with conditional workflow steps

## Change Detection Logic

The action searches for these patterns in git diffs:

### Filters
```php
// Added filter (detected)
+ apply_filters('new_filter_name', $value);

// Removed filter (detected)
- apply_filters('old_filter_name', $value);
```

### Actions
```php
// Added action (detected)
+ do_action('new_action_name', $data);

// Removed action (detected)
- do_action('old_action_name', $data);
```

### Views
```
// View file change (detected)
diff --git a/src/views/single-event.php b/src/views/single-event.php
```

## Migration from Reusable Workflow

This action replaces the `analyze-changes.yml` reusable workflow. The main differences:

1. **Usage**: Called with `uses: the-events-calendar/actions/.github/actions/analyze-changes@main`
2. **Setup**: Uses the `basic-setup` action instead of workflow call
3. **Outputs**: Access through step outputs instead of job outputs

### Before (Reusable Workflow)
```yaml
uses: ./.github/workflows/reusable/release-process/analyze-changes.yml
with:
  compare-commit: ${{ github.event.pull_request.base.sha }}
  output-format: changelog
```

### After (Composite Action)
```yaml
uses: the-events-calendar/actions/.github/actions/analyze-changes@main
with:
  compare-commit: ${{ github.event.pull_request.base.sha }}
  output-format: changelog
```

## Example Output

### Changelog Format
```
* Tweak - Added filters: `tribe_events_new_filter`, `tribe_events_another_filter`
* Tweak - Removed actions: `tribe_events_old_action`
* Tweak - Changed views: `single-event`, `list/list-view`
```

### List Format
```
Added filters:
- tribe_events_new_filter
- tribe_events_another_filter
Removed actions:
- tribe_events_old_action
Changed views:
- single-event
- list/list-view
```

### HTML Format
```html
<h4>Filters added</h4>
<ul>
  <li><samp>tribe_events_new_filter</samp></li>
  <li><samp>tribe_events_another_filter</samp></li>
</ul>
<h4>Actions removed</h4>
<ul>
  <li><samp>tribe_events_old_action</samp></li>
</ul>
```

## Requirements

- Repository must be checked out with sufficient history (`fetch-depth: 0` recommended)
- Git must be available
- For changelog mode: `add-changelog` action must be available
- Source code should be in `src/` directory or repository root

## Troubleshooting

### No changes detected
- Verify the compare commit exists and is accessible
- Check that changes exist in PHP files
- Ensure the repository has sufficient git history

### Missing hook detection
- Verify hooks use standard WordPress syntax: `apply_filters('hook_name', ...)`
- Check that changes are in tracked files
- Ensure proper git diff is generated

### Changelog entries not created
- Verify `output-format` is set to `'changelog'`
- Check that `add-changelog` action is available
- Ensure proper permissions for file creation
