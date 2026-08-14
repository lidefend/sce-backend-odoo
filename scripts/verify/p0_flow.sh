#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_lib/common.sh"

: "${DB_NAME:?DB_NAME required}"

log "[verify.p0.flow] reset db=${DB_NAME}"
DB_NAME="${DB_NAME}" bash scripts/db/reset.sh

log "[verify.p0.flow] install core"
SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 DB_NAME="${DB_NAME}" MODULE="smart_construction_core" bash scripts/mod/install.sh

log "[verify.p0.flow] install seed"
SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 SC_SEED_ENABLED=1 SC_BOOTSTRAP_MODE=demo DB_NAME="${DB_NAME}" MODULE="smart_construction_seed" bash scripts/mod/install.sh

log "[verify.p0.flow] restart odoo to load newly installed modules"
compose up -d odoo

log "[verify.p0.flow] run p0 verification"
SC_LOGIN_ENV_EXPECTED=prod SC_P0_VERIFY_USER_DATA_BASELINE=1 \
  DB_NAME="${DB_NAME}" bash scripts/verify/p0_base.sh

log "[verify.p0.flow] done db=${DB_NAME}"
