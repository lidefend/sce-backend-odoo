# ======================================================
# ================== Contract ==========================
# ======================================================
.PHONY: contract.export contract.export_all contract.catalog.export contract.evidence.export contract.registry.export verify.contract.catalog verify.scene.contract.shape verify.contract.evidence gate.contract gate.contract.bootstrap gate.contract.bootstrap-pass verify.contract.lint contract.structure.fingerprint verify.contract.structure_lock contract.view_structure.fingerprint contract.view_structure.export contract.view_structure.baseline verify.contract.view_structure verify.contract.view_structure_candidate gate.contract.view_structure contract.view_carrier.export verify.contract.view_carrier gate.contract.view_carrier

VIEW_STRUCTURE_POLICY ?= scripts/verify/baselines/formal_business_product_menu_policy_v1.json
VIEW_STRUCTURE_DATABASE_POLICY ?= docs/governance/database_architecture_policy.md
VIEW_STRUCTURE_BASELINE ?= contracts/generated/product_view_structure_contract.json
VIEW_STRUCTURE_CANDIDATE ?= artifacts/contract/product_view_structure_contract.json
VIEW_STRUCTURE_CONTAINER_CANDIDATE ?= /tmp/product_view_structure_contract.json
VIEW_STRUCTURE_FINGERPRINT ?= artifacts/contract/product_view_candidate_fingerprint.json
VIEW_STRUCTURE_REPORT ?= artifacts/backend/product_view_structure_contract_guard.json
VIEW_STRUCTURE_BASELINE_SHA ?= $(shell git merge-base HEAD origin/main)
VIEW_CARRIER_CANDIDATE ?= artifacts/contract/product_view_contract_carriers_candidate.json
VIEW_CARRIER_CONTAINER_CANDIDATE ?= /tmp/product_view_contract_carriers_candidate.json
VIEW_CARRIER_SCHEMA ?= contracts/schemas/product-view-contract-carriers-v1.yaml

verify.contract.lint:
	@python3 scripts/verify/contracts_lint.py
	@$(MAKE) --no-print-directory contract.registry.export

contract.registry.export:
	@python3 scripts/contract/export_contract_registry.py

INTENT_SURFACE_MD ?= artifacts/intent_surface_report.md
INTENT_SURFACE_JSON ?= artifacts/intent_surface_report.json
CONTRACT_PREFLIGHT_INTENT_SURFACE_MD ?= artifacts/intent_surface_report.md
CONTRACT_PREFLIGHT_INTENT_SURFACE_JSON ?= artifacts/intent_surface_report.json
CONTRACT_PREFLIGHT_CONTINUE_FROM_FAILURE ?= 0

contract.export:
	@DB="$(DB_NAME)" scripts/contract/snapshot_export.sh \
	  --db "$(DB_NAME)" \
	  --user "$(CONTRACT_USER)" \
	  --case "$(CONTRACT_CASE)" \
	  --model "$(CONTRACT_MODEL)" \
	  $(if $(CONTRACT_ID),--id "$(CONTRACT_ID)",) \
	  --view_type "$(CONTRACT_VIEW)" \
	  --config "$(CONTRACT_CONFIG)" \
	  --outdir "$(CONTRACT_OUTDIR)"

contract.export_all:
	@SC_CONTRACT_STABLE=1 DB="$(DB_NAME)" CASES_FILE="docs/contract/cases.yml" OUTDIR="$(CONTRACT_OUTDIR)" CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" scripts/contract/export_all.sh

contract.catalog.export:
	@python3 scripts/contract/export_catalogs.py

contract.evidence.export:
	@python3 scripts/contract/export_evidence.py

contract.view_structure.fingerprint: guard.prod.forbid
	@test -n "$(VIEW_STRUCTURE_BASELINE_SHA)" || { echo "[contract.view_structure.fingerprint] missing baseline SHA" >&2; exit 2; }
	@python3 scripts/contract/complete_worktree_fingerprint.py \
	  --baseline "$(VIEW_STRUCTURE_BASELINE_SHA)" \
	  --output "$(VIEW_STRUCTURE_FINGERPRINT)"

contract.view_structure.export: guard.prod.forbid check-compose-project check-compose-env contract.view_structure.fingerprint
	@mkdir -p "$$(dirname "$(VIEW_STRUCTURE_CANDIDATE)")"
	@$(RUN_ENV) \
	  PRODUCT_VIEW_STRUCTURE_POLICY="$(VIEW_STRUCTURE_POLICY)" \
	  PRODUCT_VIEW_DATABASE_POLICY="$(VIEW_STRUCTURE_DATABASE_POLICY)" \
	  PRODUCT_VIEW_CANDIDATE_FINGERPRINT="$(VIEW_STRUCTURE_FINGERPRINT)" \
	  PRODUCT_VIEW_STRUCTURE_OUTPUT="$(VIEW_STRUCTURE_CONTAINER_CANDIDATE)" \
	  DB_NAME="$(DB_NAME)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/contract/export_product_view_structure.py
	@$(RUN_ENV) $(COMPOSE_BASE) exec -T $(ODOO_SERVICE) cat "$(VIEW_STRUCTURE_CONTAINER_CANDIDATE)" > "$(VIEW_STRUCTURE_CANDIDATE).tmp"
	@mv "$(VIEW_STRUCTURE_CANDIDATE).tmp" "$(VIEW_STRUCTURE_CANDIDATE)"

