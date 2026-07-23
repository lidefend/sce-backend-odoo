RELEASE_DB ?= sc_release_rehearsal
RELEASE_RESTORE_DB ?= sc_release_rehearsal_restored
RELEASE_ROLLBACK_DB ?= sc_release_rehearsal_rollback
RELEASE_PROJECT ?= sc-release-rehearsal
RELEASE_ARTIFACTS ?= artifacts/release/frontend-pilot-readiness
RELEASE_PRODUCT_MODULES ?= $(shell python3 scripts/ops/tenant_module_set.py product)
RELEASE_COMPOSE = $(COMPOSE_BIN) -p $(RELEASE_PROJECT) -f docker-compose.yml -f docker-compose.release-rehearsal.yml
RELEASE_ENV = SC_ENVIRONMENT=release_rehearsal SC_ALLOW_DEMO_DATA=0 DB_NAME=$(RELEASE_DB) ODOO_DB=$(RELEASE_DB) ODOO_DBFILTER=^$(RELEASE_DB)$$ COMPOSE_PROJECT_NAME=$(RELEASE_PROJECT) DB_DATA=$(RELEASE_PROJECT)-db REDIS_DATA=$(RELEASE_PROJECT)-redis ODOO_DATA=$(RELEASE_PROJECT)-odoo ODOO_PORT=18087 NGINX_PORT=18086 FRONTEND_DIST_DIR=./frontend/apps/web/dist-release

.PHONY: verify.release.guard verify.release.tooling verify.production.release_contract release.rehearsal.prepare release.rehearsal.build release.rehearsal.runtime.up release.rehearsal.upgrade verify.release.data_compatibility release.rehearsal.fingerprint release.rehearsal.backup release.rehearsal.filestore.recover release.rehearsal.restore release.rehearsal.rollback verify.release.rehearsal verify.release.monitoring release.rehearsal.cleanup release.production.acceptance release.production.acceptance.report release.readiness.report release.pilot.all
.PHONY: release.production.identity.preflight release.production.compose.preflight release.production.infrastructure.up release.production.runtime.up release.production.db.preflight release.production.db.init release.production.module.install release.production.module.upgrade release.production.health.readonly release.production.platform.configure release.production.platform.snapshot.initialize release.production.contract.image.acceptance
.PHONY: release.production.first_fresh.cleanup.preflight release.production.first_fresh.cleanup.confirm release.production.first_fresh.cleanup release.production.admin.harden

verify.release.guard: verify.repository.release_hygiene
	@SC_ENVIRONMENT=release_rehearsal SC_ALLOW_DEMO_DATA=0 DB_NAME=$(RELEASE_DB) python3 scripts/release/rehearsal_guard.py

verify.release.tooling:
	@python3 -m py_compile scripts/release/rehearsal_guard.py scripts/release/release_data_compatibility.py scripts/release/release_readiness_report.py scripts/release/release_acceptance_report.py scripts/release/release_monitoring_check.py scripts/release/release_fingerprint_compare.py scripts/release/test_rehearsal_guard.py scripts/release/customer_package_preflight.py scripts/release/product_module_matrix.py scripts/release/test_customer_package_preflight.py scripts/verify/frontend_pilot_readiness_guard.py
	@python3 scripts/release/test_rehearsal_guard.py
	@python3 scripts/release/test_customer_package_preflight.py
	@bash -n scripts/release/product_lifecycle.sh
	@node --check scripts/release/release_static_server.mjs
	@python3 scripts/verify/frontend_pilot_readiness_guard.py
	@$(MAKE) --no-print-directory verify.production.release_contract

