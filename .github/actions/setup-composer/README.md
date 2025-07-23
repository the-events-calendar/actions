# Setup Composer Action

A utility action that sets up Composer with intelligent caching and configurable installation options. This action consolidates Composer setup logic that was previously duplicated across multiple actions and workflows.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `composer-flags` | Additional flags for composer install | No | `'--no-progress --ignore-platform-reqs'` |
| `working-directory` | Working directory for composer operations | No | `'.'` |
| `cache-key-suffix` | Additional suffix for cache key | No | `''` |
| `skip-cache` | Skip caching step | No | `'false'` |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `cache-hit` | Whether cache was hit | String (`true`/`false`) |
| `cache-key` | Cache key used | String |
| `composer-version` | Composer version used | String |

## Usage

### Basic usage (default caching)

```yaml
- name: Setup Composer
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
```

### With custom flags

```yaml
- name: Setup Composer with dev dependencies
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    composer-flags: '--dev --optimize-autoloader'
```

### Skip caching

```yaml
- name: Setup Composer without cache
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    skip-cache: 'true'
```

### Custom working directory

```yaml
- name: Setup Composer in subdirectory
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    working-directory: 'src/php'
    cache-key-suffix: 'backend'
```

### With cache verification

```yaml
- name: Setup Composer
  id: composer
  uses: the-events-calendar/actions/.github/actions/setup-composer@main

- name: Check cache performance
  run: |
    echo "Cache hit: ${{ steps.composer.outputs.cache-hit }}"
    echo "Composer version: ${{ steps.composer.outputs.composer-version }}"
```

### In testing workflow

```yaml
name: PHP Tests
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        php-version: ['7.4', '8.0', '8.1', '8.2']
    steps:
      - uses: actions/checkout@v4

      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: ${{ matrix.php-version }}

      - name: Setup Composer
        uses: the-events-calendar/actions/.github/actions/setup-composer@main
        with:
          cache-key-suffix: 'php-${{ matrix.php-version }}'

      - name: Run tests
        run: vendor/bin/phpunit
```

## Features

### Intelligent Caching
- **Automatic Cache Keys**: Uses `composer.lock` hash for precise caching
- **OS-Specific**: Caches are isolated per operating system
- **Restore Keys**: Falls back to partial cache matches for faster builds
- **Custom Suffixes**: Allows cache isolation for different scenarios

### Flexible Installation
- **Configurable Flags**: Supports any `composer install` flags
- **Directory Support**: Works in any subdirectory with `composer.json`
- **Validation**: Verifies successful installation
- **Error Handling**: Clear error messages for common issues

### GitHub Integration
- **Step Summary**: Displays detailed installation information
- **Performance Metrics**: Shows cache hit/miss status
- **Package Counting**: Reports number of installed packages
- **Visual Feedback**: Uses emojis and formatting for clear status

## Step Summary Examples

### Successful Installation (Cache Hit)
```
## 📦 Composer Setup
* **Version**: `2.6.5`
* **Working Directory**: `.`
* **Cache**: ✅ Hit (restored from cache)
* **Flags**: `--no-progress --ignore-platform-reqs`
* **Status**: ✅ Dependencies installed
* **Packages Installed**: `42`
```

### Successful Installation (Cache Miss)
```
## 📦 Composer Setup
* **Version**: `2.6.5`
* **Working Directory**: `src/backend`
* **Cache**: ❌ Miss (dependencies downloaded)
* **Flags**: `--dev --optimize-autoloader`
* **Status**: ✅ Dependencies installed
* **Packages Installed**: `58`
```

## Migration Benefits

This action eliminates duplicated Composer setup logic found in multiple actions:

