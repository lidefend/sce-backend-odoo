#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
BACKEND_SOURCE = (ROOT / "scripts/dev/backend_acceptance_up.sh").read_text(encoding="utf-8")
FRONTEND_ACCEPTANCE_SOURCE = (ROOT / "scripts/dev/frontend_acceptance_up.sh").read_text(encoding="utf-8")

required = (
    "FRONTEND_DEV_PORT ?= 5174",
    'kill -- "-$$pid"',
    "lsof -tiTCP:$(FRONTEND_DEV_PORT)",
    'awk -v target=":$(FRONTEND_DEV_PORT)"',
)
missing = [marker for marker in required if marker not in SOURCE]
if missing:
    raise SystemExit(f"frontend dev process isolation contract missing: {missing}")

for forbidden in ("lsof -tiTCP:5174", "$$4 ~ /:5174$$/"):
    if forbidden in SOURCE:
        raise SystemExit(f"frontend stop contains fixed-port process selection: {forbidden}")

print("[frontend_dev_process_isolation_guard] PASS")

for marker in ('DATABASE="${BACKEND_ACCEPTANCE_DB:-sc_frontend_acceptance}"', '-e ODOO_DB="$DATABASE"', '-e ODOO_DBFILTER="^${DATABASE}$"'):
    if marker not in BACKEND_SOURCE:
        raise SystemExit(f"backend acceptance environment contract missing: {marker}")

if "-e ODOO_DB=sc_frontend_acceptance" in BACKEND_SOURCE:
    raise SystemExit("backend acceptance database remains hard-coded")

print("[backend_acceptance_environment_guard] PASS")

for marker in ('DATABASE="${FRONTEND_ACCEPTANCE_DB:-sc_frontend_acceptance}"', 'VITE_ODOO_DB="$3"'):
    if marker not in FRONTEND_ACCEPTANCE_SOURCE:
        raise SystemExit(f"frontend acceptance environment contract missing: {marker}")

if "VITE_ODOO_DB=sc_frontend_acceptance" in FRONTEND_ACCEPTANCE_SOURCE:
    raise SystemExit("frontend acceptance database remains hard-coded")

print("[frontend_acceptance_environment_guard] PASS")
