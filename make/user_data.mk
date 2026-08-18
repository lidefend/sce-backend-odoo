USER_DATA_REPORT_PATH ?= /tmp/user-data-production-boundary.json
USER_DATA_PLAN_PATH ?= /tmp/user-data-demo-removal-plan.json

.PHONY: verify.user_data.production_boundary verify.user_data.role_boundary user_data.demo_impact_report user_data.demo_removal.plan user_data.demo_removal.apply verify.user_data.post_demo_removal demo.ownership_cleanup.report demo.ownership_cleanup.apply

verify.user_data.production_boundary:
	@python3 scripts/verify/user_data_production_boundary_guard.py

verify.user_data.role_boundary: verify.user_data.production_boundary
	@USER_DATA_ROLE_REPORT_PATH=$(USER_DATA_REPORT_PATH) \
		$(MAKE) --no-print-directory odoo.shell.exec < scripts/user_data/user_role_boundary_audit.py

user_data.demo_impact_report: verify.user_data.production_boundary
	@USER_DATA_ACTION=impact USER_DATA_REPORT_PATH=$(USER_DATA_REPORT_PATH) \
		$(MAKE) --no-print-directory odoo.shell.exec < scripts/user_data/user_data_production_boundary.py

user_data.demo_removal.plan: verify.user_data.production_boundary
	@USER_DATA_ACTION=plan USER_DATA_REPORT_PATH=$(USER_DATA_REPORT_PATH) USER_DATA_PLAN_PATH=$(USER_DATA_PLAN_PATH) \
		$(MAKE) --no-print-directory odoo.shell.exec < scripts/user_data/user_data_production_boundary.py

user_data.demo_removal.apply: verify.user_data.production_boundary
	@USER_DATA_ACTION=apply USER_DATA_REPORT_PATH=$(USER_DATA_REPORT_PATH) USER_DATA_PLAN_PATH=$(USER_DATA_PLAN_PATH) \
		$(MAKE) --no-print-directory odoo.shell.exec < scripts/user_data/user_data_production_boundary.py

verify.user_data.post_demo_removal: verify.user_data.production_boundary
	@USER_DATA_ACTION=verify USER_DATA_REPORT_PATH=$(USER_DATA_REPORT_PATH) \
		$(MAKE) --no-print-directory odoo.shell.exec < scripts/user_data/user_data_production_boundary.py

demo.ownership_cleanup.report: guard.prod.forbid check-compose-project check-compose-env
	@DEMO_OWNERSHIP_ACTION=report $(MAKE) --no-print-directory odoo.shell.exec < scripts/ops/demo_ownership_cleanup.py

demo.ownership_cleanup.apply: guard.prod.forbid check-compose-project check-compose-env
	@DEMO_OWNERSHIP_ACTION=apply $(MAKE) --no-print-directory odoo.shell.exec < scripts/ops/demo_ownership_cleanup.py
.PHONY: tenant.payload.validate tenant.payload.operator.grant tenant.payload.plan tenant.payload.import tenant.payload.verify tenant.payload.filestore.reconcile tenant.payload.recovery.backup tenant.payload.recovery.restore tenant.payload.rehearsal.up tenant.payload.rehearsal.install tenant.payload.rehearsal.shell tenant.payload.rehearsal.sql tenant.payload.rehearsal.down verify.tenant.payload.permission audit.tenant.boundary.legacy_carriers audit.tenant.boundary.history_counts

audit.tenant.boundary.legacy_carriers: guard.prod.forbid
	@test -n "$(SC_CUSTOMER_REPOSITORY_ROOT)" || { echo "SC_CUSTOMER_REPOSITORY_ROOT is required for the final carrier inventory" >&2; exit 2; }
	@python3 scripts/audit/tenant_boundary_06_legacy_carrier_inventory.py \
		--output docs/audit/tenant_boundary_06_legacy_carrier_inventory.csv \
		$(if $(TENANT_BOUNDARY_HISTORY_COUNTS),--history-counts "$(TENANT_BOUNDARY_HISTORY_COUNTS)",) \
		$(if $(SC_CUSTOMER_REPOSITORY_ROOT),--customer-root "$(SC_CUSTOMER_REPOSITORY_ROOT)",)

