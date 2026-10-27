#!/usr/bin/env bash
set -euo pipefail
: "${ENV_FILE:?governed environment is required}"
journal_authority_env_file="$ENV_FILE"
set -a
source "$journal_authority_env_file"
set +a
[[ "${COMPOSE_PROJECT_NAME:-}" == sc-local-dev && "${DB_NAME:-}" == sc_dev_demo && "${NGINX_PORT:-}" == 18081 ]]
: "${SC_DEMO_USER_PASSWORD:?canonical demo credential required}"
if [[ "${SC_FEEDBACK_SCOPE:-}" != journal-save ]]; then
  E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" node scripts/verify/local_dev_workspace_feedback.mjs
  exit $?
fi
[[ "${CONFIRM_LOCAL_DEV_JOURNAL_SAVE:-}" == CREATE_READBACK_CLEANUP_ONE_DRAFT ]]
: "${SC_LOCAL_DEV_WRITE_LEASE_TOKEN:?governed write lease required}"
[[ "${CANDIDATE_GIT_HEAD:-}" =~ ^[a-f0-9]{40}$ ]]
export SC_RUNTIME_JOURNAL_REF="P4-JOURNAL-${CANDIDATE_GIT_HEAD}-$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
export SC_RUNTIME_JOURNAL_EVIDENCE=".runtime/product-user-gap-closeout-20261026/journal-save-browser/${CANDIDATE_GIT_HEAD}/${SC_RUNTIME_JOURNAL_REF}"
export SC_CONFIRM_JOURNAL_RECOVERY=PREFLIGHT_CLEANUP_ONE_OWNED_DRAFT
mkdir -p "$SC_RUNTIME_JOURNAL_EVIDENCE"
recover() {
  SC_RUNTIME_JOURNAL_RECOVERY="$1" make --no-print-directory ENV=dev ENV_FILE="$journal_authority_env_file" local.dev.journal.recovery.run > "$SC_RUNTIME_JOURNAL_EVIDENCE/$1.log" 2>&1
}
recover preflight
# Verify the container-observed principal before permitting any browser write.
python3 - "$SC_RUNTIME_JOURNAL_EVIDENCE/preflight.log" <<'VERIFY_PREFLIGHT'
import json,os,sys
rows=[json.loads(line.removeprefix('JOURNAL_RECOVERY ')) for line in open(sys.argv[1]) if line.startswith('JOURNAL_RECOVERY ')]
assert len(rows)==1
receipt=rows[0]
assert receipt['mode']=='preflight' and receipt['passed'] is True and receipt['rolled_back'] is True
assert receipt['ref']==os.environ['SC_RUNTIME_JOURNAL_REF'] and receipt['head']==os.environ['CANDIDATE_GIT_HEAD']
assert receipt['actor']==(os.environ.get('SC_FEEDBACK_ACTOR') or 'demo_full')
assert receipt['uid']==int(os.environ.get('SC_FEEDBACK_EXPECTED_UID') or '40')
VERIFY_PREFLIGHT
# Even a browser failure must finish recovery while this same write lease is held.
finish() {
  local browser_status=$?
  trap - EXIT
  if [[ -f "$SC_RUNTIME_JOURNAL_EVIDENCE/created-receipt.json" ]]; then
    SC_RUNTIME_JOURNAL_BROWSER_RECEIPT="$(cat "$SC_RUNTIME_JOURNAL_EVIDENCE/created-receipt.json")"
    export SC_RUNTIME_JOURNAL_BROWSER_RECEIPT
  fi
  recover cleanup || { echo "Owned journal cleanup failed: $SC_RUNTIME_JOURNAL_EVIDENCE/cleanup.log" >&2; exit 1; }
  SC_RUNTIME_JOURNAL_CLEANUP_RECEIPT="$(python3 - "$SC_RUNTIME_JOURNAL_EVIDENCE/cleanup.log" <<'RECEIPT'
import json,sys
rows=[json.loads(line.removeprefix('JOURNAL_RECOVERY ')) for line in open(sys.argv[1]) if line.startswith('JOURNAL_RECOVERY ')]
assert len(rows)==1
print(json.dumps(rows[0]))
RECEIPT
)" || exit 1
  export SC_RUNTIME_JOURNAL_CLEANUP_RECEIPT
  recover verify_absent || { echo "Independent absence verification failed" >&2; exit 1; }
  python3 - "$SC_RUNTIME_JOURNAL_EVIDENCE" "$browser_status" <<'FINALIZE'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]); path=root/'report.json'
report=json.loads(path.read_text()) if path.exists() else {'passed':False, 'failure':'browser report missing'}
rows=[json.loads(line.removeprefix('JOURNAL_RECOVERY ')) for line in (root/'verify_absent.log').read_text().splitlines() if line.startswith('JOURNAL_RECOVERY ')]
assert len(rows)==1 and rows[0]['passed'] and rows[0]['absent']
report['cleanup']=rows[0]
report['passed']=bool(report.get('browserPassed') and sys.argv[2]=='0')
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('journal browser and independent cleanup: '+('PASS' if report['passed'] else 'FAIL')+' '+str(path))
sys.exit(0 if report['passed'] else 1)
FINALIZE
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" node scripts/verify/local_dev_workspace_feedback.mjs
