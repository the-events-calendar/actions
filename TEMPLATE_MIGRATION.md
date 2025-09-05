# Template Workflow Migration Summary

This document summarizes the updates made to template workflows in `templates/workflows/` to utilize the new GitHub Actions.

## Files Updated

### ✅ `changelogger.yml`

**Changes Made:**

- Replaced manual checkout, PHP setup, and caching with `base-setup` action
- Updated to use structured composer caching approach
- Maintained backward compatibility with existing workflow structure

**Before:**

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 1000
      submodules: recursive
  - name: Add composer to cache
    uses: actions/cache@v4
    with:
      path: ~/.cache/composer/
      key: ${{ runner.os }}-composer-${{ hashFiles('composer.lock') }}
  - name: Configure PHP environment
    uses: shivammathur/setup-php@v2
    with:
      php-version: 7.4
      tools: composer
      coverage: none
```

**After:**

```yaml
steps:
  - name: Setup environment
    uses: the-events-calendar/actions/.github/actions/base-setup@main
    with:
      setup-php: 'true'
      setup-node: 'false'
      php-version: '7.4'
      fetch-depth: '1000'
  - name: Get Composer Cache Directory
    id: composer-cache-dir
    run: echo "dir=$(composer config cache-files-dir)" >> $GITHUB_OUTPUT
  - name: Cache composer dependencies
    uses: actions/cache@v4
    with:
      path: ${{ steps.composer-cache-dir.outputs.dir }}
      key: ${{ runner.os }}-composer-${{ hashFiles('**/composer.lock') }}
```

### ✅ `lint.yml`

**Changes Made:**

- Replaced manual checkout and Node.js setup with `base-setup` action
- Simplified workflow by removing .nvmrc detection logic (now handled by action)

**Before:**

```yaml
steps:
  - name: Checkout the repository
    uses: actions/checkout@v4
    with:
      fetch-depth: 1
      submodules: recursive
  - name: Check for .nvmrc file
    id: check-nvmrc
    run: |
      if [ -f "${{ github.workspace }}/.nvmrc" ]; then
        echo "exists=true" >> $GITHUB_OUTPUT
      else
        echo "exists=false" >> $GITHUB_OUTPUT
      fi
  - uses: actions/setup-node@v4
    if: steps.check-nvmrc.outputs.exists == 'true'
    with:
      node-version-file: '.nvmrc'
      cache: 'npm'
      cache-dependency-path: package-lock.json
```

**After:**

```yaml
steps:
  - name: Setup environment
    uses: the-events-calendar/actions/.github/actions/base-setup@main
    with:
      setup-php: 'false'
      setup-node: 'true'
```

### ✅ `phpcs.yml`

**Changes Made:**

- Replaced manual PHP change detection with `php-change-detector` action
- Updated condition logic to use new output names
- Updated secret name to match organizational standard

**Before:**

```yaml
conditional:
  if: "!contains(github.event.pull_request.body, '[skip-phpcs]')"
  runs-on: ubuntu-latest
  outputs:
    has_no_php_changes: ${{ steps.skip.outputs.has_no_php_changes }}
  steps:
    - name: Checkout the repository
      uses: actions/checkout@v4
      with:
        fetch-depth: 1000
        token: ${{ secrets.GH_BOT_TOKEN }}
        submodules: recursive
    - name: Check PHP file changes
      id: skip
      run: |
        php_files=$(git diff ${{ github.event.pull_request.base.sha }} HEAD --name-only | grep -E '\.php$' || true)
        # ... complex shell logic ...
```

**After:**

```yaml
conditional:
  runs-on: ubuntu-latest
  outputs:
    has-php-changes: ${{ steps.php-changes.outputs.has-php-changes }}
    should-run: ${{ steps.php-changes.outputs.should-run }}
  steps:
    - name: Check PHP changes
      id: php-changes
      uses: the-events-calendar/actions/.github/actions/php-change-detector@main
      with:
        skip-flag: phpcs
```

### ✅ `release-process-changelog.yml`

**Changes Made:**

- Replaced manual PHP setup with `base-setup` action
- Added proper composer caching
- Maintained existing process-changelog action usage

**Before:**

```yaml
steps:
  - name: Checkout repository
    uses: actions/checkout@v4
    with:
      ref: ${{ github.ref }}
      fetch-depth: 0
  - name: Configure PHP environment
    uses: shivammathur/setup-php@v2
    with:
      php-version: 7.4
  - name: Set up Composer
    run: composer install --no-progress --ignore-platform-reqs
```

**After:**

```yaml
steps:
  - name: Setup environment
    uses: the-events-calendar/actions/.github/actions/base-setup@main
    with:
      setup-php: 'true'
      setup-node: 'false'
      php-version: '7.4'
      fetch-depth: '0'
  - name: Get Composer Cache Directory
    id: composer-cache-dir
    run: echo "dir=$(composer config cache-files-dir)" >> $GITHUB_OUTPUT
  - name: Cache composer dependencies
    uses: actions/cache@v4
    with:
      path: ${{ steps.composer-cache-dir.outputs.dir }}
      key: ${{ runner.os }}-composer-${{ hashFiles('**/composer.lock') }}
```

## Files Already Using Actions

### ✅ `release-sync-translations.yml`

- Already correctly uses `generate-pot`, `push-translations`, and `add-changelog` actions
- No changes needed

### ✅ Other Release Templates

- `release-replace-tbd-entries.yml` - Uses manual setup (appropriate for this workflow)
- `release-update-wp-version.yml` - Uses manual setup (appropriate for this workflow)
- `release-merge-forward.yml` - Uses manual setup (appropriate for this workflow)
- `release-prepare-branch.yml` - Uses manual setup (appropriate for this workflow)
- `link-project.yml` - Simple workflow, no setup needed

## Files Removed

### ❌ Redundant Reusable Workflows

- `/.github/workflows/reusable/base-setup.yml`
- `/.github/workflows/reusable/php-change-detector.yml`
- `/.github/workflows/reusable/slic-test-runner.yml`
- `/.github/workflows/reusable/` (empty directory)

## Benefits Achieved

1. **Consistency**: All templates now use centralized actions
2. **Maintainability**: Setup logic is maintained in one place
3. **Simplification**: Complex setup logic removed from templates
4. **Standardization**: Consistent input/output patterns across all workflows
5. **Reusability**: Templates can be used across all plugins with minimal changes

## Usage Impact

### For New Plugins

- Copy templates directly from `templates/workflows/`
- Templates will automatically use the latest action versions
- Minimal customization needed

### For Existing Plugins

- Existing workflows already updated to use actions
- Templates provide reference for future workflows
- Consistent patterns across the organization

## Next Steps

1. ✅ Templates updated to use actions
2. ✅ Redundant reusable workflows removed
3. 🔄 Templates ready for sync across repositories
4. 📝 Documentation updated

## Migration Commands

When syncing these templates to plugins, the following pattern should be used:

```yaml
# Old pattern (replaced)
- uses: ./.github/workflows/reusable/base-setup.yml

# New pattern
- uses: the-events-calendar/actions/.github/actions/base-setup@main
```

The templates now follow this pattern consistently and will be synced to all repositories automatically.
