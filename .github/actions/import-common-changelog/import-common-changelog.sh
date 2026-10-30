#!/usr/bin/env bash
# Copies the changelog entries common gained since the plugin's last release into the plugin's
# changelog/, so the release notes of TEC and ET name the common changes they ship. Run from the
# root of the plugin checkout, with full history and tags, before the changelog is written.
#
# The range is common's commit at the plugin's last tag up to common's commit at HEAD. Entries
# are read from common's git history rather than its changelog/, because common's own release
# deletes them once written into its changelog.md. Language and Version entries stay in common:
# they describe common's own strings and libraries.
#
# A plugin without a common submodule imports nothing and succeeds.
set -euo pipefail

path=$(git config --file .gitmodules --get submodule.common.path 2>/dev/null || true)
if [ -z "$path" ]; then
  echo "No common submodule, nothing to import."
  exit 0
fi

# Release tags only: a nearer tag such as ft-002 would shorten the range and drop entries.
if ! last_tag=$(git describe --tags --abbrev=0 --match '[0-9]*.[0-9]*.[0-9]*' HEAD 2>/dev/null); then
  echo "::error::No tag is reachable from HEAD, so the last release's common is unknown. Check out with fetch-depth: 0."
  exit 1
fi
old=$(git rev-parse "$last_tag:$path")
new=$(git rev-parse "HEAD:$path")

summary="${GITHUB_STEP_SUMMARY:-/dev/null}"
echo "## Common changelog entries since $last_tag" >> "$summary"

if [ "$old" = "$new" ]; then
  echo "common is unchanged since $last_tag, nothing to import." | tee -a "$summary"
  exit 0
fi

# Failing beats writing a changelog that silently misses the entries in the unreadable range.
for sha in "$old" "$new"; do
  if ! git -C "$path" cat-file -e "$sha^{commit}" 2>/dev/null; then
    echo "::error::common commit $sha is not in the checkout. Check out the submodules with fetch-depth: 0."
    exit 1
  fi
done

mkdir -p changelog
imported=0
while IFS= read -r file; do
  dest="changelog/common-$(basename "$file")"

  # The entry as last added or edited within the range, whether or not common has since
  # processed and deleted it.
  commit=$(git -C "$path" log -1 --diff-filter=AM --format=%H "$old..$new" -- "$file")
  content=$(git -C "$path" show "$commit:$file")

  type=$(sed -n 's/^type:[[:space:]]*//p' <<< "$content" | head -1 | tr -d "\"'" | tr '[:upper:]' '[:lower:]')
  case "$type" in
    language | version) continue ;;
  esac

  # Skip an entry the plugin's changelog already carries, written by hand as was done before
  # this step existed, or imported by an earlier run of the same preparation.
  # ponytail: matches the entry's first line only, enough for one-line and folded entries;
  # parse the YAML if escaped quotes ever make a duplicate slip through.
  first=$(sed -n 's/^entry:[[:space:]]*//p' <<< "$content" | head -1 | sed -E "s/^[\"']//; s/[\"']$//; s/\\\\\"/\"/g")
  if [ -n "$first" ] && [[ "$first" != [\|\>]* ]] \
    && grep -qsF -- "$(tr '[:lower:]' '[:upper:]' <<< "${type:0:1}")${type:1} - $first" changelog.md readme.txt; then
    echo "- skipped \`$file\`, already in the changelog" >> "$summary"
    continue
  fi
  if [ -n "$first" ] && grep -qsF -- "$first" changelog/*.yaml; then
    echo "- skipped \`$file\`, a pending entry already has it" >> "$summary"
    continue
  fi

  printf '%s\n' "$content" > "$dest"
  echo "- \`$dest\` from common \`${commit:0:8}\`" >> "$summary"
  imported=$((imported + 1))
done < <(git -C "$path" log --diff-filter=A --name-only --format= "$old..$new" -- changelog | grep '\.yaml$' | sort -u)

echo "Imported $imported common changelog entries (common ${old:0:8}..${new:0:8})."
