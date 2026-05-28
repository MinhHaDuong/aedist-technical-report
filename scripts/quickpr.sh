#!/usr/bin/env bash
#
# quickpr — open a one-shot PR with auto-merge for chore work.
#
# Usage:
#   scripts/quickpr.sh "<message>" <file> [file ...]
#
# When to use:
#   Chore work scoped to tickets/, docs/, .claude/, top-level docs,
#   .github/workflows/, *.md. Single intent, no implementation code.
#
# When NOT to use:
#   - Implementation work touching src/, tests/, experiments/ — use
#     /start-ticket → /celebrate so ticket bookkeeping happens.
#   - Multi-commit work or anything needing rebase / scope-overflow review.
#
# Behavior:
#   - Branches off origin/main with a slug derived from <message>.
#   - Stages exactly the named files (refuses src/ tests/ experiments/).
#   - Commits with <message>, pushes, opens PR, enables auto-merge.
#   - Restores the starting branch on exit.
#   - Idempotent: re-runs reuse an existing branch and PR if found.
#
# Assumes:
#   - Default branch is `main`.
#   - GitHub remote is `origin`.
#   - `gh` is installed and authenticated.

set -euo pipefail

# --- args --------------------------------------------------------------------

case "${1:-}" in
    -h|--help|"")
        sed -n '3,25p' "$0" | sed 's/^# \?//'
        exit 0
        ;;
esac

if [ $# -lt 2 ]; then
    echo "usage: quickpr.sh \"<message>\" <file> [file ...]" >&2
    exit 64
fi

msg="$1"
shift
files=("$@")

# --- pre-flight --------------------------------------------------------------

if ! repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "quickpr: not in a git repository" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "quickpr: gh not authenticated (run \`gh auth login\`)" >&2
    exit 1
fi

forbidden_re='^(src|tests|experiments)/'
for f in "${files[@]}"; do
    if [ ! -e "$f" ]; then
        echo "quickpr: file does not exist: $f" >&2
        exit 1
    fi
    rel=$(realpath --relative-to="$repo_root" -- "$f")
    if [[ "$rel" =~ $forbidden_re ]]; then
        echo "quickpr: refusing — $rel touches src/tests/experiments." >&2
        echo "         Use /start-ticket → /celebrate for implementation work." >&2
        exit 1
    fi
done

starting_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$starting_branch" = "HEAD" ]; then
    echo "quickpr: detached HEAD — switch to a branch first" >&2
    exit 1
fi

# --- branch name -------------------------------------------------------------

slug=$(echo "$msg" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//' \
    | cut -c1-40)
slug="${slug:-quickpr}"
stamp=$(date -u +%Y%m%d-%H%M%S)
branch="quickpr/${slug}-${stamp}"

# --- run ---------------------------------------------------------------------

git fetch origin main --quiet

if git show-ref --verify --quiet "refs/heads/$branch"; then
    git switch --quiet "$branch"
else
    git switch --quiet -c "$branch" origin/main
fi

trap 'git switch --quiet "$starting_branch" 2>/dev/null || true' EXIT

git add -- "${files[@]}"
if git diff --cached --quiet; then
    echo "quickpr: nothing to commit — the listed files match origin/main" >&2
    exit 1
fi
git commit --quiet -m "$msg"
git push --quiet -u origin "$branch"

existing=$(gh pr list --head "$branch" --json number --jq '.[0].number' 2>/dev/null || true)
if [ -n "$existing" ]; then
    pr_number="$existing"
    pr_url=$(gh pr view "$pr_number" --json url --jq .url)
else
    pr_url=$(gh pr create --title "$msg" --body "Opened via scripts/quickpr.sh.")
    pr_number="${pr_url##*/}"
fi

if ! gh pr merge "$pr_number" --merge --delete-branch --auto >/dev/null 2>&1; then
    echo "quickpr: auto-merge could not be enabled — review the PR manually" >&2
fi

echo "$pr_url"
