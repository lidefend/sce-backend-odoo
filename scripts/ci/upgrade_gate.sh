#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_GATE_ENTRY:?DENY: use make test-upgrade-gate; direct upgrade_gate.sh execution is forbidden}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "upgrade_gate.sh" "$ROOT_DIR" "test-upgrade-gate"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
source "$(dirname "$0")/../_lib/common.sh"

guard_prod_forbid

log "upgrade gate via run_ci"
SC_GOVERNED_CI_ENTRY=1 bash "$(dirname "$0")/run_ci.sh"
