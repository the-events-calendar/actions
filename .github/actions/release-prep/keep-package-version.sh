#!/usr/bin/env bash
# Writes a four-part release, such as the 5.30.3.1 security release, to package.json as 5.30.3+1.
#
# pup writes the release version into every .puprc paths.versions file, package.json included, and
# npm only takes semver: wp-scripts build fails on "version": "5.30.3.1". The toolbox runs pup and
# commits with git add --all in one action, so this runs before it: it writes the semver form, the
# fourth part as build metadata (5.30.3+1, which npm reads as 5.30.3), stages it, and marks
# package.json skip-worktree, which git add --all leaves alone. The toolbox then commits this version
# and not the one pup writes over it.
#
# Reads VERSION. A three-part version, or a repository without a tracked package.json, is left to pup.
# tests/test-keep-package-version.py tests it.

set -euo pipefail

if ! [[ "${VERSION:-}" =~ ^([0-9]+\.[0-9]+\.[0-9]+)\.([0-9]+)$ ]]; then
  exit 0
fi
export SEMVER="${BASH_REMATCH[1]}+${BASH_REMATCH[2]}"

if ! git ls-files --error-unmatch package.json > /dev/null 2>&1; then
  exit 0
fi

# The first "version" key only, as pup replaces: the changelogger section has a "version" type too.
perl -0pi -e 's/("version"\s*:\s*")[^"]+/${1}$ENV{SEMVER}/' package.json
git add package.json
git update-index --skip-worktree package.json

echo "package.json gets $SEMVER: npm does not take the four-part $VERSION." >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
