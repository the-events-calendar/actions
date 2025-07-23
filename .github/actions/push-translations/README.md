# Push Translations Action

A composite action that pushes POT (Portable Object Template) files to the StellarWP translation service and imports them into GlotPress for translation management. This action automates the deployment of translation templates to make them available for translators.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `plugin_slug` | Plugin slug identifier for the translation system | Yes | - |
| `pot_path` | Path to the POT file to upload | Yes | - |

## Outputs

| Output | Description | Type |
|--------|-------------|------|
| `glotpress-result` | Result from GlotPress import operation | String |

## Environment Variables Required

This action requires the following environment variables to be set:

| Variable | Description |
|----------|-------------|
| `TRANSLATIONS_DEPLOY_HOST` | Hostname of the translation server |
| `TRANSLATIONS_DEPLOY_USER` | SSH username for the translation server |
| `TRANSLATIONS_DEPLOY_SSH_KEY` | SSH private key for authentication |
| `TRANSLATIONS_DEPLOY_POT_LOCATION` | Target directory path on the translation server |

## Usage

### Basic usage

```yaml
- name: Push POT file to translation service
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
  env:
    TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
    TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
    TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### Complete translation workflow

```yaml
name: Translation Deployment
on:
  push:
    branches: [main]
    paths: ['languages/*.pot']

jobs:
  deploy-translations:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate POT file
        uses: the-events-calendar/actions/.github/actions/generate-pot@main
        with:
          plugin_path: ./
          pot_path: ./languages/the-events-calendar.pot

      - name: Push to translation service
        id: push
        uses: the-events-calendar/actions/.github/actions/push-translations@main
        with:
          plugin_slug: the-events-calendar
          pot_path: ./languages/the-events-calendar.pot
        env:
          TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
          TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
          TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
          TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

      - name: Display import results
        run: echo "GlotPress import result: ${{ steps.push.outputs.glotpress-result }}"
```

### Multi-plugin deployment

```yaml
strategy:
  matrix:
    plugin:
      - slug: the-events-calendar
        pot: ./plugins/the-events-calendar/languages/the-events-calendar.pot
      - slug: events-pro
        pot: ./plugins/events-pro/languages/events-pro.pot
      - slug: event-tickets
        pot: ./plugins/event-tickets/languages/event-tickets.pot

steps:
  - name: Push ${{ matrix.plugin.slug }} translations
    uses: the-events-calendar/actions/.github/actions/push-translations@main
    with:
      plugin_slug: ${{ matrix.plugin.slug }}
      pot_path: ${{ matrix.plugin.pot }}
    env:
      TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
      TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
      TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
      TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}
```

### With error handling and notifications

```yaml
- name: Push translations with error handling
  id: push-translations
  continue-on-error: true
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
  env:
    TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
    TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
    TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

- name: Handle translation deployment failure
  if: steps.push-translations.outcome == 'failure'
  run: |
    echo "Translation deployment failed. Notifying team..."
    # Add notification logic here

- name: Notify translators of new strings
  if: steps.push-translations.outcome == 'success'
  run: |
    echo "New translation strings available!"
    echo "Import result: ${{ steps.push-translations.outputs.glotpress-result }}"
```

## Features

### Secure Deployment
- **SSH Authentication**: Uses SSH keys for secure server access
- **rsync Transfer**: Efficient and reliable file transfer with rsync
- **Temporary Files**: Automatic cleanup of temporary processing files

### GlotPress Integration
- **Automatic Import**: Directly imports POT files into GlotPress
- **Build Tracking**: Generates unique build IDs for tracking deployments
- **Result Reporting**: Provides detailed feedback on import status

### Process Management
- **Unique Identifiers**: Creates unique build UUIDs to prevent conflicts
- **Step Summary**: Displays progress and results in GitHub Actions UI
- **Error Handling**: Robust error handling and cleanup procedures

## Deployment Process

### 1. Build ID Generation
Creates a unique identifier based on:
- Git commit SHA
- Current timestamp
- MD5 hash for uniqueness

### 2. File Transfer
- Uses rsync with optimized flags for WordPress deployments
- Preserves file integrity during transfer
- Handles network interruptions gracefully

### 3. GlotPress Import
- Connects to translation server via SSH
- Executes WP-CLI commands to import POT files
- Captures import results for verification

### 4. Result Processing
- Fetches import results from temporary output files
- Displays results in GitHub Actions summary
- Cleans up temporary files to prevent accumulation

## Server Requirements

### Translation Server Setup
The target server must have:
- **SSH Access**: Configured SSH daemon with key authentication
- **WordPress Installation**: With GlotPress plugin installed
- **WP-CLI**: Installed and configured for GlotPress commands
- **Web Server**: Accessible for result retrieval

### File Structure
```text
translations.stellarwp.com/
├── html/
│   ├── bot-output/          # Temporary result files
│   └── wp-config.php        # WordPress configuration
└── pot-files/
    └── tec/                 # POT file storage
        ├── plugin1.pot
        └── plugin2.pot
