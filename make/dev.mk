# ======================================================
# ==================== Dev =============================
# ======================================================
.PHONY: up down restart logs ps odoo-shell prod.restart.safe prod.restart.full deploy.prod.sim.oneclick prod.sim.fresh.replay prod.sim.data.replay prod.sim.business.usable.init prod.sim.replay.then.usable.init prod.sim.replay.then.project frontend.dev frontend.stop frontend.restart frontend.logs acceptance.runtime.preflight acceptance.runtime.infrastructure.restore frontend.acceptance.up frontend.acceptance.down frontend.acceptance.health backend.acceptance.up backend.acceptance.down backend.acceptance.health frontend.collection.acceptance.up frontend.collection.acceptance.down backend.collection.acceptance.up backend.collection.acceptance.down verify.dev.acceptance.release release.dev.acceptance.publish release.daily_dev.acceptance.publish release.daily_product_navigation.snapshot local.dev.demo_credentials.prepare local.dev.ready local.dev.up local.dev.down local.dev.restart local.dev.frontend local.dev.logs local.dev.ps local.dev.test local.dev.upgrade local.dev.sync_demo local.dev.snapshot local.dev.contract_snapshot local.dev.rebuild_demo local.dev.verify_demo local.dev.health verify.local.dev.payment_request.native_parity.readonly verify.local.dev.payment_request.floorplan.readonly local.sample.require_env local.sample.ready local.sample.prepare local.sample.up local.sample.down local.sample.logs local.sample.snapshot local.sample.restore local.sample.discard local.sample.health local.clean.require_env local.clean.prepare local.clean.up local.clean.down local.clean.restart local.clean.logs local.clean.frontend local.clean.install local.clean.rebuild local.clean.health local.env.status verify.local.development_lifecycle.unit
up: check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/up.sh
down: check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/down.sh
restart: guard.prod.danger check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/restart.sh
logs: check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/logs.sh
ps: check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/ps.sh
odoo-shell: check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/shell.sh

# Local development uses three deliberately separate lifecycle units:
# - sc_dev_demo: persistent feature demo synchronized with current product code.
# - sc_dev_sample: disposable compatibility sample restored from daily development.
# - sc_clean: disposable clean-install rehearsal without demo data.
LOCAL_DEV_ENV_FILE ?= /home/lidefend/workspace/sce-backend-odoo/.env.dev
LOCAL_SAMPLE_ENV_FILE ?= /home/lidefend/workspace/sce-backend-odoo/.env.local.sample
LOCAL_CLEAN_ENV_FILE ?= /home/lidefend/workspace/sce-backend-odoo/.env.local.clean
LOCAL_CLEAN_MODULES ?= sc_norm_engine
LOCAL_ENV_ISOLATE = env \
	-u DB_NAME -u DB -u BD -u DB_USER -u DB_PASSWORD \
	-u DB_DATA -u REDIS_DATA -u ODOO_DATA -u ODOO_DB -u ODOO_DBFILTER \
	-u ODOO_PORT -u LIST_DB -u COMPOSE_PROJECT_NAME -u PROJECT -u ODOO_CONF \
	-u VITE_ODOO_DB -u VITE_APP_ENV -u FRONTEND_DIST_DIR \
	-u SC_ENVIRONMENT -u SC_ALLOW_DEMO_DATA -u ISOLATED_DEMO_TENANT

verify.local.development_lifecycle.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_local_development_lifecycle

local.dev.demo_credentials.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" TARGET_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/dev/local_dev_demo_credentials_prepare.sh

local.dev.ready: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_dev_readiness.sh

local.dev.up: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" up

local.dev.down: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" down

local.dev.restart: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" restart

local.dev.frontend: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/frontend_static_build.sh

local.dev.logs: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_doctor.sh persistent

local.dev.ps: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ps

local.dev.test: guard.prod.forbid local.dev.ready
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE="$(MODULE)" TEST_TAGS="$(TEST_TAGS)" test.safe

