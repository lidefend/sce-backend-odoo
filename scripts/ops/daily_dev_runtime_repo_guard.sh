#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "[daily_dev_runtime_repo_guard] FAIL: not inside a git repository" >&2
  exit 2
fi

cd "$repo_root"

deployment_mode="${DAILY_DEV_DEPLOYMENT_MODE:-main}"
expected_branch="${DAILY_DEV_RUNTIME_BRANCH:-main}"
candidate_source_branch="${DAILY_DEV_CANDIDATE_SOURCE_BRANCH:-}"
candidate_expected_sha="${DAILY_DEV_CANDIDATE_EXPECTED_SHA:-}"
max_allowed_stashes="${DAILY_DEV_RUNTIME_MAX_STASHES:-0}"
forbidden_refs_pattern="${DAILY_DEV_RUNTIME_FORBIDDEN_REF_PATTERN:-refs/remotes/localpush/}"

errors=()

branch="$(git branch --show-current)"
head="$(git rev-parse HEAD)"

case "$deployment_mode" in
  main)
    if [[ "$expected_branch" != "main" ]]; then
      errors+=("main deployment mode cannot override the expected branch")
    fi
    if [[ "$branch" != "$expected_branch" ]]; then
      errors+=("expected branch '$expected_branch', got '$branch'")
    fi
    if git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1; then
      ahead_behind="$(git rev-list --left-right --count 'HEAD...@{upstream}')"
      if [[ "$ahead_behind" != "0	0" ]]; then
        errors+=("branch is not aligned with upstream: $ahead_behind")
      fi
    else
      errors+=("branch has no upstream")
    fi
    ;;
  candidate)
    if [[ ! "$candidate_source_branch" =~ ^(feature|fix|refactor|audit|release|codex)/.+$ ]]; then
      errors+=("candidate source branch is missing or not governed")
    elif ! git check-ref-format "refs/heads/$candidate_source_branch" >/dev/null 2>&1; then
      errors+=("candidate source branch is not a valid Git ref")
    fi
    if [[ ! "$candidate_expected_sha" =~ ^[0-9a-f]{40}$ ]]; then
      errors+=("candidate expected SHA must be a full lowercase commit identity")
    elif [[ "$head" != "$candidate_expected_sha" ]]; then
      errors+=("candidate HEAD differs: expected '$candidate_expected_sha', got '$head'")
    fi
    if [[ -n "$branch" ]]; then
      errors+=("candidate runtime must use detached HEAD, got branch '$branch'")
    fi
    candidate_ref="refs/daily-candidates/$candidate_source_branch"
    if ! git show-ref --verify --quiet "$candidate_ref"; then
      errors+=("candidate evidence ref is missing: $candidate_ref")
    elif [[ "$(git rev-parse "$candidate_ref")" != "$candidate_expected_sha" ]]; then
      errors+=("candidate evidence ref differs from expected SHA")
    fi
    ;;
  *)
    errors+=("unsupported deployment mode '$deployment_mode'")
    ;;
esac

if [[ -n "$(git status --porcelain)" ]]; then
  errors+=("working tree is not clean")
fi

stash_count="$(git stash list | wc -l | tr -d ' ')"
if (( stash_count > max_allowed_stashes )); then
  errors+=("stash count $stash_count exceeds allowed $max_allowed_stashes")
fi

if git show-ref | grep -Eq "$forbidden_refs_pattern"; then
  errors+=("forbidden temporary/archive refs are present")
fi

for path in artifacts migration_assets tmp; do
  if [[ -d "$path" ]] && git status --porcelain -- "$path" | grep -q .; then
    errors+=("runtime repo contains uncommitted generated data under $path")
  fi
done

if (( ${#errors[@]} > 0 )); then
  echo "[daily_dev_runtime_repo_guard] FAIL"
  for error in "${errors[@]}"; do
    echo "- $error"
  done
  exit 1
fi

runtime_identity="${branch:-detached}"
echo "[daily_dev_runtime_repo_guard] PASS mode=$deployment_mode branch=$runtime_identity source_branch=${candidate_source_branch:-$expected_branch} head=$(git rev-parse --short HEAD)"