contract.view_structure.baseline: contract.view_structure.export
	@python3 scripts/verify/product_view_structure_contract_guard.py \
	  --manifest "$(VIEW_STRUCTURE_CANDIDATE)" --policy "$(VIEW_STRUCTURE_POLICY)" \
	  --database-policy "$(VIEW_STRUCTURE_DATABASE_POLICY)" --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" \
	  --report "$(VIEW_STRUCTURE_REPORT)"
	@mkdir -p "$$(dirname "$(VIEW_STRUCTURE_BASELINE)")"
	@cp "$(VIEW_STRUCTURE_CANDIDATE)" "$(VIEW_STRUCTURE_BASELINE).tmp"
	@mv "$(VIEW_STRUCTURE_BASELINE).tmp" "$(VIEW_STRUCTURE_BASELINE)"
	@echo "[contract.view_structure.baseline] baseline=$(VIEW_STRUCTURE_BASELINE)"

verify.contract.view_structure_candidate: contract.view_structure.export
	@python3 scripts/verify/product_view_structure_contract_guard.py \
	  --manifest "$(VIEW_STRUCTURE_CANDIDATE)" --policy "$(VIEW_STRUCTURE_POLICY)" \
	  --database-policy "$(VIEW_STRUCTURE_DATABASE_POLICY)" --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" \
	  --report "$(VIEW_STRUCTURE_REPORT)"

verify.contract.view_structure: guard.prod.forbid contract.view_structure.fingerprint
	@python3 scripts/verify/product_view_structure_contract_guard.py \
	  --manifest "$(VIEW_STRUCTURE_BASELINE)" --policy "$(VIEW_STRUCTURE_POLICY)" \
	  --database-policy "$(VIEW_STRUCTURE_DATABASE_POLICY)" --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" \
	  --report "$(VIEW_STRUCTURE_REPORT)"

gate.contract.view_structure: contract.view_structure.export
	@python3 scripts/verify/product_view_structure_contract_guard.py \
	  --manifest "$(VIEW_STRUCTURE_BASELINE)" --candidate "$(VIEW_STRUCTURE_CANDIDATE)" \
	  --policy "$(VIEW_STRUCTURE_POLICY)" --database-policy "$(VIEW_STRUCTURE_DATABASE_POLICY)" \
	  --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" --report "$(VIEW_STRUCTURE_REPORT)"

contract.view_carrier.export: guard.prod.forbid check-compose-project check-compose-env verify.contract.view_structure_candidate
	@mkdir -p "$$(dirname "$(VIEW_CARRIER_CANDIDATE)")"
	@rm -f "$(VIEW_CARRIER_CANDIDATE)" "$(VIEW_CARRIER_CANDIDATE).tmp"
	@$(RUN_ENV) $(COMPOSE_BASE) exec -T $(ODOO_SERVICE) rm -f "$(VIEW_CARRIER_CONTAINER_CANDIDATE)"
	@$(RUN_ENV) \
	  PRODUCT_VIEW_CARRIER_STRUCTURE_INPUT="$(VIEW_STRUCTURE_CANDIDATE)" \
	  PRODUCT_VIEW_CARRIER_FINGERPRINT="$(VIEW_STRUCTURE_FINGERPRINT)" \
	  PRODUCT_VIEW_CARRIER_OUTPUT="$(VIEW_CARRIER_CONTAINER_CANDIDATE)" \
	  DB_NAME="$(DB_NAME)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/contract/export_product_view_contract_carriers.py
	@$(RUN_ENV) $(COMPOSE_BASE) exec -T $(ODOO_SERVICE) cat "$(VIEW_CARRIER_CONTAINER_CANDIDATE)" > "$(VIEW_CARRIER_CANDIDATE).tmp"
	@mv "$(VIEW_CARRIER_CANDIDATE).tmp" "$(VIEW_CARRIER_CANDIDATE)"

verify.contract.view_carrier: contract.view_carrier.export
	@PYTHONPATH="$(ROOT_DIR)" python3 scripts/verify/product_view_contract_carriers_guard.py \
	  --artifact "$(VIEW_CARRIER_CANDIDATE)" --structure "$(VIEW_STRUCTURE_CANDIDATE)" \
	  --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" --schema "$(VIEW_CARRIER_SCHEMA)"

gate.contract.view_carrier: verify.contract.view_carrier
	@echo "[gate.contract.view_carrier] PASS artifact=$(VIEW_CARRIER_CANDIDATE)"

VIEW_NORMALIZED_CAPABILITY_MAP ?= contracts/product/native-view-normalized-capability-map-v1.yaml
VIEW_NORMALIZED_CAPABILITY_MAP_SCHEMA ?= contracts/schemas/native-view-normalized-capability-map-v1.yaml
VIEW_CAPABILITY_TAXONOMY ?= contracts/product/native-view-capability-taxonomy-v1.yaml
VIEW_CAPABILITY_REASONS ?= contracts/product/native-view-capability-reason-codes-v1.yaml