local.dev.upgrade: guard.prod.forbid local.dev.ready
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE="$(MODULE)" mod.upgrade

local.dev.sync_demo: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" demo.load.full
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" up
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.dev.verify_demo

local.dev.snapshot: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_dev_snapshot.sh persistent

local.dev.contract_snapshot: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  CONTRACT_START_CASE="$(CONTRACT_START_CASE)" CONTRACT_CASE_ONLY="$(CONTRACT_CASE_ONLY)" \
	  contract.export_all
local.dev.rebuild_demo: guard.prod.forbid local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_DEV_DEMO_REBUILD="$${CONFIRM_LOCAL_DEV_DEMO_REBUILD:-}" \
	  bash scripts/dev/local_dev_demo_rebuild.sh
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.dev.verify_demo

local.dev.verify_demo: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" verify.demo

local.sample.require_env: guard.prod.forbid
	@test -f "$(LOCAL_SAMPLE_ENV_FILE)" || { echo "sample env is not prepared: $(LOCAL_SAMPLE_ENV_FILE)" >&2; exit 2; }

local.sample.ready: local.sample.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_sample_readiness.sh

local.sample.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" SOURCE_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  TARGET_ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" bash scripts/dev/local_sample_env_prepare.sh

local.sample.up: guard.prod.forbid local.sample.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" up

local.sample.down: guard.prod.forbid local.sample.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" down

local.sample.logs: guard.prod.forbid local.sample.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_doctor.sh sample

local.sample.snapshot: guard.prod.forbid local.sample.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_dev_snapshot.sh sample