audit.tenant.boundary.history_counts: guard.prod.forbid check-compose-env
	@test -n "$(TENANT_BOUNDARY_HISTORY_COUNT_OUTPUT)" || { echo "TENANT_BOUNDARY_HISTORY_COUNT_OUTPUT is required" >&2; exit 2; }
	@python3 scripts/audit/tenant_boundary_06_history_counts.py \
		--inventory docs/audit/tenant_boundary_06_legacy_carrier_inventory.csv \
		--output "$(TENANT_BOUNDARY_HISTORY_COUNT_OUTPUT)" \
		--project "$(CANDIDATE_PROJECT)" --database "$(CANDIDATE_DB)" --db-user "$(DB_USER)" \
		$(if $(TENANT_BOUNDARY_CUSTOMER_MODULE),--customer-module "$(TENANT_BOUNDARY_CUSTOMER_MODULE)",) \
		$(if $(TENANT_BOUNDARY_CUSTOMER_LEGACY_MODULE),--customer-legacy-module "$(TENANT_BOUNDARY_CUSTOMER_LEGACY_MODULE)",)
tenant.payload.validate: guard.prod.forbid
	@test -n "$(TENANT_PAYLOAD)" || { echo "TENANT_PAYLOAD is required" >&2; exit 2; }
	@python3 scripts/tenant_payload/cli.py validate --payload "$(TENANT_PAYLOAD)" $(if $(TENANT_KEY),--tenant-key "$(TENANT_KEY)",)

tenant.payload.operator.grant: guard.prod.forbid check-compose-project check-compose-env
	@test -n "$(TENANT_PAYLOAD_OPERATOR_LOGIN)" || { echo "TENANT_PAYLOAD_OPERATOR_LOGIN is required" >&2; exit 2; }
	@test -n "$(TENANT_PAYLOAD_DB_ALLOWLIST)" || { echo "TENANT_PAYLOAD_DB_ALLOWLIST is required" >&2; exit 2; }
	@test -n "$(APPROVED_BY)" || { echo "APPROVED_BY is required" >&2; exit 2; }
	@$(RUN_ENV) DB_NAME=$(DB_NAME) bash scripts/tenant_payload/run_operator_grant.sh

tenant.payload.plan: guard.prod.forbid check-compose-project check-compose-env tenant.payload.validate
	@SC_TENANT_PAYLOAD_ACTION=plan $(RUN_ENV) bash scripts/tenant_payload/run_odoo_action.sh

tenant.payload.import: guard.prod.forbid check-compose-project check-compose-env tenant.payload.validate
	@SC_TENANT_PAYLOAD_ACTION=import $(RUN_ENV) bash scripts/tenant_payload/run_odoo_action.sh

tenant.payload.verify: guard.prod.forbid check-compose-project check-compose-env tenant.payload.validate
	@SC_TENANT_PAYLOAD_ACTION=verify $(RUN_ENV) bash scripts/tenant_payload/run_odoo_action.sh

tenant.payload.filestore.reconcile: guard.prod.forbid check-compose-project check-compose-env tenant.payload.validate
	@test "$(CONFIRM_TENANT_PAYLOAD_FILESTORE_RECONCILE)" = "1" || { echo "CONFIRM_TENANT_PAYLOAD_FILESTORE_RECONCILE=1 is required" >&2; exit 2; }
	@SC_TENANT_PAYLOAD_ACTION=reconcile $(RUN_ENV) bash scripts/tenant_payload/run_odoo_action.sh

tenant.payload.recovery.backup: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/tenant_payload/paired_recovery.sh backup

tenant.payload.recovery.restore: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/tenant_payload/paired_recovery.sh restore

tenant.payload.rehearsal.up: guard.prod.forbid
	@[[ "$(COMPOSE_PROJECT_NAME)" =~ ^sc-locked-p002r-[a-z0-9-]+$$ ]] || { echo "TPV1_REHEARSAL_PROJECT_INVALID" >&2; exit 2; }
	@[[ "$(DB_NAME)" =~ ^sc_p002r_[a-z0-9_]+$$ ]] || { echo "TPV1_REHEARSAL_DATABASE_INVALID" >&2; exit 2; }
	@test -d "$(SC_CUSTOMER_ADDONS_ROOT)" || { echo "SC_CUSTOMER_ADDONS_ROOT is invalid" >&2; exit 2; }
	@DB_CI="$(DB_NAME)" SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		$(COMPOSE_BIN) -p "$(COMPOSE_PROJECT_NAME)" -f docker-compose.ci.yml \
		-f docker-compose.tenant-payload-rehearsal.yml up -d --wait db redis odoo