verify.production.release_contract:
	@python3 -m py_compile addons/smart_core/core/platform_database_contract.py addons/smart_core/tests/test_platform_database_contract.py addons/smart_construction_core/services/locked_menu_policy_contract.py scripts/release/candidate_scan_contract.py scripts/release/product_release_manifest.py scripts/release/release_source_identity.py scripts/release/production_compose_contract.py scripts/release/production_db_contract.py scripts/release/production_db_init.py scripts/release/production_admin_harden.py scripts/release/production_first_fresh_cleanup.py scripts/release/configure_colocated_platform_core.py scripts/release/initialize_colocated_platform_snapshot.py scripts/release/production_colocated_backup.py scripts/release/verify_colocated_platform_matrix.py scripts/release/test_candidate_scan_contract.py scripts/release/test_product_release.py scripts/release/test_release_source_identity.py scripts/release/test_production_compose_contract.py scripts/release/test_production_db_init.py scripts/release/test_production_admin_harden.py scripts/release/test_production_first_fresh_cleanup.py scripts/release/test_production_release_contract.py scripts/release/test_production_colocated_release.py scripts/release/test_locked_menu_policy_contract.py scripts/verify/production_git_authority_guard.py scripts/verify/test_production_git_authority_guard.py
	@python3 addons/smart_core/tests/test_platform_database_contract.py
	@python3 scripts/release/test_candidate_scan_contract.py
	@python3 scripts/release/test_product_release.py
	@python3 scripts/release/test_release_source_identity.py
	@python3 scripts/release/test_production_compose_contract.py
	@python3 scripts/release/test_production_db_init.py
	@python3 scripts/release/test_production_admin_harden.py
	@python3 scripts/release/test_production_first_fresh_cleanup.py
	@python3 scripts/release/test_production_release_contract.py
	@python3 scripts/release/test_production_colocated_release.py
	@python3 scripts/release/test_locked_menu_policy_contract.py
	@python3 scripts/verify/test_production_git_authority_guard.py
	@bash -n scripts/release/immutable_candidate_build.sh scripts/release/immutable_candidate_publish.sh scripts/release/immutable_candidate_scan.sh scripts/release/production_odoo_entrypoint.sh scripts/release/production_db_manage.sh scripts/release/production_contract_image_acceptance.sh

PRODUCTION_CONTRACT_COMPOSE = $(COMPOSE_BIN) -f docker-compose.production-candidate.yml
PRODUCTION_DB_MANAGER = $(PRODUCTION_CONTRACT_COMPOSE) run --rm --no-deps --entrypoint /usr/local/bin/production-db-manage odoo

release.production.identity.preflight:
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@test -n "$(EXPECTED_RELEASE_SHA)" || (echo "EXPECTED_RELEASE_SHA is required"; exit 2)
	@test -n "$(EXPECTED_IMAGE_DIGEST)" || (echo "EXPECTED_IMAGE_DIGEST is required"; exit 2)
	@test -n "$(IMAGE_MANIFEST_PATH)" || (echo "IMAGE_MANIFEST_PATH is required"; exit 2)
	@test -n "$(RELEASE_MANIFEST_PATH)" || (echo "RELEASE_MANIFEST_PATH is required"; exit 2)
	@test -n "$(RELEASE_MANIFEST_CHECKSUM_PATH)" || (echo "RELEASE_MANIFEST_CHECKSUM_PATH is required"; exit 2)
	@python3 scripts/release/release_source_identity.py artifact-preflight \
		--image "$(CANDIDATE_IMAGE)" \
		--image-manifest "$(IMAGE_MANIFEST_PATH)" \
		--release-manifest "$(RELEASE_MANIFEST_PATH)" \
		--release-manifest-checksum "$(RELEASE_MANIFEST_CHECKSUM_PATH)" \
		--expected-release-sha "$(EXPECTED_RELEASE_SHA)" \
		--expected-image-digest "$(EXPECTED_IMAGE_DIGEST)"

