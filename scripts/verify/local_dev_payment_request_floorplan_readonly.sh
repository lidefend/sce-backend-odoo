#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
SOURCE_SHA="${SOURCE_SHA:?SOURCE_SHA is required}"
LOCAL_DEV_FLOORPLAN_SCOPE="${LOCAL_DEV_FLOORPLAN_SCOPE:-base}"
[[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == base || "$LOCAL_DEV_FLOORPLAN_SCOPE" == consumption || "$LOCAL_DEV_FLOORPLAN_SCOPE" == project_create || "$LOCAL_DEV_FLOORPLAN_SCOPE" == references || "$LOCAL_DEV_FLOORPLAN_SCOPE" == authority ]] || exit 2
export LOCAL_DEV_FLOORPLAN_SCOPE
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "SOURCE_SHA must be an exact commit" >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "local.dev env file not found: $ENV_FILE" >&2; exit 2; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ "${NGINX_PORT:-}" == "18081" ]] || { echo "expected custom frontend port 18081" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }

if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == project_create ]]; then export CONTRACT_REFERENCE_PREFLIGHT=project_create; fi
if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == consumption ]]; then export CONTRACT_REFERENCE_PREFLIGHT=guidance; fi
if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == references ]]; then export CONTRACT_REFERENCE_PREFLIGHT=1; fi
if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == authority ]]; then
  LOCAL_DEV_AUTHORITY_TARGET="${LOCAL_DEV_AUTHORITY_TARGET:-floorplan}"
  [[ "$LOCAL_DEV_AUTHORITY_TARGET" == floorplan || "$LOCAL_DEV_AUTHORITY_TARGET" == editable ]] || exit 2
  export CONTRACT_REFERENCE_PREFLIGHT=authority CONTRACT_AUTHORITY_SOURCE_SHA="$SOURCE_SHA" CONTRACT_AUTHORITY_TARGET="$LOCAL_DEV_AUTHORITY_TARGET"
fi

output_dir="$ROOT_DIR/artifacts/playwright/local-dev-payment-request-floorplan"
mkdir -p "$output_dir"
resolve_target() {
  local phase="${1:?resolver phase is required}"
  local resolver_log="$output_dir/resolver-${LOCAL_DEV_FLOORPLAN_SCOPE}-${phase}.log"
  local resolver_status=0
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_request_native_parity_ids.py" \
    > "$resolver_log" 2>&1 || resolver_status=$?
  if [[ "$resolver_status" -ne 0 ]]; then
    echo "payment floorplan resolver failed: scope=$LOCAL_DEV_FLOORPLAN_SCOPE phase=$phase status=$resolver_status log=$resolver_log" >&2
    tail -n 20 "$resolver_log" >&2
    return "$resolver_status"
  fi
  local resolved
  resolved="$(sed -n 's/^LOCAL_DEV_PAYMENT_PARITY_JSON=//p' "$resolver_log" | tail -1)"
  [[ -n "$resolved" ]] || { echo "payment floorplan resolver returned no identity: $resolver_log" >&2; return 1; }
  printf '%s\n' "$resolved"
}

before="$(resolve_target before)"
[[ -n "$before" ]] || { echo "payment floorplan target resolution failed" >&2; exit 1; }

if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == references || "$LOCAL_DEV_FLOORPLAN_SCOPE" == authority ]]; then
  output_name="$LOCAL_DEV_FLOORPLAN_SCOPE"
  if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" == authority && "$LOCAL_DEV_AUTHORITY_TARGET" == editable ]]; then output_name=authority-editable; fi
  printf '%s\n' "$before" > "$output_dir/${output_name}.json"
  echo "readonly reference preflight: $output_dir/${output_name}.json"
  exit 0
fi
if [[ "$LOCAL_DEV_FLOORPLAN_SCOPE" != project_create ]]; then
BEFORE_JSON="$before" SOURCE_SHA="$SOURCE_SHA" OUTPUT_DIR="$output_dir" ROOT_DIR="$ROOT_DIR" python3 - <<'PY_DECLARATION'
import json, os, hashlib
from pathlib import Path
root, output = Path(os.environ['ROOT_DIR']), Path(os.environ['OUTPUT_DIR'])
target = json.loads(os.environ['BEFORE_JSON'])
(output / 'before.json').write_text(json.dumps(target))
target['contract_resolution']['expected_sha'] = os.environ['SOURCE_SHA']
(output / 'resolution.json').write_text(json.dumps(target['contract_resolution']))
for profile in ('edit', 'readonly'):
    declaration = json.loads((root / 'config/acceptance/backend_contract_instance_daily_v1.json').read_text())
    declaration['purpose'] = 'Existing local.dev readonly observation; exact record/profile prerequisite.'
    declaration['database'] = target['database']
    declaration['account'] = {'login': target['user']['login'], 'role_code': target['acceptance_authority']['role_code'],
                              'company_name': target['user']['company_name']}
    declaration['resolution'].update(governed_producer=target['contract_resolution']['producer'],
                                    producer_output_key='LOCAL_DEV_PAYMENT_PARITY_JSON', company_key='local')
    declaration['request']['render_profile'] = profile
    (output / f'declaration-{profile}.json').write_text(json.dumps(declaration))

