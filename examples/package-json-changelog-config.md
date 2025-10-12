# package.json Changelog Configuration Examples

This document shows how each TEC plugin should configure their changelog URL in their `package.json` file.

## The Events Calendar

Add to `package.json`:
```json
{
  "name": "the-events-calendar",
  "version": "6.14.0",
  "tec": {
    "changelog_url": "https://theeventscalendar.com/category/release-notes/"
  },
  "dependencies": {...}
}
```

## Event Tickets

Add to `package.json`:
```json
{
  "name": "event-tickets",
  "version": "5.10.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5t"
  },
  "dependencies": {...}
}
```

## Events Pro

Add to `package.json`:
```json
{
  "name": "events-pro",
  "version": "6.14.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5p"
  },
  "dependencies": {...}
}
```

## Event Tickets Plus

Add to `package.json`:
```json
{
  "name": "event-tickets-plus",
  "version": "5.10.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5e"
  },
  "dependencies": {...}
}
```

## Events Community

Add to `package.json`:
```json
{
  "name": "events-community",
  "version": "4.10.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5c"
  },
  "dependencies": {...}
}
```

## Events Filter Bar

Add to `package.json`:
```json
{
  "name": "events-filterbar",
  "version": "5.6.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5f"
  },
  "dependencies": {...}
}
```

## Events Eventbrite

Add to `package.json`:
```json
{
  "name": "events-eventbrite",
  "version": "4.8.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5b"
  },
  "dependencies": {...}
}
```

## Tribe Common

Add to `package.json`:
```json
{
  "name": "tribe-common",
  "version": "4.18.0",
  "tec": {
    "changelog_url": "https://evnt.is/1b5m"
  },
  "dependencies": {...}
}
```

## Configuration Notes

- The `tec.changelog_url` should be placed in the `tec` section of the `package.json` file
- Each plugin should use their specific changelog URL
- If no `tec.changelog_url` is configured, the action will fall back to the parameter value or default
- The configuration is checked every time the changelog processing script runs
- URLs should point to the plugin's specific changelog page on the website
- This approach avoids conflicts with pup's `.puprc` configuration schema