release.production.compose.preflight: release.production.identity.preflight
	@test "$(PRODUCTION_COMPOSE_PROJECT)" = "sc_production" || (echo "PRODUCTION_COMPOSE_PROJECT must be sc_production"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@test -n "$(ODOO_IMAGE_REF)" || (echo "ODOO_IMAGE_REF is required"; exit 2)
	@test -n "$(NGINX_IMAGE_REF)" || (echo "NGINX_IMAGE_REF is required"; exit 2)
	@python3 scripts/release/production_compose_contract.py \
		--project "$(PRODUCTION_COMPOSE_PROJECT)" \
		--database "$(TARGET_DB)" \
		--odoo-image-ref "$(ODOO_IMAGE_REF)" \
		--nginx-image-ref "$(NGINX_IMAGE_REF)" \
		--expected-digest "$(EXPECTED_IMAGE_DIGEST)" \
		--release-manifest "$(RELEASE_MANIFEST_PATH)"

release.production.infrastructure.up: guard.prod.danger release.production.compose.preflight
	@$(PRODUCTION_CONTRACT_COMPOSE) up -d --wait db redis

release.production.runtime.up: guard.prod.danger release.production.compose.preflight
	@$(PRODUCTION_CONTRACT_COMPOSE) up -d --wait odoo nginx

release.production.db.preflight: release.production.compose.preflight
	@$(PRODUCTION_DB_MANAGER) preflight

release.production.db.init: guard.prod.danger release.production.compose.preflight
	@$(PRODUCTION_DB_MANAGER) init

release.production.module.install: guard.prod.danger release.production.compose.preflight
	@test -n "$(TARGET_MODULE)" || (echo "TARGET_MODULE is required"; exit 2)
	@$(PRODUCTION_DB_MANAGER) install

release.production.module.upgrade: guard.prod.danger release.production.compose.preflight
	@test -n "$(TARGET_MODULE)" || (echo "TARGET_MODULE is required"; exit 2)
	@$(PRODUCTION_DB_MANAGER) upgrade

release.production.health.readonly: release.production.compose.preflight
	@$(PRODUCTION_DB_MANAGER) health

release.production.platform.configure: guard.prod.danger release.production.compose.preflight
	@test "$(SC_COLOCATED_PLATFORM_CONFIG_APPLY)" = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION" || (echo "explicit colocated platform configuration acknowledgement is required"; exit 2)
	@$(PRODUCTION_CONTRACT_COMPOSE) run --rm --no-deps \
		-e SC_COLOCATED_PLATFORM_CONFIG_APPLY="$(SC_COLOCATED_PLATFORM_CONFIG_APPLY)" \
		--entrypoint /usr/local/bin/production-db-manage odoo configure-platform

release.production.platform.snapshot.initialize: guard.prod.danger release.production.compose.preflight
	@test "$(SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY)" = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION" || (echo "explicit snapshot initialization acknowledgement is required"; exit 2)
	@test -n "$(PLATFORM_RELEASE_PRODUCT_KEY)" || (echo "PLATFORM_RELEASE_PRODUCT_KEY is required"; exit 2)
	@test -n "$(PLATFORM_RELEASE_VERSION)" || (echo "PLATFORM_RELEASE_VERSION is required"; exit 2)
	@$(PRODUCTION_CONTRACT_COMPOSE) run --rm --no-deps \
		-e SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY="$(SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY)" \
		-e PLATFORM_RELEASE_PRODUCT_KEY="$(PLATFORM_RELEASE_PRODUCT_KEY)" \
		-e PLATFORM_RELEASE_VERSION="$(PLATFORM_RELEASE_VERSION)" \
		--entrypoint /usr/local/bin/production-db-manage odoo initialize-platform-snapshot

release.production.contract.image.acceptance:
	@bash scripts/release/production_contract_image_acceptance.sh

release.production.first_fresh.cleanup.preflight:
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(PRODUCTION_COMPOSE_PROJECT)" = "sc_production" || (echo "PRODUCTION_COMPOSE_PROJECT must be sc_production"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@python3 scripts/release/production_first_fresh_cleanup.py plan

release.production.first_fresh.cleanup.confirm:
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(CONFIRM_FRESH_PRODUCTION_DEPLOY)" = "YES_DELETE_OLD_PROJECT_DATA" || \
		(echo "CONFIRM_FRESH_PRODUCTION_DEPLOY=YES_DELETE_OLD_PROJECT_DATA is required"; exit 2)

release.production.first_fresh.cleanup: guard.prod.danger release.production.first_fresh.cleanup.confirm release.production.first_fresh.cleanup.preflight
	@python3 scripts/release/production_first_fresh_cleanup.py apply

release.production.admin.harden: guard.prod.danger release.production.compose.preflight
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@test "$(CONFIRM_ADMIN_HARDEN)" = "YES_HARDEN_FRESH_PRODUCTION_ADMIN" || \
		(echo "CONFIRM_ADMIN_HARDEN=YES_HARDEN_FRESH_PRODUCTION_ADMIN is required"; exit 2)
	@ENV="$(ENV)" PROD_DANGER="$${PROD_DANGER:-}" TARGET_DB="$(TARGET_DB)" \
		CONFIRM_ADMIN_HARDEN="$(CONFIRM_ADMIN_HARDEN)" \
		python3 scripts/release/production_admin_harden.py
	@$(PRODUCTION_CONTRACT_COMPOSE) run --rm --no-deps -T \
		-e ENV=prod \
		-e PROD_DANGER=1 \
		-e CONFIRM_ADMIN_HARDEN="$(CONFIRM_ADMIN_HARDEN)" \
		-e SC_BOOTSTRAP_ADMIN_PASSWORD \
		--entrypoint /bin/sh odoo -eu -c '\
			python3 /usr/local/bin/production_db_contract.py health; \
			python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "$${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"; \
			exec odoo shell -c "$${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}" -d "$${TARGET_DB}"' \
		< scripts/release/production_admin_harden.py

release.rehearsal.prepare: verify.release.guard
	@mkdir -p $(RELEASE_ARTIFACTS)/backup $(RELEASE_ARTIFACTS)/fingerprints
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) down -v --remove-orphans
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) up -d --wait db redis odoo
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) exec -T odoo odoo -c /var/lib/odoo/odoo.conf -d $(RELEASE_DB) --no-http --workers=0 --max-cron-threads=0 -i $(RELEASE_PRODUCT_MODULES) --without-demo=all --stop-after-init

