# Detect Branch Type Action

A utility action that analyzes Git branch names to determine their type and characteristics for conditional workflow logic. This action helps standardize branch-based conditional execution across multiple workflows.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `branch-name` | Branch name to analyze | No | `${{ github.head_ref \|\| github.ref_name }}` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `branch-name` | The actual branch name being analyzed | String |
| `branch-type` | Type of branch (main, release, feature, hotfix, develop, other) | String |
| `is-main` | Whether this is a main/master branch | String (`true`/`false`) |
| `is-release` | Whether this is a release branch | String (`true`/`false`) |
| `is-feature` | Whether this is a feature branch | String (`true`/`false`) |
| `is-hotfix` | Whether this is a hotfix branch | String (`true`/`false`) |
| `is-develop` | Whether this is a develop branch | String (`true`/`false`) |
| `should-deploy` | Whether deployments should typically run on this branch type | String (`true`/`false`) |
| `should-release` | Whether release processes should run on this branch type | String (`true`/`false`) |

## Usage

### Basic usage

```yaml
- name: Detect branch type
  id: branch
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

- name: Show branch info
  run: |
    echo "Branch: ${{ steps.branch.outputs.branch-name }}"
    echo "Type: ${{ steps.branch.outputs.branch-type }}"
    echo "Should deploy: ${{ steps.branch.outputs.should-deploy }}"
```

### Conditional deployment

```yaml
- name: Detect branch type
  id: branch
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

- name: Deploy to staging
  if: steps.branch.outputs.should-deploy == 'true'
  run: deploy-staging.sh

- name: Deploy to production
  if: steps.branch.outputs.is-main == 'true'
  run: deploy-production.sh
```

### Release workflow

```yaml
- name: Detect branch type
  id: branch
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

- name: Process release
  if: steps.branch.outputs.should-release == 'true'
  run: |
    echo "Processing release for ${{ steps.branch.outputs.branch-type }} branch"
    ./scripts/release-process.sh

- name: Create release candidate
  if: steps.branch.outputs.is-release == 'true'
  run: ./scripts/create-rc.sh
```

### Custom branch analysis

```yaml
- name: Analyze specific branch
  id: branch
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main
  with:
    branch-name: 'feature/new-dashboard'

- name: Feature-specific actions
  if: steps.branch.outputs.is-feature == 'true'
  run: npm run test:feature
```

### Multi-job workflow

```yaml
jobs:
  analyze-branch:
    runs-on: ubuntu-latest
    outputs:
      branch-type: ${{ steps.branch.outputs.branch-type }}
      should-deploy: ${{ steps.branch.outputs.should-deploy }}
      is-release: ${{ steps.branch.outputs.is-release }}
    steps:
      - name: Detect branch type
        id: branch
        uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

  deploy:
    needs: analyze-branch
    if: needs.analyze-branch.outputs.should-deploy == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: echo "Deploying..."

  release:
    needs: analyze-branch
    if: needs.analyze-branch.outputs.is-release == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Create release
        run: echo "Creating release..."
```

## Branch Type Detection

The action recognizes standard Git branching patterns:

### Main Branches

- `main` → `branch-type: main`, `should-deploy: true`, `should-release: true`
- `master` → `branch-type: main`, `should-deploy: true`, `should-release: true`

### Release Branches

- `release/1.0.0` → `branch-type: release`, `should-deploy: true`, `should-release: true`
- `release/v2.1.0` → `branch-type: release`, `should-deploy: true`, `should-release: true`

### Feature Branches

- `feature/new-ui` → `branch-type: feature`, `should-deploy: false`, `should-release: false`
- `feature/user-auth` → `branch-type: feature`, `should-deploy: false`, `should-release: false`

### Hotfix Branches

- `hotfix/critical-bug` → `branch-type: hotfix`, `should-deploy: true`, `should-release: true`
- `hotfix/security-fix` → `branch-type: hotfix`, `should-deploy: true`, `should-release: true`

### Develop Branches

- `develop` → `branch-type: develop`, `should-deploy: true`, `should-release: false`
- `dev` → `branch-type: develop`, `should-deploy: true`, `should-release: false`

### Other Branches

- `docs/update-readme` → `branch-type: other`, `should-deploy: false`, `should-release: false`
- `chore/cleanup` → `branch-type: other`, `should-deploy: false`, `should-release: false`

## Features

### Smart Branch Analysis

- **Pattern Matching**: Uses regex patterns to identify branch types
- **Flexible Naming**: Supports various naming conventions
- **Clean Processing**: Automatically removes `refs/heads/` prefix

### Deployment Logic

The action provides intelligent deployment recommendations:

- **Main/Master**: Always eligible for deployment and release
- **Release**: Eligible for deployment and release processes
- **Hotfix**: Eligible for deployment and release (urgent fixes)
- **Develop**: Eligible for deployment but not release (staging)
- **Feature**: Not eligible for deployment or release (development)

### GitHub Integration

