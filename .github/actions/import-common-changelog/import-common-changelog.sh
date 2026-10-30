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

# The newest release tag reachable from HEAD, matched on the whole name: a tag such as ft-002 or
# 6.18.3-rc1 would shorten the range and drop the entries before it.
last_tag=$(git tag --merged HEAD | { grep -E '^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$' || true; } | sort -V | tail -1)
if [ -z "$last_tag" ]; then
  echo "::error::No release tag is reachable from HEAD, so the last release's common is unknown. Check out with fetch-depth: 0."
  exit 1
fi
# Two release branches open at once: the newer one does not contain the older one's tag until it
# is merged in, so the range starts a release early and the older release's entries come again.
newest_tag=$(git tag | { grep -E '^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$' || true; } | sort -V | tail -1)
if [ "$newest_tag" != "$last_tag" ]; then
  echo "::warning::The newest release tag is $newest_tag, but HEAD only contains $last_tag. If this branch should carry $newest_tag, merge it in first, or its common entries are imported again."
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

# An entry's identity: its type and its text, whitespace removed, so the folded YAML of an entry
# and its one line in changelog.md compare equal, and a different entry never does.
entry_key() {
  local type text
  type=$(sed -n 's/^type:[[:space:]]*//p' <<< "$1" | head -1 | tr -d "\"'[:space:]")
  text=$(awk 'f && /^[A-Za-z_]+:/ { exit } /^entry:/ { f = 1; sub(/^entry:[ \t]*/, "") } f' <<< "$1")
  # A block scalar's indicator (| or >-) is on the entry line, the text below it.
  if [[ "${text%%$'\n'*}" =~ ^[\|\>][-+0-9]*$ ]]; then
    text=${text#*$'\n'}
  fi
  text=$(tr -d '[:space:]' <<< "$text")
  case "$text" in
    \"*\") text=${text:1:${#text}-2}; text=${text//\\\"/\"}; text=${text//\\\\/\\} ;;
    \'*\') text=${text:1:${#text}-2}; text=${text//\'\'/\'} ;;
  esac
  printf '%s-%s\n' "$(tr '[:lower:]' '[:upper:]' <<< "${type:0:1}")${type:1}" "$text"
}

# Every entry the plugin already carries: written in changelog.md or readme.txt, by hand as was
# done before this step existed or by an earlier run of the same preparation, or still pending.
known=$(mktemp)
sed -nE 's/^\* ([A-Za-z]+) - (.*)$/\1-\2/p' changelog.md readme.txt 2>/dev/null | tr -d ' \t\r' > "$known" || true
for pending in changelog/*.yaml; do
  [ -f "$pending" ] && entry_key "$(cat "$pending")" >> "$known"
done

mkdir -p changelog
imported=0
# Each time a file was added, not each path: common's release deletes its entries, so a later
# entry can reuse the filename of one already released within the range.
while read -r added; do
  while IFS= read -r file; do
    # The entry as it stood when common's release deleted it, or as it stands at HEAD.
    deleted=$(git -C "$path" log --reverse --full-history --diff-filter=D --format=%H "$added..$new" -- "$file" | awk 'NR == 1')
    if [ -n "$deleted" ]; then
      # Only common's release deletes an entry while writing changelog.md. Any other deletion, a
      # revert or an entry dropped in review, means the change never shipped.
      if ! git -C "$path" diff-tree --no-commit-id --name-only -r "$deleted" | grep -qx 'changelog.md'; then
        echo "- skipped \`$file\` from common \`${added:0:8}\`, deleted in \`${deleted:0:8}\` by something other than a release" >> "$summary"
        continue
      fi
      content=$(git -C "$path" show "$deleted^:$file")
    else
      content=$(git -C "$path" show "$new:$file")
    fi

    type=$(sed -n 's/^type:[[:space:]]*//p' <<< "$content" | head -1 | tr -d "\"'" | tr '[:upper:]' '[:lower:]')
    case "$type" in
      language | version) continue ;;
    esac

    key=$(entry_key "$content")
    if grep -qxF -- "$key" "$known"; then
      echo "- skipped \`$file\` from common \`${added:0:8}\`, the plugin already has it" >> "$summary"
      continue
    fi
    echo "$key" >> "$known"

    name=$(basename "$file" .yaml)
    dest="changelog/common-$name-${added:0:8}.yaml"
    printf '%s\n' "$content" > "$dest"
    echo "- \`$dest\` from common \`${added:0:8}\`" >> "$summary"
    imported=$((imported + 1))
  done < <(git -C "$path" diff-tree --no-commit-id --name-only -r --diff-filter=A "$added" -- changelog | { grep '\.yaml$' || true; })
# --full-history: with a path limit, git follows only the first parent of a merge whose changelog/
# matches it, which is a merged release branch that added its entries and then deleted them.
done < <(git -C "$path" log --reverse --full-history --diff-filter=A --format=%H "$old..$new" -- changelog)
rm -f "$known"

echo "Imported $imported common changelog entries (common ${old:0:8}..${new:0:8})."