release.rehearsal.build:
	@VITE_ODOO_DB=$(RELEASE_DB) VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=release_rehearsal scripts/dev/pnpm_exec.sh -C frontend/apps/web exec vite build --outDir dist-release-rehearsal
	@mkdir -p $(RELEASE_ARTIFACTS)
	@find frontend/apps/web/dist-release-rehearsal -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $$1}' > $(RELEASE_ARTIFACTS)/frontend-candidate-build.sha256

release.rehearsal.runtime.up: verify.release.guard release.rehearsal.build
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) up -d --wait nginx
	@curl -fsS http://127.0.0.1:18086/login >/dev/null

release.rehearsal.upgrade: verify.release.guard
	@bash scripts/release/with_rehearsal_lock.sh $(RELEASE_DB) env $(RELEASE_ENV) $(RELEASE_COMPOSE) exec -T odoo odoo -c /var/lib/odoo/odoo.conf -d $(RELEASE_DB) --no-http --workers=0 --max-cron-threads=0 -u $(RELEASE_PRODUCT_MODULES) --without-demo=all --stop-after-init

verify.release.data_compatibility: verify.release.guard
	@mkdir -p $(RELEASE_ARTIFACTS)
	@$(RELEASE_ENV) RELEASE_REPORT_PATH=/tmp/release-data-compatibility.json $(RELEASE_COMPOSE) exec -T -e RELEASE_REPORT_PATH odoo odoo shell -d $(RELEASE_DB) -c /var/lib/odoo/odoo.conf < scripts/release/release_data_compatibility.py
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) cp odoo:/tmp/release-data-compatibility.json $(RELEASE_ARTIFACTS)/data-compatibility.json >/dev/null

release.rehearsal.fingerprint: verify.release.guard
	@mkdir -p $(RELEASE_ARTIFACTS)/fingerprints
	@$(RELEASE_ENV) RELEASE_FINGERPRINT_PATH=/tmp/release-fingerprint.json $(RELEASE_COMPOSE) exec -T -e RELEASE_FINGERPRINT_PATH odoo odoo shell -d $(RELEASE_DB) -c /var/lib/odoo/odoo.conf < scripts/release/release_fingerprint.py
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) cp odoo:/tmp/release-fingerprint.json $(RELEASE_ARTIFACTS)/fingerprints/$${PHASE:-current}.json >/dev/null

release.rehearsal.backup: verify.release.guard
	@$(RELEASE_ENV) RELEASE_PROJECT=$(RELEASE_PROJECT) bash scripts/release/with_rehearsal_lock.sh $(RELEASE_DB) bash scripts/release/rehearsal_backup_restore.sh backup $(RELEASE_DB)

release.rehearsal.filestore.recover: verify.release.guard
	@$(RELEASE_ENV) RELEASE_PROJECT=$(RELEASE_PROJECT) bash scripts/release/with_rehearsal_lock.sh $(RELEASE_DB) bash scripts/release/rehearsal_backup_restore.sh recover-source $(RELEASE_DB)

release.rehearsal.restore: verify.release.guard
	@$(RELEASE_ENV) RELEASE_PROJECT=$(RELEASE_PROJECT) bash scripts/release/with_rehearsal_lock.sh $(RELEASE_DB) bash scripts/release/rehearsal_backup_restore.sh restore $(RELEASE_DB) $(RELEASE_RESTORE_DB)

release.rehearsal.rollback: verify.release.guard
	@$(RELEASE_ENV) RELEASE_PROJECT=$(RELEASE_PROJECT) bash scripts/release/with_rehearsal_lock.sh $(RELEASE_DB) bash scripts/release/rehearsal_backup_restore.sh rollback $(RELEASE_DB) $(RELEASE_ROLLBACK_DB)