PY_DECLARATION
for profile in edit readonly; do
  approval_status=0
  ACCEPTANCE_PASSWORD="$SC_DEMO_USER_PASSWORD" \
  python3 "$ROOT_DIR/scripts/ops/dev_acceptance_release_probe.py" \
    --base-url "http://127.0.0.1:${NGINX_PORT}" --db-name "$DB_NAME" \
    --expected-sha "$SOURCE_SHA" --login "$(BEFORE_JSON="$before" python3 -c 'import json,os;print(json.loads(os.environ["BEFORE_JSON"])["user"]["login"])')" \
    --contract-declaration "$output_dir/declaration-$profile.json" \
    --record-resolution "$output_dir/resolution.json" --require-contract \
    --output "$output_dir/approval-$profile.json" > "$output_dir/approval-$profile.log" 2>&1 || approval_status=$?
  if [[ "$approval_status" -ne 0 ]]; then
    echo "backend approval $profile failed: status=$approval_status report=$output_dir/approval-$profile.json log=$output_dir/approval-$profile.log" >&2
    APPROVAL_REPORT="$output_dir/approval-$profile.json" python3 - <<'PY_APPROVAL_ERROR' >&2 || true
import json, os
from pathlib import Path
p = Path(os.environ["APPROVAL_REPORT"])
if p.is_file():
    try:
        report = json.loads(p.read_text())
    except (OSError, ValueError):
        print("approval report unavailable or malformed; original process status retained")
        report = {}
    for key, value in report.items():
        if isinstance(value, dict) and value.get("errors"):
            print(key + ": " + json.dumps(value["errors"], ensure_ascii=False)[:1200])
PY_APPROVAL_ERROR
    exit "$approval_status"
  fi
  echo "[local.dev.payment.floorplan] backend approval $profile PASS (approval-$profile.log)"
done
fi

# Approval is an input authority, not a result inferred after unit planning.
BEFORE_JSON="$before" SOURCE_SHA="$SOURCE_SHA" OUTPUT_DIR="$output_dir" ROOT_DIR="$ROOT_DIR" python3 - <<'PY_UNITS'
import json, os, hashlib
from pathlib import Path
root, output = Path(os.environ['ROOT_DIR']), Path(os.environ['OUTPUT_DIR'])
target = json.loads(os.environ['BEFORE_JSON'])
# Input declaration for the existing evidence_scope engine. The source revision
# is provenance; file hashes and authoritative readback bind the affected keys.
shared = ['scripts/verify/local_dev_payment_request_floorplan_readonly.sh',
          'scripts/verify/local_dev_payment_request_floorplan_readonly.mjs',
          'scripts/verify/local_dev_payment_request_native_parity_ids.py',
          'scripts/verify/lib/acceptance_contract_receipt.mjs',
          'scripts/ops/dev_acceptance_release_probe.py', 'make/dev.mk']
consumer_files = sorted({str(item.relative_to(root))
    for directory in ('frontend/apps/web/src', 'frontend/packages')
    for item in (root / directory).rglob('*') if item.is_file()})
build_files = sorted({str(item.relative_to(root))
    for directory in ('frontend', 'frontend/apps/web')
    for pattern in ('package.json', '*lock*', '*config*')
    for item in (root / directory).glob(pattern) if item.is_file()})
consumers = {surface: consumer_files + build_files for surface in ('list', 'create', 'edit', 'readonly')}
approved = {}
for profile in (() if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'project_create' else ('edit', 'readonly')):
    receipt = json.loads((output / f'approval-{profile}.json').read_text())['contract']
    if receipt.get('status') != 'PASS' or not receipt.get('approved_semantic_sha256') or receipt.get('approved_semantic_sha256') != receipt.get('recomputed_semantic_sha256'):
        raise SystemExit('approved profile semantic digest is missing or unverified')
    approved[profile] = {'semantic_sha256': receipt['approved_semantic_sha256'],
                         'request': receipt['request'],
                         'actor': {key: receipt['identity'].get(key) for key in ('uid', 'login', 'role_code', 'company_id', 'company_name')}}