tenant.payload.rehearsal.install: guard.prod.forbid
	@[[ "$(COMPOSE_PROJECT_NAME)" =~ ^sc-locked-p002r-[a-z0-9-]+$$ ]] || { echo "TPV1_REHEARSAL_PROJECT_INVALID" >&2; exit 2; }
	@[[ "$(DB_NAME)" =~ ^sc_p002r_[a-z0-9_]+$$ ]] || { echo "TPV1_REHEARSAL_DATABASE_INVALID" >&2; exit 2; }
	@test -n "$(TENANT_REHEARSAL_MODULES)" || { echo "TENANT_REHEARSAL_MODULES is required" >&2; exit 2; }
	@DB_CI="$(DB_NAME)" SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		$(COMPOSE_BIN) -p "$(COMPOSE_PROJECT_NAME)" -f docker-compose.ci.yml \
		-f docker-compose.tenant-payload-rehearsal.yml run --rm --no-deps -T \
		--entrypoint odoo odoo -c /var/lib/odoo/odoo.conf -d "$(DB_NAME)" \
		-i "$(TENANT_REHEARSAL_MODULES)" --without-demo=all --workers=0 \
		--max-cron-threads=0 --no-http --stop-after-init

tenant.payload.rehearsal.shell: guard.prod.forbid
	@[[ "$(COMPOSE_PROJECT_NAME)" =~ ^sc-locked-p002r-[a-z0-9-]+$$ ]] || { echo "TPV1_REHEARSAL_PROJECT_INVALID" >&2; exit 2; }
	@[[ "$(DB_NAME)" =~ ^sc_p002r_[a-z0-9_]+$$ ]] || { echo "TPV1_REHEARSAL_DATABASE_INVALID" >&2; exit 2; }
	@DB_CI="$(DB_NAME)" SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		$(COMPOSE_BIN) -p "$(COMPOSE_PROJECT_NAME)" -f docker-compose.ci.yml \
		-f docker-compose.tenant-payload-rehearsal.yml exec -T odoo \
		odoo shell -c /var/lib/odoo/odoo.conf -d "$(DB_NAME)" --no-http

tenant.payload.rehearsal.sql: guard.prod.forbid
	@[[ "$(COMPOSE_PROJECT_NAME)" =~ ^sc-locked-p002r-[a-z0-9-]+$$ ]] || { echo "TPV1_REHEARSAL_PROJECT_INVALID" >&2; exit 2; }
	@[[ "$(DB_NAME)" =~ ^sc_p002r_[a-z0-9_]+$$ ]] || { echo "TPV1_REHEARSAL_DATABASE_INVALID" >&2; exit 2; }
	@DB_CI="$(DB_NAME)" SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		$(COMPOSE_BIN) -p "$(COMPOSE_PROJECT_NAME)" -f docker-compose.ci.yml \
		-f docker-compose.tenant-payload-rehearsal.yml exec -T db \
		psql -X -v ON_ERROR_STOP=1 -U "$(DB_USER)" -d "$(DB_NAME)"

tenant.payload.rehearsal.down: guard.prod.forbid
	@[[ "$(COMPOSE_PROJECT_NAME)" =~ ^sc-locked-p002r-[a-z0-9-]+$$ ]] || { echo "TPV1_REHEARSAL_PROJECT_INVALID" >&2; exit 2; }
	@DB_CI="$(DB_NAME)" SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		$(COMPOSE_BIN) -p "$(COMPOSE_PROJECT_NAME)" -f docker-compose.ci.yml \
		-f docker-compose.tenant-payload-rehearsal.yml down \
		$(if $(filter 1,$(REMOVE_TENANT_REHEARSAL_VOLUMES)),-v,)

verify.tenant.payload.permission: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) DB_NAME=$(DB_NAME) bash scripts/tenant_payload/run_permission_probe.sh