verify.release.rehearsal: verify.release.data_compatibility
	@python3 scripts/release/release_fingerprint_compare.py
	@curl -fsS http://127.0.0.1:18087/web/health >/dev/null
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) exec -T db pg_isready -U $(DB_USER) -d $(RELEASE_DB)

verify.release.monitoring:
	@RELEASE_HEALTH_URL=http://127.0.0.1:18087/web/health RELEASE_ARTIFACTS=$(RELEASE_ARTIFACTS) python3 scripts/release/release_monitoring_check.py

release.production.acceptance:
	@bash scripts/release/production_acceptance.sh

release.production.acceptance.report:
	@python3 scripts/release/release_acceptance_report.py

release.readiness.report:
	@python3 scripts/release/release_readiness_report.py

release.pilot.all: verify.release.tooling release.rehearsal.prepare release.rehearsal.runtime.up release.rehearsal.upgrade verify.release.rehearsal release.rehearsal.backup release.rehearsal.restore release.rehearsal.rollback verify.release.monitoring release.production.acceptance release.readiness.report

release.rehearsal.cleanup: verify.release.guard
	@$(RELEASE_ENV) $(RELEASE_COMPOSE) down --remove-orphans

# Immutable production candidate. These targets are restricted to dev/test and
# never point at the production database or production compose project.
SOURCE_SHA ?=
CANDIDATE_SHORT_SHA := $(shell printf '%s' '$(SOURCE_SHA)' | cut -c1-12)
CANDIDATE_IMAGE_REPOSITORY ?= ghcr.io/lidefend/sce-product
CANDIDATE_IMAGE ?= $(CANDIDATE_IMAGE_REPOSITORY):$(shell python3 scripts/release/product_release.py --version)
CANDIDATE_PROJECT ?= sc-production-candidate
CANDIDATE_DB ?= sc_user_data_rehearsal_candidate
HISTORY_SOURCE_DB ?= sc_demo
HISTORY_SOURCE_BACKUP ?= artifacts/production-blocker/source/daily-dev-history-source-backup
DAILY_DEV_PROJECT ?= sc-backend-odoo-dev
CANDIDATE_ARTIFACTS ?= artifacts/release/immutable-production-candidate-v1

.PHONY: release.workspace.prepare release.production.readonly_baseline release.candidate.build release.boundary.candidate.build release.candidate.publish release.candidate.scan
.PHONY: product.install product.upgrade product.verify tenant.rc.payload.export tenant.rc.profile.product tenant.rc.profile.sample tenant.rc.profile.customer tenant.rc.profile.digest.verify tenant.rc.runtime.acceptance
.PHONY: release.history.source_probe release.history.backup release.history.restore release.history.upgrade
.PHONY: release.history.source_restore
.PHONY: release.history.runtime_up release.history.runtime_down release.history.fingerprint.source_pre
.PHONY: release.history.fingerprint.candidate_pre release.history.fingerprint.candidate_post

release.workspace.prepare: guard.prod.forbid
	@test -n "$(RELEASE_WORKSPACE)" || (echo "RELEASE_WORKSPACE is required"; exit 2)
	@RELEASE_WORKSPACE="$(RELEASE_WORKSPACE)" bash scripts/release/prepare_rc_workspace.sh

release.production.readonly_baseline: guard.prod.readonly check-compose-project check-compose-env
	@CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/production_readonly_baseline.sh

release.candidate.build: guard.prod.forbid verify.repository.release_hygiene
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/immutable_candidate_build.sh

release.boundary.candidate.build: guard.prod.forbid verify.repository.release_hygiene
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_SOURCE_REF=HEAD ALLOW_BOUNDARY_BRANCH_BUILD=1 \
		CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" \
		bash scripts/release/immutable_candidate_build.sh

release.candidate.publish: guard.prod.forbid
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" \
		bash scripts/release/immutable_candidate_publish.sh

release.candidate.scan: guard.prod.forbid
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/immutable_candidate_scan.sh

PRODUCT_PROJECT ?= sc-tenant-rc-product