- **Step Summary**: Displays branch analysis with visual indicators
- **Detailed Output**: All branch characteristics available as outputs
- **Visual Feedback**: Uses emojis and formatting for clear status

## Step Summary Example

```text
## 🌿 Branch Analysis
* **Branch**: `release/6.2.0`
* **Type**: `release`
* **Deployment**: ✅ Eligible
* **Release Process**: ✅ Eligible
```

## Common Use Cases

### Conditional Deployments

```yaml
# Deploy to staging for develop branches
- name: Deploy to staging
  if: steps.branch.outputs.is-develop == 'true'
  run: deploy-staging.sh

# Deploy to production for main/release/hotfix
- name: Deploy to production
  if: steps.branch.outputs.should-deploy == 'true' && steps.branch.outputs.branch-type != 'develop'
  run: deploy-production.sh
```

### Release Automation

```yaml
# Only run release processes on eligible branches
- name: Process changelog
  if: steps.branch.outputs.should-release == 'true'
  uses: ./.github/actions/process-changelog

- name: Create GitHub release
  if: steps.branch.outputs.is-main == 'true'
  uses: actions/create-release@v1
```

### Feature Branch Testing

```yaml
# Extended testing for feature branches
- name: Run extended tests
  if: steps.branch.outputs.is-feature == 'true'
  run: npm run test:extended

# Quick tests for main branches
- name: Run quick tests
  if: steps.branch.outputs.is-main == 'true'
  run: npm run test:quick
```

### Environment-Specific Logic

```yaml
# Different database setups per branch type
- name: Setup test database
  if: steps.branch.outputs.is-feature == 'true'
  run: setup-test-db.sh

- name: Setup staging database
  if: steps.branch.outputs.is-develop == 'true'
  run: setup-staging-db.sh

- name: Setup production database
  if: steps.branch.outputs.should-release == 'true'
  run: setup-prod-db.sh
```

## Migration Benefits

This action standardizes branch detection logic that was previously scattered across workflows:

### Before (Inconsistent Logic)

```yaml
# Workflow 1
- name: Check if main
  run: |
    if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      echo "is_main=true" >> $GITHUB_OUTPUT
    fi

# Workflow 2
- name: Check branch type
  run: |
    if [[ "$GITHUB_REF_NAME" =~ ^release/.* ]]; then
      echo "Deploy to staging"
    fi

# Workflow 3
- name: Branch detection
  run: |
    case "${{ github.ref_name }}" in
      main|master) echo "DEPLOY=true" ;;
      release/*) echo "DEPLOY=true" ;;
      *) echo "DEPLOY=false" ;;
    esac
```

### After (Standardized)

```yaml
# Any workflow
- name: Detect branch
  id: branch
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

- name: Deploy if eligible
  if: steps.branch.outputs.should-deploy == 'true'
  run: deploy.sh
```

## Output Reference

### Branch Types

- `main` - Main/master branch
- `release` - Release branch (release/*)
- `feature` - Feature branch (feature/*)
- `hotfix` - Hotfix branch (hotfix/*)
- `develop` - Development branch (develop/dev)
- `other` - Any other branch pattern

### Boolean Outputs

All boolean outputs return `"true"` or `"false"` as strings:

- `is-main` - Main/master branch
- `is-release` - Release branch
- `is-feature` - Feature branch
- `is-hotfix` - Hotfix branch
- `is-develop` - Develop branch
- `should-deploy` - Recommended for deployment
- `should-release` - Recommended for release processes

## Best Practices

### Use Early in Workflows

```yaml
jobs:
  analyze:
    steps:
      - name: Detect branch type
        id: branch
        uses: the-events-calendar/actions/.github/actions/detect-branch-type@main
    outputs:
      branch-type: ${{ steps.branch.outputs.branch-type }}
      should-deploy: ${{ steps.branch.outputs.should-deploy }}

  # Use outputs in dependent jobs
  deploy:
    needs: analyze
    if: needs.analyze.outputs.should-deploy == 'true'
```

### Combine with Other Conditions

```yaml
- name: Deploy to production
  if: |
    steps.branch.outputs.is-main == 'true' &&
    github.event_name == 'push' &&
    success()
  run: deploy-production.sh
```

### Error Handling

```yaml
- name: Detect branch type
  id: branch
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/detect-branch-type@main

- name: Fallback logic
  if: steps.branch.outcome == 'failure'
  run: echo "Using default branch logic"
```

## Troubleshooting

### Unexpected Branch Type

If branches aren't classified correctly:

- Check branch naming follows standard patterns
- Verify regex patterns match your naming convention
- Consider if your branch needs custom classification

### Boolean Comparison Issues

Remember that outputs are strings:

- ✅ `if: steps.branch.outputs.is-main == 'true'`
- ❌ `if: steps.branch.outputs.is-main == true`

### Missing Branch Name

If branch name is empty:

- Ensure workflow runs on push/pull_request events
- Check if `github.head_ref` or `github.ref_name` are available
- Provide explicit `branch-name` input if needed
