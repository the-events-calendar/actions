# Merge Forward Action

A composite action that creates pull requests to merge changes from one branch to another for release management. This action automates the process of merging changes forward between release branches or from release branches to main/master.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `forward-branch` | Name of the branch to merge into (e.g. release/T25.adamwarlock, master) | Yes | - |
| `gh-bot-token` | GitHub bot token for authentication | No | `${{ github.token }}` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `pull-request-url` | URL of the created pull request | String |
| `pull-request-created` | Whether a pull request was created | String (`true`/`false`) |
| `skip-reason` | Reason why PR creation was skipped (if applicable) | String |

## Usage

### Basic usage

```yaml
- name: Merge forward to release branch
  uses: the-events-calendar/actions/.github/actions/merge-forward@main
  with:
    forward-branch: release/T25.adamwarlock
    gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}
```

### Complete workflow example

```yaml
name: Merge Forward
on:
  workflow_dispatch:
    inputs:
      forward-branch:
        description: 'Name of the branch to merge into'
        required: true
        default: 'release/T25.name'

jobs:
  merge-forward:
    runs-on: ubuntu-latest
    steps:
      - name: Merge forward changes
        id: merge
        uses: the-events-calendar/actions/.github/actions/merge-forward@main
        with:
          forward-branch: ${{ github.event.inputs.forward-branch }}
          gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}

      - name: Display results
        run: |
          echo "PR Created: ${{ steps.merge.outputs.pull-request-created }}"
          if [ "${{ steps.merge.outputs.pull-request-created }}" == "true" ]; then
            echo "PR URL: ${{ steps.merge.outputs.pull-request-url }}"
          else
            echo "Skip Reason: ${{ steps.merge.outputs.skip-reason }}"
          fi
```

### With conditional handling

```yaml
- name: Merge forward to master
  id: merge-master
  uses: the-events-calendar/actions/.github/actions/merge-forward@main
  with:
    forward-branch: master
    gh-bot-token: ${{ secrets.GHA_BOT_TOKEN_MANAGER }}

- name: Handle successful merge
  if: steps.merge-master.outputs.pull-request-created == 'true'
  run: |
    echo "Merge forward PR created successfully!"
    echo "Review at: ${{ steps.merge-master.outputs.pull-request-url }}"

- name: Handle skipped merge
  if: steps.merge-master.outputs.pull-request-created == 'false'
  run: |
    echo "Merge forward was skipped: ${{ steps.merge-master.outputs.skip-reason }}"
```

## Features

### Intelligent Branch Management
- **Branch Existence Check**: Verifies if the target branch exists before proceeding
- **Automatic Branch Creation**: Creates the target branch if it doesn't exist
- **Clean Merge Strategy**: Uses `--no-ff` merges to maintain clear history

### Conflict Detection
- **Merge Validation**: Detects and reports merge conflicts
- **Graceful Failure**: Provides clear error messages when merges fail
- **Branch Cleanup**: Maintains clean repository state even on failures

### Pull Request Automation
- **Automatic PR Creation**: Creates properly formatted pull requests
- **Skip Flag Integration**: Includes skip flags to prevent unnecessary CI runs
- **Metadata Addition**: Adds relevant labels and assignments

## Merge Process

### 1. Branch Analysis
The action first checks if the target branch exists:
- **Branch Exists**: Proceeds with merge process
- **Branch Missing**: Creates the branch and skips PR creation

### 2. Merge Execution
When the target branch exists:
- Creates a temporary merge branch: `task/merge-forward-{source}-to-{target}`
- Performs a no-fast-forward merge to maintain history
- Pushes the merge branch to remote

### 3. Pull Request Creation
- Creates a PR with descriptive title and body
- Includes relevant metadata and skip flags
- Assigns to the workflow triggerer
- Adds automation labels

## Error Handling

### Common Issues

#### Target Branch Doesn't Exist
```
Skip Reason: Forward branch release/T25.newbranch does not exist
```
**Solution**: The action automatically creates the branch for future use.

#### Merge Conflicts
```
❌ Merge conflicts detected
```
**Solution**: Resolve conflicts manually in the source branch before retrying.

#### Authentication Issues
```
Error: Could not create pull request
```
**Solutions**:
- Verify `gh-bot-token` has proper permissions
- Ensure token has `pull_requests:write` access
- Check repository permissions

### Debug Information

The action provides comprehensive debugging information:

```yaml
## Branch Analysis
- **Forward Branch**: `release/T25.adamwarlock`
- **Current Branch**: `main`

## Creating Merge Branch
- **Head Branch**: `task/merge-forward-main-to-release/T25.adamwarlock`

## Creating Pull Request
✅ Pull request created successfully
- **URL**: [https://github.com/repo/pull/123](https://github.com/repo/pull/123)
```

## Best Practices

### Branch Naming Conventions
- Use descriptive release branch names: `release/T25.feature-name`
- Follow consistent patterns for easier automation
- Include ticket numbers or version identifiers

### Workflow Integration
```yaml
- name: Merge to release branch
  uses: the-events-calendar/actions/.github/actions/merge-forward@main
  with:
    forward-branch: ${{ env.RELEASE_BRANCH }}

- name: Merge to master after release
  uses: the-events-calendar/actions/.github/actions/merge-forward@main
  with:
    forward-branch: master
```

### Token Management
- Use dedicated bot tokens for automation
- Store tokens securely in GitHub Secrets
- Rotate tokens regularly for security

## Integration with Release Process

This action integrates well with other release actions:

```yaml
jobs:
  prepare-release:
    steps:
      - name: Prepare release branch
        uses: the-events-calendar/actions/.github/actions/prepare-branch@main
        
  merge-forward:
    needs: prepare-release
    steps:
      - name: Merge to release branch
        uses: the-events-calendar/actions/.github/actions/merge-forward@main
        with:
          forward-branch: ${{ needs.prepare-release.outputs.release-branch }}
```

## Skip Flags

The action automatically includes skip flags in created PRs:
- `[skip-changelog]` - Skip changelog validation
- `[skip-lint]` - Skip linting checks  
- `[skip-phpcs]` - Skip code style checks

These flags prevent unnecessary CI runs for automated merge commits.

## Troubleshooting

### PR Not Created
- Check if target branch exists
- Verify authentication token permissions
- Ensure no merge conflicts exist

### Merge Conflicts
- Review changes in both branches
- Resolve conflicts manually
- Consider using feature branches for complex merges

### Permission Errors
- Verify token has required permissions
- Check repository settings
- Ensure workflow has necessary access 