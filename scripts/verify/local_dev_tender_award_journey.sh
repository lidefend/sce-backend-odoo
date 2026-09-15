#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
PRODUCT_CANDIDATE_SHA="${PRODUCT_CANDIDATE_SHA:?PRODUCT_CANDIDATE_SHA is required}"
P4_TOOL_CANDIDATE_SHA="${P4_TOOL_CANDIDATE_SHA:?P4_TOOL_CANDIDATE_SHA is required}"
P4_TENDER_AWARD_BATCH="${P4_TENDER_AWARD_BATCH:?P4_TENDER_AWARD_BATCH is required}"
ARTIFACT_DIR="${ARTIFACT_DIR:-${ROOT_DIR}/artifacts/p4-tender-award/${P4_TENDER_AWARD_BATCH}-${P4_TOOL_CANDIDATE_SHA:0:8}}"

[[ "$(git -C "${ROOT_DIR}" rev-parse HEAD)" == "${P4_TOOL_CANDIDATE_SHA}" ]] || { echo "[DENY] tool SHA mismatch" >&2; exit 2; }
[[ "$(git -C "${ROOT_DIR}" status --porcelain=v2 --untracked-files=all)" == "" ]] || { echo "[DENY] tool worktree must be clean" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

fixture() {
  local mode="$1" confirm="$2"
  P4_TENDER_AWARD_MODE="${mode}" \
  P4_TENDER_AWARD_BATCH="${P4_TENDER_AWARD_BATCH}" \
  P4_TENDER_AWARD_CONFIRM="${confirm}" \
    make -C "${ROOT_DIR}" --no-print-directory local.dev.tender_award_fixture
}

extract_json() {
  local input="$1" output="$2"
  python3 - "${input}" "${output}" <<'PY'
import json, sys
source, target = sys.argv[1:]
prefix = "LOCAL_DEV_TENDER_AWARD_FIXTURE_JSON="
rows = [line[len(prefix):] for line in open(source, encoding="utf-8") if line.startswith(prefix)]
if len(rows) != 1:
    raise SystemExit("expected one fixture result in %s" % source)
with open(target, "w", encoding="utf-8") as handle:
    json.dump(json.loads(rows[0]), handle, ensure_ascii=False, indent=2, sort_keys=True)
PY
}

pre_log="${ARTIFACT_DIR}/fixture-pre-inspect.log"
fixture inspect INSPECT | tee "${pre_log}"
extract_json "${pre_log}" "${ARTIFACT_DIR}/fixture-pre-inspect.json"
python3 - "${ARTIFACT_DIR}/fixture-pre-inspect.json" <<'PY'
import json, sys
row = json.load(open(sys.argv[1], encoding="utf-8"))
if row.get("existing_batch"):
    raise SystemExit("batch already exists; inspect/cleanup explicitly before a new journey")
PY

prepare_log="${ARTIFACT_DIR}/fixture-prepare.log"
fixture prepare PREPARE | tee "${prepare_log}"
extract_json "${prepare_log}" "${ARTIFACT_DIR}/fixture-prepare.json"

set +e
ROOT_DIR="${ROOT_DIR}" \
PRODUCT_CANDIDATE_SHA="${PRODUCT_CANDIDATE_SHA}" \
P4_TOOL_CANDIDATE_SHA="${P4_TOOL_CANDIDATE_SHA}" \
P4_TENDER_AWARD_BATCH="${P4_TENDER_AWARD_BATCH}" \
ARTIFACT_DIR="${ARTIFACT_DIR}/browser" \
  make -C "${ROOT_DIR}" --no-print-directory local.dev.tender_award_browser \
  2>&1 | tee "${ARTIFACT_DIR}/browser.log"
browser_status=${PIPESTATUS[0]}
set -e
if [[ "${browser_status}" -ne 0 ]]; then
  echo "[local.dev.tender-award] browser failed; batch retained for diagnosis" >&2
  echo "[local.dev.tender-award] inspect: P4_TENDER_AWARD_MODE=inspect P4_TENDER_AWARD_BATCH=${P4_TENDER_AWARD_BATCH} P4_TENDER_AWARD_CONFIRM=INSPECT make local.dev.tender_award_fixture" >&2
  echo "[local.dev.tender-award] cleanup after diagnosis: P4_TENDER_AWARD_MODE=cleanup P4_TENDER_AWARD_BATCH=${P4_TENDER_AWARD_BATCH} P4_TENDER_AWARD_CONFIRM=CLEANUP make local.dev.tender_award_fixture" >&2
  exit "${browser_status}"
fi

post_log="${ARTIFACT_DIR}/fixture-post-inspect.log"
fixture inspect INSPECT | tee "${post_log}"
extract_json "${post_log}" "${ARTIFACT_DIR}/fixture-post-inspect.json"
python3 - "${ARTIFACT_DIR}/fixture-post-inspect.json" <<'PY'
import json, sys
row = json.load(open(sys.argv[1], encoding="utf-8"))
fact = row.get("fixture") or {}
expected = row.get("expected") or {}
checks = {
    "batch_exists": row.get("existing_batch") is True,
    "state_confirmed": fact.get("state") == "won" and fact.get("award_confirmation_state") == "confirmed",
    "amounts": fact.get("bid_amount") == 1200.0 and fact.get("line_total") == 1000.0 and fact.get("award_amount") == 900.0,
    "source": fact.get("award_source_kind") == expected.get("source_kind") and fact.get("award_source_reference") == expected.get("source_reference"),
    "tax_basis": fact.get("award_tax_basis") == "unknown",
    "confirmation_identity": bool(fact.get("award_confirmed_by_id")) and bool(fact.get("award_confirmed_at")),
    "no_contract": not fact.get("contract_id"),
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("post-confirmation authoritative checks failed: %s" % ",".join(failed))
PY

cleanup_log="${ARTIFACT_DIR}/fixture-cleanup.log"
fixture cleanup CLEANUP | tee "${cleanup_log}"
extract_json "${cleanup_log}" "${ARTIFACT_DIR}/fixture-cleanup.json"
final_log="${ARTIFACT_DIR}/fixture-final-inspect.log"
fixture inspect INSPECT | tee "${final_log}"
extract_json "${final_log}" "${ARTIFACT_DIR}/fixture-final-inspect.json"
python3 - "${ARTIFACT_DIR}" "${PRODUCT_CANDIDATE_SHA}" "${P4_TOOL_CANDIDATE_SHA}" <<'PY'
import json, os, sys
out, product, tool = sys.argv[1:]
final = json.load(open(os.path.join(out, "fixture-final-inspect.json"), encoding="utf-8"))
if final.get("existing_batch"):
    raise SystemExit("fixture batch remains after cleanup")
summary = {
    "pass": True,
    "product_candidate_sha": product,
    "tool_candidate_sha": tool,
    "batch": final.get("batch"),
    "database": final.get("database"),
    "end_state": "batch-owned tender, line and opening deleted; reused project/partner unchanged",
    "browser_summary": os.path.join(out, "browser", "summary.json"),
    "authoritative_post_confirmation": os.path.join(out, "fixture-post-inspect.json"),
    "authoritative_final_state": os.path.join(out, "fixture-final-inspect.json"),
}
with open(os.path.join(out, "journey-summary.json"), "w", encoding="utf-8") as handle:
    json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
print("LOCAL_DEV_TENDER_AWARD_JOURNEY_JSON=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
PY
