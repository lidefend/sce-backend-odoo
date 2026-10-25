# P4 offline role declaration inventory; never an authorization/runtime gate.
.PHONY: verify.general_contract.review_authority.unit
verify.general_contract.review_authority.unit:
	@python3 -m unittest scripts.verify.test_general_contract_review_authority

.PHONY: verify.local.dev.general_contract.finance_review.orm
verify.local.dev.general_contract.finance_review.orm:
	@$(MAKE) local.dev.test MODULE=smart_construction_core TEST_TAGS=general_contract_finance_review

.PHONY: verify.daily.demo.contract.api.unit daily.demo.contract.api_acceptance
verify.daily.demo.contract.api.unit: verify.general_contract.review_authority.unit
	@python3 -m unittest scripts.verify.test_daily_demo_contract_api_acceptance
daily.demo.contract.api_acceptance: verify.daily.demo.contract.api.unit daily.demo.write.recovery_gate
	@SC_DEMO_CONTRACT_KEY=$(SC_DEMO_CONTRACT_KEY) SC_DEMO_CONTRACT_RECORD_ID=$(SC_DEMO_CONTRACT_RECORD_ID) PYTHONPATH="$(CURDIR)$${PYTHONPATH:+:$$PYTHONPATH}" python3 scripts/verify/daily_demo_contract_api_acceptance.py

.PHONY: verify.daily.demo.contract.ui
verify.daily.demo.contract.ui: guard.prod.forbid $(if $(filter execute resume,$(SC_DEMO_UI_MODE)),daily.demo.write.recovery_gate,)
	@node --check scripts/verify/daily_demo_contract_ui_browser.mjs
	@node scripts/verify/daily_demo_contract_ui_policy.test.mjs
	@node scripts/verify/daily_demo_contract_ui_browser.mjs

.PHONY: verify.system.permission_role.inventory.unit audit.system.permission_role.inventory
verify.system.permission_role.inventory.unit:
	@python3 -m unittest scripts/verify/test_system_permission_role_inventory.py

audit.system.permission_role.inventory: verify.system.permission_role.inventory.unit
	@python3 scripts/verify/system_permission_role_inventory.py --output .runtime/system-permission-roles/inventory.json

.PHONY: audit.system.permission_role.write_candidates verify.system.permission_role.write_candidates
audit.system.permission_role.write_candidates: verify.system.permission_role.write_candidates

verify.system.permission_role.write_candidates: verify.system.permission_role.inventory.unit
	@python3 scripts/verify/system_permission_role_inventory.py --write-candidates --output .runtime/system-permission-roles/write-candidates.json

.PHONY: verify.system.permission_role.runtime_probe.unit audit.system.permission_role.demo_observation
verify.system.permission_role.runtime_probe.unit:
	@python3 -m unittest scripts/verify/test_system_permission_runtime_observation.py

# Existing daily demo duty and owner SSH identity; no deployment or credential write.
.PHONY: daily.demo.contract.write_acceptance daily.demo.write.recovery_gate
SC_DEMO_CONTRACT_PHASE ?= create
SC_DEMO_CONTRACT_RECORD_ID ?= 0
daily.demo.write.recovery_gate: guard.prod.forbid
	@test "$${SC_DEMO_WRITE_CONFIRM:-}" = CREATE_AND_SUBMIT_DEMO_ACCEPTANCE_CONTRACT
	@[[ "$(DAILY_CONTINUITY_TOOL_SHA)" =~ ^[0-9a-f]{40}$$ ]] && [[ "$(DAILY_RUNTIME_EXPECTED_SHA)" =~ ^[0-9a-f]{40}$$ ]]
	@[[ "$(DAILY_DEMO_PRESERVE_UUID)" =~ ^[0-9a-f-]{36}$$ ]] && [[ "$(SC_DEMO_CONTRACT_KEY)" =~ ^DEMO-DELIVERY-[A-Z0-9-]+$$ ]]
	@[[ "$(SC_DEMO_BACKUP_SET)" =~ ^sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$ ]]
	@[[ "$(SC_DEMO_CONTRACT_PHASE)" =~ ^(create|approve|reject|cross_company|readback)$$ ]] && [[ "$(SC_DEMO_CONTRACT_RECORD_ID)" =~ ^[0-9]+$$ ]]
	@ssh sc-root 'python3 -B -c '\''import sys,json; from pathlib import Path; root=Path("/opt/sce/deployment-tools/$(DAILY_CONTINUITY_TOOL_SHA)"); sys.path.insert(0,str(root/"scripts/ops")); import daily_candidate_data_continuity as c; contract=c._load_contract(root/"scripts/ops/daily_candidate_data_continuity_contract_v1.json"); runtime=c._assert_runtime(contract); assert runtime["source_revision"]=="$(DAILY_RUNTIME_EXPECTED_SHA)"; manifest=c.validate_backup(contract,Path(contract["backup_root"])/"$(SC_DEMO_BACKUP_SET)",strict_permissions=True); receipt=json.load(open("/tmp/daily-duty-recovery-restore.json")); assert receipt["backup_set_id"]==manifest["backup_set_id"] and receipt["isolated_restore_pass"] and receipt["temporary_resources_removed"]; assert manifest["sentinels_before"]["database_uuid"]=="$(DAILY_DEMO_PRESERVE_UUID)"; assert c._sentinels(contract)["database_uuid"]=="$(DAILY_DEMO_PRESERVE_UUID)"; print("recovery preflight PASS")'\'''
