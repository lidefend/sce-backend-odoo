#!/usr/bin/env bash
set -euo pipefail

readonly ALLOWED_BRANCH_REGEX="${CANONICAL_ALLOWED_WRITE_BRANCH_REGEX:-^(feature|fix|refactor|audit|release|codex)/.+}"
readonly REQUIRE_CLEAN="${CODEX_PREFLIGHT_REQUIRE_CLEAN:-0}"
readonly REQUIRE_DOCKER="${CODEX_PREFLIGHT_REQUIRE_DOCKER:-0}"

repo_root="$(git rev-parse --show-toplevel)"
current_dir="$(pwd -P)"
canonical_root="$(cd "$repo_root" && pwd -P)"
branch="$(git branch --show-current)"
full_sha="$(git rev-parse HEAD)"
short_sha="$(git rev-parse --short HEAD)"

echo "CODEX PREFLIGHT"
echo "PWD: ${current_dir}"
echo "REPOSITORY_ROOT: ${canonical_root}"
echo "BRANCH: ${branch}"
echo "SHA: ${short_sha}"
echo "FULL_SHA: ${full_sha}"

if [[ "$current_dir" != "$canonical_root" ]]; then
  echo "FAIL: command must run from repository root"
  exit 1
fi

if [[ -z "$branch" ]] || [[ ! "$branch" =~ $ALLOWED_BRANCH_REGEX ]]; then
  echo "FAIL: branch is not an allowed write branch"
  echo "ALLOWED_BRANCH_REGEX: ${ALLOWED_BRANCH_REGEX}"
  exit 1
fi
echo "OK: allowed write branch"

python3 scripts/verify/agent_context_lint.py
python3 scripts/verify/agent_context_verify.py
echo "OK: agent engineering context"

if [[ "$REQUIRE_DOCKER" == "1" ]]; then
  if ! docker ps >/dev/null 2>&1; then
    echo "FAIL: docker ps failed"
    exit 1
  fi
  echo "OK: docker ps"
else
  echo "INFO: docker check not required for this preflight mode"
fi

status="$(git status --porcelain --untracked-files=all)"
tracked_diff_sha="$(git diff --binary --no-ext-diff | sha256sum | awk '{print $1}')"
staged_diff_sha="$(git diff --cached --binary --no-ext-diff | sha256sum | awk '{print $1}')"
untracked_manifest_sha="$({
  while IFS= read -r -d '' path; do
    content_sha="$(sha256sum -- "$path" | awk '{print $1}')"
    printf '%q %s\n' "$path" "$content_sha"
  done < <(git ls-files --others --exclude-standard -z)
} | sha256sum | awk '{print $1}')"
candidate_fingerprint="$(printf '%s\n%s\n%s\n%s\n' \
  "$full_sha" "$tracked_diff_sha" "$staged_diff_sha" "$untracked_manifest_sha" \
  | sha256sum | awk '{print $1}')"

echo "TRACKED_DIFF_SHA256: ${tracked_diff_sha}"
echo "STAGED_DIFF_SHA256: ${staged_diff_sha}"
echo "UNTRACKED_MANIFEST_SHA256: ${untracked_manifest_sha}"
echo "CANDIDATE_FINGERPRINT_SHA256: ${candidate_fingerprint}"

if [[ -z "$status" ]]; then
  echo "WORKTREE_STATE: CLEAN"
  exit 0
fi

echo "WORKTREE_STATE: DIRTY"
echo "----- WORKTREE STATUS -----"
printf '%s\n' "$status"
echo "---------------------------"

if printf '%s\n' "$status" | cut -c4- | grep -E '(^| -> )docs/audit/.*\.csv$' >/dev/null 2>&1; then
  echo "FAIL: docs/audit CSV changes detected"
  exit 1
fi

if [[ "$REQUIRE_CLEAN" == "1" ]]; then
  echo "FAIL: clean worktree required for this preflight mode"
  exit 1
fi

echo "OK: dirty worktree inventoried for governed iteration"
