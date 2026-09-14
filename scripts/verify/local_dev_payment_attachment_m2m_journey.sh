#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
[[ -f "$ENV_FILE" ]] || { echo "local.dev env file not found: $ENV_FILE" >&2; exit 2; }
LOCAL_DEV_CANONICAL_ENV_FILE="$(readlink -f "$ENV_FILE")"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ "${NGINX_PORT:-}" == "18081" ]] || { echo "expected custom frontend port 18081" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }
CANDIDATE_GIT_HEAD="${CANDIDATE_GIT_HEAD:-$(git -C "$ROOT_DIR" rev-parse HEAD)}"
[[ "$CANDIDATE_GIT_HEAD" =~ ^[0-9a-f]{40}$ ]] || { echo "candidate head is invalid" >&2; exit 2; }
[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$CANDIDATE_GIT_HEAD" ]] || { echo "candidate head mismatch" >&2; exit 2; }

EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT_DIR/artifacts/playwright/local-dev-payment-attachment-m2m-journey}"
mkdir -p "$EVIDENCE_DIR"
BASELINE_SHA="${BASELINE_SHA:-$(git -C "$ROOT_DIR" merge-base HEAD origin/main)}"
python3 "$ROOT_DIR/scripts/contract/complete_worktree_fingerprint.py" \
  --baseline "$BASELINE_SHA" --output "$EVIDENCE_DIR/fingerprint-before.json" >/dev/null
CANDIDATE_FINGERPRINT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["digest"])' "$EVIDENCE_DIR/fingerprint-before.json")"

restore_needed=0
restore_on_exit() {
  local status=$?
  if (( restore_needed == 1 )); then
    echo "[local.dev.payment.attachment-m2m] restoring governed fixture after interrupted journey" >&2
    ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
      make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture || true
  fi
  exit "$status"
}
trap restore_on_exit EXIT

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_attachment_m2m_ids.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_ATTACHMENT_M2M_JSON=//p' | tail -1
}

ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
  make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture
before="$(resolve_target)"
[[ -n "$before" ]] || { echo "payment attachment M2M target resolution failed" >&2; exit 1; }
restore_needed=1

LOCAL_DEV_PAYMENT_ATTACHMENT_M2M_JSON="$before" \
CANDIDATE_GIT_HEAD="$CANDIDATE_GIT_HEAD" CANDIDATE_FINGERPRINT="$CANDIDATE_FINGERPRINT" \
EVIDENCE_DIR="$EVIDENCE_DIR" FRONTEND_URL="http://127.0.0.1:5176" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_attachment_m2m_journey.mjs"

after="$(resolve_target)"
BEFORE_JSON="$before" AFTER_JSON="$after" EVIDENCE_DIR="$EVIDENCE_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path

before = json.loads(os.environ["BEFORE_JSON"])
after = json.loads(os.environ["AFTER_JSON"])
attachment_id = before["attachment"]["id"]
if attachment_id not in before["request"]["attachment_ids"]:
    raise SystemExit("governed M2M baseline did not contain the fixture attachment")
if attachment_id in after["request"]["attachment_ids"]:
    raise SystemExit("saved journey did not detach the M2M relationship")
if after["attachment"]["id"] != attachment_id or not after["attachment"]["exists"]:
    raise SystemExit("detaching the relationship deleted or replaced the attachment object")
Path(os.environ["EVIDENCE_DIR"], "authoritative-after-save.json").write_text(
    json.dumps({"before": before, "after": after}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("[local.dev.payment.attachment-m2m] relationship detached; attachment object retained")
PY

ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
  make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture
reset="$(resolve_target)"
RESET_JSON="$reset" EVIDENCE_DIR="$EVIDENCE_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path

reset = json.loads(os.environ["RESET_JSON"])
attachment_id = reset["attachment"]["id"]
if not reset["attachment"]["exists"] or attachment_id not in reset["request"]["attachment_ids"]:
    raise SystemExit("governed fixture reset did not restore the attachment relationship")
Path(os.environ["EVIDENCE_DIR"], "authoritative-after-reset.json").write_text(
    json.dumps(reset, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("[local.dev.payment.attachment-m2m] fixture reset restored the governed baseline")
PY

python3 "$ROOT_DIR/scripts/contract/complete_worktree_fingerprint.py" \
  --baseline "$BASELINE_SHA" --output "$EVIDENCE_DIR/fingerprint-after.json" >/dev/null
after_fingerprint="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["digest"])' "$EVIDENCE_DIR/fingerprint-after.json")"
[[ "$after_fingerprint" == "$CANDIDATE_FINGERPRINT" ]] || { echo "candidate fingerprint changed during M2M journey" >&2; exit 1; }

restore_needed=0
trap - EXIT
echo "[local.dev.payment.attachment-m2m] PASS candidate=$CANDIDATE_GIT_HEAD fingerprint=$CANDIDATE_FINGERPRINT"