units, inputs = [], {}
for surface, files in ({} if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'project_create' else consumers).items():
    if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'consumption' and surface not in ('edit', 'readonly'):
        continue
    files = shared + files + ['frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue',
                              'frontend/apps/web/src/app/runtime/recordEntryContract.ts']
    digests = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    for width in (1440, 390):
        key = f'{surface}:{width}' if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'base' else f'{surface}:auth_occurrence:{width}'
        payload = {'files': digests, 'width': width, 'surface': surface,
                   'readback': target, 'declaration': (json.loads((output / f'declaration-{surface}.json').read_text())
                       if surface in ('edit', 'readonly') else {'source': 'live_ui.contract.v2', 'surface': surface,
                         'model': target['contract_resolution']['targets']['payment_request']['model'],
                         'action_id': target['action']['id'], 'menu_id': target['menu']['id']})}
        # target is the actual before readback; expected_sha is separately held
        # only in the exported resolution, not inserted into that readback.
        payload['readback'] = {**target, 'contract_resolution': {**target['contract_resolution'], 'expected_sha': None}}
        if surface in approved:
            payload['approved_contract'] = approved[surface]
        inputs[key] = payload
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        units.append({'id': key, 'fingerprint': fingerprint, 'required': True})
        if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'consumption' and surface == 'edit':
            span_key = f'{surface}:span:{width}'
            inputs[span_key] = {**payload, 'assertion': 'span'}
            units.append({'id': span_key, 'fingerprint': hashlib.sha256(json.dumps(inputs[span_key], sort_keys=True).encode()).hexdigest(), 'required': True})
            guidance_key = f'edit:guidance:{width}'
            inputs[guidance_key] = {**payload, 'assertion': 'native_action_guidance_confirm_cancel'}
            units.append({'id': guidance_key, 'fingerprint': hashlib.sha256(json.dumps(inputs[guidance_key], sort_keys=True).encode()).hexdigest(), 'required': True})
if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'consumption':
    # Entry does not consume the form layout/header or either form semantic seal.
    # Keep shared boot/routing/collection dependencies conservative but separate.
    entry_files = sorted(set(shared + build_files + [name for name in consumer_files
        if not name.startswith('frontend/apps/web/src/pages/contractForm/')
        and name != 'frontend/apps/web/src/pages/ContractFormPage.vue']))
    entry_input = {'assertion': 'declared_search_and_actual_row_click',
        'files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in entry_files},
        'identity': {'database': target['database'], 'user': target['user'],
            'action': target['action'], 'menu': target['menu'],
            'record': {key: target['record'].get(key) for key in ('id', 'xmlid', 'name')},
            'authority': target.get('acceptance_authority'),
            'request': approved['edit']['request'], 'actor': approved['edit']['actor']}}

    inputs['entry_click'] = entry_input
    units.append({'id': 'entry_click', 'fingerprint': hashlib.sha256(json.dumps(entry_input, sort_keys=True).encode()).hexdigest(), 'required': True})
if os.environ['LOCAL_DEV_FLOORPLAN_SCOPE'] == 'project_create':
    (output / 'before.json').write_text(json.dumps(target))
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in shared + consumer_files + build_files}
    for entry in target['project_create_entries']:
        for width in (1440, 390):
            key = f"project_create:{entry['kind']}:{width}"
            inputs[key] = {'files': files, 'entry': entry, 'width': width, 'readback': target, 'authority': 'live_create_contract; no_positive_record_seal'}
            units.append({'id': key, 'fingerprint': hashlib.sha256(json.dumps(inputs[key], sort_keys=True).encode()).hexdigest(), 'required': True})
(output / 'units.json').write_text(json.dumps({'schema': 'evidence_scope.units.v1',
  'check': 'verify.local.dev.payment_request.floorplan.readonly',
  'identity': {'base_url': 'http://127.0.0.1:18081', 'database': target['database'],
               'uid': target['user']['id'], 'company_id': target['user']['company_id']},
  'units': units, 'inputs': inputs, 'source_sha': os.environ['SOURCE_SHA']}))
PY_UNITS