daily.demo.contract.write_acceptance: daily.demo.write.recovery_gate
	@ssh sc-root \
	  'python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo --env SC_DEMO_WRITE_CONFIRM=CREATE_AND_SUBMIT_DEMO_ACCEPTANCE_CONTRACT --env SC_DEMO_EXPECTED_UUID=$(DAILY_DEMO_PRESERVE_UUID) --env SC_DEMO_CONTRACT_KEY=$(SC_DEMO_CONTRACT_KEY) --env SC_DEMO_CONTRACT_PHASE=$(SC_DEMO_CONTRACT_PHASE) --env SC_DEMO_CONTRACT_RECORD_ID=$(SC_DEMO_CONTRACT_RECORD_ID)' \
	  < scripts/verify/daily_demo_contract_write_acceptance.py

.PHONY: verify.daily.demo.business_readiness.unit audit.daily.demo.business_readiness
.PHONY: verify.daily.demo.project_manager.repair.unit daily.demo.project_manager.repair
verify.daily.demo.project_manager.repair.unit:
	@python3 -m unittest scripts.verify.test_daily_demo_project_manager_repair

# Reuse the same paired-backup/UUID/revision gate as this batch's contract writes.
# Its legacy confirmation remains required in addition to this exact repair token.
daily.demo.project_manager.repair: verify.daily.demo.project_manager.repair.unit daily.demo.write.recovery_gate
	@test "$${SC_DEMO_MANAGER_REPAIR_CONFIRM:-}" = BIND_DEMO_PJ_001_MANAGER_TO_PM1
	@ssh sc-root \
	  'python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo --env SC_DEMO_MANAGER_REPAIR_CONFIRM=BIND_DEMO_PJ_001_MANAGER_TO_PM1' \
	  < scripts/verify/daily_demo_project_manager_repair.py

verify.daily.demo.business_readiness.unit:
	@python3 -m unittest scripts.verify.test_daily_demo_business_readiness

# Reuse the declared demo shell; no fixture setup and database-enforced read-only.
audit.daily.demo.business_readiness: guard.prod.forbid verify.daily.demo.business_readiness.unit
	@test -n "$(DAILY_RUNTIME_EXPECTED_SHA)" && [[ "$(DAILY_RUNTIME_EXPECTED_SHA)" =~ ^[0-9a-f]{40}$$ ]]
	@ssh -o BatchMode=yes -o ConnectTimeout=10 sc-root \
	  'test "$$(git -C /opt/projects/repos/sce-product-odoo rev-parse HEAD)" = "$(DAILY_RUNTIME_EXPECTED_SHA)" && python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo' \
	  < scripts/verify/daily_demo_business_readiness.py

.PHONY: audit.daily.demo.data_inventory
audit.daily.demo.data_inventory: guard.prod.forbid verify.daily.demo.business_readiness.unit
	@test -n "$(DAILY_RUNTIME_EXPECTED_SHA)" && [[ "$(DAILY_RUNTIME_EXPECTED_SHA)" =~ ^[0-9a-f]{40}$$ ]]
	@ssh -o BatchMode=yes -o ConnectTimeout=10 sc-root \
	  'test "$$(git -C /opt/projects/repos/sce-product-odoo rev-parse HEAD)" = "$(DAILY_RUNTIME_EXPECTED_SHA)" && python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo --env DAILY_DEMO_OBSERVATION=inventory' \
	  < scripts/verify/daily_demo_business_readiness.py

