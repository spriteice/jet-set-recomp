#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Set a clone up to commit as the project: Claude's identity, full history, the latest origin/main
# (a sandbox's clone can be older than the remote), and, in a clone
# of this repo, the audit as commit hooks. Commits are signed by the cloud sandbox's own key, which
# GitHub shows as Verified for that identity, so this keeps that signing and says whether it's on.
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
# Every commit starts from the latest origin/main (docs/project-instructions.md, section 2), and a
# clone made from a cache can be behind it.
if git -C "$repo" remote get-url origin >/dev/null 2>&1; then
    if git -C "$repo" fetch -q origin main; then
        echo "$repo: origin/main is $(git -C "$repo" rev-parse --short origin/main); start every commit from it"
    else
        echo "$repo: could not fetch origin/main; fetch it before you commit, or you build on an outdated main" >&2
    fi
fi

# The audit runs at commit time too, where the repo has it (dream-recomp has its own checks): pre-commit
# audits the staged files, commit-msg checks the message, so a leak is stopped before a push publishes
# it (docs/project-rules.md, "Before every commit"). A hook that isn't ours is left alone and named.
install_hook() { # NAME ARGS: the hook runs audit_repo.py with ARGS from the repo's top level
    local path="$hooks/$1"
    if [ -e "$path" ] && ! grep -q "scripts/08_git_setup.sh" "$path"; then
        echo "$repo: $path isn't ours, so the audit doesn't run at commit time; make it call audit_repo.py" >&2
        return
    fi
    # shellcheck disable=SC2016  # the hook expands $(git ...) when it runs, not here
    printf '#!/usr/bin/env bash\n# Installed by scripts/08_git_setup.sh: the audit at commit time (docs/project-rules.md).\ncd "$(git rev-parse --show-toplevel)" && exec python3 scripts/audit_repo.py . %s\n' "$2" > "$path"
    chmod +x "$path"
}
if [ -f "$repo/scripts/audit_repo.py" ]; then
    hooks="$(git -C "$repo" rev-parse --git-path hooks)"
    case "$hooks" in /*) ;; *) hooks="$repo/$hooks" ;; esac
    mkdir -p "$hooks"
    install_hook pre-commit ""
    # shellcheck disable=SC2016  # $1 is the message file, expanded when the hook runs
    install_hook commit-msg '--message "$1"'
    echo "$repo: the audit runs at commit time (pre-commit and commit-msg hooks)"
fi

if [ "$(git -C "$repo" config --get commit.gpgsign || true)" = true ] &&
    [ -n "$(git -C "$repo" config --get user.signingkey || true)" ]; then
    echo "$repo: commits as Claude, signed by the sandbox"
else
    echo "$repo: commits as Claude, but this sandbox doesn't sign them, so GitHub shows them Unverified" >&2
    echo "and the audit rejects them. Say so in the review pack; don't commit until signing is on." >&2
fi