### Before (Duplicated Code)
```yaml
# In process-changelog action
- name: Set up Composer
  run: composer install --no-progress --ignore-platform-reqs

# In basic-setup action
- name: Add composer to cache
  uses: actions/cache@v4
  with:
    path: ~/.cache/composer/
    key: ${{ runner.os }}-composer-${{ hashFiles('composer.lock') }}

- name: Install composer dependencies
  uses: php-actions/composer@v6
  with:
    php_version: 7.4
    dev: yes
    args: --ignore-platform-reqs

# In add-changelog action
- name: Add composer to cache
  uses: actions/cache@v4
  with:
    path: ~/.cache/composer/
    key: ${{ runner.os }}-composer-${{ hashFiles('composer.lock') }}

- name: Install composer dependencies
  uses: php-actions/composer@v6
  with:
    php_version: 7.4
    dev: yes
    args: --ignore-platform-reqs
```

### After (Modularized)
```yaml
# In any action
- name: Setup Composer
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
```

## Common Use Cases

### WordPress Plugin Development

```yaml
name: WordPress Plugin CI
jobs:
  test:
    steps:
      - name: Setup PHP environment
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.1'
          extensions: mbstring, xml, ctype, iconv, intl, pdo_sqlite

      - name: Setup Composer
        uses: the-events-calendar/actions/.github/actions/setup-composer@main
        with:
          composer-flags: '--dev --optimize-autoloader'

      - name: Run PHPCS
        run: vendor/bin/phpcs

      - name: Run PHPUnit tests
        run: vendor/bin/phpunit
```

### Multi-PHP Testing

```yaml
strategy:
  matrix:
    php-version: ['7.4', '8.0', '8.1', '8.2']
    dependency-version: ['lowest', 'highest']
    include:
      - dependency-version: lowest
        composer-flags: '--prefer-lowest --prefer-stable'
      - dependency-version: highest
        composer-flags: '--prefer-stable'

steps:
  - name: Setup Composer
    uses: the-events-calendar/actions/.github/actions/setup-composer@main
    with:
      composer-flags: ${{ matrix.composer-flags }}
      cache-key-suffix: 'php-${{ matrix.php-version }}-${{ matrix.dependency-version }}'
```

### Monorepo Support

```yaml
strategy:
  matrix:
    package: ['core', 'admin', 'frontend']
    include:
      - package: core
        working-directory: 'packages/core'
      - package: admin
        working-directory: 'packages/admin'
      - package: frontend
        working-directory: 'packages/frontend'

steps:
  - name: Setup Composer for ${{ matrix.package }}
    uses: the-events-calendar/actions/.github/actions/setup-composer@main
    with:
      working-directory: ${{ matrix.working-directory }}
      cache-key-suffix: '${{ matrix.package }}'
```

### Release Building

```yaml
- name: Setup Composer for production
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    composer-flags: '--no-dev --optimize-autoloader --classmap-authoritative'
    cache-key-suffix: 'production'

- name: Build release package
  run: |
    # Remove development files
    rm -rf tests/ phpcs.xml phpunit.xml

    # Create release zip
    zip -r plugin-release.zip . -x "*.git*" "node_modules/*"
```

### Development Environment

```yaml
- name: Setup Composer for development
  uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    composer-flags: '--dev'

- name: Install development tools
  run: |
    vendor/bin/phpcs --config-set installed_paths vendor/wp-coding-standards/wpcs
    vendor/bin/phpcs --config-set default_standard WordPress
```

## Cache Strategy

### Cache Key Components
1. **Operating System**: `${{ runner.os }}`
2. **Composer Lock Hash**: `${{ hashFiles('composer.lock') }}`
3. **Custom Suffix**: `${{ inputs.cache-key-suffix }}`

### Cache Locations
- **Linux/macOS**: `~/.cache/composer/`
- **Windows**: `%LOCALAPPDATA%\Composer\`

### Cache Optimization
```yaml
# Good: Specific cache per scenario
- uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    cache-key-suffix: 'tests-php8.1'

# Good: Skip cache for one-time builds
- uses: the-events-calendar/actions/.github/actions/setup-composer@main
  with:
    skip-cache: 'true'
