#!/usr/bin/env bash
set -euo pipefail

# Diagnostic, not a gate. The contract snapshot gate is fail-fast and aborts on
# the first case that returns an unexpected response, so a fixture or seed
# defect costs one full run per discovery. This entry reuses the very same
# per-case export (`contract.export_all` with CASE_ONLY) and keeps going, so one
# run lists every failing case. It never relaxes the gate: the gate target is
# unchanged, and this entry is not evidence of a pass.
#
# Runs inside the isolated contract-snapshot environment, exactly like
# local.contract-snapshot.gate_contract.run, so DB/config identity is the
# registered one and nothing here is hand-assembled.

: "${DB_NAME:?DB_NAME is required}"
: "${CASES_FILE:?CASES_FILE is required}"

OUTDIR="${OUTDIR:-tmp/contract_snapshot_audit}"
mkdir -p "${OUTDIR}"

mapfile -t case_names < <(
  python3 - "${CASES_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    cases = json.load(handle)
for case in cases:
    name = str((case or {}).get("case") or "").strip()
    if name:
        print(name)
PY
)

(( ${#case_names[@]} > 0 )) || {
  echo "[matrix_audit] no cases in ${CASES_FILE}" >&2
  exit 2
}

pass_count=0
fail_count=0

for name in "${case_names[@]}"; do
  log="${OUTDIR}/${name}.stderr"
  if SC_CONTRACT_STABLE=1 DB="${DB_NAME}" CASES_FILE="${CASES_FILE}" \
      OUTDIR="${OUTDIR}" CONTRACT_CONFIG="${CONTRACT_CONFIG:-}" ODOO_CONF="${ODOO_CONF:-}" \
      CASE_ONLY="${name}" scripts/contract/export_all.sh >/dev/null 2>"${log}"; then
    echo "PASS ${name}"
    pass_count=$((pass_count + 1))
  else
    detail="$(tail -n 1 "${log}" 2>/dev/null || true)"
    echo "FAIL ${name} :: ${detail}"
    fail_count=$((fail_count + 1))
  fi
done

echo "[matrix_audit] summary pass=${pass_count} fail=${fail_count} total=${#case_names[@]} outdir=${OUTDIR}"

if (( fail_count > 0 )); then
  exit 2
fi
