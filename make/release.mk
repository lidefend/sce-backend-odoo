RELEASE_DB ?= sc_release_rehearsal
RELEASE_RESTORE_DB ?= sc_release_rehearsal_restored
RELEASE_ROLLBACK_DB ?= sc_release_rehearsal_rollback
RELEASE_PROJECT ?= sc-release-rehearsal
RELEASE_ARTIFACTS ?= artifacts/release/frontend-pilot-readiness
RELEASE_PRODUCT_MODULES ?= $(shell python3 scripts/ops/tenant_module_set.py product)
ADMIN_IDENTITY_BASELINE_MODE ?= dry-run
ADMIN_IDENTITY_LOGIN ?= admin
ADMIN_IDENTITY_EXPECTED_USER_COUNT ?= 1
ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE ?= restricted
PRODUCTION_ACCEPTANCE_PACKAGE_LOCK := scripts/ops/production_acceptance_package_v1.sha256
PRODUCTION_ACCEPTANCE_PACKAGE_DIGEST := $(strip $(shell cat $(PRODUCTION_ACCEPTANCE_PACKAGE_LOCK) 2>/dev/null))
ACCEPTANCE_HARNESS_OUTPUT ?= artifacts/backend/production_acceptance_harness.json
ACCEPTANCE_PACKAGE_DIGEST ?=
ACCEPTANCE_RUN_COUNT ?= 1
export ACCEPTANCE_PASSWORD
RELEASE_COMPOSE = $(COMPOSE_BIN) -p $(RELEASE_PROJECT) -f docker-compose.yml -f docker-compose.release-rehearsal.yml
RELEASE_ENV = SC_ENVIRONMENT=release_rehearsal SC_ALLOW_DEMO_DATA=0 DB_NAME=$(RELEASE_DB) ODOO_DB=$(RELEASE_DB) ODOO_DBFILTER=^$(RELEASE_DB)$$ COMPOSE_PROJECT_NAME=$(RELEASE_PROJECT) DB_DATA=$(RELEASE_PROJECT)-db REDIS_DATA=$(RELEASE_PROJECT)-redis ODOO_DATA=$(RELEASE_PROJECT)-odoo ODOO_PORT=18087 NGINX_PORT=18086 FRONTEND_DIST_DIR=./frontend/apps/web/dist-release

.PHONY: verify.release.guard verify.release.tooling verify.production.release_contract release.rehearsal.prepare release.rehearsal.build release.rehearsal.runtime.up release.rehearsal.upgrade verify.release.data_compatibility release.rehearsal.fingerprint release.rehearsal.backup release.rehearsal.filestore.recover release.rehearsal.restore release.rehearsal.rollback verify.release.rehearsal verify.release.monitoring release.rehearsal.cleanup release.production.acceptance release.production.acceptance.report release.readiness.report release.pilot.all
.PHONY: release.production.identity.preflight release.production.compose.preflight release.production.infrastructure.up release.production.runtime.up release.production.db.preflight release.production.db.init release.production.module.install release.production.module.upgrade release.production.health.readonly release.production.platform.configure release.production.platform.snapshot.initialize release.production.contract.image.acceptance
.PHONY: release.production.first_fresh.cleanup.preflight release.production.first_fresh.cleanup.confirm release.production.first_fresh.cleanup release.production.admin.harden release.production.admin_identity.baseline release.production.formal_modules.install_missing
.PHONY: production.backup.install.preflight production.backup.install production.backup.run production.restore.rehearsal production.restore.cleanup production.backup.timer.restore verify.production.backup_restore_contract
.PHONY: verify.production.acceptance.harness acceptance.package.verify verify.production.promotion.config.preflight release.daily_dev.production_acceptance.harness release.production.acceptance.harness release.daily_dev.promotion.config.preflight release.production.promotion.config.preflight

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

verify.production.acceptance.harness: guard.prod.forbid
	@python3 -m py_compile scripts/ops/production_acceptance_harness.py scripts/ops/test_production_acceptance_harness.py scripts/ops/production_promotion_config_preflight.py scripts/ops/test_production_promotion_config_preflight.py scripts/ops/safe_worktree_cleanup.py scripts/ops/test_safe_worktree_cleanup.py
	@python3 -m unittest scripts/ops/test_production_acceptance_harness.py scripts/ops/test_production_promotion_config_preflight.py scripts/ops/test_safe_worktree_cleanup.py
	@$(MAKE) --no-print-directory acceptance.package.verify

