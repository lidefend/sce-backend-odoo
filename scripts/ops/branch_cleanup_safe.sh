#!/usr/bin/env bash
# Delete one already-landed candidate branch, locally and on the selected
# remote, with both deletions bound to the exact reviewed SHAs.
#
# There is no force switch.  A branch is admissible only when its tip is
# contained in the bound main of the selected remote, or when the GitHub lane
# can prove an exact-head merged pull request.  It is additionally refused while
# that main still binds the branch in .agent/active-runs.json, so retiring a
# branch can never silently leave a dangling run binding behind.  An unreadable
# remote is never treated as an absent branch, and any identity drift aborts
# before deletion.
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

merged_pr_number=""
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
  merged_pr_number="$(jq -r --arg sha "$expected_branch_sha" '.[] | select(.headRefOid == $sha) | .number' <<<"$pr_json" | head -n 1)"
  if ! [[ "$merged_pr_number" =~ ^[0-9]+$ ]]; then
    echo "❌ merged PR number is invalid for ${branch}" >&2
    exit 2
  fi
  squash_merge_verified=1
  echo "[branch.cleanup.feature] exact-head merged PR detected for ${branch}"
fi

# A run-index binding left on the selected remote's main dangles when this branch
# is deleted. Product branches must clear that binding in an ordinary merged PR.
# A bookkeeping-only cleanup branch may instead retire its own exact-head merged
# binding; otherwise each cleanup would require another recursively bound
# cleanup PR. The exception is limited to a P4 run and a PR whose complete diff
# stays inside governed ledger, documentation and operations paths.
if ! git cat-file -e "${expected_main_sha}^{commit}" 2>/dev/null; then
  git fetch --quiet "$remote" main >/dev/null 2>&1 || true
fi
if ! git cat-file -e "${expected_main_sha}^{commit}" 2>/dev/null; then
  echo "❌ cannot read ${remote}/main ${expected_main_sha} locally; refusing to retire without the binding check" >&2
  exit 2
fi
if git cat-file -e "${expected_main_sha}:.agent/active-runs.json" 2>/dev/null; then
  if ! bound_run_path="$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(3)
if not isinstance(data, dict):
    sys.exit(3)
branches = data.get("branches")
if not isinstance(branches, dict):
    sys.exit(3)
path = branches.get(sys.argv[1], "")
if path and (not isinstance(path, str) or not path.startswith(".agent/runs/")):
    sys.exit(3)
print(path)
' "$branch" 2>/dev/null <<<"$(git show "${expected_main_sha}:.agent/active-runs.json")")"; then
    echo "❌ cannot parse the active-run binding for ${branch}" >&2
    exit 2
  fi
  if [[ -z "$bound_run_path" ]]; then
    echo "[branch.cleanup.feature] binding check: ${remote}/main does not bind ${branch}"
  else
    if [[ "$squash_merge_verified" != "1" || -z "$merged_pr_number" ]]; then
      echo "❌ ${remote}/main still binds ${branch} in .agent/active-runs.json" >&2
      echo "   only an exact merged bookkeeping PR may retire its own binding" >&2
      exit 2
    fi
    if ! bound_run="$(git show "${expected_main_sha}:${bound_run_path}" 2>/dev/null)"; then
      echo "❌ active binding points to an unreadable run: ${bound_run_path}" >&2
      exit 2
    fi
    if ! bound_goal_path="$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(3)
goal = data.get("goal")
if not isinstance(goal, str) or not goal.startswith(".agent/goals/"):
    sys.exit(3)
print(goal)
' <<<"$bound_run")"; then
      echo "❌ active binding has no valid P4 goal path: ${bound_run_path}" >&2
      exit 2
    fi
    if ! bound_goal="$(git show "${expected_main_sha}:${bound_goal_path}" 2>/dev/null)"; then
      echo "❌ active binding points to an unreadable goal: ${bound_goal_path}" >&2
      exit 2
    fi
    if ! python3 -c '
import json
import sys
import yaml

branch, run_path, goal_text = sys.argv[1:4]
try:
    run = json.load(sys.stdin)
    goal = yaml.safe_load(goal_text) or {}
except Exception:
    sys.exit(3)
if run.get("schema_version") != 1 or run.get("branch") != branch:
    sys.exit(4)
if run.get("status") not in {"pending_merge_decision", "completed"}:
    sys.exit(5)
scope = run.get("scope")
if not isinstance(scope, list) or not scope or not all(isinstance(path, str) for path in scope):
    sys.exit(6)
body = goal.get("goal") if isinstance(goal, dict) else None
if not isinstance(body, dict) or body.get("formal_product_layer") != "P4":
    sys.exit(7)
allowed = (".agent/", "docs/", "scripts/ops/", "make/")
if not all(path.startswith(allowed) for path in scope):
    sys.exit(8)
if run_path != ".agent/runs/" + str(run.get("id") or "") + "/run.json":
    sys.exit(9)
' "$branch" "$bound_run_path" "$bound_goal" <<<"$bound_run"; then
      echo "❌ ${remote}/main binding is not eligible for bookkeeping self-retirement: ${bound_run_path}" >&2
      echo "   require a P4 run, governed paths only and pending/completed state" >&2
      exit 2
    fi
    if ! merged_pr_files="$(gh pr view "$merged_pr_number" --json files,headRefOid)"; then
      echo "❌ cannot read merged PR #${merged_pr_number} files; refusing self-retirement" >&2
      exit 2
    fi
    if ! jq -e --arg sha "$expected_branch_sha" '
      .headRefOid == $sha
      and (.files | length) > 0
      and all(.files[].path;
        startswith(".agent/")
        or startswith("docs/")
        or startswith("scripts/ops/")
        or startswith("make/"))
    ' <<<"$merged_pr_files" >/dev/null; then
      echo "❌ merged PR #${merged_pr_number} is not a bookkeeping-only cleanup" >&2
      exit 2
    fi
    echo "[branch.cleanup.feature] binding check: exact merged bookkeeping PR may retire its own run"
  fi
else
  echo "[branch.cleanup.feature] binding check: ${remote}/main carries no run index"
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
