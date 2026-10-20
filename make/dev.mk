# ======================================================
# ==================== Dev =============================
# ======================================================
.PHONY: local.dev.rebuild_realistic local.dev.verify_realistic
.PHONY: up down restart logs ps odoo-shell prod.restart.safe prod.restart.full deploy.prod.sim.oneclick prod.sim.fresh.replay prod.sim.data.replay prod.sim.business.usable.init prod.sim.replay.then.usable.init prod.sim.replay.then.project frontend.dev frontend.stop frontend.restart frontend.logs acceptance.runtime.preflight acceptance.runtime.infrastructure.restore frontend.acceptance.up frontend.acceptance.down frontend.acceptance.health backend.acceptance.up backend.acceptance.down backend.acceptance.health backend.acceptance.logs frontend.collection.acceptance.up frontend.collection.acceptance.down backend.collection.acceptance.up backend.collection.acceptance.down verify.dev.acceptance.release release.dev.acceptance.publish release.daily_dev_acceptance.publish release.daily_product_navigation.snapshot release.daily_product_navigation.refresh release.daily_product_navigation.converge local.dev.demo_credentials.prepare local.dev.ready local.dev.up local.dev.down local.dev.restart local.dev.frontend local.dev.frontend.watch local.dev.candidate.frontend.up local.dev.candidate.frontend.down local.dev.candidate.frontend.health local.dev.candidate.frontend.visual-smoke local.dev.logs local.dev.ps local.dev.test local.dev.upgrade local.dev.verify_authority local.dev.sync_demo local.dev.demo_users.sync local.dev.reset_payment_request_fixture local.dev.demo.settlement_snapshot.repair local.dev.snapshot local.dev.contract_snapshot local.dev.project_create_contract_action_scope local.dev.project_profile_write_fixture local.dev.project_profile_write_browser local.dev.personnel_authorization_fixture local.dev.personnel_authorization_browser local.dev.tender_award_fixture local.dev.tender_award_browser verify.local.dev.tender_award.unit verify.local.dev.tender_award.journey local.dev.rebuild_demo local.dev.verify_demo local.dev.health verify.local.dev.frontend.quick.unit verify.local.dev.frontend.quick.gate verify.local.dev.payment_request.native_parity.readonly verify.local.dev.payment_request.floorplan.readonly verify.local.dev.payment_request.floorplan.submit verify.local.dev.payment_request.full_chain verify.local.dev.payment_request.settlement_component.journey verify.local.dev.payment_request.attachment_m2m.journey local.sample.require_env local.sample.ready local.sample.prepare local.sample.up local.sample.down local.sample.logs local.sample.snapshot local.sample.restore local.sample.discard local.sample.health local.clean.require_env local.clean.prepare local.clean.up local.clean.down local.clean.restart local.clean.logs local.clean.frontend local.env.status verify.local.development_lifecycle.unit verify.local.dev.project_create_contract_action_scope verify.local.dev.form_structure_surface_capability.orm verify.local.dev.canonical_navigation_projection.orm verify.local.dev.platform_database_governance.orm local.dev.data_space.enroll_identities verify.local.dev.data_space_identity_enrollment.orm verify.local.dev.data_space_uncached_membership.orm
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

# The registered isolated contract-lifecycle profile documented in
# docs/architecture/backend_contract_lifecycle_authority_v1.md: project
# sc-contract-lifecycle-v1, database sc_contract_lifecycle, dbfilter
# ^sc_contract_lifecycle$. It exists so the backend contract lifecycle and its
# SLO telemetry can be exercised against the source mount of the worktree that
# runs it. Its env file stays worktree-local.
LOCAL_CONTRACT_LIFECYCLE_ENV_FILE ?= $(ROOT_DIR)/.env.local.contract-lifecycle
LOCAL_CONTRACT_LIFECYCLE_MODULES ?= smart_core
# Same rationale as SC_ACCEPTANCE_FIXTURE_PASSWORD: the profile is an isolated
# synthetic database, so a fixed, intentionally simple value keeps repeated
# verification reproducible. Override explicitly when a distinct value is
# required.
LOCAL_CONTRACT_LIFECYCLE_PASSWORD ?= scdevpass
LOCAL_CONTRACT_LIFECYCLE_NGINX_PORT ?= 18090
LOCAL_CONTRACT_LIFECYCLE_ODOO_PORT ?= 8079
# Deploy-time revision injection for the supply-chain attestation: the profile
# declares which revision it serves, so the probe can bind the running
# deployment SHA instead of the placeholder "unknown". Defaults to this
# worktree's HEAD.
CONTRACT_LIFECYCLE_SOURCE_REVISION ?= $(shell git -C $(ROOT_DIR) rev-parse HEAD 2>/dev/null)
export LOCAL_CONTRACT_LIFECYCLE_PASSWORD

# The registered isolated contract-snapshot profile (documented in
# docs/architecture/backend_contract_lifecycle_authority_v1.md): project
# sc-contract-snapshot-v1, database sc_contract_snapshot, dbfilter
# ^sc_contract_snapshot$. It exists so the contract snapshot lane
# (docs/contract/cases.yml -> docs/contract/snapshots/**) can be regenerated
# against THIS worktree's source mount while reusing the registered demo
# dataset (sc-local-dev / sc_dev_demo) as its seed. Its env file stays
# worktree-local.
LOCAL_CONTRACT_SNAPSHOT_ENV_FILE ?= $(ROOT_DIR)/.env.local.contract-snapshot
LOCAL_CONTRACT_SNAPSHOT_MODULES ?= smart_core
LOCAL_CONTRACT_SNAPSHOT_PASSWORD ?= scdevpass
LOCAL_CONTRACT_SNAPSHOT_NGINX_PORT ?= 18091
LOCAL_CONTRACT_SNAPSHOT_ODOO_PORT ?= 8080
export LOCAL_CONTRACT_SNAPSHOT_PASSWORD

LOCAL_CLEAN_MODULES ?= sc_norm_engine
LOCAL_ENV_ISOLATE = env \
	-u DB_NAME -u DB -u BD -u DB_USER -u DB_PASSWORD \
	-u DB_DATA -u REDIS_DATA -u ODOO_DATA -u ODOO_DB -u ODOO_DBFILTER \
	-u ODOO_PORT -u LIST_DB -u COMPOSE_PROJECT_NAME -u PROJECT -u ODOO_CONF \
	-u VITE_ODOO_DB -u VITE_APP_ENV -u FRONTEND_DIST_DIR \
	-u SC_ENVIRONMENT -u SC_ALLOW_DEMO_DATA -u ISOLATED_DEMO_TENANT

.PHONY: verify.local.dev.layout_authority.unit
verify.local.dev.layout_authority.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_local_development_lifecycle.LayoutAuthorityReadonlyProbeTest

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

local.dev.frontend.watch: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  FRONTEND_PROFILE=local-dev \
	  FRONTEND_DEV_PIDFILE="$(FRONTEND_DEV_PID)" \
	  FRONTEND_DEV_LOGFILE="$(FRONTEND_DEV_LOG)" \
	  bash scripts/dev/frontend_dev_reset.sh

# Candidate browser carrier: serves only the current allowed topic worktree on
# 127.0.0.1:5176 and proxies API requests to the existing local.dev service.
# It never remounts the primary-worktree Nginx static volume.
local.dev.candidate.frontend.up: guard.prod.forbid
	@python3 scripts/dev/local_dev_candidate_frontend.py up

local.dev.candidate.frontend.down: guard.prod.forbid
	@python3 scripts/dev/local_dev_candidate_frontend.py down

local.dev.candidate.frontend.health: guard.prod.forbid
	@python3 scripts/dev/local_dev_candidate_frontend.py health

local.dev.candidate.frontend.visual-smoke: guard.prod.forbid
	@python3 scripts/dev/local_dev_candidate_frontend.py visual-smoke

verify.local.dev.frontend.quick.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_local_dev_frontend_quick

verify.local.dev.frontend.quick.gate: guard.prod.forbid verify.local.dev.frontend.quick.unit
	@python3 scripts/dev/local_dev_frontend_quick.py

local.dev.logs: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_doctor.sh persistent

local.dev.ps: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ps

local.dev.test: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 MODULE="$(MODULE)" TEST_TAGS="$(TEST_TAGS)" test.safe

.PHONY: local.dev.form_lowcode.browser
local.dev.form_lowcode.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_form_lowcode_browser.sh

local.dev.upgrade: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 MODULE="$(MODULE)" mod.upgrade
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.dev.verify_authority

local.dev.verify_authority: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 \
	  bash scripts/dev/local_dev_demo_authority_verify.sh

local.dev.sync_demo: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" demo.load.full
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" up
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.dev.verify_demo