product.install: guard.prod.forbid
	@test -n "$(DB_NAME)" || (echo "DB_NAME is required"; exit 2)
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@DB_NAME="$(DB_NAME)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" PRODUCT_PROJECT="$(PRODUCT_PROJECT)" \
		PRODUCT_PROFILE_COMPOSE="$(PRODUCT_PROFILE_COMPOSE)" bash scripts/release/product_lifecycle.sh install

product.upgrade: guard.prod.forbid
	@test -n "$(DB_NAME)" || (echo "DB_NAME is required"; exit 2)
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@DB_NAME="$(DB_NAME)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" PRODUCT_PROJECT="$(PRODUCT_PROJECT)" \
		PRODUCT_PROFILE_COMPOSE="$(PRODUCT_PROFILE_COMPOSE)" bash scripts/release/product_lifecycle.sh upgrade

product.verify: guard.prod.forbid
	@test -n "$(DB_NAME)" || (echo "DB_NAME is required"; exit 2)
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@DB_NAME="$(DB_NAME)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" PRODUCT_PROJECT="$(PRODUCT_PROJECT)" \
		PRODUCT_PROFILE_COMPOSE="$(PRODUCT_PROFILE_COMPOSE)" bash scripts/release/product_lifecycle.sh verify

tenant.rc.payload.export: guard.prod.forbid check-compose-env
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@test -n "$(CANDIDATE_IMAGE_DIGEST)" || (echo "CANDIDATE_IMAGE_DIGEST is required"; exit 2)
	@test -n "$(RC_HISTORY_BACKUP)" || (echo "RC_HISTORY_BACKUP is required"; exit 2)
	@test -n "$(RC_TENANT_PAYLOAD_EXPORTER)" || (echo "RC_TENANT_PAYLOAD_EXPORTER is required"; exit 2)
	@test -n "$(RC_TENANT_PAYLOAD_SIGNING_KEY)" || (echo "RC_TENANT_PAYLOAD_SIGNING_KEY is required"; exit 2)
	@test -n "$(RC_TENANT_PAYLOAD_PUBLIC_KEY)" || (echo "RC_TENANT_PAYLOAD_PUBLIC_KEY is required"; exit 2)
	@test -n "$(RC_TENANT_PAYLOAD_OUTPUT)" || (echo "RC_TENANT_PAYLOAD_OUTPUT is required"; exit 2)
	@CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_IMAGE_DIGEST="$(CANDIDATE_IMAGE_DIGEST)" \
		RC_HISTORY_BACKUP="$(RC_HISTORY_BACKUP)" RC_TENANT_PAYLOAD_EXPORTER="$(RC_TENANT_PAYLOAD_EXPORTER)" \
		RC_TENANT_PAYLOAD_SIGNING_KEY="$(RC_TENANT_PAYLOAD_SIGNING_KEY)" \
		RC_TENANT_PAYLOAD_PUBLIC_KEY="$(RC_TENANT_PAYLOAD_PUBLIC_KEY)" \
		RC_TENANT_PAYLOAD_OUTPUT="$(RC_TENANT_PAYLOAD_OUTPUT)" \
		RC_PAYLOAD_ID="$(RC_PAYLOAD_ID)" RC_SOURCE_SNAPSHOT_ID="$(RC_SOURCE_SNAPSHOT_ID)" \
		RC_PAYLOAD_SIGNATURE_KEY_ID="$(RC_PAYLOAD_SIGNATURE_KEY_ID)" \
		RC_PAYLOAD_ENCRYPTION_KEY_ID="$(RC_PAYLOAD_ENCRYPTION_KEY_ID)" \
		bash scripts/release/export_authorized_tenant_payload.sh

tenant.rc.profile.product: guard.prod.forbid check-compose-env
	@CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_IMAGE_DIGEST="$(CANDIDATE_IMAGE_DIGEST)" \
		CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/tenant_rc_profile_rehearsal.sh product

tenant.rc.profile.sample: guard.prod.forbid check-compose-env
	@CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_IMAGE_DIGEST="$(CANDIDATE_IMAGE_DIGEST)" \
		CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" RC_CUSTOMER_ADDONS_ROOT="$(RC_CUSTOMER_ADDONS_ROOT)" \
		RC_SYNTHETIC_CUSTOMER_MODULE="$(RC_SYNTHETIC_CUSTOMER_MODULE)" \
		RC_SYNTHETIC_TENANT_KEY="$(RC_SYNTHETIC_TENANT_KEY)" \
		RC_SYNTHETIC_MODULE_VERSION="$(RC_SYNTHETIC_MODULE_VERSION)" \
		bash scripts/release/tenant_rc_profile_rehearsal.sh sample