.PHONY: verify.contract.native_view_normalized_map gate.contract.native_view_normalized_map
verify.contract.native_view_normalized_map: verify.contract.view_carrier
	@PYTHONPATH="$(ROOT_DIR)" python3 scripts/verify/native_view_normalized_capability_map_guard.py \
	  --structure "$(VIEW_STRUCTURE_CANDIDATE)" --carrier "$(VIEW_CARRIER_CANDIDATE)" \
	  --fingerprint "$(VIEW_STRUCTURE_FINGERPRINT)" --carrier-schema "$(VIEW_CARRIER_SCHEMA)" \
	  --taxonomy "$(VIEW_CAPABILITY_TAXONOMY)" \
	  --normalized-map "$(VIEW_NORMALIZED_CAPABILITY_MAP)" --reasons "$(VIEW_CAPABILITY_REASONS)" \
	  --schema "$(VIEW_NORMALIZED_CAPABILITY_MAP_SCHEMA)"

gate.contract.native_view_normalized_map: verify.contract.native_view_normalized_map
	@echo "[gate.contract.native_view_normalized_map] PASS map=$(VIEW_NORMALIZED_CAPABILITY_MAP)"

verify.contract.catalog: guard.prod.forbid
	@python3 scripts/verify/intent_cases_integrity_guard.py --cases-file docs/contract/cases.yml
	@$(MAKE) --no-print-directory contract.catalog.export
	@test -s docs/contract/exports/intent_catalog.json || (echo "❌ intent_catalog.json missing" && exit 2)
	@test -s docs/contract/exports/scene_catalog.json || (echo "❌ scene_catalog.json missing" && exit 2)
	@python3 scripts/verify/intent_cases_catalog_guard.py --cases-file docs/contract/cases.yml --catalog docs/contract/exports/intent_catalog.json
	@python3 scripts/verify/intent_catalog_case_coverage_guard.py --cases-file docs/contract/cases.yml --catalog docs/contract/exports/intent_catalog.json
	@python3 scripts/verify/intent_catalog_inferred_guard.py --catalog docs/contract/exports/intent_catalog.json
	@python3 scripts/verify/intent_catalog_example_shape_guard.py --catalog docs/contract/exports/intent_catalog.json
	@python3 scripts/verify/intent_catalog_snapshot_reference_guard.py --catalog docs/contract/exports/intent_catalog.json
	@python3 -c 'import json; from pathlib import Path; i=json.loads(Path("docs/contract/exports/intent_catalog.json").read_text(encoding="utf-8")); s=json.loads(Path("docs/contract/exports/scene_catalog.json").read_text(encoding="utf-8")); assert isinstance(i.get("intents"), list) and i["intents"]; assert isinstance(s.get("scenes"), list) and s["scenes"]; print("[verify.contract.catalog] PASS")'

verify.scene.contract.shape: guard.prod.forbid
	@$(MAKE) --no-print-directory contract.catalog.export
	@python3 scripts/verify/scene_contract_shape_guard.py --catalog docs/contract/exports/scene_catalog.json --report artifacts/scene_contract_shape_guard.json

verify.contract.evidence: guard.prod.forbid
	@$(MAKE) --no-print-directory verify.contract.preflight
	@test -s artifacts/contract/phase11_1_contract_evidence.json || (echo "❌ phase11_1_contract_evidence.json missing" && exit 2)
	@test -s artifacts/contract/phase11_1_contract_evidence.md || (echo "❌ phase11_1_contract_evidence.md missing" && exit 2)
	@echo "[verify.contract.evidence] PASS"

gate.contract:
	@$(MAKE) --no-print-directory verify.contract.preflight
	@DB="$(DB_NAME)" CASES_FILE="docs/contract/cases.yml" REF_DIR="docs/contract/snapshots" CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" scripts/contract/gate_contract.sh

gate.contract.bootstrap:
	@$(MAKE) --no-print-directory verify.contract.preflight
	@DB="$(DB_NAME)" CASES_FILE="docs/contract/cases.yml" REF_DIR="docs/contract/snapshots" CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" scripts/contract/gate_contract.sh --bootstrap

gate.contract.bootstrap-pass:
	@$(MAKE) --no-print-directory verify.contract.preflight
	@DB="$(DB_NAME)" CASES_FILE="docs/contract/cases.yml" REF_DIR="docs/contract/snapshots" CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" scripts/contract/gate_contract.sh --bootstrap --bootstrap-pass

# --- Contract structure fingerprint (hard lock) -----------------------
# The fingerprint captures contract-relevant code structure (field
# declarations + state-machine definitions).  If the code changes in
# ways that affect the contract, the fingerprint changes and CI fails
# unless the contract YAML under contracts/ was also updated.

.PHONY: contract.structure.fingerprint verify.contract.structure_lock

contract.structure.fingerprint: guard.prod.forbid
	@python3 scripts/ci/generate_contract_structure_fingerprint.py --write

# verify.contract.structure_lock is defined in make/ci.mk
