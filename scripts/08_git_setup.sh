#!/usr/bin/env bash
# Set a clone up to commit as the project: the spriteice identity, full history, and, when the
# environment holds the signing key, signed commits that GitHub shows as Verified.
#
#   scripts/08_git_setup.sh [REPO]     (REPO defaults to this checkout; run it for dream-recomp too)
#
# JSR_SIGNING_KEY is the base64 of a signing-only SSH private key, registered on GitHub as a Signing
# Key. Without it, commits aren't signed with the project's key,
# and this says so.
set -euo pipefail

repo="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
git -C "$repo" rev-parse --git-dir >/dev/null

git -C "$repo" config user.name spriteice
git -C "$repo" config user.email 62098029+spriteice@users.noreply.github.com

if [ "$(git -C "$repo" rev-parse --is-shallow-repository)" = true ]; then
    git -C "$repo" fetch -q --unshallow || echo "could not fetch full history: git log -L will be incomplete" >&2
fi

if [ -n "${JSR_SIGNING_KEY:-}" ]; then
    key="${JSR_SIGNING_KEY_FILE:-$HOME/.ssh/jsr_signing}"
    mkdir -p "$(dirname "$key")"
    (umask 077 && printf '%s' "$JSR_SIGNING_KEY" | base64 -d > "$key")
    ssh-keygen -y -f "$key" >/dev/null || { echo "JSR_SIGNING_KEY isn't a valid SSH private key" >&2; exit 1; }
    git -C "$repo" config gpg.format ssh
    # A harness may set its own signing program globally; this key is signed with plain ssh-keygen.
    git -C "$repo" config gpg.ssh.program ssh-keygen
    git -C "$repo" config user.signingkey "$key"
    git -C "$repo" config commit.gpgsign true
    echo "$repo: commits as spriteice, signed"
else
    echo "$repo: commits as spriteice, not signed with the project key (no JSR_SIGNING_KEY), so GitHub shows them Unverified"
fi