.PHONY: local.dev.demo.load local.dev.demo.seed
local.dev.demo.load: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@test -n "$(SCENARIO)" || (echo "SCENARIO is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SCENARIO="$(SCENARIO)" demo.load

local.dev.demo.seed: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@test -n "$(STEPS)" || (echo "STEPS is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 STEPS="$(STEPS)" \
	  bash scripts/demo/run_seed.sh

local.dev.reset_payment_request_fixture: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 STEPS=payment_request_floorplan_demo PAYMENT_REQUEST_FIXTURE_SCOPE="$(if $(LOCAL_DEV_PAYMENT_FIXTURE_SCOPE),$(LOCAL_DEV_PAYMENT_FIXTURE_SCOPE),submit)" \
	  bash scripts/demo/run_seed.sh

# Governed repair for the demo invoice-snapshot drift that the demo seed can
# only report. The seed records the sample snapshot while settlements are
# drafts; a later project-stage promotion leaves an approved settlement holding
# the snapshot of the earlier stage, and approved settlement facts are
# immutable. This entry fills invoice_amount only where it is still NULL, for
# the projects the seed owns, and refuses real business values.
# DEMO_SETTLEMENT_SNAPSHOT_ACTION=report (default) | apply (needs CONFIRM=1).
local.dev.demo.settlement_snapshot.repair: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 \
	  DEMO_SETTLEMENT_SNAPSHOT_ACTION="$${DEMO_SETTLEMENT_SNAPSHOT_ACTION:-report}" \
	  DEMO_SETTLEMENT_SNAPSHOT_CONFIRM="$${DEMO_SETTLEMENT_SNAPSHOT_CONFIRM:-}" \
	  bash scripts/ops/odoo_shell_exec.sh \
	  < scripts/ops/repair_demo_settlement_invoice_snapshot.py

# Re-applies only the demo user step so the canonical sc-local-dev demo
# credential (scripts/dev/local_dev_demo_credentials_prepare.sh) matches the
# accounts in sc_dev_demo, without re-running the full demo load.
local.dev.demo_users.sync: guard.prod.forbid local.dev.ready local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1 STEPS=demo_users \
	  bash scripts/demo/run_seed.sh

local.dev.snapshot: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_dev_snapshot.sh persistent

local.dev.contract_snapshot: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  CONTRACT_START_CASE="$(CONTRACT_START_CASE)" CONTRACT_CASE_ONLY="$(CONTRACT_CASE_ONLY)" \
	  contract.export_all

# Bounded affected-surface contract gate over the registered local.dev profile
# (database sc_dev_demo, source = THIS worktree). Iteration/diagnostic entry: it
# regenerates and compares ONLY the declared case names in LOCAL_DEV_GATE_CASES,
# each of which must exist in docs/contract/cases.yml (a missing name fails
# closed). It never writes the tracked reference directory and is NOT a
# substitute for the full delivery gate (gate.contract). Set
# LOCAL_DEV_GATE_REF_DIR to compare against an alternate reference directory.
LOCAL_DEV_GATE_CASES ?=
LOCAL_DEV_GATE_REF_DIR ?= docs/contract/snapshots
.PHONY: local.dev.gate_contract.bounded local.dev.gate_contract.bounded.run
local.dev.gate_contract.bounded: guard.prod.forbid local.dev.ready
	@test -n "$(LOCAL_DEV_GATE_CASES)" || (echo "LOCAL_DEV_GATE_CASES is required (comma-separated declared case names)" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  LOCAL_DEV_GATE_CASES="$(LOCAL_DEV_GATE_CASES)" \
	  LOCAL_DEV_GATE_REF_DIR="$(LOCAL_DEV_GATE_REF_DIR)" \
	  local.dev.gate_contract.bounded.run

local.dev.gate_contract.bounded.run:
	@DB="$(DB_NAME)" CASES_FILE="docs/contract/cases.yml" CASE_FILTER="$(LOCAL_DEV_GATE_CASES)" \
	  REF_DIR="$(LOCAL_DEV_GATE_REF_DIR)" TMP_DIR="tmp/contract_gate_scope_run" \
	  CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" \
	  scripts/contract/gate_contract.sh

local.dev.project_create_contract_action_scope: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_project_create_contract_action_scope.sh

# Registered verify alias for the run index: the declaration-driven record scope
# journey (declared sections/fields, declared follower capability against the
# live list authority and the declared relation collection) on the governed
# local.dev runtime. It reuses the local.dev target and adds no new environment.
.PHONY: verify.local.dev.project_create_contract_action_scope
verify.local.dev.project_create_contract_action_scope: guard.prod.forbid local.dev.project_create_contract_action_scope

# Registered verify alias for the run index: the real-ORM lock on the declared
# form-surface capability probe, pinned to the fixed test tag so a run that
# collects zero tests cannot pass.
.PHONY: verify.local.dev.form_structure_surface_capability.orm
verify.local.dev.form_structure_surface_capability.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="/smart_core:TestFormStructureSurfaceCapabilityOrm" local.dev.test

# Registered verify alias for the run index: the pure lock on
# MenuService.project_canonical_navigation, pinned to its fixed test tag so a run
# that collects zero tests cannot pass.
.PHONY: verify.local.dev.canonical_navigation_projection.orm
verify.local.dev.canonical_navigation_projection.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="/smart_core:TestCanonicalNavigationProjection" local.dev.test

# Registered verify alias for the run index: the real-ORM lock on the user view
# preference surface -- an illegal or mismatched identity is refused before any
# read or write, the stored/effective projections never instantiate the page
# assembler, and the server never applies a stored order to the declared list
# contract (the frontend consumer is the single application site). Pinned to its
# fixed test tag so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.user_view_preference.runtime.orm
verify.local.dev.user_view_preference.runtime.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="/smart_core:TestUserViewPreferenceRuntime" local.dev.test

local.dev.project_profile_write_fixture: guard.prod.forbid local.dev.ready
	@test -n "$(P4_PROJECT_PROFILE_MODE)" || (echo "P4_PROJECT_PROFILE_MODE is required" >&2; exit 2)
	@test -n "$(P4_PROJECT_PROFILE_BATCH)" || (echo "P4_PROJECT_PROFILE_BATCH is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  P4_PROJECT_PROFILE_MODE="$(P4_PROJECT_PROFILE_MODE)" \
	  P4_PROJECT_PROFILE_BATCH="$(P4_PROJECT_PROFILE_BATCH)" \
	  P4_PROJECT_PROFILE_CONFIRM="$(P4_PROJECT_PROFILE_CONFIRM)" \
	  CANDIDATE_GIT_HEAD="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  bash scripts/verify/local_dev_project_profile_write_fixture.sh

local.dev.project_profile_write_browser: guard.prod.forbid local.dev.ready
	@test -n "$(PRODUCT_CANDIDATE_SHA)" || (echo "PRODUCT_CANDIDATE_SHA is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  PRODUCT_CANDIDATE_SHA="$(PRODUCT_CANDIDATE_SHA)" \
	  P4_TOOL_CANDIDATE_SHA="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  FRONTEND_URL="$(FRONTEND_URL)" \
	  bash scripts/verify/local_dev_project_profile_write_browser.sh

local.dev.personnel_authorization_fixture: guard.prod.forbid local.dev.ready
	@test -n "$(P4_PERSONNEL_AUTH_MODE)" || (echo "P4_PERSONNEL_AUTH_MODE is required" >&2; exit 2)
	@test -n "$(P4_PERSONNEL_AUTH_BATCH)" || (echo "P4_PERSONNEL_AUTH_BATCH is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  P4_PERSONNEL_AUTH_MODE="$(P4_PERSONNEL_AUTH_MODE)" \
	  P4_PERSONNEL_AUTH_BATCH="$(P4_PERSONNEL_AUTH_BATCH)" \
	  P4_PERSONNEL_AUTH_CONFIRM="$(P4_PERSONNEL_AUTH_CONFIRM)" \
	  CANDIDATE_GIT_HEAD="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  bash scripts/verify/local_dev_personnel_authorization_fixture.sh

local.dev.personnel_authorization_browser: guard.prod.forbid local.dev.ready
	@test -n "$(PRODUCT_CANDIDATE_SHA)" || (echo "PRODUCT_CANDIDATE_SHA is required" >&2; exit 2)
	@test -n "$(P4_PERSONNEL_AUTH_BATCH)" || (echo "P4_PERSONNEL_AUTH_BATCH is required" >&2; exit 2)
	@test -n "$(PERSON_ID)" || (echo "PERSON_ID is required" >&2; exit 2)
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  PRODUCT_CANDIDATE_SHA="$(PRODUCT_CANDIDATE_SHA)" \
	  P4_TOOL_CANDIDATE_SHA="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  P4_PERSONNEL_AUTH_BATCH="$(P4_PERSONNEL_AUTH_BATCH)" \
	  PERSON_ID="$(PERSON_ID)" PROJECT_ID="$(PROJECT_ID)" \
	  FRONTEND_URL="$(FRONTEND_URL)" \
	  bash scripts/verify/local_dev_personnel_authorization_browser.sh

verify.local.dev.tender_award.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_local_dev_tender_award_fixture

local.dev.tender_award_fixture: guard.prod.forbid local.dev.ready
	@test -n "$(P4_TENDER_AWARD_MODE)" || (echo "P4_TENDER_AWARD_MODE is required" >&2; exit 2)
	@test -n "$(P4_TENDER_AWARD_BATCH)" || (echo "P4_TENDER_AWARD_BATCH is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  P4_TENDER_AWARD_MODE="$(P4_TENDER_AWARD_MODE)" \
	  P4_TENDER_AWARD_BATCH="$(P4_TENDER_AWARD_BATCH)" \
	  P4_TENDER_AWARD_CONFIRM="$(P4_TENDER_AWARD_CONFIRM)" \
	  CANDIDATE_GIT_HEAD="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  bash scripts/verify/local_dev_tender_award_fixture.sh

local.dev.tender_award_browser: guard.prod.forbid local.dev.ready
	@test -n "$(PRODUCT_CANDIDATE_SHA)" || (echo "PRODUCT_CANDIDATE_SHA is required" >&2; exit 2)
	@test -n "$(P4_TOOL_CANDIDATE_SHA)" || (echo "P4_TOOL_CANDIDATE_SHA is required" >&2; exit 2)
	@test -n "$(P4_TENDER_AWARD_BATCH)" || (echo "P4_TENDER_AWARD_BATCH is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=0 \
	  PRODUCT_CANDIDATE_SHA="$(PRODUCT_CANDIDATE_SHA)" \
	  P4_TOOL_CANDIDATE_SHA="$(P4_TOOL_CANDIDATE_SHA)" \
	  P4_TENDER_AWARD_BATCH="$(P4_TENDER_AWARD_BATCH)" \
	  FRONTEND_URL="$(FRONTEND_URL)" ARTIFACT_DIR="$(ARTIFACT_DIR)" \
	  bash scripts/verify/local_dev_tender_award_browser.sh

verify.local.dev.tender_award.journey: guard.prod.forbid local.dev.ready
	@test -n "$(PRODUCT_CANDIDATE_SHA)" || (echo "PRODUCT_CANDIDATE_SHA is required" >&2; exit 2)
	@test -n "$(P4_TENDER_AWARD_BATCH)" || (echo "P4_TENDER_AWARD_BATCH is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  PRODUCT_CANDIDATE_SHA="$(PRODUCT_CANDIDATE_SHA)" \
	  P4_TOOL_CANDIDATE_SHA="$(shell git -C $(ROOT_DIR) rev-parse HEAD)" \
	  P4_TENDER_AWARD_BATCH="$(P4_TENDER_AWARD_BATCH)" \
	  FRONTEND_URL="$(FRONTEND_URL)" ARTIFACT_DIR="$(ARTIFACT_DIR)" \
	  bash scripts/verify/local_dev_tender_award_journey.sh

local.dev.rebuild_demo: guard.prod.forbid local.dev.demo_credentials.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_DEV_DEMO_REBUILD="$${CONFIRM_LOCAL_DEV_DEMO_REBUILD:-}" \
	  bash scripts/dev/local_dev_demo_rebuild.sh
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory local.dev.verify_demo

local.dev.rebuild_realistic: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_DEV_REALISTIC_REBUILD="$${CONFIRM_LOCAL_DEV_REALISTIC_REBUILD:-}" \
	  bash scripts/dev/local_dev_realistic_rebuild.sh

local.dev.verify_realistic: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_dev_realistic_authority_verify.sh

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
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" SOURCE_SHA="$(SOURCE_SHA)" LOCAL_DEV_FLOORPLAN_SCOPE="$(LOCAL_DEV_FLOORPLAN_SCOPE)" \
	  bash scripts/verify/local_dev_payment_request_floorplan_readonly.sh

.PHONY: verify.frontend.professionalization.payment_domain.browser
verify.frontend.professionalization.payment_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_payment_domain_browser.sh

.PHONY: verify.frontend.professionalization.settlement_domain.browser
verify.frontend.professionalization.settlement_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_settlement_domain_browser.sh

.PHONY: verify.frontend.professionalization.cost_domain.browser
verify.frontend.professionalization.cost_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_cost_domain_browser.sh

.PHONY: verify.frontend.professionalization.material_domain.browser
verify.frontend.professionalization.material_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_material_domain_browser.sh

.PHONY: verify.frontend.professionalization.quality_safety_domain.browser
verify.frontend.professionalization.quality_safety_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_quality_safety_domain_browser.sh

.PHONY: verify.frontend.professionalization.collaboration_domain.browser
verify.frontend.professionalization.collaboration_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_collaboration_domain_browser.sh

.PHONY: verify.frontend.professionalization.base_configuration_domain.browser
verify.frontend.professionalization.base_configuration_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_base_configuration_domain_browser.sh

.PHONY: verify.frontend.professionalization.administration_domain.browser
verify.frontend.professionalization.administration_domain.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_administration_domain_browser.sh

.PHONY: verify.frontend.professionalization.workbench_center.browser
verify.frontend.professionalization.workbench_center.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_workbench_center_browser.sh

.PHONY: verify.frontend.professionalization.finance_center.browser
verify.frontend.professionalization.finance_center.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_finance_center_browser.sh

.PHONY: verify.frontend.professionalization.tax_center.browser
verify.frontend.professionalization.tax_center.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_tax_center_browser.sh

.PHONY: verify.frontend.professionalization.accounting_center.browser
verify.frontend.professionalization.accounting_center.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_accounting_center_browser.sh

.PHONY: verify.frontend.professionalization.reporting_center.browser
verify.frontend.professionalization.reporting_center.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_reporting_center_browser.sh

.PHONY: verify.frontend.professionalization.systemwide_public_metric.browser
verify.frontend.professionalization.systemwide_public_metric.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/frontend_systemwide_public_metric_browser.sh

.PHONY: verify.frontend.professionalization.systemwide_public_metric.acceptance
verify.frontend.professionalization.systemwide_public_metric.acceptance: guard.prod.forbid verify.frontend.professionalization.systemwide_coverage.runtime verify.frontend.professionalization.systemwide_public_metric.browser
	@python3 scripts/verify/frontend_systemwide_public_metric_report.py \
	  --coverage artifacts/frontend-professionalization/frontend_systemwide_coverage_audit_runtime_v1.json \
	  --browser artifacts/playwright/systemwide-public-metric-acceptance/summary.json \
	  --json-output docs/frontend_productization/systemwide-public-metric-acceptance-v1.json \
	  --markdown-output docs/frontend_productization/systemwide-public-metric-acceptance-v1.md

verify.local.dev.payment_request.floorplan.submit: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  PAYMENT_REQUEST_JOURNEY_SCOPE=payment bash scripts/verify/local_dev_payment_request_floorplan_submit.sh

verify.local.dev.payment_request.full_chain: guard.prod.forbid local.dev.ready
	@test -n "$(SOURCE_SHA)" || { echo "SOURCE_SHA is required" >&2; exit 2; }
	@test -n "$(CANDIDATE_FINGERPRINT)" || { echo "CANDIDATE_FINGERPRINT is required" >&2; exit 2; }
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  SOURCE_SHA="$(SOURCE_SHA)" CANDIDATE_FINGERPRINT="$(CANDIDATE_FINGERPRINT)" \
	  bash scripts/verify/local_dev_payment_request_full_chain.sh

.PHONY: verify.local.dev.payment_request.relation_lifecycle
verify.local.dev.payment_request.relation_lifecycle: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  PAYMENT_REQUEST_JOURNEY_SCOPE=relation bash scripts/verify/local_dev_payment_request_floorplan_submit.sh

verify.local.dev.payment_request.settlement_component.journey: guard.prod.forbid local.dev.ready local.dev.candidate.frontend.health
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_payment_settlement_component_journey.sh

verify.local.dev.payment_request.attachment_m2m.journey: guard.prod.forbid local.dev.ready local.dev.candidate.frontend.health
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/verify/local_dev_payment_attachment_m2m_journey.sh

local.clean.require_env: guard.prod.forbid
	@test -f "$(LOCAL_CLEAN_ENV_FILE)" || { echo "clean env is not prepared: $(LOCAL_CLEAN_ENV_FILE)" >&2; exit 2; }

.PHONY: local.contract-lifecycle.require_env local.contract-lifecycle.prepare \
	local.contract-lifecycle.rebuild local.contract-lifecycle.up \
	local.contract-lifecycle.down local.contract-lifecycle.ps \
	local.contract-lifecycle.odoo-shell local.contract-lifecycle.odoo-shell.run \
	local.contract-lifecycle.upgrade local.contract-lifecycle.discard

local.contract-lifecycle.require_env: guard.prod.forbid
	@test -f "$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" || { echo "contract-lifecycle env is not prepared: $(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" >&2; exit 2; }

local.contract-lifecycle.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" SOURCE_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  TARGET_ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" \
	  CONTRACT_LIFECYCLE_SOURCE_REVISION="$(CONTRACT_LIFECYCLE_SOURCE_REVISION)" \
	  LOCAL_CONTRACT_LIFECYCLE_PASSWORD="$(LOCAL_CONTRACT_LIFECYCLE_PASSWORD)" \
	  LOCAL_CONTRACT_LIFECYCLE_NGINX_PORT="$(LOCAL_CONTRACT_LIFECYCLE_NGINX_PORT)" \
	  LOCAL_CONTRACT_LIFECYCLE_ODOO_PORT="$(LOCAL_CONTRACT_LIFECYCLE_ODOO_PORT)" \
	  LOCAL_CONTRACT_LIFECYCLE_PREPARE_FOR_REBUILD="$${LOCAL_CONTRACT_LIFECYCLE_PREPARE_FOR_REBUILD:-0}" \
	  CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD="$${CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD:-}" \
	  bash scripts/dev/local_contract_lifecycle_env_prepare.sh

local.contract-lifecycle.rebuild: guard.prod.forbid local.contract-lifecycle.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  LOCAL_CONTRACT_LIFECYCLE_MODULES="$(LOCAL_CONTRACT_LIFECYCLE_MODULES)" \
	  CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD="$${CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD:-}" \
	  bash scripts/dev/local_contract_lifecycle_rebuild.sh

local.contract-lifecycle.up: guard.prod.forbid local.contract-lifecycle.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" up

local.contract-lifecycle.down: guard.prod.forbid local.contract-lifecycle.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" down

local.contract-lifecycle.ps: guard.prod.forbid local.contract-lifecycle.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" ps

local.contract-lifecycle.odoo-shell: guard.prod.forbid local.contract-lifecycle.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" \
	  local.contract-lifecycle.odoo-shell.run

# Loads the profile env through Make so RUN_ENV forwards the correct
# COMPOSE_PROJECT_NAME/COMPOSE_FILES/database identity to the shared shell
# entrypoint. Invoked only through the guarded outer target.
local.contract-lifecycle.odoo-shell.run:
	@$(RUN_ENV) DB_NAME="$(DB_NAME)" bash scripts/ops/odoo_shell_exec.sh

local.contract-lifecycle.upgrade: guard.prod.forbid local.contract-lifecycle.require_env
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" \
	  MODULE="$(MODULE)" CODEX_NEED_UPGRADE=1 CODEX_MODULES="$(MODULE)" mod.upgrade

local.contract-lifecycle.discard: guard.prod.forbid local.contract-lifecycle.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CONTRACT_LIFECYCLE_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_CONTRACT_LIFECYCLE_DISCARD="$${CONFIRM_LOCAL_CONTRACT_LIFECYCLE_DISCARD:-}" \
	  bash scripts/dev/local_contract_lifecycle_discard.sh

.PHONY: local.contract-snapshot.require_env local.contract-snapshot.prepare \
	local.contract-snapshot.seed local.contract-snapshot.rebuild \
	local.contract-snapshot.up local.contract-snapshot.down local.contract-snapshot.ps \
	local.contract-snapshot.logs local.contract-snapshot.odoo-shell \
	local.contract-snapshot.odoo-shell.run local.contract-snapshot.preference_record.probe \
	local.contract-snapshot.upgrade \
	local.contract-snapshot.discard local.contract-snapshot.contract_export \
	local.contract-snapshot.gate_contract local.contract-snapshot.gate_contract.run \
	local.contract-snapshot.matrix_audit local.contract-snapshot.matrix_audit.run

local.contract-snapshot.require_env: guard.prod.forbid
	@test -f "$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" || { echo "contract-snapshot env is not prepared: $(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" >&2; exit 2; }

local.contract-snapshot.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" SOURCE_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  TARGET_ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  LOCAL_CONTRACT_SNAPSHOT_PASSWORD="$(LOCAL_CONTRACT_SNAPSHOT_PASSWORD)" \
	  LOCAL_CONTRACT_SNAPSHOT_NGINX_PORT="$(LOCAL_CONTRACT_SNAPSHOT_NGINX_PORT)" \
	  LOCAL_CONTRACT_SNAPSHOT_ODOO_PORT="$(LOCAL_CONTRACT_SNAPSHOT_ODOO_PORT)" \
	  LOCAL_CONTRACT_SNAPSHOT_PREPARE_FOR_REBUILD="$${LOCAL_CONTRACT_SNAPSHOT_PREPARE_FOR_REBUILD:-0}" \
	  CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD="$${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD:-}" \
	  bash scripts/dev/local_contract_snapshot_env_prepare.sh

local.contract-snapshot.seed: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_CONTRACT_SNAPSHOT_SEED="$${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_SEED:-}" \
	  bash scripts/dev/local_contract_snapshot_seed.sh

local.contract-snapshot.rebuild: guard.prod.forbid local.contract-snapshot.prepare
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  LOCAL_CONTRACT_SNAPSHOT_MODULES="$(LOCAL_CONTRACT_SNAPSHOT_MODULES)" \
	  CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD="$${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_REBUILD:-}" \
	  bash scripts/dev/local_contract_snapshot_rebuild.sh

local.contract-snapshot.up: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" up

local.contract-snapshot.down: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" down

local.contract-snapshot.ps: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" ps

local.contract-snapshot.logs: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" logs

local.contract-snapshot.odoo-shell: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  local.contract-snapshot.odoo-shell.run

# Loads the profile env through Make so RUN_ENV forwards the correct
# COMPOSE_PROJECT_NAME/COMPOSE_FILES/database identity to the shared shell
# entrypoint. Invoked only through the guarded outer target.
local.contract-snapshot.odoo-shell.run:
	@$(RUN_ENV) DB_NAME="$(DB_NAME)" bash scripts/ops/odoo_shell_exec.sh

# Read-only inventory of the historical preference sentinel row in the
# registered contract-snapshot database (sc_contract_snapshot). The tracked
# snapshot's environment-assigned ``id`` is described but never used as a
# deletion handle; resolution is always by (user_id, scope_key). Commit is
# refused and the carrier rolls back. See
# scripts/verify/local_contract_snapshot_preference_record_probe.py.
local.contract-snapshot.preference_record.probe: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  local.contract-snapshot.odoo-shell < scripts/verify/local_contract_snapshot_preference_record_probe.py

local.contract-snapshot.upgrade: guard.prod.forbid local.contract-snapshot.require_env
	@test -n "$(MODULE)" || (echo "MODULE is required" >&2; exit 2)
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  MODULE="$(MODULE)" CODEX_NEED_UPGRADE=1 CODEX_MODULES="$(MODULE)" mod.upgrade

# Regenerate the contract snapshot lane against this worktree's source mount.
# Writes docs/contract/snapshots/<case>.json for every case in cases.yml; use
# CONTRACT_CASE_ONLY=<case> or CONTRACT_START_CASE=<case> to bound the run.
local.contract-snapshot.contract_export: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  CONTRACT_OUTDIR="$(CONTRACT_OUTDIR)" \
	  CONTRACT_START_CASE="$(CONTRACT_START_CASE)" CONTRACT_CASE_ONLY="$(CONTRACT_CASE_ONLY)" \
	  contract.export_all

# Compare regenerated snapshots against the tracked references. Defaults to the
# full cases file; set LOCAL_CONTRACT_SNAPSHOT_CASES_FILE to a subset to bound
# the run while iterating. Set LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS=--bootstrap to
# copy genuinely new baselines into the reference directory.
#
# A full matrix run is single-shot per freshly seeded profile: matrix cases
# perform writes, and my_work_complete_batch_pm declares a fixed request_id that
# leaves a durable idempotency record. Run local.contract-snapshot.rebuild (or
# discard + prepare + seed + upgrade) before a full gate run; the seed purges the
# transient run-state a dump can carry in, and refuses to run against a live
# profile.
LOCAL_CONTRACT_SNAPSHOT_CASES_FILE ?= docs/contract/cases.yml
REF_DIR ?= docs/contract/snapshots
LOCAL_CONTRACT_SNAPSHOT_AUDIT_OUTDIR ?= tmp/contract_snapshot_audit

local.contract-snapshot.gate_contract.run:
	@DB="$(DB_NAME)" CASES_FILE="$(LOCAL_CONTRACT_SNAPSHOT_CASES_FILE)" REF_DIR="$(REF_DIR)" \
	  CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" \
	  scripts/contract/gate_contract.sh $(LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS)

local.contract-snapshot.gate_contract: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  LOCAL_CONTRACT_SNAPSHOT_CASES_FILE="$(LOCAL_CONTRACT_SNAPSHOT_CASES_FILE)" \
	  REF_DIR="$(REF_DIR)" LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS="$(LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS)" \
	  local.contract-snapshot.gate_contract.run

local.contract-snapshot.matrix_audit.run:
	@DB_NAME="$(DB_NAME)" CASES_FILE="$(LOCAL_CONTRACT_SNAPSHOT_CASES_FILE)" \
	  OUTDIR="$(LOCAL_CONTRACT_SNAPSHOT_AUDIT_OUTDIR)" \
	  CONTRACT_CONFIG="$(CONTRACT_CONFIG)" ODOO_CONF="$(ODOO_CONF)" \
	  bash scripts/dev/local_contract_snapshot_matrix_audit.sh

# Diagnostic only: list every case that fails to export, instead of stopping at
# the first one. The gate (local.contract-snapshot.gate_contract) stays fail-fast
# and is unchanged; this target is not evidence of a pass.
local.contract-snapshot.matrix_audit: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" \
	  LOCAL_CONTRACT_SNAPSHOT_CASES_FILE="$(LOCAL_CONTRACT_SNAPSHOT_CASES_FILE)" \
	  LOCAL_CONTRACT_SNAPSHOT_AUDIT_OUTDIR="$(LOCAL_CONTRACT_SNAPSHOT_AUDIT_OUTDIR)" \
	  local.contract-snapshot.matrix_audit.run

local.contract-snapshot.discard: guard.prod.forbid local.contract-snapshot.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CONTRACT_SNAPSHOT_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  CONFIRM_LOCAL_CONTRACT_SNAPSHOT_DISCARD="$${CONFIRM_LOCAL_CONTRACT_SNAPSHOT_DISCARD:-}" \
	  bash scripts/dev/local_contract_snapshot_discard.sh

local.clean.prepare: guard.prod.forbid
	@ROOT_DIR="$(ROOT_DIR)" SOURCE_ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  TARGET_ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" bash scripts/dev/local_clean_env_prepare.sh

local.clean.up: guard.prod.forbid local.clean.prepare local.clean.frontend.prepare_output
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" up

local.clean.down: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" down

local.clean.restart: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" restart

local.clean.logs: guard.prod.forbid local.clean.require_env
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/local_environment_doctor.sh clean

local.clean.frontend: guard.prod.forbid local.clean.prepare local.clean.frontend.prepare_output
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

# Required feature environment plus explicitly optional lanes; strict all-profile status remains below.
.PHONY: local.env.readiness verify.local.env.readiness.unit
verify.local.env.readiness.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_local_environment_readiness.py

local.env.readiness: guard.prod.forbid
	@python3 scripts/dev/local_environment_readiness.py --root "$(ROOT_DIR)" \
	  --dev-env "$(LOCAL_DEV_ENV_FILE)" --sample-env "$(LOCAL_SAMPLE_ENV_FILE)" \
	  --clean-env "$(LOCAL_CLEAN_ENV_FILE)"

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
# Development/acceptance fixture login password.
# The local acceptance tenant is an isolated synthetic database, so a fixed,
# intentionally simple value keeps repeated verification reproducible instead
# of rotating a secret on every run. Override explicitly when a distinct value
# is required: `make <target> SC_ACCEPTANCE_FIXTURE_PASSWORD=<value>`.
SC_ACCEPTANCE_FIXTURE_PASSWORD ?= scdevpass
export SC_ACCEPTANCE_FIXTURE_PASSWORD

acceptance.runtime.preflight: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh preflight

acceptance.runtime.infrastructure.restore: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh infrastructure-restore

.PHONY: acceptance.runtime.baseline_recovery.audit acceptance.runtime.baseline_rebuild acceptance.runtime.carrier.discard acceptance.runtime.carrier.provision verify.acceptance.runtime.baseline_rebuild.unit
verify.acceptance.runtime.baseline_rebuild.unit: guard.prod.forbid
	@bash -n scripts/dev/frontend_acceptance_baseline_rebuild.sh scripts/dev/frontend_acceptance_runtime.sh scripts/dev/frontend_acceptance_operation_entry.sh scripts/dev/frontend_acceptance_carrier_common.sh scripts/dev/frontend_acceptance_carrier_discard.sh scripts/dev/frontend_acceptance_carrier_provision.sh
	@python3 -m unittest scripts.verify.test_frontend_acceptance_baseline_rebuild scripts.verify.test_frontend_acceptance_runtime_profile scripts.verify.test_frontend_release_ci_identity scripts.verify.test_frontend_acceptance_carrier_discard
	@python3 scripts/verify/frontend_acceptance_environment_source_guard.py

# P4 environment entries for the managed local acceptance carrier
# (project sc-fe-r2-p1-01). discard removes only the three declared volumes;
# provision rebuilds the declared empty infrastructure and delegates the
# database/install/upgrade steps to the existing governed provisioning script.
# Both require the exact declared identity and an explicit confirmation phrase,
# and are the governed substitute for a hand-assembled `docker compose down`.
acceptance.runtime.carrier.discard: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" CONFIRM_ACCEPTANCE_CARRIER_DISCARD="$${CONFIRM_ACCEPTANCE_CARRIER_DISCARD:-}" bash scripts/dev/frontend_acceptance_operation_entry.sh carrier-discard

acceptance.runtime.carrier.provision: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" CONFIRM_ACCEPTANCE_CARRIER_PROVISION="$${CONFIRM_ACCEPTANCE_CARRIER_PROVISION:-}" bash scripts/dev/frontend_acceptance_operation_entry.sh carrier-provision

acceptance.runtime.baseline_recovery.audit: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh baseline-recovery-audit

acceptance.runtime.baseline_rebuild: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" EXPECTED_HEAD="$(EXPECTED_HEAD)" EXPECTED_DATABASES="$(EXPECTED_DATABASES)" APPLY="$(APPLY)" CONFIRM_ACCEPTANCE_BASELINE_REBUILD="$${CONFIRM_ACCEPTANCE_BASELINE_REBUILD:-}" bash scripts/dev/frontend_acceptance_operation_entry.sh baseline-rebuild

frontend.acceptance.up: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-up

frontend.acceptance.down: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-down

frontend.acceptance.health:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh frontend-health

backend.acceptance.up: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-up
.PHONY: backend.acceptance.replace-stale
backend.acceptance.replace-stale: guard.prod.forbid
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-replace-stale
backend.acceptance.down:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-down
backend.acceptance.health:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-health
backend.acceptance.logs:
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh backend-logs

backend.collection.acceptance.up: backend.acceptance.up
backend.collection.acceptance.down: backend.acceptance.down
frontend.collection.acceptance.up: frontend.acceptance.up
frontend.collection.acceptance.down: frontend.acceptance.down

ACCEPTANCE_BASE_URL ?= http://127.0.0.1:$(NGINX_PORT)
ACCEPTANCE_PROBE_OUTPUT ?= artifacts/backend/dev_acceptance_release_probe.json
# The daily/dev profile probes a different declared runtime than the acceptance
# instance. Keep its probe output separate so a daily run can never overwrite the
# instance receipt the acceptance lanes consume.
DAILY_ACCEPTANCE_PROBE_OUTPUT ?= artifacts/backend/daily_dev_acceptance_probe.json
ACCEPTANCE_LOGIN ?=
ACCEPTANCE_PASSWORD ?=
ACCEPTANCE_NAV_MIN_ACTIONS ?=
ACCEPTANCE_NAV_MAX_ACTIONS ?=
ACCEPTANCE_NAV_FORBIDDEN_LABELS ?=
ACCEPTANCE_NAV_REQUIRED_PATHS ?=
ACCEPTANCE_NAV_REQUIRED_ACTIONS ?=
ACCEPTANCE_CONTRACT_DECLARATION ?= config/acceptance/backend_contract_instance_v1.json
ACCEPTANCE_RECORD_RESOLUTION ?= artifacts/backend/acceptance_record_identity.json
ACCEPTANCE_CONTRACT_RESOLVER ?= scripts/verify/frontend_delivery_hardening_runtime_ids.py
ACCEPTANCE_CONTRACT_RESOLVER_KEY ?= FRONTEND_DELIVERY_HARDENING_TARGETS_JSON
# Daily development runtime carries the governed acceptance fixture (owner
# authorized 2026-10-04) so the readonly probe can produce an exact-instance
# backend contract receipt from the runtime it measures. This is a separate
# declared scope; the isolated sc_frontend_acceptance guard is unchanged.
DAILY_DEV_ACCEPTANCE_DB ?= sc_demo
DAILY_ACCEPTANCE_CONTRACT_DECLARATION ?= config/acceptance/backend_contract_instance_daily_v1.json
ACCEPTANCE_CONTRACT_PASSWORD ?= $(SC_ACCEPTANCE_FIXTURE_PASSWORD)
DAILY_ACCEPTANCE_REQUIRE_CONTRACT ?= 1
DAILY_ACCEPTANCE_FIXTURE_CONFIRM ?= ENSURE_DAILY_DEV_ACCEPTANCE_FIXTURE
# The accepted navigation action count is only determinate once a concrete role
# is locked.  The daily lane declares its principal role and resolves the count
# for that role from the versioned contract surface (never pinned here), so a
# contracted surface iteration is a data change while a delivered/contract or
# role-identity disagreement still fails the probe.
DAILY_ACCEPTANCE_NAV_MIN_ACTIONS ?= $(shell python3 scripts/verify/acceptance_action_count.py)
DAILY_ACCEPTANCE_NAV_MAX_ACTIONS ?= $(shell python3 scripts/verify/acceptance_action_count.py)
DAILY_ACCEPTANCE_NAV_PRINCIPAL_ROLE ?= $(shell python3 scripts/verify/acceptance_action_count.py --role)
DAILY_ACCEPTANCE_NAV_FORBIDDEN_LABELS ?= $(shell python3 -c 'import json; print(",".join(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["forbidden_labels"]))')
DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS ?= $(shell python3 -c 'import json; print(",".join(json.load(open("config/frontend/acceptance_environments_v1.json", encoding="utf-8"))["profiles"]["daily"]["navigation_policy"]["required_paths"]))')
DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY ?= construction.standard

verify.dev.acceptance.release: guard.prod.forbid check-compose-project check-compose-env
	@$(RUN_ENV) SC_ACCEPTANCE_EXPECTED_SHA="$$(git rev-parse HEAD)" DB_NAME=$(DB_NAME) ACCEPTANCE_BACKUP_DIR="$(ACCEPTANCE_BACKUP_DIR)" ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_NAV_MIN_ACTIONS="$(ACCEPTANCE_NAV_MIN_ACTIONS)" ACCEPTANCE_NAV_MAX_ACTIONS="$(ACCEPTANCE_NAV_MAX_ACTIONS)" ACCEPTANCE_NAV_FORBIDDEN_LABELS="$(ACCEPTANCE_NAV_FORBIDDEN_LABELS)" ACCEPTANCE_NAV_REQUIRED_PATHS="$(ACCEPTANCE_NAV_REQUIRED_PATHS)" ACCEPTANCE_NAV_REQUIRED_ACTIONS="$(ACCEPTANCE_NAV_REQUIRED_ACTIONS)" ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/ops/dev_acceptance_release_probe.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

.PHONY: verify.daily_dev.acceptance.readonly.probe
verify.daily_dev.acceptance.readonly.probe: ACCEPTANCE_PROBE_OUTPUT := $(DAILY_ACCEPTANCE_PROBE_OUTPUT)
verify.daily_dev.acceptance.readonly.probe: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@SC_ACCEPTANCE_PROFILE=daily SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" node scripts/verify/frontend_acceptance_environment_cli.mjs --tool daily-release-probe --operation readonly --expected-sha "$(ACCEPTANCE_TARGET_SHA)" --login "$(ACCEPTANCE_LOGIN)" --api-url "$(ACCEPTANCE_BASE_URL)"
	@test -n "$$ACCEPTANCE_LOGIN" -a -n "$$ACCEPTANCE_PASSWORD" || (echo "daily readonly credentials must be supplied through environment"; exit 2)
	@SC_ACCEPTANCE_EXPECTED_SHA="$(ACCEPTANCE_TARGET_SHA)" DB_NAME="$(DB_NAME)" ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" ACCEPTANCE_NAV_MIN_ACTIONS="$(DAILY_ACCEPTANCE_NAV_MIN_ACTIONS)" ACCEPTANCE_NAV_MAX_ACTIONS="$(DAILY_ACCEPTANCE_NAV_MAX_ACTIONS)" ACCEPTANCE_NAV_FORBIDDEN_LABELS="$(DAILY_ACCEPTANCE_NAV_FORBIDDEN_LABELS)" ACCEPTANCE_NAV_REQUIRED_PATHS="$(DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS)" ACCEPTANCE_NAV_REQUIRED_ACTIONS="" ACCEPTANCE_NAV_PRINCIPAL_ROLE="$(DAILY_ACCEPTANCE_NAV_PRINCIPAL_ROLE)" ACCEPTANCE_CONTRACT_DECLARATION="$(DAILY_ACCEPTANCE_CONTRACT_DECLARATION)" ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)" ACCEPTANCE_CONTRACT_PASSWORD="$(ACCEPTANCE_CONTRACT_PASSWORD)" ACCEPTANCE_REQUIRE_CONTRACT="$(DAILY_ACCEPTANCE_REQUIRE_CONTRACT)" ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/ops/dev_acceptance_release_probe.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

# --- daily development acceptance fixture lane -------------------------------
# Root-cause locks for the daily fixture lane. The P0 platform fix keeps the
# superuser has_group pass-through out of Odoo's public/portal audience markers;
# the fixture fix freezes its own payment execution without weakening the model
# guard. Both run against the registered local.dev profile and the real modules.
.PHONY: verify.smart_core.res_users_audience_group.orm verify.smart_core.relation_entry_publication.orm verify.acceptance_fixture.execution_freeze.orm verify.contract.project_ledger_entry_carrier.orm
verify.smart_core.res_users_audience_group.orm: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS=res_users_audience_group test.safe

# Root-cause lock for the P0 relation-open projection: a declared relation open
# entry must be a published (menu_id, action_id) pair from the same authority as
# navigation.route_authority, never a natively visible but unpublished menu.
verify.smart_core.relation_entry_publication.orm: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS=relation_entry_override test.safe

# The module this lane pins is listed in forbidden_implicit_modules: it is only
# ever installed on the managed acceptance carrier. Selecting the tag on
# local.dev matched nothing and still exited zero, so the registered lane now
# runs where the module actually exists and its tests actually execute.
verify.acceptance_fixture.execution_freeze.orm: guard.prod.forbid
	@$(MAKE) --no-print-directory acceptance.frontend.fixture_orm

# Carrier lock for the single project-center record entry: 项目台账 is the one
# permission/contract-driven project record surface, and the retired 项目信息编辑
# entry's complete composition must be provably carried into it (every field and
# button of the retired form, plus the 提交立项 button advertising exactly the
# groups the model method enforces). This binds declaration to behaviour at the
# owning layer instead of relying on selector strings.
verify.contract.project_ledger_entry_carrier.orm: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_core TEST_TAGS=core_extension_v2_finalize test.safe

# Governed report/apply entry for the unified ledger field-overlay repair. The
# ledger is the single project-center record entry, so its runtime contract must
# render the composition its authoritative native form declares; a stale legacy
# ui.form.field.policy overlay from the retired 项目信息编辑 era suppressed
# project_code. The migration in migrations/17.0.0.170 carries the repair into
# every module upgrade; this entry reports/repairs an already-deployed database
# through the registered compose project and DB_NAME binding.
.PHONY: verify.project.ledger.field_overlay.repair.unit project.ledger.field_overlay.repair
verify.project.ledger.field_overlay.repair.unit: guard.prod.forbid
	@python3 -m py_compile \
	  scripts/ops/repair_project_ledger_field_overlay.py \
	  addons/smart_construction_core/services/project_ledger_field_overlay_repair.py
	@python3 -c "import ast,sys; [ast.parse(open(p).read()) for p in sys.argv[1:]]" \
	  addons/smart_construction_core/migrations/17.0.0.170/pre-migration.py
project.ledger.field_overlay.repair: guard.prod.forbid check-compose-project check-compose-env verify.project.ledger.field_overlay.repair.unit
	@PROJECT_LEDGER_OVERLAY_ACTION="$${PROJECT_LEDGER_OVERLAY_ACTION:-report}" \
	  $(MAKE) --no-print-directory odoo.shell.exec < scripts/ops/repair_project_ledger_field_overlay.py

# The fixture carrier and its deterministic records are provisioned in the daily
# runtime database through the governed entries below. Both write entries require
# an explicit confirmation and bind DB_NAME=sc_demo; the contract resolution
# artifact is bound to the served runtime SHA and never to a local HEAD guess.
.PHONY: verify.daily_dev.acceptance_fixture.unit daily.dev.acceptance_fixture.ensure daily.dev.acceptance_contract.resolve
verify.daily_dev.acceptance_fixture.unit: guard.prod.forbid
	@bash -n scripts/dev/daily_dev_acceptance_fixture.sh
	@python3 -m py_compile \
	  addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py \
	  scripts/ops/dev_acceptance_release_probe.py \
	  scripts/verify/test_daily_acceptance_fixture_lane.py
	@python3 -m unittest scripts.verify.test_daily_acceptance_fixture_lane

daily.dev.acceptance_fixture.ensure: guard.prod.forbid
	@test "$(DB_NAME)" = "$(DAILY_DEV_ACCEPTANCE_DB)" || { echo "[DENY] daily dev acceptance fixture requires DB_NAME=$(DAILY_DEV_ACCEPTANCE_DB) (got $(DB_NAME))"; exit 3; }
	@test "$${CONFIRM_DAILY_DEV_ACCEPTANCE_FIXTURE:-}" = "$(DAILY_ACCEPTANCE_FIXTURE_CONFIRM)" || { echo "daily dev acceptance fixture confirmation is required"; exit 2; }
	@$(MAKE) --no-print-directory mod.install MODULE=smart_construction_acceptance_fixture
	@$(RUN_ENV) DB_NAME="$(DAILY_DEV_ACCEPTANCE_DB)" SC_ACCEPTANCE_FIXTURE_PASSWORD="$${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" bash scripts/dev/daily_dev_acceptance_fixture.sh

daily.dev.acceptance_contract.resolve: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -f "$(DAILY_ACCEPTANCE_CONTRACT_DECLARATION)" || (echo "[DENY] daily contract declaration missing: $(DAILY_ACCEPTANCE_CONTRACT_DECLARATION)"; exit 3)
	@set -eu; \
	served="$$(python3 -c 'import json,sys,urllib.request; print(json.load(urllib.request.urlopen(sys.argv[1], timeout=20)).get("git_sha",""))' "$(ACCEPTANCE_BASE_URL)/api/runtime-version")"; \
	test "$$served" = "$(ACCEPTANCE_TARGET_SHA)" || { echo "[DENY] daily served_sha=$$served != ACCEPTANCE_TARGET_SHA=$(ACCEPTANCE_TARGET_SHA)"; exit 4; }; \
	target_output="$$( $(RUN_ENV) DB_NAME="$(DAILY_DEV_ACCEPTANCE_DB)" SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=1 SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev bash scripts/ops/odoo_shell_exec.sh < $(ACCEPTANCE_CONTRACT_RESOLVER) 2>&1 )" || { printf '%s\n' "$$target_output"; exit 1; }; \
	payload="$$(printf '%s\n' "$$target_output" | sed -n 's/^$(ACCEPTANCE_CONTRACT_RESOLVER_KEY)=//p' | tail -n 1)"; \
	test -n "$$payload" || { printf '%s\n' "$$target_output"; echo "daily record identity payload missing"; exit 2; }; \
	mkdir -p "$$(dirname "$(ACCEPTANCE_RECORD_RESOLUTION)")"; \
	RESOLVED="$$payload" RESOLVED_SHA="$(ACCEPTANCE_TARGET_SHA)" PRODUCER="$(ACCEPTANCE_CONTRACT_RESOLVER)" python3 -c 'import json,os; payload=json.loads(os.environ["RESOLVED"]); envelope={"schema":"acceptance.record_identity_resolution.v1","producer":os.environ["PRODUCER"],"expected_sha":os.environ["RESOLVED_SHA"],"targets":payload}; open("$(ACCEPTANCE_RECORD_RESOLUTION)","w",encoding="utf-8").write(json.dumps(envelope,ensure_ascii=False,indent=2,sort_keys=True)+"\n")'; \
	echo "[daily.dev.acceptance_contract.resolve] wrote $(ACCEPTANCE_RECORD_RESOLUTION) sha=$$served"

.PHONY: verify.dev.acceptance.release.schema.guard
verify.dev.acceptance.release.schema.guard: guard.prod.forbid
	@python3 -m py_compile scripts/verify/dev_acceptance_release_probe_schema_guard.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

.PHONY: verify.dev.acceptance.record_identity.resolve verify.dev.acceptance.contract
verify.dev.acceptance.record_identity.resolve: guard.prod.forbid check-compose-project check-compose-env
	@set -eu; \
	resolved_sha="$(if $(ACCEPTANCE_TARGET_SHA),$(ACCEPTANCE_TARGET_SHA),$$(git rev-parse HEAD))"; \
	target_output="$$( $(RUN_ENV) DB_NAME=$(FRONTEND_ACCEPTANCE_DB) SC_ENVIRONMENT=acceptance SC_ALLOW_DEMO_DATA=1 bash scripts/ops/odoo_shell_exec.sh < $(ACCEPTANCE_CONTRACT_RESOLVER) 2>&1 )" || { printf '%s\n' "$$target_output"; exit 1; }; \
	payload="$$(printf '%s\n' "$$target_output" | sed -n 's/^$(ACCEPTANCE_CONTRACT_RESOLVER_KEY)=//p' | tail -n 1)"; \
	test -n "$$payload" || { printf '%s\n' "$$target_output"; echo "record identity resolution payload missing"; exit 2; }; \
	mkdir -p "$$(dirname "$(ACCEPTANCE_RECORD_RESOLUTION)")"; \
	RESOLVED="$$payload" RESOLVED_SHA="$$resolved_sha" PRODUCER="$(ACCEPTANCE_CONTRACT_RESOLVER)" python3 -c 'import json,os; payload=json.loads(os.environ["RESOLVED"]); targets=payload; envelope={"schema":"acceptance.record_identity_resolution.v1","producer":os.environ["PRODUCER"],"expected_sha":os.environ["RESOLVED_SHA"],"targets":targets}; open("$(ACCEPTANCE_RECORD_RESOLUTION)","w",encoding="utf-8").write(json.dumps(envelope,ensure_ascii=False,indent=2,sort_keys=True)+"\n")'; \
	echo "[verify.dev.acceptance.record_identity.resolve] wrote $(ACCEPTANCE_RECORD_RESOLUTION) sha=$$resolved_sha"

verify.dev.acceptance.contract: guard.prod.forbid
	@test -f "$(ACCEPTANCE_RECORD_RESOLUTION)" || (echo "governed record identity resolution required: make verify.dev.acceptance.record_identity.resolve (or retain the existing artifact)"; exit 2)
	@SC_ACCEPTANCE_EXPECTED_SHA="$(if $(ACCEPTANCE_TARGET_SHA),$(ACCEPTANCE_TARGET_SHA),$$(git rev-parse HEAD))" DB_NAME=$(FRONTEND_ACCEPTANCE_DB) ACCEPTANCE_BASE_URL="$(ACCEPTANCE_BASE_URL)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_CONTRACT_DECLARATION="$(ACCEPTANCE_CONTRACT_DECLARATION)" ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)" ACCEPTANCE_REQUIRE_CONTRACT=1 ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/ops/dev_acceptance_release_probe.py
	@ACCEPTANCE_PROBE_OUTPUT="$(ACCEPTANCE_PROBE_OUTPUT)" python3 scripts/verify/dev_acceptance_release_probe_schema_guard.py

release.dev.acceptance.publish: guard.prod.forbid check-compose-project check-compose-env verify.frontend.build verify.user_confirmed.formal_surface.locked verify.dev.acceptance.release
	@echo "[release.dev.acceptance.publish] PASS base_url=$(ACCEPTANCE_BASE_URL) db=$(DB_NAME) artifact=$(ACCEPTANCE_PROBE_OUTPUT)"

release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_MIN_ACTIONS := $(DAILY_ACCEPTANCE_NAV_MIN_ACTIONS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_MAX_ACTIONS := $(DAILY_ACCEPTANCE_NAV_MAX_ACTIONS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_PRINCIPAL_ROLE := $(DAILY_ACCEPTANCE_NAV_PRINCIPAL_ROLE)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_FORBIDDEN_LABELS := $(DAILY_ACCEPTANCE_NAV_FORBIDDEN_LABELS)
release.daily_dev.acceptance.publish: ACCEPTANCE_NAV_REQUIRED_PATHS := $(DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS)
release.daily_dev.acceptance.publish: guard.prod.forbid verify.daily_dev.acceptance.env.guard env.matrix.check verify.daily_dev.runtime_repo.clean verify.daily_dev.product_menu_release_gate.guard release.dev.acceptance.publish
	@echo "[release.daily_dev.acceptance.publish] PASS base_url=$(ACCEPTANCE_BASE_URL) db=$(DB_NAME) head=$$(git rev-parse --short HEAD)"

DAILY_PRODUCT_NAVIGATION_DUTY ?= demo
DAILY_PRODUCT_NAVIGATION_PRODUCT_KEYS ?= $(if $(strip $(PRODUCT_MENU_CATALOG_PRODUCT_KEYS)),$(PRODUCT_MENU_CATALOG_PRODUCT_KEYS),construction.standard construction.preview)

release.daily_product_navigation.snapshot: guard.prod.forbid
	@test "$(ENV)" = "dev" || { echo "daily product navigation snapshot requires ENV=dev" >&2; exit 2; }
	@test "$(DB_NAME)" = "sc_demo" || { echo "daily product navigation snapshot requires DB_NAME=sc_demo" >&2; exit 2; }
	@case "$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY)" in construction.standard|construction.preview) ;; *) echo "daily product navigation snapshot product key is not allowed" >&2; exit 2;; esac
	@test "$${CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT:-}" = "RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION" || { echo "daily product navigation snapshot confirmation is required" >&2; exit 2; }
	@CONFIRM_DAILY_DUTY_EDITION_RELEASE=RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY \
	  python3 scripts/ops/daily_runtime_duty_edition_release.py publish \
	    --duty "$(DAILY_PRODUCT_NAVIGATION_DUTY)" \
	    --product-key "$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY)" \
	    --emit-refresh-json

# Refresh every published product snapshot from the locked contract. One command
# owns the whole published face so a baseline change and its runtime snapshot can
# never be separated into two manual steps again.
release.daily_product_navigation.refresh: guard.prod.forbid
	@test "$${CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT:-}" = "RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION" || { echo "daily product navigation refresh requires CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT=RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION" >&2; exit 2; }
	@set -e; for key in $$(printf '%s' "$(DAILY_PRODUCT_NAVIGATION_PRODUCT_KEYS)" | tr ',' ' '); do \
	  $(MAKE) --no-print-directory release.daily_product_navigation.snapshot DAILY_PRODUCT_NAVIGATION_PRODUCT_KEY="$$key"; \
	done

# Converge then prove in one governed run: refresh the snapshots from the locked
# contract, reload the served runtime (the worker caches the published route
# authority), then run the daily release-gate guard over the full product scope.
release.daily_product_navigation.converge: guard.prod.forbid
	@$(MAKE) --no-print-directory release.daily_product_navigation.refresh
	@python3 scripts/ops/daily_runtime_duty_odoo_shell.py --duty "$(DAILY_PRODUCT_NAVIGATION_DUTY)" --database "$(DB_NAME)" --restart
	@$(MAKE) --no-print-directory verify.daily_dev.product_menu_release_gate.guard

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

.PHONY: local.dev.menu_facts.snapshot
local.dev.menu_facts.snapshot: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_menu_fact_snapshot.py

.PHONY: local.dev.native_projection.audit
local.dev.native_projection.audit: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_native_projection_audit.py

.PHONY: local.clean.frontend.prepare_output
local.clean.frontend.prepare_output: guard.prod.forbid local.clean.prepare
	@$(LOCAL_ENV_ISOLATE) ROOT_DIR="$(ROOT_DIR)" ENV_FILE="$(LOCAL_CLEAN_ENV_FILE)" \
	  bash scripts/dev/local_clean_frontend_output_prepare.sh

.PHONY: local.dev.data_scope.inventory
local.dev.data_scope.inventory: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_data_scope_inventory.py

# Local-dev-only governed onboarding (owner ruling 2026-10-14, Option 1):
# the demo environment's main company IS the first onboarded business company,
# so onboarding retires its bootstrap carrier marker and writes ONE registration
# row. No business row changes company. Without the confirmation it is read-only.
.PHONY: local.dev.data_space.onboard
local.dev.data_space.onboard: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_CONFIRM_DATA_SPACE_ONBOARDING="$${SC_CONFIRM_DATA_SPACE_ONBOARDING:-}" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/ops/onboard_local_dev_demo_data_space.py

# Onboarding owns the operator identity realm, but an Odoo module upgrade
# reloads the demo user data while post_init_hook does not run again. This is
# the governed, idempotent reconcile entry for that case; read-only by default.
.PHONY: local.dev.data_space.enroll_identities
local.dev.data_space.enroll_identities: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_CONFIRM_DATA_SPACE_IDENTITY_ENROLLMENT="$${SC_CONFIRM_DATA_SPACE_IDENTITY_ENROLLMENT:-}" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/ops/enroll_local_dev_demo_data_space_identities.py

.PHONY: local.dev.demo.data_space.onboarding.plan
local.dev.demo.data_space.onboarding.plan: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_demo_data_space_onboarding_plan.py

.PHONY: local.dev.payroll.data_scope.readiness
local.dev.payroll.data_scope.readiness: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_payroll_data_scope_readiness.py

.PHONY: local.dev.data_scope.ceiling.readiness
local.dev.data_scope.ceiling.readiness: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/local_dev_data_scope_ceiling_readiness.py

# Read-only readback of the upgrade-time business-data ownership gate: which
# companies already own industry rows, and which of them were never onboarded.
# The gate itself runs in the module's pre-migration, so this entry exists to
# answer "would the next upgrade be refused, and for whom" before it is run.
.PHONY: local.dev.business_data.ownership.readiness
local.dev.business_data.ownership.readiness: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) $(RUN_ENV) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  SC_EXPECTED_DB="$${SC_EXPECTED_DB:-sc_dev_demo}" \
	  bash scripts/ops/odoo_shell_exec.sh < scripts/verify/business_data_ownership_readiness.py

# Registered verify alias for the run index: the real-principal lock on the
# installed data-purpose ceiling behind every declared ``source_bounded`` model,
# pinned to the fixed test tag so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.source_bounded_data_space_rules.orm
verify.local.dev.source_bounded_data_space_rules.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_core TEST_TAGS="source_bounded_data_space_rules" local.dev.test

# Registered verify alias for the run index: the upgrade-time business-data
# ownership gate, on real companies and the real registration authority, pinned
# to the fixed test tag so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.business_data_ownership.orm
verify.local.dev.business_data_ownership.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_core TEST_TAGS="data_space_business_data_ownership" local.dev.test

# Registered verify alias for the run index: the environment data-space
# onboarding boundary (both onboarding shapes, the carrier refusal and the
# customer-role refusal) on the real registration authority, pinned to the fixed
# test tag so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.data_space_boundary.orm
verify.local.dev.data_space_boundary.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="data_space_boundary" local.dev.test

# Registered verify alias for the run index: the per-principal delivery lock on
# sc.dictionary startup scope (global/company/role), pinned to the fixed test tag
# so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.dictionary_scope_delivery.orm
verify.local.dev.dictionary_scope_delivery.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="dictionary_scope_delivery" local.dev.test

# Registered verify alias for the run index: the real-principal lock on platform
# database governance (lifecycle entries, independent maintenance approval, and
# the never-a-business-data-grant boundary), pinned to the fixed test tag so a
# run that collects zero tests cannot pass.
.PHONY: verify.local.dev.platform_database_governance.orm
verify.local.dev.platform_database_governance.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="platform_database_governance" local.dev.test

# Onboarding must produce a readable data space: the operator identity realm is
# enrolled with the registration, never assembled per user in demo data.
.PHONY: verify.local.dev.data_space_identity_enrollment.orm
verify.local.dev.data_space_identity_enrollment.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="data_space_identity_enrollment" local.dev.test

# The data-space ceiling must read membership facts, not `has_group`: that
# helper is `tools.ormcache`d, so an out-of-band writer (odoo shell, cron, ops
# script) that never signals cache invalidation leaves a long-lived worker
# denying an authorized operator and serving a revoked one. The deployed daily
# runtime returned 403 for an enrolled operator exactly this way. Pinned to the
# fixed test tag so a run that collects zero tests cannot pass.
.PHONY: verify.local.dev.data_space_uncached_membership.orm
verify.local.dev.data_space_uncached_membership.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_core TEST_TAGS="data_space_uncached_membership" local.dev.test

# Owner-authorized independent control/target rehearsal. Never uses local.dev DBs.
.PHONY: platform.database.rehearsal.prepare platform.database.rehearsal.preflight platform.database.rehearsal.exercise platform.database.rehearsal.continue platform.database.rehearsal.export platform.database.rehearsal.readback platform.database.rehearsal.recover platform.database.rehearsal.cleanup
platform.database.rehearsal.prepare platform.database.rehearsal.preflight platform.database.rehearsal.exercise platform.database.rehearsal.continue platform.database.rehearsal.export platform.database.rehearsal.readback platform.database.rehearsal.recover platform.database.rehearsal.cleanup: guard.prod.forbid
	@python3 scripts/ops/platform_database_rehearsal.py $(lastword $(subst ., ,$@))

.PHONY: verify.local.dev.demo_action_roles.orm
verify.local.dev.demo_action_roles.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_action_roles" local.dev.test

.PHONY: verify.local.dev.demo_loaded_chains.orm
verify.local.dev.demo_loaded_chains.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_loaded_chains" local.dev.test

.PHONY: verify.local.dev.baseline_readiness.orm
verify.local.dev.baseline_readiness.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_baseline_readiness" local.dev.test

.PHONY: verify.local.dev.golden_chain.orm
verify.local.dev.golden_chain.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_golden_chain" local.dev.test

.PHONY: verify.local.dev.api_scenario.orm
verify.local.dev.api_scenario.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_api_scenario" local.dev.test

.PHONY: verify.local.dev.scenario_tick.orm
verify.local.dev.scenario_tick.orm: guard.prod.forbid
	@$(LOCAL_ENV_ISOLATE) $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  MODULE=smart_construction_demo TEST_TAGS="demo_scenario_tick" local.dev.test

# Unit guard for the bounded runtime-performance observation carrier. It runs the
# probe against a fake environment: no database, no runtime write, no browser.
.PHONY: verify.local.dev.runtime.performance.unit
verify.local.dev.runtime.performance.unit: guard.prod.forbid
	@python3 -m py_compile scripts/verify/local_dev_runtime_performance.py scripts/verify/test_local_dev_runtime_performance.py
	@python3 -m py_compile scripts/verify/local_dev_runtime_permission_probe.py scripts/verify/test_local_dev_runtime_permission_probe.py
	@python3 scripts/verify/test_local_dev_runtime_performance.py
	@python3 -m unittest scripts.verify.test_local_dev_runtime_permission_probe

.PHONY: local.dev.runtime.performance.observe
local.dev.runtime.performance.observe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_MODE="$(if $(PRODUCT_PERFORMANCE_MODE),$(PRODUCT_PERFORMANCE_MODE),observe)" \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  PRODUCT_PERFORMANCE_V2_SHA256="$$(sha256sum addons/smart_core/handlers/ui_contract_v2.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_UI_SHA256="$$(sha256sum addons/smart_core/handlers/ui_contract.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_ASSEMBLER_SHA256="$$(sha256sum addons/smart_core/app_config_engine/services/assemblers/page_assembler.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_DISPATCHER_SHA256="$$(sha256sum addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_PREFERENCE_SHA256="$$(sha256sum addons/smart_core/handlers/user_view_preference.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_REQUEST_CASE="$(if $(PRODUCT_PERFORMANCE_REQUEST_CASE),$(PRODUCT_PERFORMANCE_REQUEST_CASE),web_startup)" \
	  PRODUCT_PERFORMANCE_STAGE_PROBE_RELATIONS="$(PRODUCT_PERFORMANCE_STAGE_PROBE_RELATIONS)" \
	  PRODUCT_PERFORMANCE_SCENE_SHA256="$$(sha256sum addons/smart_core/governance/scene_normalizer.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_MENU_SHA256="$$(sha256sum addons/smart_core/delivery/menu_service.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_HANDLER_SHA256="$$(sha256sum addons/smart_core/handlers/system_init.py | awk '{print $$1}')" \
	  PRODUCT_PERFORMANCE_MENU_CONFIG_SHA256="$$(sha256sum addons/smart_core/app_config_engine/models/app_nav_config.py | awk '{print $$1}')" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_performance.py

.PHONY: local.dev.runtime.performance.browser
local.dev.runtime.performance.browser: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  PRODUCT_PERFORMANCE_BROWSER_SCOPE="$(if $(PRODUCT_PERFORMANCE_BROWSER_SCOPE),$(PRODUCT_PERFORMANCE_BROWSER_SCOPE),login)" \
	  bash scripts/verify/local_dev_runtime_performance_browser.sh

.PHONY: local.dev.runtime.startup_fact_reuse.probe
local.dev.runtime.startup_fact_reuse.probe: guard.prod.forbid local.dev.ready
	@python3 -m py_compile scripts/verify/local_dev_runtime_startup_fact_reuse_probe.py
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_MODE="$(if $(STARTUP_FACT_REUSE_MODE),$(STARTUP_FACT_REUSE_MODE),candidate)" \
	  PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_PROFILE="$(if $(STARTUP_FACT_REUSE_PROFILE),$(STARTUP_FACT_REUSE_PROFILE),counter)" \
	  PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_SAMPLES="$(if $(STARTUP_FACT_REUSE_SAMPLES),$(STARTUP_FACT_REUSE_SAMPLES),4)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_startup_fact_reuse_probe.py

# Read-only proof that declared admin-surface actions reach the published route
# authority with ``entry_target`` instead of a model-name inference. See
# scripts/verify/local_dev_runtime_entry_target_probe.py.
.PHONY: local.dev.runtime.entry_target.probe
local.dev.runtime.entry_target.probe: guard.prod.forbid local.dev.ready
	@python3 -m py_compile scripts/verify/local_dev_runtime_entry_target_probe.py
	@python3 scripts/verify/test_local_dev_runtime_entry_target_probe.py
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_entry_target_probe.py

# Read-only cache-identity probe for the R2 relation-demand boundary: where the
# R2 methods run relative to the persisted runtime-source write, and whether the
# persisted source token covers the affected code identity. Rollback-only writes,
# commit refused; see scripts/verify/local_dev_runtime_cache_identity_probe.py.
.PHONY: local.dev.runtime.cache_identity.probe
local.dev.runtime.cache_identity.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_cache_identity_probe.py

# Read-only preference-record inventory for R5: which ``sc.user.view.preference``
# rows exist on the governed runtime, who owns each one, and what the tracked
# snapshot's ``id`` claim resolves to today -- always by (user, scope_key), never
# by the snapshot id. Commit is refused; no product code, schema, fixture or ACL
# change; no row is written or deleted; see
# scripts/verify/local_dev_runtime_preference_record_probe.py.
.PHONY: local.dev.runtime.preference_record.probe
local.dev.runtime.preference_record.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_preference_record_probe.py

# Read-only permission-gate attribution probe for R4: splits the controller
# ``permission`` segment into its real sub-phases and separates the process-first
# initialization cost from the per-request cost, on the registered demo finance
# principal and the observed action. Commit is refused; no product code, schema,
# fixture or ACL change; see scripts/verify/local_dev_runtime_permission_probe.py.
.PHONY: local.dev.runtime.permission.probe
local.dev.runtime.permission.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  PRODUCT_PERFORMANCE_PERMISSION_CARRIER="$(PRODUCT_PERFORMANCE_PERMISSION_CARRIER)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_permission_probe.py

# Read-only bounded contract-request observation for R5: one fixed identity and
# one fixed ui.contract.v2 request repeated for a real distribution, with an
# explicit hot/variant/cold split, the router dispatch_* segments, SQL counts
# a copy.deepcopy profile, an inner attribution of authority_and_cache_lookup
# and a paired garbage-collection control group for one-off pauses. Commit is
# refused; no product code, schema, fixture or ACL change; see
# scripts/verify/local_dev_runtime_contract_request_probe.py.
.PHONY: local.dev.runtime.contract_request.probe
local.dev.runtime.contract_request.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_contract_request_probe.py

# Read-only per-request allocation attribution: on one fixed identity and one
# fixed ui.contract.v2 request it separates the real generation-0/1/2
# distribution (gc enabled) from a nesting-aware net-container attribution over
# a curated set of existing callables (gc disabled), so the residual hot-request
# allocation volume is located instead of inferred. Commit is refused; no
# product code, schema, fixture or ACL change; see
# scripts/verify/local_dev_runtime_allocation_attribution_probe.py.
.PHONY: local.dev.runtime.allocation_attribution.probe
local.dev.runtime.allocation_attribution.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_allocation_attribution_probe.py

# Read-only role-dimension contract observation: the same fixed ui.contract.v2
# request under several declared demo principals, so the contract identity and
# the visible relation surface are shown to vary by role, per-role first/cold/
# hot costs are separated from the process-first cost, and a role without the
# capability is refused explicitly instead of via an empty contract. Commit is
# refused; no product code, schema, fixture or ACL change; see
# scripts/verify/local_dev_runtime_contract_role_matrix_probe.py.
.PHONY: local.dev.runtime.contract_role_matrix.probe
local.dev.runtime.contract_role_matrix.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_contract_role_matrix_probe.py

# Uninstrumented record-form repeat probe: no SQL, deepcopy or GC wrappers, so
# the measured dispatch is the product path rather than the attribution probe's
# own graph walk. Same registered principal and record for first/hot repeats.
# Commit is refused; no product code, schema, fixture or ACL change; see
# scripts/verify/local_dev_runtime_record_form_probe.py.
.PHONY: local.dev.runtime.record_form.probe
local.dev.runtime.record_form.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_record_form_probe.py

# Runtime proof that the assembled-cache key/token move when the principal loses
# a group or a policy definition changes. Writes happen inside savepoints and are
# rolled back; commit is refused. See
# scripts/verify/local_dev_runtime_projection_cache_identity_probe.py.
.PHONY: local.dev.runtime.projection_cache_identity.probe
local.dev.runtime.projection_cache_identity.probe: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ODOO_SHELL_RUN_ISOLATED=1 \
	  $(MAKE) --no-print-directory ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" \
	  odoo.shell.exec < scripts/verify/local_dev_runtime_projection_cache_identity_probe.py

# P4 system performance baseline. One bounded capture on the registered
# sc-local-dev / sc_dev_demo profile; reuses the existing governed probes and
# normalizes their payloads once into artifacts/backend/system_performance_baseline.json
# and docs/ops/audit/system_performance_baseline.md. It starts no environment and
# never writes product code; missing identity is reported as an explicit gap.
# PRODUCT_PERFORMANCE_BASELINE_SOURCES selects the bounded capture set, for example
# "sla,observe" (default) or "sla,observe,contract_profile,contract_request,permission,cache_identity".
.PHONY: local.dev.runtime.performance.baseline
local.dev.runtime.performance.baseline: guard.prod.forbid local.dev.ready
	@if [ "$(DB_NAME)" != "sc_dev_demo" ] || [ "$(COMPOSE_PROJECT_NAME)" != "sc-local-dev" ]; then \
	  echo "❌ baseline capture requires the registered sc-local-dev/sc_dev_demo profile"; \
	  exit 2; \
	fi
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  MAKE="$(MAKE)" PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID="$(PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID)" \
	  PRODUCT_PERFORMANCE_BASELINE_SOURCES="$(if $(PRODUCT_PERFORMANCE_BASELINE_SOURCES),$(PRODUCT_PERFORMANCE_BASELINE_SOURCES),sla,observe)" \
	  PRODUCT_PERFORMANCE_BASELINE_STRICT="$(PRODUCT_PERFORMANCE_BASELINE_STRICT)" \
	  PRODUCT_PERFORMANCE_BASELINE_REUSE_UNCHANGED="$(PRODUCT_PERFORMANCE_BASELINE_REUSE_UNCHANGED)" \
	  bash scripts/verify/local_dev_performance_baseline.sh

# Non-zero unit tests for the baseline normalizer: positive cases must reach a
# complete baseline; negative cases must register a gap or fail closed.
.PHONY: verify.system.performance.baseline.unit
verify.system.performance.baseline.unit: guard.prod.forbid
	@python3 -m py_compile scripts/verify/system_performance_baseline.py scripts/verify/test_system_performance_baseline.py scripts/verify/local_dev_runtime_contract_role_matrix_probe.py scripts/verify/local_dev_runtime_record_form_probe.py scripts/verify/test_local_dev_runtime_record_form_probe.py scripts/verify/local_dev_runtime_projection_cache_identity_probe.py scripts/ops/local_dev_performance_identity.py
	@python3 -m unittest scripts.verify.test_system_performance_baseline scripts.verify.test_local_dev_runtime_record_form_probe

# Candidate view metadata is changed only inside a rollback-only shell transaction.
.PHONY: local.dev.user_permission.rehearsal
local.dev.user_permission.rehearsal: guard.prod.forbid local.dev.ready
	@$(LOCAL_ENV_ISOLATE) ENV=dev ENV_FILE="$(LOCAL_DEV_ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  ODOO_SHELL_RUN_ISOLATED=1 SC_ACCEPTANCE_USER_PERMISSION_REHEARSE=1 \
	  SC_ACCEPTANCE_USER_PERMISSION_SOURCE_SHA256="$$(sha256sum addons/smart_construction_core/views/support/runtime_user_management_views.xml | cut -d ' ' -f 1)" \
	  bash -c 'source "$$ROOT_DIR/scripts/common/env.sh"; exec bash "$$ROOT_DIR/scripts/ops/odoo_shell_exec.sh"' < scripts/verify/user_permission_view_contract_boundary_guard.py
