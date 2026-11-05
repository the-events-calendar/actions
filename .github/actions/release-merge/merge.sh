#!/usr/bin/env bash
# Merges a release branch into the base branch through the GitHub API, then, when DEVELOP is set,
# the base back into it.
#
# The branch arrives prepared: release prep bumped every version file. VERSION only names the tag,
# so no file is checked against it. A four-part release keeps package.json on three parts
# (keep-package-version.sh), which a file check would refuse.
#
# Merges HEAD, the commit the run started on, not the branch by name: a push after the run started
# is refused rather than merged unreviewed. A tag VERSION that does not hold the branch is an earlier
# release of the same version, and refused; one that holds it is a run repeated after a late failure.
# A branch already in the base merges as a no-op, so a repeated run passes.
#
# Reads BRANCH, HEAD, VERSION, BASE, DEVELOP, GH_TOKEN, GITHUB_REPOSITORY and GITHUB_OUTPUT.
# tests/test-release-merge.py tests it.

set -euo pipefail

fail() {
  echo "::error::$1 Nothing was merged."
  exit 1
}

api() {
  gh api "repos/${GITHUB_REPOSITORY}/$1" "${@:2}"
}

# Merges $2 into $1 and sets merged to the merge commit, or to nothing when $1 already holds $2.
# A variable, not printed: fail inside a $(...) would exit the subshell and lose its message.
merge() {
  local out
  if ! out=$(gh api -X POST "repos/${GITHUB_REPOSITORY}/merges" -f base="$1" -f head="$2" \
    -f commit_message="$3" --jq '.sha // empty' 2>&1); then
    case "$out" in
      *"Merge conflict"* | *"HTTP 409"*) fail "$4 conflicts with $1. Merge $1 into $4, then start the run again." ;;
      *) fail "Merging $4 into $1 failed: $out" ;;
    esac
  fi
  merged="$out"
}

if ! [[ "${VERSION:-}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
  fail "'${VERSION:-}' is not a version: three or four numeric parts, e.g. 6.18.3 or 6.18.2.1."
fi
for name in "$BRANCH" "$BASE" ${DEVELOP:+"$DEVELOP"}; do
  if ! [[ "$name" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ "$name" == refs/* ]]; then
    fail "'$name' is not a branch name."
  fi
done
if [ "$BRANCH" = "$BASE" ] || [ "$BRANCH" = "${DEVELOP:-}" ] || [ "$BASE" = "${DEVELOP:-}" ]; then
  fail "branch, base-branch and develop-branch have to be three branches."
fi
if [ -n "${HEAD:-}" ] && ! [[ "$HEAD" =~ ^[0-9a-f]{40}$ ]]; then
  fail "head '$HEAD' is not a full commit hash."
fi

tip=$(api "git/ref/heads/${BRANCH}" --jq .object.sha)
if [ -n "${HEAD:-}" ] && [ "$HEAD" != "$tip" ]; then
  fail "$BRANCH is at $tip, not at $HEAD, the commit this run started on: it moved after the run started. Start the run again on the branch as it is now."
fi

if api "git/ref/tags/${VERSION}" --silent 2> /dev/null; then
  status=$(api "compare/${VERSION}...${tip}" --jq .status)
  if [ "$status" != behind ] && [ "$status" != identical ]; then
    fail "The tag $VERSION already exists and does not hold $BRANCH: $VERSION was released before. Release another version."
  fi
fi

merge "$BASE" "$tip" "Merge branch '${BRANCH}' into ${BASE}" "$BRANCH"
base_sha="$merged"
if [ -z "$base_sha" ]; then
  base_sha=$(api "git/ref/heads/${BASE}" --jq .object.sha)
  echo "$BASE already holds $BRANCH: nothing to merge."
fi

if [ -n "${DEVELOP:-}" ]; then
  merge "$DEVELOP" "$base_sha" "Merge branch '${BASE}' into ${DEVELOP}" "$BASE"
fi

{
  echo "version=${VERSION}"
  echo "branch=${BRANCH}"
  echo "base-sha=${base_sha}"
} >> "$GITHUB_OUTPUT"