verify.production.promotion.config.preflight: guard.prod.forbid
	@python3 -m py_compile scripts/ops/production_promotion_config_preflight.py scripts/ops/test_production_promotion_config_preflight.py
	@python3 -m unittest scripts/ops/test_production_promotion_config_preflight.py
	@$(MAKE) --no-print-directory acceptance.package.verify

acceptance.package.verify:
	@test -s "$(PRODUCTION_ACCEPTANCE_PACKAGE_LOCK)" || (echo "acceptance package lock is missing"; exit 2)
	@observed="$$(python3 scripts/ops/production_acceptance_harness.py --print-package-digest)"; \
	  test "$$observed" = "$(PRODUCTION_ACCEPTANCE_PACKAGE_DIGEST)" || \
	    (echo "acceptance package digest drift expected=$(PRODUCTION_ACCEPTANCE_PACKAGE_DIGEST) observed=$$observed"; exit 2); \
	  if [ -n "$(ACCEPTANCE_PACKAGE_DIGEST)" ] && [ "$(ACCEPTANCE_PACKAGE_DIGEST)" != "$$observed" ]; then \
	    echo "requested acceptance package digest does not match immutable package"; exit 2; \
	  fi; \
	  echo "[acceptance.package.verify] PASS digest=$$observed"

release.daily_dev.production_acceptance.harness: ACCEPTANCE_RUN_COUNT := 2
release.daily_dev.production_acceptance.harness: ACCEPTANCE_PACKAGE_DIGEST := $(PRODUCTION_ACCEPTANCE_PACKAGE_DIGEST)
release.daily_dev.production_acceptance.harness: guard.prod.forbid verify.production.acceptance.harness
	@test "$(ENV)" = "dev" || (echo "ENV=dev is required"; exit 2)
	@test "$(DB_NAME)" = "sc_demo" || (echo "DB_NAME=sc_demo is required"; exit 2)
	@test -n "$(ACCEPTANCE_BASE_URL)" || (echo "ACCEPTANCE_BASE_URL is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" || (echo "ACCEPTANCE_LOGIN is required"; exit 2)
	@test -n "$$ACCEPTANCE_PASSWORD" || (echo "ACCEPTANCE_PASSWORD is required"; exit 2)
	@ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" DB_NAME="$(DB_NAME)" \
	  ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_RUN_COUNT="$(ACCEPTANCE_RUN_COUNT)" \
	  ACCEPTANCE_PACKAGE_DIGEST="$(ACCEPTANCE_PACKAGE_DIGEST)" \
	  ACCEPTANCE_HARNESS_OUTPUT="$(ACCEPTANCE_HARNESS_OUTPUT)" \
	  python3 scripts/ops/production_acceptance_harness.py

release.production.acceptance.harness: guard.prod.readonly acceptance.package.verify
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test -n "$(DB_NAME)" || (echo "DB_NAME is required"; exit 2)
	@test -n "$(ACCEPTANCE_BASE_URL)" || (echo "ACCEPTANCE_BASE_URL is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" || (echo "ACCEPTANCE_LOGIN is required"; exit 2)
	@test -n "$$ACCEPTANCE_PASSWORD" || (echo "ACCEPTANCE_PASSWORD is required"; exit 2)
	@test -n "$(ACCEPTANCE_PACKAGE_DIGEST)" || (echo "ACCEPTANCE_PACKAGE_DIGEST is required"; exit 2)
	@test "$(ACCEPTANCE_RUN_COUNT)" = "1" || (echo "production ACCEPTANCE_RUN_COUNT must be 1"; exit 2)
	@ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" DB_NAME="$(DB_NAME)" \
	  ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_RUN_COUNT="$(ACCEPTANCE_RUN_COUNT)" \
	  ACCEPTANCE_PACKAGE_DIGEST="$(ACCEPTANCE_PACKAGE_DIGEST)" \
	  ACCEPTANCE_HARNESS_OUTPUT="$(ACCEPTANCE_HARNESS_OUTPUT)" \
	  python3 scripts/ops/production_acceptance_harness.py

PROMOTION_CONFIG_FILE ?=
PROMOTION_SECRET_FILE ?=
PROMOTION_READINESS_OUTPUT ?=
PROMOTION_PREFLIGHT_RUN_COUNT ?= 1

release.daily_dev.promotion.config.preflight: guard.prod.forbid acceptance.package.verify
	@test "$(ENV)" = "dev" || (echo "ENV=dev is required"; exit 2)
	@test -n "$(PROMOTION_CONFIG_FILE)" || (echo "PROMOTION_CONFIG_FILE is required"; exit 2)
	@test -n "$(PROMOTION_SECRET_FILE)" || (echo "PROMOTION_SECRET_FILE is required"; exit 2)
	@test -n "$(PROMOTION_READINESS_OUTPUT)" || (echo "PROMOTION_READINESS_OUTPUT is required"; exit 2)
	@python3 scripts/ops/production_promotion_config_preflight.py \
	  --config-file "$(PROMOTION_CONFIG_FILE)" \
	  --secret-file "$(PROMOTION_SECRET_FILE)" \
	  --output "$(PROMOTION_READINESS_OUTPUT)" \
	  --run-http \
	  --run-count "2" \
	  --expected-environment daily \
	  --skip-image-check

release.production.promotion.config.preflight: guard.prod.readonly acceptance.package.verify
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test -n "$(PROMOTION_CONFIG_FILE)" || (echo "PROMOTION_CONFIG_FILE is required"; exit 2)
	@test -n "$(PROMOTION_SECRET_FILE)" || (echo "PROMOTION_SECRET_FILE is required"; exit 2)
	@test -n "$(PROMOTION_READINESS_OUTPUT)" || (echo "PROMOTION_READINESS_OUTPUT is required"; exit 2)
	@python3 scripts/ops/production_promotion_config_preflight.py \
	  --config-file "$(PROMOTION_CONFIG_FILE)" \
	  --secret-file "$(PROMOTION_SECRET_FILE)" \
	  --output "$(PROMOTION_READINESS_OUTPUT)" \
	  --run-http \
	  --run-count "$(PROMOTION_PREFLIGHT_RUN_COUNT)" \
	  --expected-environment production

verify.production.release_contract:
	@python3 -m py_compile addons/smart_core/core/platform_database_contract.py addons/smart_core/tests/test_platform_database_contract.py addons/smart_construction_core/services/locked_menu_policy_contract.py scripts/release/candidate_scan_contract.py scripts/release/release_candidate.py scripts/release/release_candidate_report.py scripts/release/release_publication.py scripts/release/product_release_manifest.py scripts/release/release_source_identity.py scripts/release/production_compose_contract.py scripts/release/production_db_contract.py scripts/release/production_db_init.py scripts/release/production_admin_harden.py scripts/release/production_admin_identity_baseline.py scripts/release/production_formal_module_install.py scripts/release/production_formal_module_state.py scripts/release/production_first_fresh_cleanup.py scripts/release/configure_colocated_platform_core.py scripts/release/initialize_colocated_platform_snapshot.py scripts/release/production_colocated_backup.py scripts/release/production_backup_restore.py scripts/ops/production_backup_install.py scripts/ops/production_acceptance_harness.py scripts/ops/test_production_acceptance_harness.py scripts/ops/production_promotion_config_preflight.py scripts/ops/test_production_promotion_config_preflight.py scripts/ops/safe_worktree_cleanup.py scripts/ops/test_safe_worktree_cleanup.py scripts/ops/rc6_candidate_identity_freeze.py scripts/ops/test_rc6_candidate_identity_freeze.py scripts/release/verify_colocated_platform_matrix.py scripts/release/test_candidate_scan_contract.py scripts/release/test_release_candidate.py scripts/release/test_release_publication.py scripts/release/test_product_release.py scripts/release/test_release_source_identity.py scripts/release/test_production_compose_contract.py scripts/release/test_production_db_init.py scripts/release/test_production_admin_harden.py scripts/release/test_production_admin_identity_baseline.py scripts/release/test_production_formal_module_install.py scripts/release/test_production_first_fresh_cleanup.py scripts/release/test_production_release_contract.py scripts/release/test_production_colocated_release.py scripts/release/test_production_backup_restore_contract.py scripts/release/test_locked_menu_policy_contract.py scripts/verify/production_git_authority_guard.py scripts/verify/test_production_git_authority_guard.py
	@python3 addons/smart_core/tests/test_platform_database_contract.py
	@python3 scripts/release/test_candidate_scan_contract.py
	@python3 scripts/release/test_release_candidate.py
	@python3 scripts/release/test_release_publication.py
	@python3 scripts/release/test_product_release.py
	@python3 scripts/release/test_release_source_identity.py
	@python3 scripts/release/test_production_compose_contract.py
	@python3 scripts/release/test_production_db_init.py
	@python3 scripts/release/test_production_admin_harden.py
	@python3 scripts/release/test_production_admin_identity_baseline.py
	@python3 scripts/release/test_production_formal_module_install.py
	@python3 scripts/release/test_production_first_fresh_cleanup.py
	@python3 scripts/release/test_production_release_contract.py
	@python3 scripts/release/test_production_colocated_release.py
	@python3 scripts/release/test_production_backup_restore_contract.py
	@python3 scripts/release/test_locked_menu_policy_contract.py
	@python3 -m unittest scripts/ops/test_production_acceptance_harness.py scripts/ops/test_production_promotion_config_preflight.py scripts/ops/test_safe_worktree_cleanup.py
	@$(MAKE) --no-print-directory acceptance.package.verify
	@python3 scripts/verify/test_production_git_authority_guard.py
	@python3 scripts/ops/test_rc6_candidate_identity_freeze.py
	@python3 scripts/ops/rc6_candidate_identity_freeze.py verify-declaration --declaration config/releases/rc6_candidate.json
	@$(MAKE) --no-print-directory daily.candidate.continuity.test
	@$(MAKE) --no-print-directory daily.candidate.sentinel.test
	@$(MAKE) --no-print-directory daily.candidate.clone_rehearsal.test
	@bash -n scripts/release/immutable_candidate_build.sh scripts/release/immutable_candidate_publish.sh scripts/release/immutable_candidate_scan.sh scripts/release/production_odoo_entrypoint.sh scripts/release/production_db_manage.sh scripts/release/production_contract_image_acceptance.sh

BACKUP_INSTALL_ROOT ?= /opt/ops
BACKUP_ROOT ?= /data/backups/sc_production
BACKUP_FILESTORE_ROOT ?= /opt/sce-runtime/filestore
BACKUP_DB_CONTAINER ?= sc_production-db-1
BACKUP_ODOO_CONTAINER ?= sc_production-odoo-1
BACKUP_TOOL_SOURCE_SHA ?=
EXPECTED_LIVE_MAIN_SHA ?=
BACKUP_ENCRYPTION_STATUS ?=
BACKUP_RETENTION_DAYS ?=
BACKUP_DIR ?=
RESTORE_ID ?=
RESTORE_REPORT ?=
RESTORE_ODOO_IMAGE ?=
RESTORE_POSTGRES_IMAGE ?=
BACKUP_INSTALL_ROLLBACK_MANIFEST ?=

production.backup.install.preflight:
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(PRODUCTION_COMPOSE_PROJECT)" = "sc_production" || (echo "PRODUCTION_COMPOSE_PROJECT must be sc_production"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@EXPECTED_BACKUP_TOOL_SOURCE_SHA="$(BACKUP_TOOL_SOURCE_SHA)" \
		EXPECTED_LIVE_MAIN_SHA="$(EXPECTED_LIVE_MAIN_SHA)" \
		PRODUCTION_COMPOSE_PROJECT="$(PRODUCTION_COMPOSE_PROJECT)" \
		BACKUP_TARGET_DB="$(TARGET_DB)" \
		BACKUP_DB_CONTAINER="$(BACKUP_DB_CONTAINER)" \
		BACKUP_ODOO_CONTAINER="$(BACKUP_ODOO_CONTAINER)" \
		BACKUP_FILESTORE_ROOT="$(BACKUP_FILESTORE_ROOT)" \
		BACKUP_INSTALL_ROOT="$(BACKUP_INSTALL_ROOT)" \
		BACKUP_ROOT="$(BACKUP_ROOT)" \
		BACKUP_ENCRYPTION_STATUS="$(BACKUP_ENCRYPTION_STATUS)" \
		BACKUP_RETENTION_DAYS="$(BACKUP_RETENTION_DAYS)" \
		python3 scripts/ops/production_backup_install.py preflight

production.backup.install: guard.prod.danger
	@test "$(CONFIRM_BACKUP_TOOL_INSTALL)" = "YES_INSTALL_GOVERNED_BACKUP_TOOL" || (echo "exact backup tool installation acknowledgement is required"; exit 2)
	@$(MAKE) --no-print-directory production.backup.install.preflight
	@EXPECTED_BACKUP_TOOL_SOURCE_SHA="$(BACKUP_TOOL_SOURCE_SHA)" \
		EXPECTED_LIVE_MAIN_SHA="$(EXPECTED_LIVE_MAIN_SHA)" \
		PRODUCTION_COMPOSE_PROJECT="$(PRODUCTION_COMPOSE_PROJECT)" \
		BACKUP_TARGET_DB="$(TARGET_DB)" \
		BACKUP_DB_CONTAINER="$(BACKUP_DB_CONTAINER)" \
		BACKUP_ODOO_CONTAINER="$(BACKUP_ODOO_CONTAINER)" \
		BACKUP_FILESTORE_ROOT="$(BACKUP_FILESTORE_ROOT)" \
		BACKUP_INSTALL_ROOT="$(BACKUP_INSTALL_ROOT)" \
		BACKUP_ROOT="$(BACKUP_ROOT)" \
		BACKUP_ENCRYPTION_STATUS="$(BACKUP_ENCRYPTION_STATUS)" \
		BACKUP_RETENTION_DAYS="$(BACKUP_RETENTION_DAYS)" \
		CONFIRM_BACKUP_TOOL_INSTALL="$(CONFIRM_BACKUP_TOOL_INSTALL)" \
		python3 scripts/ops/production_backup_install.py install

production.backup.run: guard.prod.danger
	@test "$(CONFIRM_PRODUCTION_BACKUP)" = "YES_CREATE_SC_PRODUCTION_TRIPLE_BACKUP" || (echo "exact production backup acknowledgement is required"; exit 2)
	@systemctl start scems-production-backup.service
	@systemctl show scems-production-backup.service --property=Result --value | grep -qx success

production.restore.rehearsal: guard.prod.danger
	@test "$(CONFIRM_RESTORE_REHEARSAL)" = "YES_RUN_ISOLATED_RESTORE_REHEARSAL" || (echo "exact restore rehearsal acknowledgement is required"; exit 2)
	@test -n "$(BACKUP_DIR)" -a -n "$(RESTORE_ID)" -a -n "$(RESTORE_REPORT)" || (echo "BACKUP_DIR, RESTORE_ID and RESTORE_REPORT are required"; exit 2)
	@test -n "$(RESTORE_ODOO_IMAGE)" -a -n "$(RESTORE_POSTGRES_IMAGE)" || (echo "immutable rehearsal images are required"; exit 2)
	@set -a; . /etc/scems/production-backup.env; set +a; \
		/opt/ops/production_backup_restore.py restore-rehearsal \
			--backup-dir "$(BACKUP_DIR)" \
			--restore-id "$(RESTORE_ID)" \
			--odoo-image "$(RESTORE_ODOO_IMAGE)" \
			--postgres-image "$(RESTORE_POSTGRES_IMAGE)" \
			--report "$(RESTORE_REPORT)"

production.restore.cleanup: guard.prod.danger
	@test "$(CONFIRM_RESTORE_CLEANUP)" = "YES_CLEANUP_SCOPED_RESTORE_RESOURCES" || (echo "exact restore cleanup acknowledgement is required"; exit 2)
	@test -n "$(RESTORE_REPORT)" || (echo "RESTORE_REPORT is required"; exit 2)
	@/opt/ops/production_backup_restore.py cleanup-rehearsal --report "$(RESTORE_REPORT)"

production.backup.timer.restore: guard.prod.danger
	@test "$(CONFIRM_BACKUP_TIMER_RESTORE)" = "YES_RESTORE_VERIFIED_BACKUP_TIMER" || (echo "exact timer restoration acknowledgement is required"; exit 2)
	@test -n "$(BACKUP_INSTALL_ROLLBACK_MANIFEST)" -a -n "$(BACKUP_DIR)" -a -n "$(RESTORE_REPORT)" || (echo "timer evidence paths are required"; exit 2)
	@CONFIRM_BACKUP_TIMER_RESTORE="$(CONFIRM_BACKUP_TIMER_RESTORE)" \
		/opt/ops/production_backup_install.py timer-restore \
			--rollback-manifest "$(BACKUP_INSTALL_ROLLBACK_MANIFEST)" \
			--backup-dir "$(BACKUP_DIR)" \
			--restore-report "$(RESTORE_REPORT)"

verify.production.backup_restore_contract:
	@python3 -m py_compile scripts/release/production_backup_restore.py scripts/ops/production_backup_install.py scripts/release/test_production_backup_restore_contract.py
	@python3 scripts/release/test_production_backup_restore_contract.py

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

release.production.admin_identity.baseline: guard.prod.danger release.production.compose.preflight
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@test "$(ADMIN_IDENTITY_BASELINE_MODE)" = "dry-run" -o "$(ADMIN_IDENTITY_BASELINE_MODE)" = "apply" || \
		(echo "ADMIN_IDENTITY_BASELINE_MODE must be dry-run or apply"; exit 2)
	@test "$(ADMIN_IDENTITY_LOGIN)" = "admin" || (echo "ADMIN_IDENTITY_LOGIN must be admin"; exit 2)
	@test "$(ADMIN_IDENTITY_EXPECTED_USER_COUNT)" = "1" || (echo "ADMIN_IDENTITY_EXPECTED_USER_COUNT must be 1"; exit 2)
	@test "$(ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE)" = "restricted" || (echo "ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE must be restricted"; exit 2)
	@test -n "$(ADMIN_IDENTITY_RUN_ID)" || (echo "ADMIN_IDENTITY_RUN_ID is required"; exit 2)
	@test -n "$(ADMIN_IDENTITY_TOOL_SOURCE_SHA)" || (echo "ADMIN_IDENTITY_TOOL_SOURCE_SHA is required"; exit 2)
	@test -n "$(ADMIN_IDENTITY_DEPLOYED_PATH)" || (echo "ADMIN_IDENTITY_DEPLOYED_PATH is required"; exit 2)
	@test -n "$(ADMIN_IDENTITY_EVIDENCE_OUTPUT)" || (echo "ADMIN_IDENTITY_EVIDENCE_OUTPUT is required"; exit 2)
	@if [ "$(ADMIN_IDENTITY_BASELINE_MODE)" = "apply" ]; then \
		test "$(CONFIRM_ADMIN_IDENTITY_BASELINE)" = "YES_APPLY_FRESH_PRODUCTION_ADMIN_IDENTITY_BASELINE" || \
			(echo "CONFIRM_ADMIN_IDENTITY_BASELINE=YES_APPLY_FRESH_PRODUCTION_ADMIN_IDENTITY_BASELINE is required"; exit 2); \
	fi
	@ENV="$(ENV)" PROD_DANGER="$${PROD_DANGER:-}" TARGET_DB="$(TARGET_DB)" \
		ADMIN_IDENTITY_BASELINE_MODE="$(ADMIN_IDENTITY_BASELINE_MODE)" \
		ADMIN_IDENTITY_LOGIN="$(ADMIN_IDENTITY_LOGIN)" \
		ADMIN_IDENTITY_EXPECTED_USER_COUNT="$(ADMIN_IDENTITY_EXPECTED_USER_COUNT)" \
		ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE="$(ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE)" \
		ADMIN_IDENTITY_RUN_ID="$(ADMIN_IDENTITY_RUN_ID)" \
		ADMIN_IDENTITY_TOOL_SOURCE_SHA="$(ADMIN_IDENTITY_TOOL_SOURCE_SHA)" \
		ADMIN_IDENTITY_DEPLOYED_PATH="$(ADMIN_IDENTITY_DEPLOYED_PATH)" \
		ADMIN_IDENTITY_EVIDENCE_OUTPUT="$(ADMIN_IDENTITY_EVIDENCE_OUTPUT)" \
		CONFIRM_ADMIN_IDENTITY_BASELINE="$(CONFIRM_ADMIN_IDENTITY_BASELINE)" \
		FORMAL_MODULE_CONTRACT="$(RELEASE_PRODUCT_MODULES)" \
		python3 scripts/release/production_admin_identity_baseline.py
	@$(PRODUCTION_CONTRACT_COMPOSE) run --rm --no-deps -T \
		-e ENV=prod \
		-e PROD_DANGER=1 \
		-e TARGET_DB="$(TARGET_DB)" \
		-e ADMIN_IDENTITY_BASELINE_MODE="$(ADMIN_IDENTITY_BASELINE_MODE)" \
		-e ADMIN_IDENTITY_LOGIN="$(ADMIN_IDENTITY_LOGIN)" \
		-e ADMIN_IDENTITY_EXPECTED_USER_COUNT="$(ADMIN_IDENTITY_EXPECTED_USER_COUNT)" \
		-e ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE="$(ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE)" \
		-e ADMIN_IDENTITY_RUN_ID="$(ADMIN_IDENTITY_RUN_ID)" \
		-e ADMIN_IDENTITY_TOOL_SOURCE_SHA="$(ADMIN_IDENTITY_TOOL_SOURCE_SHA)" \
		-e ADMIN_IDENTITY_DEPLOYED_PATH="$(ADMIN_IDENTITY_DEPLOYED_PATH)" \
		-e ADMIN_IDENTITY_EVIDENCE_OUTPUT="$(ADMIN_IDENTITY_EVIDENCE_OUTPUT)" \
		-e CONFIRM_ADMIN_IDENTITY_BASELINE="$(CONFIRM_ADMIN_IDENTITY_BASELINE)" \
		-e FORMAL_MODULE_CONTRACT="$(RELEASE_PRODUCT_MODULES)" \
		-v "$(ADMIN_IDENTITY_DEPLOYED_PATH):$(ADMIN_IDENTITY_DEPLOYED_PATH):ro" \
		--entrypoint /bin/sh odoo -eu -c '\
			python3 /usr/local/bin/production_db_contract.py health; \
			python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "$${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"; \
			exec odoo shell -c "$${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}" -d "$${TARGET_DB}"' \
		< scripts/release/production_admin_identity_baseline.py

release.production.formal_modules.install_missing: guard.prod.danger release.production.compose.preflight
	@test "$(ENV)" = "prod" || (echo "ENV=prod is required"; exit 2)
	@test "$(TARGET_DB)" = "sc_production" || (echo "TARGET_DB must be sc_production"; exit 2)
	@test "$(CONFIRM_FORMAL_MODULE_INSTALL)" = "YES_INSTALL_MISSING_FORMAL_MODULES" || \
		(echo "CONFIRM_FORMAL_MODULE_INSTALL=YES_INSTALL_MISSING_FORMAL_MODULES is required"; exit 2)
	@ENV="$(ENV)" PROD_DANGER="$${PROD_DANGER:-}" TARGET_DB="$(TARGET_DB)" \
		CONFIRM_FORMAL_MODULE_INSTALL="$(CONFIRM_FORMAL_MODULE_INSTALL)" \
		python3 scripts/release/production_formal_module_install.py execute

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

.PHONY: release.workspace.prepare release.rc6.workspace.prepare release.rc6.identity.publish verify.release.rc6.identity release.production.readonly_baseline release.candidate release.candidate.build release.boundary.candidate.build release.publish release.candidate.publish release.candidate.scan
.PHONY: product.install product.upgrade product.verify tenant.rc.payload.export tenant.rc.profile.product tenant.rc.profile.sample tenant.rc.profile.customer tenant.rc.profile.digest.verify tenant.rc.runtime.acceptance
.PHONY: release.history.source_probe release.history.backup release.history.restore release.history.upgrade
.PHONY: release.history.source_restore
.PHONY: release.history.runtime_up release.history.runtime_down release.history.fingerprint.source_pre
.PHONY: release.history.fingerprint.candidate_pre release.history.fingerprint.candidate_post

release.workspace.prepare: guard.prod.forbid
	@test -n "$(RELEASE_WORKSPACE)" || (echo "RELEASE_WORKSPACE is required"; exit 2)
	@RELEASE_WORKSPACE="$(RELEASE_WORKSPACE)" bash scripts/release/prepare_rc_workspace.sh

RC6_FREEZE_WORKSPACE ?=
RC6_BUILD_ARTIFACTS ?=
RC6_FREEZE_EVIDENCE ?=
RC6_FREEZE_DECLARATION ?= config/releases/rc6_candidate.json

release.rc6.workspace.prepare: guard.prod.forbid
	@test -n "$(RC6_FREEZE_WORKSPACE)" || (echo "RC6_FREEZE_WORKSPACE is required"; exit 2)
	@python3 scripts/ops/rc6_candidate_identity_freeze.py prepare-workspace \
		--workspace "$(RC6_FREEZE_WORKSPACE)"

release.rc6.identity.publish: guard.prod.forbid
	@test "$${CONFIRM_RC6_IMAGE_PUSH:-}" = "PUSH_FROZEN_RC6_SOURCE_TAG_ONLY" || { echo "exact RC6 image push confirmation is required" >&2; exit 2; }
	@test -n "$(RC6_BUILD_ARTIFACTS)" || (echo "RC6_BUILD_ARTIFACTS is required"; exit 2)
	@test -n "$(RC6_FREEZE_EVIDENCE)" || (echo "RC6_FREEZE_EVIDENCE is required"; exit 2)
	@python3 scripts/ops/rc6_candidate_identity_freeze.py publish-image \
		--artifacts "$(RC6_BUILD_ARTIFACTS)" \
		--output "$(RC6_FREEZE_EVIDENCE)"

verify.release.rc6.identity: guard.prod.forbid
	@python3 -m py_compile scripts/ops/rc6_candidate_identity_freeze.py scripts/ops/test_rc6_candidate_identity_freeze.py
	@python3 scripts/ops/test_rc6_candidate_identity_freeze.py
	@python3 scripts/ops/rc6_candidate_identity_freeze.py verify-declaration \
		--declaration "$(RC6_FREEZE_DECLARATION)"

release.production.readonly_baseline: guard.prod.readonly check-compose-project check-compose-env
	@CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/production_readonly_baseline.sh

# Daily RC entry: synchronize the approved main, freeze its identity, build,
# archive/reload, scan, generate an SBOM, and emit release-report.json. It never
# pushes an image, creates a tag/release, or deploys.
release.candidate: guard.prod.forbid
	@test -n "$(VERSION)" || (echo "VERSION is required (example: VERSION=1.0.0-rc.5)"; exit 2)
	@ENV="$(ENV)" python3 scripts/release/release_candidate.py --version "$(VERSION)"

release.candidate.build: guard.prod.forbid verify.repository.release_hygiene
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" bash scripts/release/immutable_candidate_build.sh

release.boundary.candidate.build: guard.prod.forbid verify.repository.release_hygiene
	@test -n "$(SOURCE_SHA)" || (echo "SOURCE_SHA is required"; exit 2)
	@SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_SOURCE_REF=HEAD ALLOW_BOUNDARY_BRANCH_BUILD=1 \
		CANDIDATE_IMAGE="$(CANDIDATE_IMAGE)" CANDIDATE_ARTIFACTS="$(CANDIDATE_ARTIFACTS)" \
		bash scripts/release/immutable_candidate_build.sh

release.publish: guard.prod.forbid
	@test -n "$(VERSION)" || (echo "VERSION is required"; exit 2)
	@test -n "$(CANDIDATE_ATTEMPT_ID)" || (echo "CANDIDATE_ATTEMPT_ID is required"; exit 2)
	@test -n "$(EXPECTED_SOURCE_SHA)" || (echo "EXPECTED_SOURCE_SHA is required"; exit 2)
	@test -n "$(EXPECTED_PUBLICATION_TOOL_SHA)" || (echo "EXPECTED_PUBLICATION_TOOL_SHA is required"; exit 2)
	@test -n "$(EXPECTED_LIVE_MAIN_SHA)" || (echo "EXPECTED_LIVE_MAIN_SHA is required"; exit 2)
	@ENV="$(ENV)" python3 scripts/release/release_publication.py \
		--version "$(VERSION)" \
		--candidate-attempt-id "$(CANDIDATE_ATTEMPT_ID)" \
		--expected-source-sha "$(EXPECTED_SOURCE_SHA)" \
		--expected-publication-tool-sha "$(EXPECTED_PUBLICATION_TOOL_SHA)" \
		--expected-live-main-sha "$(EXPECTED_LIVE_MAIN_SHA)" \
		$(if $(PUBLICATION_ATTEMPT_ID),--publication-attempt-id "$(PUBLICATION_ATTEMPT_ID)",)

# Compatibility name: all calls are routed through the immutable publication
# attempt contract. The former manifest-mutating shell implementation is denied.
release.candidate.publish: release.publish

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
