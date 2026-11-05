#!/usr/bin/env bash
# Set a clone up to commit as the project: Claude's identity and full history. Commits are signed by
# the cloud sandbox's own key, which GitHub shows as Verified for that identity, so this keeps that
# signing and says whether it's on.
#
#   scripts/08_git_setup.sh [REPO]     (REPO defaults to this checkout; run it for dream-recomp too)
set -euo pipefail

repo="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
git -C "$repo" rev-parse --git-dir >/dev/null

git -C "$repo" config user.name Claude
git -C "$repo" config user.email noreply@anthropic.com
# An older version of this script set its own signing key here, which would override the sandbox's.
for key in gpg.format gpg.ssh.program user.signingkey commit.gpgsign; do
    git -C "$repo" config --local --unset "$key" || true
done

if [ "$(git -C "$repo" rev-parse --is-shallow-repository)" = true ]; then
    git -C "$repo" fetch -q --unshallow || echo "could not fetch full history: git log -L will be incomplete" >&2
fi

if [ "$(git -C "$repo" config --get commit.gpgsign || true)" = true ] &&
    [ -n "$(git -C "$repo" config --get user.signingkey || true)" ]; then
    echo "$repo: commits as Claude, signed by the sandbox"
else
    echo "$repo: commits as Claude, but this sandbox doesn't sign them, so GitHub shows them Unverified" >&2
    echo "and the audit rejects them. Say so in the review pack; don't commit until signing is on." >&2
fi