```

## Security Considerations

### SSH Key Management
- Use dedicated SSH keys for deployment
- Rotate keys regularly
- Limit key permissions to deployment operations only
- Store keys securely in GitHub Secrets

### Server Access
- Restrict SSH access to deployment users only
- Use fail2ban or similar for intrusion prevention
- Monitor deployment logs for unusual activity
- Implement IP whitelisting where possible

### File Permissions
- Ensure proper file permissions on uploaded POT files
- Limit write access to necessary directories only
- Use dedicated user accounts for deployment

## Troubleshooting

### Common Issues

#### SSH Connection Failed
```
Error: Permission denied (publickey)
```
**Solutions**:
- Verify SSH key is correctly configured in secrets
- Check that the key matches the server configuration
- Ensure the SSH key has proper permissions
- Verify the hostname and user are correct

#### rsync Transfer Failed
```
Error: rsync failed with exit code 1
```
**Solutions**:
- Check network connectivity to the server
- Verify the remote path exists and is writable
- Ensure rsync is installed on both systems
- Check file permissions on source and destination

#### GlotPress Import Failed
```
Error: WP-CLI command failed
```
**Solutions**:
- Verify WP-CLI is installed and accessible
- Check that GlotPress plugin is active
- Ensure the plugin slug exists in GlotPress
- Review WordPress error logs for details

#### Result Retrieval Failed
```
Error: Could not fetch import results
```
**Solutions**:
- Check web server configuration
- Verify the bot-output directory is web-accessible
- Ensure proper file permissions on output files
- Check for web server restrictions

### Debug Mode

Enable debugging by adding diagnostic steps:

```yaml
- name: Debug server connectivity
  run: |
    echo "Testing SSH connection..."
    ssh -o StrictHostKeyChecking=no ${{ env.TRANSLATIONS_DEPLOY_USER }}@${{ env.TRANSLATIONS_DEPLOY_HOST }} "pwd && ls -la"

- name: Push translations with debug
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
  env:
    TRANSLATIONS_DEPLOY_HOST: ${{ secrets.TRANSLATIONS_HOST }}
    TRANSLATIONS_DEPLOY_USER: ${{ secrets.TRANSLATIONS_USER }}
    TRANSLATIONS_DEPLOY_SSH_KEY: ${{ secrets.TRANSLATIONS_SSH_KEY }}
    TRANSLATIONS_DEPLOY_POT_LOCATION: ${{ secrets.TRANSLATIONS_POT_LOCATION }}

- name: Debug GlotPress status
  run: |
    ssh ${{ env.TRANSLATIONS_DEPLOY_USER }}@${{ env.TRANSLATIONS_DEPLOY_HOST }} \
    "cd translations.stellarwp.com/html && wp glotpress project list"
```

## Integration Examples

### With Conditional Deployment
```yaml
- name: Check for POT changes
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      pot:
        - 'languages/*.pot'

- name: Deploy only if POT changed
  if: steps.changes.outputs.pot == 'true'
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
```

### With Slack Notifications
```yaml
- name: Push translations
  id: push
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot

- name: Notify Slack
  if: steps.push.outcome == 'success'
  uses: 8398a7/action-slack@v3
  with:
    status: custom
    custom_payload: |
      {
        text: "New translation strings deployed for my-plugin",
        attachments: [{
          color: "good",
          fields: [{
            title: "Import Result",
            value: "${{ steps.push.outputs.glotpress-result }}",
            short: false
          }]
        }]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

## Best Practices

### Deployment Timing
- Deploy translations after successful builds
- Coordinate with translation team schedules
- Avoid deployments during active translation sessions
- Use staging environments for testing

### Version Control
- Commit POT files to track string changes
- Tag releases to correlate with translation deployments
- Document significant string changes in release notes
- Use branching strategies that support translation workflows

### Quality Assurance
- Validate POT files before deployment
- Test import process in staging environment
- Monitor import results for errors or warnings
- Implement rollback procedures for failed deployments

### Team Communication
- Notify translators of new string deployments
- Provide context for significant string changes
- Establish clear timelines for translation completion
- Use translation management tools for coordination

## Performance Optimization

### Large POT Files
For plugins with many translatable strings:
- Compress POT files before transfer
- Use incremental transfers when possible
- Implement parallel processing for multiple plugins
- Monitor transfer times and optimize as needed

### Frequent Deployments
- Implement caching for unchanged POT files
- Use conditional deployment based on file changes
- Batch multiple plugin deployments
- Schedule deployments during off-peak hours

```yaml
# Conditional deployment example
- name: Check POT file hash
  id: pot-hash
  run: |
    CURRENT_HASH=$(md5sum ./languages/my-plugin.pot | cut -d' ' -f1)
    STORED_HASH=$(curl -s https://translations.stellarwp.com/api/pot-hash/my-plugin || echo "")
    if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
      echo "needs-deployment=true" >> $GITHUB_OUTPUT
    else
      echo "needs-deployment=false" >> $GITHUB_OUTPUT
    fi

- name: Deploy only if changed
  if: steps.pot-hash.outputs.needs-deployment == 'true'
  uses: the-events-calendar/actions/.github/actions/push-translations@main
  with:
    plugin_slug: my-plugin
    pot_path: ./languages/my-plugin.pot
``` 