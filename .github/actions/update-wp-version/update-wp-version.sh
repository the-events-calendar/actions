#!/usr/bin/env bash
# Sets "Tested up to" in readme.txt and, when asked, "Requires at least" two minor versions
# behind it in readme.txt and the plugin file. Run from the root of the plugin checkout.
#
# Both inputs arrive through the environment, never expanded into the source, so a dispatch
# input is data: TESTED_UP_TO (e.g. 6.8.1) and UPDATE_MIN_VERSION (yes or no).
set -e

TESTED_VERSION="$TESTED_UP_TO"

# No zero-padded parts: bash arithmetic reads 010 as octal 8.
if ! [[ "$TESTED_VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?$ ]]; then
  echo "::error::tested_up_to must look like 6.8 or 6.8.1, got '$TESTED_VERSION'."
  exit 1
fi

IFS='.' read -r -a tested_parts <<< "$TESTED_VERSION"

# Two minor versions behind, major.minor only. WordPress publishes no mapping
# from x.0 back into the previous major, so refuse rather than derive one.
MIN_VERSION=""
if [ "$UPDATE_MIN_VERSION" = "yes" ]; then
  min_major=$((tested_parts[0]))
  min_minor=$((tested_parts[1] - 2))
  if [ "$min_minor" -lt 0 ]; then
    echo "::error::Cannot derive a minimum version two minors behind $TESTED_VERSION; set it by hand."
    exit 1
  fi
  MIN_VERSION="$min_major.$min_minor"
  echo "MIN_VERSION=$MIN_VERSION" >> $GITHUB_OUTPUT
fi

echo "## Version Updates" >> $GITHUB_STEP_SUMMARY
echo "* Tested Up To: \`$TESTED_VERSION\`" >> $GITHUB_STEP_SUMMARY

if [ "$UPDATE_MIN_VERSION" = "yes" ]; then
  echo "* Minimum Required Version: \`$MIN_VERSION\`" >> $GITHUB_STEP_SUMMARY
else
  echo "* Minimum Required Version: Unchanged" >> $GITHUB_STEP_SUMMARY
fi

# Update readme.txt
if [ -f "readme.txt" ]; then
  sed -i "s/Tested up to: [0-9.]*/Tested up to: $TESTED_VERSION/" readme.txt
  if [ "$UPDATE_MIN_VERSION" = "yes" ]; then
    sed -i "s/Requires at least: [0-9.]*/Requires at least: $MIN_VERSION/" readme.txt
  fi
  echo "* Updated \`readme.txt\`" >> $GITHUB_STEP_SUMMARY
fi

# Update plugin.php if minimum version is being updated
if [ "$UPDATE_MIN_VERSION" = "yes" ]; then
  # Get plugin file from .puprc versions array that is a PHP file in the base directory
  PLUGIN_FILE=$(jq -r '.paths.versions[] | select(.file | test("^[^/]+\\.php$")) | .file' .puprc)

  if [ -f "$PLUGIN_FILE" ]; then
    sed -i "s/Requires at least: [0-9.]*/Requires at least: $MIN_VERSION/" "$PLUGIN_FILE"
    echo "* Updated \`$PLUGIN_FILE\`" >> $GITHUB_STEP_SUMMARY
  fi
fi
