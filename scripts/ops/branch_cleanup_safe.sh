#!/usr/bin/env bash
# Delete one already-landed candidate branch, locally and on the selected
# remote, with both deletions bound to the exact reviewed SHAs.
#
# There is no force switch.  A branch is admissible only when its tip is
# contained in the bound main of the selected remote, or when the GitHub lane
# can prove an exact-head merged pull request.  An unreadable remote is never
# treated as an absent branch, and any identity drift aborts before deletion.
set -euo pipefail

# CLEAN_BRANCH_ROOT exists so the governed rules can be exercised against an
# isolated repository in tests; it defaults to this checkout.
ROOT_DIR="${CLEAN_BRANCH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT_DIR"
CANONICAL_ALLOWED_WRITE_BRANCH_REGEX='^(feature|fix|refactor|audit|release|codex)/.+'
CONFIRMATION="DELETE_EXACT_REVIEWED_BRANCH"

branch="${1:-}"
remote="${CLEAN_BRANCH_REMOTE:-origin}"
expected_branch_sha="${EXPECTED_BRANCH_SHA:-}"
expected_main_sha="${EXPECTED_MAIN_SHA:-}"
apply="${APPLY:-0}"
confirm="${CLEAN_BRANCH_CONFIRM:-}"

if [[ -z "$branch" ]]; then
  echo "❌ CLEAN_BRANCH is required" >&2
  exit 2
fi
if [[ "$branch" == "HEAD" ]]; then
  echo "❌ detached HEAD; refusing cleanup" >&2
  exit 2
fi
if ! [[ "$branch" =~ $CANONICAL_ALLOWED_WRITE_BRANCH_REGEX ]]; then
  echo "❌ branch is outside the canonical governed prefixes (current=${branch})" >&2
  exit 2
fi
if [[ "$branch" =~ ^(main|master|release/) ]]; then
  echo "❌ refusing to delete protected branch ${branch}" >&2
  exit 2
fi
if ! [[ "$expected_branch_sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "❌ EXPECTED_BRANCH_SHA must be the full reviewed branch SHA" >&2
  exit 2
fi
if ! [[ "$expected_main_sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "❌ EXPECTED_MAIN_SHA must be the full SHA of ${remote}/main" >&2
  exit 2
fi
if [[ "$apply" == "1" && "$confirm" != "$CONFIRMATION" ]]; then
  echo "❌ APPLY=1 requires CLEAN_BRANCH_CONFIRM=${CONFIRMATION}" >&2
  exit 2
fi

if ! git show-ref --verify --quiet "refs/heads/${branch}"; then
  echo "❌ local branch not found: ${branch}" >&2
  exit 2
fi
if ! git remote get-url "$remote" >/dev/null 2>&1; then
  echo "❌ remote '${remote}' not configured" >&2
  exit 2
fi

current="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current" == "$branch" ]]; then
  echo "❌ cannot delete currently checked-out branch (${branch})" >&2
  exit 2
fi
if git worktree list --porcelain | grep -qx "branch refs/heads/${branch}"; then
  echo "❌ branch is checked out by a worktree (${branch})" >&2
  exit 2
fi

echo "[branch.cleanup.feature] reading ${remote} identity for ${branch}"
main_line="$(git ls-remote --heads "$remote" refs/heads/main)" || {
  echo "❌ cannot read ${remote}/main; refusing to judge merge state" >&2; exit 2; }
remote_line="$(git ls-remote --heads "$remote" "refs/heads/${branch}")" || {
  echo "❌ cannot read ${remote} branch ${branch}" >&2; exit 2; }

observed_main="${main_line%%$'\t'*}"
observed_remote="${remote_line%%$'\t'*}"
if [[ -z "$observed_main" ]]; then
  echo "❌ ${remote} exposes no main branch" >&2
  exit 2
fi
if [[ "$observed_main" != "$expected_main_sha" ]]; then
  echo "❌ ${remote}/main drift: expected ${expected_main_sha}, observed ${observed_main}" >&2
  exit 2
fi

local_sha="$(git rev-parse "refs/heads/${branch}")"
if [[ "$local_sha" != "$expected_branch_sha" ]]; then
  echo "❌ local SHA drift: expected ${expected_branch_sha}, observed ${local_sha}" >&2
  exit 2
fi

remote_state="present"
if [[ -z "$remote_line" ]]; then
  remote_state="absent"
elif [[ "$observed_remote" != "$expected_branch_sha" ]]; then
  echo "❌ ${remote} branch drift: expected ${expected_branch_sha}, observed ${observed_remote}" >&2
  exit 2
fi

squash_merge_verified=0
if git merge-base --is-ancestor "$expected_branch_sha" "$expected_main_sha"; then
  echo "[branch.cleanup.feature] containment check: ${expected_branch_sha} is in ${remote}/main"
else
  if [[ "$remote" != "origin" ]]; then
    echo "❌ branch is not contained in ${remote}/main ${expected_main_sha}" >&2
    exit 2
  fi
  if ! command -v gh >/dev/null 2>&1; then
    echo "❌ gh not found; cannot verify merged PR for ${branch}" >&2
    exit 2
  fi
  pr_json="$(gh pr list --state merged --head "$branch" --json headRefOid,number)" || \
    (echo "❌ gh pr list failed; network/auth required to verify merge for ${branch}" >&2; exit 2)
  pr_count="$(jq --arg sha "$expected_branch_sha" '[.[] | select(.headRefOid == $sha)] | length' <<<"$pr_json")" || \
    (echo "❌ merged PR identity parse failed for ${branch}" >&2; exit 2)
  if [[ "$pr_count" -lt 1 ]]; then
    echo "❌ branch is not contained in ${remote}/main and has no exact-head merged PR: ${branch}" >&2
    exit 2
  fi
  squash_merge_verified=1
  echo "[branch.cleanup.feature] exact-head merged PR detected for ${branch}"
fi

if [[ "$apply" != "1" ]]; then
  echo "[branch.cleanup.feature] DRY-RUN ok branch=${branch} remote=${remote} sha=${expected_branch_sha} main=${expected_main_sha} remote_state=${remote_state} squash_verified=${squash_merge_verified}"
  exit 0
fi

if [[ "$remote_state" == "present" ]]; then
  echo "[branch.cleanup.feature] deleting remote: ${remote}/${branch} (lease ${expected_branch_sha})"
  git push "--force-with-lease=refs/heads/${branch}:${expected_branch_sha}" "$remote" ":refs/heads/${branch}"
else
  echo "[branch.cleanup.feature] remote already absent: ${remote}/${branch}"
fi

echo "[branch.cleanup.feature] deleting local: ${branch} (expected ${expected_branch_sha})"
git update-ref -d "refs/heads/${branch}" "$expected_branch_sha"

echo "✅ [branch.cleanup.feature] done"