```

## Best Practices

### Use Specific Flags
```yaml
# Production builds
composer-flags: '--no-dev --optimize-autoloader'

# Development builds
composer-flags: '--dev'

# Testing builds
composer-flags: '--prefer-stable'

# Fast CI builds
composer-flags: '--no-progress --no-interaction'
```

### Cache Key Management
```yaml
# Good: Isolate cache by environment
cache-key-suffix: 'production'

# Good: Isolate cache by PHP version
cache-key-suffix: 'php-${{ matrix.php-version }}'

# Good: Isolate cache by test suite
cache-key-suffix: 'integration-tests'
```

### Error Handling
```yaml
- name: Setup Composer
  id: composer
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/setup-composer@main

- name: Fallback installation
  if: steps.composer.outcome == 'failure'
  run: |
    echo "Composer action failed, trying manual installation"
    composer install --no-cache
```

### Working Directory Patterns
```yaml
# Good: Explicit working directory
working-directory: 'backend/'

# Good: Matrix-based directories
working-directory: ${{ matrix.package-path }}

# Avoid: Changing to directory manually
# run: cd backend && composer install
```

## Performance Optimization

### Cache Hit Strategies
- Use specific `cache-key-suffix` for different scenarios
- Keep `composer.lock` committed for consistent caching
- Use matrix builds with appropriate cache keys

### Speed Improvements
```yaml
# Fastest for CI
composer-flags: '--no-progress --no-interaction --prefer-dist'

# Skip development dependencies in production
composer-flags: '--no-dev'

# Optimize autoloader for production
composer-flags: '--optimize-autoloader --classmap-authoritative'
```

## Troubleshooting

### Cache Issues

**Problem**: Cache not working effectively
```yaml
# Solution: Add specific cache suffix
cache-key-suffix: 'unique-identifier'

# Solution: Check composer.lock exists and is committed
```

### Permission Issues

**Problem**: Composer cache permission denied
```yaml
# Solution: Skip cache temporarily
skip-cache: 'true'
```

### Memory Issues

**Problem**: Composer runs out of memory
```yaml
# Solution: Add memory limit flag
composer-flags: '--no-progress --ignore-platform-reqs -d memory_limit=2G'
```

### Dependency Conflicts

**Problem**: Platform requirements not met
```yaml
# Solution: Ignore platform requirements
composer-flags: '--ignore-platform-reqs'

# Solution: Use prefer-lowest for compatibility testing
composer-flags: '--prefer-lowest --prefer-stable'
```

### Slow Installation

**Problem**: Composer install takes too long
```yaml
# Solution: Use prefer-dist for faster downloads
composer-flags: '--prefer-dist --no-progress'

# Solution: Skip cache if it's corrupted
skip-cache: 'true'
```

## Output Examples

### Cache Hit
```yaml
cache-hit: "true"
cache-key: "Linux-composer-a1b2c3d4e5f6"
composer-version: "2.6.5"
```

### Cache Miss
```yaml
cache-hit: "false"
cache-key: "Linux-composer-a1b2c3d4e5f6"
composer-version: "2.6.5"
```

## Integration Examples

### With PHP Setup
```yaml
- name: Setup PHP
  uses: shivammathur/setup-php@v2
  with:
    php-version: '8.1'

- name: Setup Composer
  uses: the-events-calendar/actions/.github/actions/setup-composer@main

- name: Run tools
  run: |
    vendor/bin/phpcs
    vendor/bin/phpunit
```

### With Other Actions
```yaml
- name: Basic setup
  uses: the-events-calendar/actions/.github/actions/basic-setup@main
  with:
    setup-php: 'true'

- name: Setup Composer
  uses: the-events-calendar/actions/.github/actions/setup-composer@main

- name: Process changelog
  uses: the-events-calendar/actions/.github/actions/process-changelog@main
```