LOCAL_DEV_SAMPLE_BACKUP_DIR ?=
local.sample.restore: guard.prod.forbid local.sample.prepare
	@test -n "$(LOCAL_DEV_SAMPLE_BACKUP_DIR)" || (echo "LOCAL_DEV_SAMPLE_BACKUP_DIR is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  LOCAL_DEV_SAMPLE_BACKUP_DIR="$(LOCAL_DEV_SAMPLE_BACKUP_DIR)" \
	  CONFIRM_LOCAL_DEV_SAMPLE_RESTORE="$${CONFIRM_LOCAL_DEV_SAMPLE_RESTORE:-}" \
	  bash scripts/dev/local_dev_sample_restore.sh

local.sample.discard: guard.prod.forbid local.sample.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_DEV_SAMPLE_DISCARD="$${CONFIRM_LOCAL_DEV_SAMPLE_DISCARD:-}" \
	  bash scripts/dev/local_sample_discard.sh

local.sample.health: guard.prod.forbid local.sample.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_health.sh sample

local.dev.health: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_health.sh persistent

verify.local.dev.payment_request.native_parity.readonly: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_payment_request_native_parity_readonly.sh

verify.local.dev.payment_request.floorplan.readonly: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_payment_request_floorplan_readonly.sh

local.clean.require_env: guard.prod.forbid
	@test -f "$(LOCAL_CLEAN_ENV_FILE)" || { echo "clean env is not prepared: $(LOCAL_CLEAN_ENV_FILE)" >&2; exit 2; }

local.clean.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" SOURCE_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  TARGET_ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" bash scripts/dev/local_clean_env_prepare.sh

local.clean.up: guard.prod.forbid local.clean.prepare
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" up

local.clean.down: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" down

local.clean.restart: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" restart

local.clean.logs: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_doctor.sh clean

local.clean.frontend: guard.prod.forbid local.clean.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/frontend_static_build.sh

local.clean.install: guard.prod.forbid local.clean.up
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" \
	  MODULE="$(LOCAL_CLEAN_MODULES)" WITHOUT_DEMO=--without-demo=all mod.install
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.clean.frontend
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" restart

.PHONY: local.clean.upgrade
local.clean.upgrade: guard.prod.forbid local.clean.up
	@test -n "$(strip $(MODULE))" || { echo "MODULE is required for local.clean.upgrade" >&2; exit 2; }
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" \
	  CODEX_MODE=fast CODEX_NEED_UPGRADE=1 MODULE="$(MODULE)" mod.upgrade
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" restart

.PHONY: local.clean.contract_projection_cache.probe
local.clean.contract_projection_cache.probe: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" \
	  python3 scripts/verify/contract_projection_cache_runtime_probe.py \
	  --phase "$${CACHE_PROBE_PHASE:-initial}" \
	  --output "$${CACHE_PROBE_OUTPUT:-artifacts/backend/contract_projection_cache_runtime_probe.json}"

local.clean.rebuild: export LOCAL_CLEAN_PREPARE_FOR_REBUILD=1
local.clean.rebuild: guard.prod.forbid local.clean.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_CLEAN_REBUILD="$${CONFIRM_LOCAL_CLEAN_REBUILD:-}" \
	  LOCAL_CLEAN_MODULES="$(LOCAL_CLEAN_MODULES)" bash scripts/dev/local_clean_rebuild.sh

local.clean.health: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  LOCAL_CLEAN_HEALTH_MODULES="$(LOCAL_CLEAN_HEALTH_MODULES)" \
	  bash scripts/dev/local_environment_health.sh clean

local.env.status: guard.prod.forbid
	@status=0; \
	if [ -f "$(LOCAL_DEV_ENV_FILE)" ]; then \
	  $(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	    bash scripts/dev/local_environment_health.sh persistent || status=1; \
	else \
	  echo "[local.env.status] feature demo environment is not prepared"; status=1; \
	fi; \
	if [ -f "$(LOCAL_SAMPLE_ENV_FILE)" ]; then \
	  $(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_SAMPLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	    bash scripts/dev/local_environment_health.sh sample || status=1; \
	else \
	  echo "[local.env.status] technical sample environment is not prepared"; status=1; \
	fi; \
	if [ -f "$(LOCAL_CLEAN_ENV_FILE)" ]; then \
	  $(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	    bash scripts/dev/local_environment_health.sh clean || status=1; \
	else \
	  echo "[local.env.status] clean environment is not prepared"; status=1; \
	fi; \
	exit $$status

FRONTEND_DEV_LOG ?= /tmp/sc-frontend-dev.log
FRONTEND_DEV_PID ?= /tmp/sc-frontend-dev.pid
FRONTEND_DEV_PORT ?= 5174

frontend.dev: guard.prod.forbid
	@FRONTEND_PROFILE=$${FRONTEND_PROFILE:-daily} \
	  FRONTEND_DEV_PIDFILE="$(FRONTEND_DEV_PID)" \
	  FRONTEND_DEV_LOGFILE="$(FRONTEND_DEV_LOG)" \
	  bash scripts/dev/frontend_dev_reset.sh

frontend.stop: guard.prod.forbid
	@echo "[frontend.stop] stopping frontend dev server"
	@if [ -f "$(FRONTEND_DEV_PID)" ]; then \
		pid="$$(cat "$(FRONTEND_DEV_PID)" 2>/dev/null || true)"; \
		if [ -n "$$pid" ] && kill -0 "$$pid" 2>/dev/null; then \
			kill -- "-$$pid" 2>/dev/null || kill "$$pid" 2>/dev/null || true; \
			echo "[frontend.stop] killed process-group=$$pid"; \
		fi; \
	fi
	@pids=""; \
	if command -v lsof >/dev/null 2>&1; then \
		pids="$$(lsof -tiTCP:$(FRONTEND_DEV_PORT) -sTCP:LISTEN 2>/dev/null || true)"; \
	elif command -v ss >/dev/null 2>&1; then \
		pids="$$(ss -ltnp 2>/dev/null | awk -v target=":$(FRONTEND_DEV_PORT)" '$$4 ~ target"$$" {print $$NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)"; \
	fi; \
	if [ -n "$$pids" ]; then \
		for pid in $$pids; do kill "$$pid" 2>/dev/null || true; echo "[frontend.stop] killed listener pid=$$pid port=$(FRONTEND_DEV_PORT)"; done; \
	else \
		echo "[frontend.stop] no listener on :$(FRONTEND_DEV_PORT)"; \
	fi
	@rm -f "$(FRONTEND_DEV_PID)"

frontend.restart: guard.prod.forbid
	@FRONTEND_PROFILE=$${FRONTEND_PROFILE:-daily} \
	  FRONTEND_DEV_PIDFILE="$(FRONTEND_DEV_PID)" \
	  FRONTEND_DEV_LOGFILE="$(FRONTEND_DEV_LOG)" \
	  bash scripts/dev/frontend_dev_reset.sh
	@echo "[frontend.restart] done"

frontend.logs:
	@echo "[frontend.logs] $(FRONTEND_DEV_LOG)"
	@tail -n 120 "$(FRONTEND_DEV_LOG)" || true

FRONTEND_ACCEPTANCE_PORT ?= 5175
FRONTEND_ACCEPTANCE_BASE_URL ?= http://127.0.0.1:$(FRONTEND_ACCEPTANCE_PORT)
FRONTEND_ACCEPTANCE_DB ?= sc_frontend_acceptance
BACKEND_ACCEPTANCE_NAME ?= sc-backend-odoo-acceptance
BACKEND_ACCEPTANCE_PORT ?= 18082
BACKEND_ACCEPTANCE_DB ?= sc_frontend_acceptance
BACKEND_ACCEPTANCE_BASE_URL ?= http://127.0.0.1:$(BACKEND_ACCEPTANCE_PORT)
SC_ACCEPTANCE_RUNTIME_PROFILE ?= local

acceptance.runtime.preflight: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh preflight

acceptance.runtime.infrastructure.restore: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh infrastructure-restore

frontend.acceptance.up: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-up

frontend.acceptance.down: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-down

frontend.acceptance.health:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-health

backend.acceptance.up: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-up
backend.acceptance.down:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-down
backend.acceptance.health:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-health

backend.collection.acceptance.up: backend.acceptance.up
backend.collection.acceptance.down: backend.acceptance.down
frontend.collection.acceptance.up: frontend.acceptance.up
frontend.collection.acceptance.down: frontend.acceptance.down

ACCEPTANCE_BASE_URL ?= http://127.0.0.1:$(NGINX_PORT)
ACCEPTANCE_PROBE_OUTPUT ?= artifacts/backend/dev_acceptance_release_probe.json
ACCEPTANCE_LOGIN ?=
ACCEPTANCE_PASSWORD ?=
ACCEPTANCE_NAV_MIN_ACTIONS ?=
ACCEPTANCE_NAV_MAX_ACTIONS ?=
ACCEPTANCE_NAV_FORBIDDEN_LABELS ?=
ACCEPTANCE_NAV_REQUIRED_PATHS ?=
ACCEPTANCE_NAV_REQUIRED_ACTIONS ?=
DAILY_ACCEPTANCE_NAV_MIN_ACTIONS ?= $(shell python3 -c 'import json; print(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["min_actions"])')
DAILY_ACCEPTANCE_NAV_MAX_ACTIONS ?= $(shell python3 -c 'import json; print(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["max_actions"])')
DAILY_ACCEPTANCE_NAV_FORBIDDEN_LABELS ?= $(shell python3 -c 'import json; print(",".join(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["forbidden_labels"]))')
DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS ?= $(shell python3 -c 'import json; print(",".join(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["required_paths"]))')
DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY ?= construction.standard

verify.dev.acceptance.release: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) SC_ACCEPTANCE_EXPECTED_SHA="$$(git rev-parse HEAD)" DB_NAME=$(DB_NAME) ACCEPTANCE_BACKUP_DIR="$(ACCEPTANCE_BACKUP_DIR)" ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_NAV_MIN_ACTIONS="$(ACCEPTANCE_NAV_MIN_ACTIONS)" ACCEPTANCE_NAV_MAX_ACTIONS="$(ACCEPTANCE_NAV_MAX_ACTIONS)" ACCEPTANCE_NAV_FORBIDDEN_LABELS="$(ACCEPTANCE_NAV_FORBIDDEN_LABELS)" ACCEPTANCE_NAV_REQUIRED_PATHS="$(ACCEPTANCE_NAV_REQUIRED_PATHS)" ACCEPTANCE_NAV_REQUIRED_ACTIONS="$(ACCEPTANCE_NAV_REQUIRED_ACTIONS)" ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/ops/dev_acceptance_release_probe.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

.PHONY: verify.dev.acceptance.release.schema.guard
verify.dev.acceptance.release.schema.guard: guard.prod.forbid
	@python3 -m py_compile scripts/verify/dev_acceptance_release_probe_schema_guard.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

release.dev.acceptance.publish: guard.prod.forbid check-compose-project check-compose-env verify.frontend.build verify.user_confirmed.formal_surface.locked verify.dev.acceptance.release
	@echo "[release.dev.acceptance.publish] PASS base_url=$(ACCEPTANCE_BASE_URL) db=$(DB_NAME) artifact=$(ACCEPTANCE_PROBE_OUTPUT)"

release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_MIN_ACTIONS := $(DAILY_ACCEPTANCE_NAV_MIN_ACTIONS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_MAX_ACTIONS := $(DAILY_ACCEPTANCE_NAV_MAX_ACTIONS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_FORBIDDEN_LABELS := $(DAILY_ACCEPTANCE_NAV_FORBIDDEN_LABELS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_REQUIRED_PATHS := $(DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS)
release.daily_dev.acceptance.publish: guard.prod.forbid verify.daily_dev.acceptance.env.guard env.matrix.check verify.daily_dev.runtime_repo.clean release.dev.acceptance.publish
	@echo "[release.daily_dev.acceptance.publish] PASS base_url=$(ACCEPTANCE_BASE_URL) db=$(DB_NAME) head=$$(git rev-parse --short HEAD)"

release.daily_product_navigation.snapshot: guard.prod.forbid check-compose-project check-compose-env
	@test "$(ENV)" = "dev" || { echo "daily product navigation snapshot requires ENV=dev" >&2; exit 2; }
	@test "$(DB_NAME)" = "sc_demo" || { echo "daily product navigation snapshot requires DB_NAME=sc_demo" >&2; exit 2; }
	@case "$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY)" in construction.standard|construction.preview) ;; *) echo "daily product navigation snapshot product key is not allowed" >&2; exit 2;; esac
	@test "$${CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT:-}" = "RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION" || { echo "daily product navigation snapshot confirmation is required" >&2; exit 2; }
	@$(RUN_ENV) DB_NAME=sc_demo \
	  PLATFORM_RELEASE_DB=sc_demo \
	  PLATFORM_RELEASE_PRODUCT_KEY="$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY)" \
	  PLATFORM_RELEASE_VERSION="daily-navigation-$$(echo "$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY)" | cut -d. -f2)-$$(git rev-parse --short=12 HEAD)" \
	  SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/release/initialize_colocated_platform_snapshot.py

prod.restart.safe: guard.prod.danger check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/restart.sh

prod.restart.full: guard.prod.danger check-compose-project check-compose-env
	@$(RUN_ENV) bash scripts/dev/down.sh
	@$(RUN_ENV) bash scripts/dev/up.sh

deploy.prod.sim.oneclick: guard.prod.forbid check-compose-project check-compose-env gate.compose.config
	@$(RUN_ENV) COMPOSE_FILES="-f $(COMPOSE_FILE_BASE) -f docker-compose.prod-sim.yml" bash scripts/deploy/prod_sim_oneclick.sh

prod.sim.fresh.replay: guard.prod.forbid check-compose-project check-compose-env gate.compose.config
	@$(RUN_ENV) ENV=test ENV_FILE=.env.prod.sim COMPOSE_FILES="-f $(COMPOSE_FILE_BASE) -f docker-compose.prod-sim.yml" bash scripts/deploy/prod_sim_fresh_replay.sh

prod.sim.data.replay: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) ENV=test ENV_FILE=.env.prod.sim COMPOSE_FILES="-f $(COMPOSE_FILE_BASE) -f docker-compose.prod-sim.yml" DB_NAME=$(DB_NAME) HISTORY_CONTINUITY_MODE=replay HISTORY_CONTINUITY_INCLUDE_FORMAL_PROJECTIONS=0 HISTORY_CONTINUITY_USE_PACKAGED_PAYLOADS="$(or $(HISTORY_CONTINUITY_USE_PACKAGED_PAYLOADS),1)" RUN_ID="$(RUN_ID)" HISTORY_CONTINUITY_START_AT="$(HISTORY_CONTINUITY_START_AT)" HISTORY_CONTINUITY_STOP_AFTER="$(HISTORY_CONTINUITY_STOP_AFTER)" MIGRATION_REPLAY_DB_ALLOWLIST="$(or $(MIGRATION_REPLAY_DB_ALLOWLIST),$(DB_NAME))" MIGRATION_ARTIFACT_ROOT="$(MIGRATION_ARTIFACT_ROOT)" bash scripts/migration/history_continuity_oneclick.sh

prod.sim.business.usable.init: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) ENV=test ENV_FILE=.env.prod.sim COMPOSE_FILES="-f $(COMPOSE_FILE_BASE) -f docker-compose.prod-sim.yml" DB_NAME=$(DB_NAME) FORMAL_PROJECTION_ARTIFACT_ROOT="$(FORMAL_PROJECTION_ARTIFACT_ROOT)" MIGRATION_ARTIFACT_ROOT="$(MIGRATION_ARTIFACT_ROOT)" MIGRATION_REPLAY_DB_ALLOWLIST="$(or $(MIGRATION_REPLAY_DB_ALLOWLIST),$(DB_NAME))" bash scripts/migration/history_business_usable_init.sh

prod.sim.replay.then.usable.init: guard.prod.forbid check-compose-project check-compose-env
	@$(MAKE) prod.sim.data.replay
	@$(MAKE) prod.sim.business.usable.init

prod.sim.replay.then.project: guard.prod.forbid check-compose-project check-compose-env
	@$(MAKE) prod.sim.replay.then.usable.init

.PHONY: dev.rebuild
dev.rebuild: guard.codex.fast.noheavy guard.prod.forbid check-compose-project check-compose-env gate.compose.config
	@$(RUN_ENV) bash scripts/dev/down.sh || true
	@$(RUN_ENV) bash scripts/dev/up.sh
	@$(MAKE) db.reset
	@$(MAKE) demo.reset DB=$(DB_NAME)
	@echo "[dev.rebuild] done"

.PHONY: odoo.recreate odoo.logs odoo.exec
odoo.recreate: check-compose-project check-compose-env
	@echo "[odoo.recreate] service=$(ODOO_SERVICE)"
	@$(RUN_ENV) $(COMPOSE_BASE) up -d --force-recreate $(ODOO_SERVICE)
odoo.logs: check-compose-project check-compose-env
	@$(RUN_ENV) $(COMPOSE_BASE) logs --tail=200 $(ODOO_SERVICE)
odoo.exec: check-compose-project check-compose-env
	@$(RUN_ENV) $(COMPOSE_BASE) exec -T $(ODOO_SERVICE) bash

.PHONY: local.clean.view_structure_baseline local.clean.view_structure_gate local.clean.view_carrier_export local.clean.view_carrier_gate local.clean.view_normalized_map_gate local.clean.view_capability_ledger_gate
local.clean.view_structure_baseline: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" contract.view_structure.baseline

local.clean.view_structure_gate: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" gate.contract.view_structure

local.clean.view_carrier_export: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" contract.view_carrier.export

local.clean.view_carrier_gate: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" gate.contract.view_carrier

local.clean.view_normalized_map_gate: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" gate.contract.native_view_normalized_map

local.clean.view_capability_ledger_gate: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" gate.contract.view_capability_ledger

# ======================================================
