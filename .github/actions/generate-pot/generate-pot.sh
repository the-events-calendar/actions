#!/usr/bin/env bash
# Generates the plugin's POT with wp-cli's make-pot. Skipped, besides the plugin's .distignore:
# shared code that has its own text domain and its own POT, which a checkout would otherwise fold
# in. That is every submodule (common, in a single plugin repository) and every tracked symlink to
# a directory outside the plugin's folder (common/ and the postcss utilities, in the monorepo). A
# link within the plugin's folder holds the plugin's own strings and is kept. All are read from the
# plugin's folder.
#
# Inputs arrive through the environment, never expanded into the source: PLUGIN_PATH, POT_PATH.
set -euo pipefail

plugin=$(cd -P "$PLUGIN_PATH" && pwd)
excludes=$(
  {
    cat "$PLUGIN_PATH/.distignore" 2>/dev/null || true
    git config --file "$PLUGIN_PATH/.gitmodules" --get-regexp '\.path$' 2>/dev/null | awk '{print $2}' || true
    { git -C "$PLUGIN_PATH" -c core.quotePath=off ls-files -s 2>/dev/null || true; } \
      | awk -F'\t' '$1 ~ /^120000 / { print $2 }' | while IFS= read -r link; do
        target=$(cd -P "$PLUGIN_PATH/$link" 2>/dev/null && pwd) || continue
        # Leading ( on each pattern: inside $(...) a bare ) closes the substitution in bash 3.2.
        case "$target/" in ("$plugin"/*) ;; (*) echo "$link" ;; esac
      done
  } | paste -sd, -
)

php -d xdebug.mode=off "$(command -v wp)" i18n make-pot "$PLUGIN_PATH" "$POT_PATH" \
  --skip-audit \
  --headers='{"Report-Msgid-Bugs-To":"https://evnt.is/191x","Last-Translator":"","Language-Team":"","PO-Revision-Date":""}' \
  --exclude="$excludes"
