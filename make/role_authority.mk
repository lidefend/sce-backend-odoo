# P4 offline role declaration inventory; never an authorization/runtime gate.
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

.PHONY: verify.local.dev.system_permission.revocation_diagnosis.orm
verify.local.dev.system_permission.revocation_diagnosis.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestSystemPermissionSeparation.test_native_membership_cannot_recover_explicit_grant_origin,/smart_construction_core:TestSystemPermissionSeparation.test_revoked_role_cannot_blacklist_partner' local.dev.test

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
