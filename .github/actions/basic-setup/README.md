# Basic Setup Action

This composite action sets up a basic environment for CI/CD workflows, including PHP and Node.js configuration.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `fetch-depth` | Git fetch depth | No | `1000` |
| `php-version` | PHP version to use | No | `7.4` |
| `node-version-file` | Node version file to use (.nvmrc) | No | `.nvmrc` |
| `setup-node` | Whether to setup Node.js | No | `false` |
| `setup-php` | Whether to setup PHP | No | `true` |
| `gh-bot-token` | GitHub bot token for checkout | No | - |

## Usage

### Basic usage with PHP only (default)

```yaml
- name: Setup environment
  uses: ./.github/actions/basic-setup
```

### Setup with both PHP and Node.js

```yaml
- name: Setup environment
  uses: ./.github/actions/basic-setup
  with:
    setup-node: true
    php-version: '8.1'
    node-version-file: '.nvmrc'
```

### Setup with custom fetch depth and bot token

```yaml
- name: Setup environment
  uses: ./.github/actions/basic-setup
  with:
    fetch-depth: 50
    gh-bot-token: ${{ secrets.BOT_TOKEN }}
    setup-node: true
```

### Node.js only setup

```yaml
- name: Setup environment
  uses: ./.github/actions/basic-setup
  with:
    setup-php: false
    setup-node: true
```

## Features

- **Repository Checkout**: Automatically checks out the repository with submodules
- **PHP Environment**: Configures PHP with essential extensions (mbstring, xml, ctype, iconv, intl, pdo_sqlite, sqlite3, gd, exif)
- **Node.js Environment**: Sets up Node.js based on `.nvmrc` file with npm caching
- **Conditional Setup**: Allows enabling/disabling PHP or Node.js setup as needed
- **Dependency Installation**: Automatically runs `npm ci` when Node.js is set up

## Migration from Reusable Workflow

This action replaces the `basic-setup.yml` reusable workflow. The main differences:

1. **Secrets**: The `gh-bot-token` is now passed as an input instead of a secret
2. **Boolean inputs**: Must be passed as strings (`'true'`/`'false'`) instead of boolean values
3. **Usage**: Called with `uses: ./.github/actions/basic-setup` instead of `uses: ./.github/workflows/reusable/basic-setup.yml`

### Before (Reusable Workflow)
```yaml
uses: ./.github/workflows/reusable/basic-setup.yml
with:
  setup-node: true
secrets:
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```

### After (Composite Action)
```yaml
uses: ./.github/actions/basic-setup
with:
  setup-node: 'true'
  gh-bot-token: ${{ secrets.BOT_TOKEN }}
```