tenant.rc.profile.customer: guard.prod.forbid check-compose-env
	@CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_IMAGE_DIGEST="$(CANDIDATE_IMAGE_DIGEST)" \
		CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" RC_HISTORY_BACKUP="$(RC_HISTORY_BACKUP)" \
		RC_CUSTOMER_IDENTITY_MIGRATION="$(RC_CUSTOMER_IDENTITY_MIGRATION)" \
		RC_LEGACY_CUSTOMER_MODULE="$(RC_LEGACY_CUSTOMER_MODULE)" \
		SC_CUSTOMER_ADDONS_ROOT="$(SC_CUSTOMER_ADDONS_ROOT)" \
		SC_CUSTOMER_MODULE="$(SC_CUSTOMER_MODULE)" \
		SC_CUSTOMER_ARCHIVE_SHA256="$(SC_CUSTOMER_ARCHIVE_SHA256)" \
		SC_TENANT_ID="$(SC_TENANT_ID)" SC_PAYLOAD_MANIFEST="$(SC_PAYLOAD_MANIFEST)" \
		SC_TENANT_PAYLOAD_PUBLIC_KEY="$(SC_TENANT_PAYLOAD_PUBLIC_KEY)" \
		bash scripts/release/tenant_rc_profile_rehearsal.sh customer

tenant.rc.profile.digest.verify: guard.prod.forbid
	@python3 scripts/release/verify_tenant_rc_profile_digests.py --profiles "$(CANDIDATE_ARTIFACTS)/profiles"

tenant.rc.runtime.acceptance: guard.prod.forbid check-compose-env
	@test -n "$(CANDIDATE_IMAGE)" || (echo "CANDIDATE_IMAGE is required"; exit 2)
	@test -n "$(CANDIDATE_IMAGE_DIGEST)" || (echo "CANDIDATE_IMAGE_DIGEST is required"; exit 2)
	@CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_IMAGE_DIGEST="$(CANDIDATE_IMAGE_DIGEST)" \
		CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/tenant_rc_runtime_acceptance.sh

release.history.source_probe: guard.prod.forbid check-compose-project check-compose-env
	@HISTORY_SOURCE_DB="$(HISTORY_SOURCE_DB)" HISTORY_SOURCE_BACKUP="$(HISTORY_SOURCE_BACKUP)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_history.sh source-probe

release.history.source_restore: guard.prod.forbid check-compose-project check-compose-env
	@HISTORY_SOURCE_DB="$(HISTORY_SOURCE_DB)" DAILY_DEV_PROJECT="$(DAILY_DEV_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/restore_authorized_history_source.sh

release.history.backup: guard.prod.forbid check-compose-project check-compose-env
	@HISTORY_SOURCE_DB="$(HISTORY_SOURCE_DB)" HISTORY_SOURCE_BACKUP="$(HISTORY_SOURCE_BACKUP)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_history.sh backup

release.history.restore: guard.prod.forbid check-compose-project check-compose-env
	@HISTORY_SOURCE_DB="$(HISTORY_SOURCE_DB)" CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_history.sh restore

release.history.upgrade: guard.prod.forbid check-compose-project check-compose-env
	@CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_FORMAL_MODULES="$${CANDIDATE_FORMAL_MODULES:-smart_construction_bundle}" bash scripts/release/production_candidate_history.sh upgrade

release.history.runtime_up: guard.prod.forbid check-compose-project check-compose-env
	@CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_history.sh runtime-up

release.history.runtime_down: guard.prod.forbid check-compose-project check-compose-env
	@CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_history.sh runtime-down

release.history.fingerprint.source_pre: guard.prod.forbid check-compose-project check-compose-env
	@HISTORY_SOURCE_DB="$(HISTORY_SOURCE_DB)" DAILY_DEV_PROJECT="$(DAILY_DEV_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_fingerprint.sh source source-pre

release.history.fingerprint.candidate_pre: guard.prod.forbid check-compose-project check-compose-env
	@CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_fingerprint.sh candidate candidate-pre

release.history.fingerprint.candidate_post: guard.prod.forbid check-compose-project check-compose-env
	@CANDIDATE_DB="$(CANDIDATE_DB)" CANDIDATE_PROJECT="$(CANDIDATE_PROJECT)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" bash scripts/release/production_candidate_fingerprint.sh candidate candidate-post