ledger="$ROOT_DIR/.runtime/evidence-scope/local-dev-payment-floorplan.json"
python3 "$ROOT_DIR/scripts/ops/evidence_scope.py" plan --units "$output_dir/units.json" \
  --ledger "$ledger" --json-out "$output_dir/plan.json"
PLAN_PATH="$output_dir/plan.json" python3 - <<'PY_PLAN'
import json, os
plan = json.load(open(os.environ['PLAN_PATH']))
if plan.get('blocked'):
    raise SystemExit('unchanged failed floorplan keys are blocked; repair owning inputs before retry')
if len(plan.get('affected', [])) != len(set(plan.get('affected', []))):
    raise SystemExit('duplicate affected floorplan keys')
PY_PLAN
if PLAN_PATH="$output_dir/plan.json" python3 -c 'import json,os,sys;sys.exit(0 if not json.load(open(os.environ["PLAN_PATH"]))["affected"] else 1)'; then
  echo "[local.dev.payment.floorplan] all keys reusable; browser not_run; no new result recorded"
  exit 0
fi
# No prior summary may impersonate this invocation if browser startup fails.
rm -f "$output_dir/summary.json" "$output_dir/results.json" "$output_dir/record.json"

set +e
LOCAL_DEV_PAYMENT_FLOORPLAN_JSON="$before" SOURCE_SHA="$SOURCE_SHA" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_request_floorplan_readonly.mjs"
browser_status=$?
set -e

# A failed/missing authoritative after-readback invalidates every executed key.
set +e
after="$(resolve_target after)"
readback_status=$?
BEFORE_JSON="$before" AFTER_JSON="$after" OUTPUT_DIR="$output_dir" READBACK_STATUS="$readback_status" BROWSER_STATUS="$browser_status" python3 - <<'PY_RESULTS'
import json, os
from pathlib import Path
output = Path(os.environ['OUTPUT_DIR'])
before = json.loads(os.environ['BEFORE_JSON'])
summary_path = output / 'summary.json'
summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
try:
    after = json.loads(os.environ['AFTER_JSON'])
except (ValueError, TypeError):
    after = None
(output / 'after.json').write_text(json.dumps(after))
readback_ok = (os.environ['READBACK_STATUS'] == '0' and isinstance(after, dict)
               and after.get('business_fingerprint') == before.get('business_fingerprint')
               and bool(before.get('business_fingerprint')))
summary['after_readback'] = {'status': 'passed' if readback_ok else 'failed', 'business_fingerprint_unchanged': readback_ok}
summary['pass'] = bool(summary.get('pass') is True and readback_ok and os.environ['BROWSER_STATUS'] == '0')
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
if summary.get('observationRunId'):
    (output / ('summary-' + summary['observationRunId'] + '.json')).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
document = json.loads((output / 'units.json').read_text())
declared = {unit['id']: unit for unit in document['units']}
executed = summary.get('executed_keys') or []
if set(summary.get('unit_results', {})) != set(executed) or any(summary['unit_results'][key] != 'passed' for key in executed):
    raise SystemExit('completed unit outcomes are missing or invalid')
if len(set(executed)) != len(executed) or any(key not in declared or summary.get('unit_fingerprints', {}).get(key) != declared[key]['fingerprint'] for key in executed):
    raise SystemExit('actual executed keys do not match declared units')
# executed_keys is appended only after that key's actual assertions complete.
# A later key failure does not erase prior outcomes; global readback/errors do.
completed_ok = readback_ok and not summary.get('errors') and not summary.get('mutations')
results = {'schema': 'evidence_scope.results.v1', 'executed_units': [declared[key] for key in executed],
           'results': {key: 'passed' if completed_ok else 'failed' for key in executed},
           'planned_affected': executed, 'source': str(summary_path),
           'not_executed': [key for key in declared if key not in executed]}
(output / 'results.json').write_text(json.dumps(results))
print('[local.dev.payment.floorplan] actual executed keys:', len(executed), 'after_readback:', readback_ok)
raise SystemExit(0 if summary['pass'] else 1)
PY_RESULTS
result_status=$?
set -e
if [[ -f "$output_dir/results.json" ]] && RESULTS_PATH="$output_dir/results.json" python3 -c 'import json,os,sys;sys.exit(0 if json.load(open(os.environ["RESULTS_PATH"]))["executed_units"] else 1)'; then
  python3 "$ROOT_DIR/scripts/ops/evidence_scope.py" record --units "$output_dir/units.json" \
    --ledger "$ledger" --results "$output_dir/results.json" --source "$output_dir/summary.json" \
    --json-out "$output_dir/record.json"
fi
exit "$result_status"
