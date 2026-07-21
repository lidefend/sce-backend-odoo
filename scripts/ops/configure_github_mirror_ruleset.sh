#!/usr/bin/env bash
set -euo pipefail

# Retained at the historical path for callers, but now configures the GitHub
# authority ruleset. It never provisions a deploy key or a bypass actor.
[ "${GITHUB_AUTHORITY_RULESET_CONFIRM:-}" = "1" ] || {
  echo "[github_authority_ruleset] GITHUB_AUTHORITY_RULESET_CONFIRM=1 is required" >&2
  exit 2
}

readonly repository="lidefend/sce-backend-odoo"
readonly ruleset_name="main-github-authoritative-pr"

write_key_count="$(gh api "repos/${repository}/keys" --jq '[.[] | select(.read_only == false)] | length')"
[ "${write_key_count}" = "0" ] || {
  echo "[github_authority_ruleset] BLOCKED write_deploy_key_present" >&2
  exit 2
}

payload="$(mktemp)"
trap 'rm -f -- "${payload}"' EXIT
jq -n --arg name "${ruleset_name}" '{
  name: $name,
  target: "branch",
  enforcement: "active",
  bypass_actors: [],
  conditions: {ref_name: {include: ["refs/heads/main"], exclude: []}},
  rules: [
    {type: "deletion"},
    {type: "non_fast_forward"},
    {type: "pull_request", parameters: {
      dismiss_stale_reviews_on_push: true,
      require_code_owner_review: false,
      require_last_push_approval: false,
      required_approving_review_count: 0,
      required_review_thread_resolution: true,
      allowed_merge_methods: ["squash", "rebase"]
    }},
    {type: "required_status_checks", parameters: {
      do_not_enforce_on_create: false,
      strict_required_status_checks_policy: true,
      required_status_checks: [
        {context: "public_guard"},
        {context: "professional_authorization"},
        {context: "professional_quality_gate"}
      ]
    }}
  ]
}' > "${payload}"

ruleset_id="$(gh api "repos/${repository}/rulesets" --jq ".[] | select(.name == \"${ruleset_name}\") | .id" | head -1)"
if [ -n "${ruleset_id}" ]; then
  gh api --method PUT "repos/${repository}/rulesets/${ruleset_id}" --input "${payload}" >/dev/null
else
  ruleset_id="$(gh api --method POST "repos/${repository}/rulesets" --input "${payload}" --jq .id)"
fi

gh api "repos/${repository}/rulesets/${ruleset_id}" --jq '
  select(.enforcement == "active")
  | select(.target == "branch")
  | select(.conditions.ref_name.include == ["refs/heads/main"])
  | select((.bypass_actors | length) == 0)
  | select(any(.rules[]; .type == "pull_request"))
  | select(any(.rules[]; .type == "required_status_checks"))
  | select(any(.rules[]; .type == "deletion"))
  | select(any(.rules[]; .type == "non_fast_forward"))
  | .id' | grep -qx "${ruleset_id}"

echo "[github_authority_ruleset] PASS ruleset_id=${ruleset_id} bypass_actors=none write_deploy_keys=0"