audit.system.permission_role.demo_observation: guard.prod.forbid
	@ssh -o BatchMode=yes -o ConnectTimeout=10 sc-root \
	  'python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo' \
	  < scripts/verify/system_permission_runtime_observation.py

.PHONY: audit.system.permission_role.demo_navigation
audit.system.permission_role.demo_navigation: guard.prod.forbid
	@python3 -c 'import json; from scripts.verify.system_permission_runtime_observation import validate_witness_uids; r=json.load(open(".runtime/system-permission-roles/demo-observation.json")); print(json.dumps(validate_witness_uids([x["uid"] for x in r["acl_observations"]])))' > .runtime/system-permission-roles/navigation-uids.json
	@uids="$$(cat .runtime/system-permission-roles/navigation-uids.json)"; \
	  ssh -o BatchMode=yes -o ConnectTimeout=10 sc-root \
	  "python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo --env 'ROLE_PERMISSION_OBSERVATION_UIDS=$$uids'" \
	  < scripts/verify/system_permission_runtime_observation.py

.PHONY: audit.system.permission_role.demo_navigation.diagnostic
audit.system.permission_role.demo_navigation.diagnostic: guard.prod.forbid
	@test -n "$(ROLE_PERMISSION_DIAGNOSTIC_UID)" && [[ "$(ROLE_PERMISSION_DIAGNOSTIC_UID)" =~ ^[0-9]+$$ ]] && test "$(ROLE_PERMISSION_DIAGNOSTIC_UID)" -gt 1
	@ssh -o BatchMode=yes -o ConnectTimeout=10 sc-root \
	  'python3 /opt/projects/repos/sce-product-odoo/scripts/ops/daily_runtime_duty_odoo_shell.py --duty demo --database sc_demo --env ROLE_PERMISSION_OBSERVATION_UIDS=[$(ROLE_PERMISSION_DIAGNOSTIC_UID)]' \
	  < scripts/verify/system_permission_runtime_observation.py

.PHONY: verify.local.dev.system_permission.separation.orm
verify.local.dev.system_permission.separation.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=system_permission_separation local.dev.test

.PHONY: local.dev.system_permission.cleanup.readback
local.dev.system_permission.cleanup.readback: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/system_permission_test_cleanup_readback.py

.PHONY: verify.system.permission_role.assignment.unit
verify.system.permission_role.assignment.unit:
	@python3 -m unittest scripts/verify/test_group_assignment.py

.PHONY: verify.local.dev.system_permission.approval_scope.orm
verify.local.dev.system_permission.approval_scope.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=approval_scope_authority local.dev.test

.PHONY: verify.local.dev.system_permission.reconciliation.orm
verify.local.dev.system_permission.reconciliation.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=group_authority_reconciliation local.dev.test

.PHONY: verify.local.dev.system_permission.http
verify.local.dev.system_permission.http: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=system_permission_http local.dev.test

.PHONY: local.dev.system_permission.http.prerequisite.readback
local.dev.system_permission.http.prerequisite.readback: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/system_permission_http_prerequisite_readback.py

.PHONY: verify.local.dev.system_permission.accounting.orm
verify.local.dev.system_permission.accounting.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=system_permission_accounting local.dev.test

.PHONY: verify.local.dev.system_permission.business.orm
verify.local.dev.system_permission.business.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS=system_permission_business local.dev.test

.PHONY: verify.system.permission.concurrency.unit local.contract-lifecycle.system_permission.concurrency
verify.system.permission.concurrency.unit:
	@python3 -m unittest scripts/verify/test_system_permission_concurrency_probe.py

# Commits synthetic fixtures/audit only in the registered disposable profile.
# Caller must explicitly authorize preparation/execution/discard; never auto-prepare.
local.contract-lifecycle.system_permission.concurrency: guard.prod.forbid local.contract-lifecycle.require_env
	@test "$(SC_CONFIRM_PERMISSION_CONCURRENCY)" = "RUN_ISOLATED_PERMISSION_CONCURRENCY" || { echo "explicit isolated concurrency confirmation required" >&2; exit 2; }
	@SC_CONFIRM_PERMISSION_CONCURRENCY="$(SC_CONFIRM_PERMISSION_CONCURRENCY)" \
	  SC_ACCEPTANCE_PERMISSION_HASHES="$$(python3 scripts/verify/system_permission_concurrency_probe.py --source-hashes)" \
	  $(MAKE) --no-print-directory local.contract-lifecycle.odoo-shell < scripts/verify/system_permission_concurrency_probe.py
