DAILY_CONTINUITY_CONTRACT ?= scripts/ops/daily_candidate_data_continuity_contract_v1.json
DAILY_CONTINUITY_BACKUP_DIR ?=
DAILY_CONTINUITY_EVIDENCE ?= /tmp/daily-candidate-data-continuity.json
DAILY_CANDIDATE_SSH_HOST ?=
DAILY_CONTINUITY_TOOL_SHA ?= $(shell git rev-parse HEAD)
DAILY_CONTINUITY_REMOTE_ROOT ?= /opt/sce/deployment-tools/$(DAILY_CONTINUITY_TOOL_SHA)
DAILY_SENTINEL_TEMP_FILE ?=
DAILY_CLONE_REHEARSAL_CONTRACT ?= scripts/ops/daily_candidate_clone_upgrade_contract_v1.json
DAILY_CLONE_RC6_CANDIDATE_MANIFEST ?=
DAILY_CLONE_RC6_CANDIDATE_REPOSITORY ?= $(CURDIR)
DAILY_CLONE_RC6_IMAGE_REF := ghcr.io/lidefend/sce-product@sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb
DAILY_CLONE_RC6_CONFIG_DIGEST := sha256:f468dedc5daf5252f9d7631ee6b31a55a164b97d52f5f0e8b71e46035389e244

.PHONY: daily.candidate.continuity.test daily.candidate.continuity.baseline daily.candidate.continuity.backup daily.candidate.continuity.validate daily.candidate.continuity.restore_drill daily.candidate.continuity.remote_install daily.candidate.continuity.remote_baseline daily.candidate.continuity.remote_backup daily.candidate.continuity.remote_restore_drill daily.candidate.continuity.remote_closeout daily.candidate.sentinel.test daily.candidate.sentinel.remote_capture daily.candidate.sentinel.remote_verify daily.candidate.sentinel.remote_cleanup_temp daily.candidate.clone_rehearsal.test daily.candidate.clone_rehearsal.freeze daily.candidate.clone_rehearsal.remote_image_import daily.candidate.clone_rehearsal.remote_preflight daily.candidate.clone_rehearsal.remote_execute

daily.candidate.continuity.test: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_data_continuity.py
	@python3 scripts/ops/test_daily_candidate_data_continuity.py

daily.candidate.sentinel.test: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_data_sentinel.py
	@python3 scripts/ops/test_daily_candidate_data_sentinel.py

daily.candidate.clone_rehearsal.test: guard.prod.forbid
	@python3 -m py_compile scripts/ops/release_candidate_eligibility.py scripts/ops/test_release_candidate_eligibility.py scripts/ops/daily_candidate_clone_upgrade_rehearsal.py scripts/ops/daily_candidate_clone_upgrade_executor.py
	@python3 scripts/ops/test_release_candidate_eligibility.py
	@python3 scripts/ops/test_daily_candidate_clone_upgrade_rehearsal.py
	@python3 scripts/ops/test_daily_candidate_clone_upgrade_executor.py

daily.candidate.clone_rehearsal.freeze: guard.prod.forbid
	@test -n "$(DAILY_CLONE_RC6_CANDIDATE_MANIFEST)" || { echo "DAILY_CLONE_RC6_CANDIDATE_MANIFEST is required" >&2; exit 2; }
	@test -f "$(DAILY_CLONE_RC6_CANDIDATE_MANIFEST)" || { echo "approved RC6 candidate manifest is unavailable" >&2; exit 2; }
	@python3 scripts/ops/daily_candidate_clone_upgrade_rehearsal.py freeze \
		--contract "$(DAILY_CLONE_REHEARSAL_CONTRACT)" \
		--candidate-manifest "$(DAILY_CLONE_RC6_CANDIDATE_MANIFEST)" \
		--repository "$(DAILY_CLONE_RC6_CANDIDATE_REPOSITORY)"

daily.candidate.continuity.baseline: guard.prod.forbid
	@DAILY_CONTINUITY_EVIDENCE="$(DAILY_CONTINUITY_EVIDENCE)" \
		python3 scripts/ops/daily_candidate_data_continuity.py baseline \
		--contract "$(DAILY_CONTINUITY_CONTRACT)"

daily.candidate.continuity.backup: guard.prod.forbid
	@test "$${CONFIRM_DAILY_CANDIDATE_BACKUP:-}" = "BACKUP_DAILY_CANDIDATE_PAIRED_STATE" || { echo "exact daily candidate backup confirmation is required" >&2; exit 2; }
	@DAILY_CONTINUITY_EVIDENCE="$(DAILY_CONTINUITY_EVIDENCE)" \
		python3 scripts/ops/daily_candidate_data_continuity.py backup \
		--contract "$(DAILY_CONTINUITY_CONTRACT)"

daily.candidate.continuity.validate: guard.prod.forbid
	@test -n "$(DAILY_CONTINUITY_BACKUP_DIR)" || { echo "DAILY_CONTINUITY_BACKUP_DIR is required" >&2; exit 2; }
	@DAILY_CONTINUITY_EVIDENCE="$(DAILY_CONTINUITY_EVIDENCE)" \
		python3 scripts/ops/daily_candidate_data_continuity.py validate \
		--contract "$(DAILY_CONTINUITY_CONTRACT)" \
		--backup-dir "$(DAILY_CONTINUITY_BACKUP_DIR)"

daily.candidate.continuity.restore_drill: guard.prod.forbid
	@test -n "$(DAILY_CONTINUITY_BACKUP_DIR)" || { echo "DAILY_CONTINUITY_BACKUP_DIR is required" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL:-}" = "RESTORE_ISOLATED_COPY" || { echo "exact isolated restore confirmation is required" >&2; exit 2; }
	@DAILY_CONTINUITY_EVIDENCE="$(DAILY_CONTINUITY_EVIDENCE)" \
		python3 scripts/ops/daily_candidate_data_continuity.py restore-drill \
		--contract "$(DAILY_CONTINUITY_CONTRACT)" \
		--backup-dir "$(DAILY_CONTINUITY_BACKUP_DIR)"

daily.candidate.continuity.remote_install: guard.prod.forbid
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_CANDIDATE_SSH_HOST)" =~ ^[A-Za-z0-9._-]+$$ ]] || { echo "invalid daily candidate SSH host" >&2; exit 2; }
	@[[ "$(DAILY_CONTINUITY_TOOL_SHA)" =~ ^[0-9a-f]{40}$$ ]] || { echo "invalid immutable tool SHA" >&2; exit 2; }
	@test -z "$$(git status --porcelain)" || { echo "clean worktree is required for immutable tool install" >&2; exit 2; }
	@git archive --format=tar "$(DAILY_CONTINUITY_TOOL_SHA)" \
		scripts/ops/daily_candidate_data_continuity.py \
		scripts/ops/daily_runtime_duty_identity.py \
		scripts/ops/daily_runtime_duty_payload.py \
		scripts/ops/daily_runtime_duty_edition_release.py \
		scripts/ops/daily_runtime_duty_operator_grant.py \
		scripts/ops/daily_runtime_duty_database_registration.py \
		scripts/ops/daily_runtime_platform_security_admin_bootstrap.py \
		scripts/ops/platform_security_admin_bootstrap.py \
		scripts/ops/daily_runtime_platform_security_admin_credential.py \
		scripts/ops/platform_security_admin_credential.py \
		scripts/ops/platform_database_register.py \
		scripts/ops/platform_database_receipt.py \
		addons/smart_core/security/data_space_provisioning.py \
		addons/smart_core/security/database_governance.py \
		addons/smart_core/security/tenant_payload_operator_policy.py \
		addons/smart_core/security/tenant_payload_operator.py \
		scripts/release/configure_colocated_platform_core.py \
		scripts/release/initialize_colocated_platform_snapshot.py \
		scripts/tenant_payload/odoo_action.py \
		scripts/tenant_payload/provision_operator.py \
		scripts/ops/daily_candidate_data_continuity_contract_v1.json \
		scripts/ops/daily_runtime_tenant_recovery_contract_v1.json \
		config/ops/daily_runtime_database_duties.v1.json \
		scripts/ops/daily_candidate_data_sentinel.py \
		scripts/ops/daily_candidate_data_sentinel_contract_v1.json \
		scripts/ops/daily_candidate_clone_upgrade_rehearsal.py \
		scripts/ops/daily_candidate_clone_upgrade_contract_v1.json \
		scripts/ops/daily_candidate_clone_upgrade_executor.py \
		scripts/ops/release_candidate_eligibility.py \
		config/releases/rc6_candidate.json \
		config/releases/rc6_candidate_supersession_legacy_projection.json \
		scripts/ops/production_acceptance_harness.py \
		scripts/ops/production_acceptance_contract_v1.json \
		scripts/ops/production_acceptance_package_v1.sha256 | \
		ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'set -eu; root="/opt/sce/deployment-tools"; final="$(DAILY_CONTINUITY_REMOTE_ROOT)"; staging="$$root/.incomplete-$(DAILY_CONTINUITY_TOOL_SHA)"; install -d -m 0700 "$$root"; if test -d "$$final"; then test "$$(cat "$$final/DEPLOYMENT_TOOL_SHA")" = "$(DAILY_CONTINUITY_TOOL_SHA)"; exit 0; fi; test ! -e "$$staging"; install -d -m 0700 "$$staging"; tar -xf - -C "$$staging"; printf "%s\n" "$(DAILY_CONTINUITY_TOOL_SHA)" > "$$staging/DEPLOYMENT_TOOL_SHA"; chmod 0600 "$$staging/DEPLOYMENT_TOOL_SHA"; mv "$$staging" "$$final"'

daily.candidate.continuity.remote_baseline: daily.candidate.continuity.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'DAILY_CONTINUITY_EVIDENCE=/tmp/daily-candidate-continuity-baseline.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" baseline'

daily.candidate.continuity.remote_backup: daily.candidate.continuity.remote_install
	@test "$${CONFIRM_DAILY_CANDIDATE_BACKUP:-}" = "BACKUP_DAILY_CANDIDATE_PAIRED_STATE" || { echo "exact daily candidate backup confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE DAILY_CONTINUITY_EVIDENCE=/tmp/daily-candidate-continuity-backup.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" backup'

daily.candidate.continuity.remote_restore_drill: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CONTINUITY_BACKUP_DIR)" || { echo "DAILY_CONTINUITY_BACKUP_DIR is required" >&2; exit 2; }
	@[[ "$(DAILY_CONTINUITY_BACKUP_DIR)" =~ ^/data/backups/daily_candidate/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$ ]] || { echo "invalid daily candidate backup directory" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL:-}" = "RESTORE_ISOLATED_COPY" || { echo "exact isolated restore confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY DAILY_CONTINUITY_EVIDENCE=/tmp/daily-candidate-continuity-restore.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" restore-drill --backup-dir "$(DAILY_CONTINUITY_BACKUP_DIR)"'

daily.candidate.continuity.remote_closeout: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CONTINUITY_BACKUP_DIR)" || { echo "DAILY_CONTINUITY_BACKUP_DIR is required" >&2; exit 2; }
	@[[ "$(DAILY_CONTINUITY_BACKUP_DIR)" =~ ^/data/backups/daily_candidate/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$ ]] || { echo "invalid daily candidate backup directory" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" closeout --backup-dir "$(DAILY_CONTINUITY_BACKUP_DIR)"'

# A duty is a database with exactly one owner: the platform control plane, the
# demo, or one customer development tenant. Each duty therefore needs its own
# paired recovery point before its first business-data write, and that point has
# to be captured, validated and restored through one governed entry instead of an
# ad-hoc pg_dump. The tool resolves every runtime identity (cluster, containers,
# volumes, application role, filestore scope, backup namespace) from
# `config/ops/daily_runtime_database_duties.v1.json`; the contract may only carry
# assertion configuration, and any restatement of identity must agree with the
# declaration. `--backup-dir` and confirmations use exact values, and the remote
# tool tree is installed from one immutable commit, so the entry refuses a dirty
# worktree. These targets are remote-only: the duty storage namespaces exist on
# the daily server, not in the local iteration profile.
.PHONY: verify.daily.duty.recovery daily.runtime.duty.recovery.remote_baseline daily.runtime.duty.recovery.remote_backup daily.runtime.duty.recovery.remote_validate daily.runtime.duty.recovery.remote_restore_drill
DAILY_DUTY_RECOVERY_CONTRACT ?= scripts/ops/daily_runtime_tenant_recovery_contract_v1.json
DAILY_DUTY_RECOVERY_BACKUP_DIR ?=
DAILY_DUTY_RECOVERY_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py
DAILY_DUTY_RECOVERY_CONTRACT_PATH ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/$(DAILY_DUTY_RECOVERY_CONTRACT)
DAILY_DUTY_RECOVERY_DIR_PATTERN ?= ^/data/backups/daily-tenant-baosheng-dev/sc_tenant_baosheng_dev-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$

verify.daily.duty.recovery: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_data_continuity.py scripts/ops/test_daily_candidate_data_continuity.py
	@python3 scripts/ops/test_daily_candidate_data_continuity.py

daily.runtime.duty.recovery.remote_baseline: daily.candidate.continuity.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'DAILY_CONTINUITY_EVIDENCE=/tmp/daily-duty-recovery-baseline.json python3 "$(DAILY_DUTY_RECOVERY_TOOL)" baseline --contract "$(DAILY_DUTY_RECOVERY_CONTRACT_PATH)"'

daily.runtime.duty.recovery.remote_backup: daily.candidate.continuity.remote_install
	@test "$${CONFIRM_DAILY_CANDIDATE_BACKUP:-}" = "BACKUP_DAILY_CANDIDATE_PAIRED_STATE" || { echo "exact duty backup confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE DAILY_CONTINUITY_EVIDENCE=/tmp/daily-duty-recovery-backup.json python3 "$(DAILY_DUTY_RECOVERY_TOOL)" backup --contract "$(DAILY_DUTY_RECOVERY_CONTRACT_PATH)"'

daily.runtime.duty.recovery.remote_validate: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)" || { echo "DAILY_DUTY_RECOVERY_BACKUP_DIR is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)" =~ $(DAILY_DUTY_RECOVERY_DIR_PATTERN) ]] || { echo "invalid duty recovery backup directory" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'DAILY_CONTINUITY_EVIDENCE=/tmp/daily-duty-recovery-validate.json python3 "$(DAILY_DUTY_RECOVERY_TOOL)" validate --contract "$(DAILY_DUTY_RECOVERY_CONTRACT_PATH)" --backup-dir "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)"'

daily.runtime.duty.recovery.remote_restore_drill: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)" || { echo "DAILY_DUTY_RECOVERY_BACKUP_DIR is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)" =~ $(DAILY_DUTY_RECOVERY_DIR_PATTERN) ]] || { echo "invalid duty recovery backup directory" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL:-}" = "RESTORE_ISOLATED_COPY" || { echo "exact isolated restore confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY DAILY_CONTINUITY_EVIDENCE=/tmp/daily-duty-recovery-restore.json python3 "$(DAILY_DUTY_RECOVERY_TOOL)" restore-drill --contract "$(DAILY_DUTY_RECOVERY_CONTRACT_PATH)" --backup-dir "$(DAILY_DUTY_RECOVERY_BACKUP_DIR)"'


# A signed historical payload may only enter a duty database through that duty's
# own rendered definition, as that duty's own application user, with the payload
# and its verification key exposed as verified read-only copies. This entry adds
# no privilege of its own: the operator authorization is still the product's
# narrow importer group granted by `tenant.payload.operator.grant`, ownership is
# never defaulted here, and only a duty declared `customer` may receive one.
# `plan` additionally proves it wrote nothing, so planning is safe on a duty that
# already holds real business data.
DAILY_DUTY_PAYLOAD_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_duty_payload.py
DAILY_DUTY_PAYLOAD_DUTY ?= customer_tenant_dev
DAILY_DUTY_PAYLOAD_ID ?=
DAILY_DUTY_PAYLOAD_CHECKSUM ?=
DAILY_DUTY_PAYLOAD_EVIDENCE ?=
DAILY_DUTY_PAYLOAD_CHUNK_SIZE ?= 100

.PHONY: verify.daily.duty.payload daily.runtime.duty.payload.remote_install daily.runtime.duty.payload.remote_plan daily.runtime.duty.payload.remote_import daily.runtime.duty.payload.remote_verify

verify.daily.duty.payload: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_duty_payload.py scripts/ops/test_daily_runtime_duty_payload.py
	@python3 scripts/ops/test_daily_runtime_duty_payload.py

daily.runtime.duty.payload.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.duty.payload.remote_plan: daily.runtime.duty.payload.remote_install
	@test -n "$(DAILY_DUTY_PAYLOAD_ID)" || { echo "DAILY_DUTY_PAYLOAD_ID is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_ID)" =~ ^[a-z0-9][a-z0-9._-]{2,127}$$ ]] || { echo "invalid daily duty payload id" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" =~ ^[0-9a-f]{64}$$ ]] || { echo "DAILY_DUTY_PAYLOAD_CHECKSUM must be the approved payload checksum" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_DUTY_PAYLOAD_TOOL)" plan --duty "$(DAILY_DUTY_PAYLOAD_DUTY)" --payload-id "$(DAILY_DUTY_PAYLOAD_ID)" --approved-checksum "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" --evidence "$(DAILY_DUTY_PAYLOAD_EVIDENCE)"'

daily.runtime.duty.payload.remote_import: daily.runtime.duty.payload.remote_install
	@test -n "$(DAILY_DUTY_PAYLOAD_ID)" || { echo "DAILY_DUTY_PAYLOAD_ID is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_ID)" =~ ^[a-z0-9][a-z0-9._-]{2,127}$$ ]] || { echo "invalid daily duty payload id" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" =~ ^[0-9a-f]{64}$$ ]] || { echo "DAILY_DUTY_PAYLOAD_CHECKSUM must be the approved payload checksum" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_CHUNK_SIZE)" =~ ^[1-9][0-9]*$$ ]] || { echo "invalid daily duty payload chunk size" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_PAYLOAD_IMPORT:-}" = "IMPORT_SIGNED_PAYLOAD_INTO_DAILY_DUTY" || { echo "exact daily duty payload import confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_PAYLOAD_IMPORT=IMPORT_SIGNED_PAYLOAD_INTO_DAILY_DUTY python3 "$(DAILY_DUTY_PAYLOAD_TOOL)" import --duty "$(DAILY_DUTY_PAYLOAD_DUTY)" --payload-id "$(DAILY_DUTY_PAYLOAD_ID)" --approved-checksum "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" --chunk-size "$(DAILY_DUTY_PAYLOAD_CHUNK_SIZE)" --evidence "$(DAILY_DUTY_PAYLOAD_EVIDENCE)"'

daily.runtime.duty.payload.remote_verify: daily.runtime.duty.payload.remote_install
	@test -n "$(DAILY_DUTY_PAYLOAD_ID)" || { echo "DAILY_DUTY_PAYLOAD_ID is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_ID)" =~ ^[a-z0-9][a-z0-9._-]{2,127}$$ ]] || { echo "invalid daily duty payload id" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" =~ ^[0-9a-f]{64}$$ ]] || { echo "DAILY_DUTY_PAYLOAD_CHECKSUM must be the approved payload checksum" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_DUTY_PAYLOAD_TOOL)" verify --duty "$(DAILY_DUTY_PAYLOAD_DUTY)" --payload-id "$(DAILY_DUTY_PAYLOAD_ID)" --approved-checksum "$(DAILY_DUTY_PAYLOAD_CHECKSUM)" --evidence "$(DAILY_DUTY_PAYLOAD_EVIDENCE)"'

# The released edition a runtime serves is owned by the platform delivery
# service, and the only governed entry that published the daily product edition
# was bound to the demo database -- so a customer development tenant could not
# register the edition it runs, could not be issued the narrow import grant, and
# could not start its own versioned migration. This entry resolves its whole
# identity (database, role, stack, containers, volumes, version prefix and the
# editions it may publish) from `config/ops/daily_runtime_database_duties.v1.json`,
# drives the existing governed release scripts inside the duty's own rendered
# definition, and reads the released identity back in a separate process.
# `platform_release_db` names the database that *carries* the effective release
# snapshot, which is why a tenant duty binds it to itself; the platform control
# duty declares no edition and is refused.
DAILY_DUTY_EDITION_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_duty_edition_release.py
DAILY_DUTY_EDITION_DUTY ?= customer_tenant_dev
DAILY_DUTY_EDITION_PRODUCT_KEY ?= construction.standard
DAILY_DUTY_EDITION_EVIDENCE ?=

.PHONY: verify.daily.duty.edition_release daily.runtime.duty.edition_release.remote_install daily.runtime.duty.edition_release.remote_readback daily.runtime.duty.edition_release.remote_publish

verify.daily.duty.edition_release: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_duty_edition_release.py scripts/ops/test_daily_runtime_duty_edition_release.py
	@python3 scripts/ops/test_daily_runtime_duty_edition_release.py

daily.runtime.duty.edition_release.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.duty.edition_release.remote_readback: daily.runtime.duty.edition_release.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_DUTY_EDITION_TOOL)" readback --duty "$(DAILY_DUTY_EDITION_DUTY)" --evidence "$(DAILY_DUTY_EDITION_EVIDENCE)"'

daily.runtime.duty.edition_release.remote_publish: daily.runtime.duty.edition_release.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_EDITION_PRODUCT_KEY)" =~ ^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$$ ]] || { echo "invalid daily duty edition product key" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_EDITION_RELEASE:-}" = "RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY" || { echo "exact daily duty edition release confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_EDITION_RELEASE=RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY python3 "$(DAILY_DUTY_EDITION_TOOL)" publish --duty "$(DAILY_DUTY_EDITION_DUTY)" --product-key "$(DAILY_DUTY_EDITION_PRODUCT_KEY)" --evidence "$(DAILY_DUTY_EDITION_EVIDENCE)"'

# The narrow payload import operator is carried by the unified onboarding
# mechanism: the platform owns the account lifecycle (provision/grant/revoke)
# and the customer module must not create platform operators. This entry is the
# daily-duty transport -- it resolves the duty and the operator contract from
# `config/ops/daily_runtime_database_duties.v1.json` and drives the platform
# mechanism inside the duty's own rendered definition. It carries no operator
# identity of its own (a duty that has not declared one stops instead of
# defaulting to the widest account in the database) and it invents no approval:
# `provision` and `grant` require an approved access read back from the platform
# control database, and the approver is never supplied on the command line.
# `readback` runs as a separate process and proves it wrote nothing.
DAILY_DUTY_OPERATOR_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_duty_operator_grant.py
DAILY_DUTY_OPERATOR_DUTY ?= customer_tenant_dev
DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM ?=
DAILY_DUTY_OPERATOR_EVIDENCE ?=
DAILY_DUTY_OPERATOR_POLICY := addons/smart_core/security/tenant_payload_operator_policy.py
DAILY_DUTY_OPERATOR_LIFECYCLE := addons/smart_core/security/tenant_payload_operator.py

.PHONY: verify.daily.duty.operator_grant daily.runtime.duty.operator_grant.remote_install daily.runtime.duty.operator_grant.remote_readback daily.runtime.duty.operator_grant.remote_provision daily.runtime.duty.operator_grant.remote_grant daily.runtime.duty.operator_grant.remote_revoke

verify.daily.duty.operator_grant: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_duty_operator_grant.py scripts/ops/test_daily_runtime_duty_operator_grant.py $(DAILY_DUTY_OPERATOR_POLICY) $(DAILY_DUTY_OPERATOR_LIFECYCLE) scripts/verify/test_tenant_payload_operator_policy.py
	@python3 -m unittest scripts.verify.test_tenant_payload_operator_policy
	@python3 scripts/ops/test_daily_runtime_duty_operator_grant.py

daily.runtime.duty.operator_grant.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.duty.operator_grant.remote_readback: daily.runtime.duty.operator_grant.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_DUTY_OPERATOR_TOOL)" readback --duty "$(DAILY_DUTY_OPERATOR_DUTY)" --evidence "$(DAILY_DUTY_OPERATOR_EVIDENCE)"'

daily.runtime.duty.operator_grant.remote_provision: daily.runtime.duty.operator_grant.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM)" =~ ^[0-9a-f]{64}$$ ]] || { echo "DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM must be the payload digest the approval binds" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_OPERATOR_PROVISION:-}" = "PROVISION_DECLARED_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY" || { echo "exact daily duty operator provision confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_OPERATOR_PROVISION=PROVISION_DECLARED_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY python3 "$(DAILY_DUTY_OPERATOR_TOOL)" provision --duty "$(DAILY_DUTY_OPERATOR_DUTY)" --subject-checksum "$(DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM)" --evidence "$(DAILY_DUTY_OPERATOR_EVIDENCE)"'

daily.runtime.duty.operator_grant.remote_grant: daily.runtime.duty.operator_grant.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM)" =~ ^[0-9a-f]{64}$$ ]] || { echo "DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM must be the payload digest the approval binds" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_OPERATOR_GRANT:-}" = "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY" || { echo "exact daily duty operator grant confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_OPERATOR_GRANT=GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY python3 "$(DAILY_DUTY_OPERATOR_TOOL)" grant --duty "$(DAILY_DUTY_OPERATOR_DUTY)" --subject-checksum "$(DAILY_DUTY_OPERATOR_SUBJECT_CHECKSUM)" --evidence "$(DAILY_DUTY_OPERATOR_EVIDENCE)"'

daily.runtime.duty.operator_grant.remote_revoke: daily.runtime.duty.operator_grant.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_OPERATOR_REVOKE:-}" = "REVOKE_TEMPORARY_DAILY_DUTY_IMPORT_OPERATOR_GRANT" || { echo "exact daily duty operator revoke confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_OPERATOR_REVOKE=REVOKE_TEMPORARY_DAILY_DUTY_IMPORT_OPERATOR_GRANT python3 "$(DAILY_DUTY_OPERATOR_TOOL)" revoke --duty "$(DAILY_DUTY_OPERATOR_DUTY)" --evidence "$(DAILY_DUTY_OPERATOR_EVIDENCE)"'

# The platform registry is the single fact for which database serves which
# purpose and tenant, and the unified onboarding mechanism is its only writer.
# This entry is the daily-duty transport for that fact: it resolves the target
# from `config/ops/daily_runtime_database_duties.v1.json`, drives the immutable
# `platform.database.register` entry inside the platform control duty's own
# rendered stack, and reads the registration back in a separate process. The
# environment role and the strategy come from the platform's own vocabulary, so
# this transport declares no identity of its own and the control plane is never
# registered as a data space. Registering is idempotent in the safe direction
# only: an existing row that matches the declaration is reused, while one that
# names another identity is a stop -- a registration identity is never taken
# over or rewritten. `readback` writes nothing and is safe before any write.
DAILY_DUTY_REGISTRATION_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_duty_database_registration.py
DAILY_DUTY_REGISTRATION_DUTY ?= customer_tenant_dev
DAILY_DUTY_REGISTRATION_REASON ?=
DAILY_DUTY_REGISTRATION_EVIDENCE ?=

.PHONY: verify.daily.duty.database_registration daily.runtime.duty.database_registration.remote_install daily.runtime.duty.database_registration.remote_readback daily.runtime.duty.database_registration.remote_register

verify.daily.duty.database_registration: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_duty_database_registration.py scripts/ops/test_daily_runtime_duty_database_registration.py
	@python3 -m unittest scripts.ops.test_daily_runtime_duty_database_registration

daily.runtime.duty.database_registration.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.duty.database_registration.remote_readback: daily.runtime.duty.database_registration.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_DUTY_REGISTRATION_TOOL)" readback --duty "$(DAILY_DUTY_REGISTRATION_DUTY)" --evidence "$(DAILY_DUTY_REGISTRATION_EVIDENCE)"'

daily.runtime.duty.database_registration.remote_register: daily.runtime.duty.database_registration.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@reason_pattern='^[A-Za-z0-9][A-Za-z0-9 .,;:_-]{9,199}$$'; [[ "$(DAILY_DUTY_REGISTRATION_REASON)" =~ $$reason_pattern ]] || { echo "DAILY_DUTY_REGISTRATION_REASON must state why this database is registered (10-200 characters, one printable line)" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION:-}" = "REGISTER_DECLARED_DAILY_DUTY_IN_PLATFORM_REGISTRY" || { echo "exact daily duty database registration confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION=REGISTER_DECLARED_DAILY_DUTY_IN_PLATFORM_REGISTRY python3 "$(DAILY_DUTY_REGISTRATION_TOOL)" register --duty "$(DAILY_DUTY_REGISTRATION_DUTY)" --reason "$(DAILY_DUTY_REGISTRATION_REASON)" --evidence "$(DAILY_DUTY_REGISTRATION_EVIDENCE)"'

# The independent approving identity is a platform mechanism: the maintenance
# authorization flow must be approved by a real, named security administrator,
# and establishing that identity is its own governed bootstrap step rather than
# a side effect of a maintenance request. This entry binds it to the declared
# platform control duty, loads the immutable entry from the reviewed scripts
# mount and reads the identity and the authorization ledger back in separate
# processes, so a bootstrap that approved its own request, took over a shared
# carrier or moved the ledger is refused.
DAILY_SECURITY_ADMIN_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_platform_security_admin_bootstrap.py
DAILY_SECURITY_ADMIN_LOGIN ?=
DAILY_SECURITY_ADMIN_NAME ?=
DAILY_SECURITY_ADMIN_EVIDENCE ?=

# The named approver exists without a stored credential by design, so no
# principal can authenticate as it and the maintenance approval cannot be
# exercised for real.  This step supplies that one fact and nothing else: it only
# issues a credential for an identity that already carries exactly the
# control-plane security-administrator closure, it refuses to take over an
# account that already carries one, it approves nothing, and it asserts the
# authorization ledger is exactly as it found it.  The credential is written to
# the operator-only artefact mount -- never printed, never an argument -- and the
# clear action retires it again.
DAILY_SECURITY_ADMIN_CREDENTIAL_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_runtime_platform_security_admin_credential.py

# The declared values reach the entry through the environment, never through the
# text of a recipe.  Make expands a recipe line before any shell parses it, so a
# value interpolated into `test -n "$(VALUE)"` could otherwise contribute a
# command of its own; carrying it in the environment makes that impossible, and
# the check below is then the entry's own grammar rather than a second copy of it
# that can drift away from the authority it is meant to guard.
export DAILY_SECURITY_ADMIN_LOGIN
export DAILY_SECURITY_ADMIN_NAME
export DAILY_SECURITY_ADMIN_EVIDENCE

.PHONY: verify.platform.security_admin.bootstrap verify.platform.security_admin.credential daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.bootstrap.remote_install daily.runtime.platform.security_admin.bootstrap.remote_readback daily.runtime.platform.security_admin.bootstrap.remote_bootstrap daily.runtime.platform.security_admin.credential.remote_install daily.runtime.platform.security_admin.credential.remote_readback daily.runtime.platform.security_admin.credential.remote_issue daily.runtime.platform.security_admin.credential.remote_clear

verify.platform.security_admin.bootstrap: guard.prod.forbid
	@python3 -m py_compile scripts/ops/platform_security_admin_bootstrap.py scripts/ops/test_platform_security_admin_bootstrap.py scripts/ops/daily_runtime_platform_security_admin_bootstrap.py scripts/ops/test_daily_runtime_platform_security_admin_bootstrap.py
	@python3 -m unittest scripts.ops.test_platform_security_admin_bootstrap
	@python3 -m unittest scripts.ops.test_daily_runtime_platform_security_admin_bootstrap

verify.platform.security_admin.credential: guard.prod.forbid
	@python3 -m py_compile scripts/ops/platform_security_admin_credential.py scripts/ops/test_platform_security_admin_credential.py scripts/ops/daily_runtime_platform_security_admin_credential.py
	@python3 -m unittest scripts.ops.test_platform_security_admin_credential

# One declaration and one check for every action that carries these values to the
# remote entry as shell arguments, so no action can be guarded more loosely than
# another and no payload-breaking character is refused only in prose.
daily.runtime.security_admin.payload_inputs: guard.prod.forbid
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_CANDIDATE_SSH_HOST)" =~ ^[A-Za-z0-9._-]+$$ ]] || { echo "invalid daily candidate SSH host" >&2; exit 2; }
	@python3 -c 'import importlib.util, os, sys; sys.path.insert(0, os.getcwd()); spec = importlib.util.spec_from_file_location("platform_security_admin_credential", "scripts/ops/platform_security_admin_credential.py"); entry = importlib.util.module_from_spec(spec); spec.loader.exec_module(entry); request = entry.resolve_request({entry.LOGIN_ENV: os.environ.get("DAILY_SECURITY_ADMIN_LOGIN", ""), entry.NAME_ENV: os.environ.get("DAILY_SECURITY_ADMIN_NAME", ""), entry.EVIDENCE_ENV: os.environ.get("DAILY_SECURITY_ADMIN_EVIDENCE", ""), entry.OUTPUT_ENV: entry.DEFAULT_OUTPUT}, "readback"); print("[payload_inputs] login=%s name=%s evidence=%s" % (request["login"], request["name"], request["evidence"]))' || { echo "the declared approver inputs do not resolve against the entry's own grammar" >&2; exit 2; }

daily.runtime.platform.security_admin.bootstrap.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.platform.security_admin.bootstrap.remote_readback: daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.bootstrap.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_SECURITY_ADMIN_TOOL)" readback --login "$(DAILY_SECURITY_ADMIN_LOGIN)" --name "$(DAILY_SECURITY_ADMIN_NAME)" --evidence "$(DAILY_SECURITY_ADMIN_EVIDENCE)"'

daily.runtime.platform.security_admin.bootstrap.remote_bootstrap: daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.bootstrap.remote_install
	@test "$${SC_CONFIRM_PLATFORM_SECURITY_ADMIN_BOOTSTRAP:-}" = "BOOTSTRAP_DECLARED_PLATFORM_SECURITY_ADMIN" || { echo "exact platform security administrator bootstrap confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'SC_CONFIRM_PLATFORM_SECURITY_ADMIN_BOOTSTRAP=BOOTSTRAP_DECLARED_PLATFORM_SECURITY_ADMIN python3 "$(DAILY_SECURITY_ADMIN_TOOL)" bootstrap --login "$(DAILY_SECURITY_ADMIN_LOGIN)" --name "$(DAILY_SECURITY_ADMIN_NAME)" --evidence "$(DAILY_SECURITY_ADMIN_EVIDENCE)"'

daily.runtime.platform.security_admin.credential.remote_install: daily.candidate.continuity.remote_install
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }

daily.runtime.platform.security_admin.credential.remote_readback: daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.credential.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_SECURITY_ADMIN_CREDENTIAL_TOOL)" readback --login "$(DAILY_SECURITY_ADMIN_LOGIN)" --name "$(DAILY_SECURITY_ADMIN_NAME)" --evidence "$(DAILY_SECURITY_ADMIN_EVIDENCE)"'

daily.runtime.platform.security_admin.credential.remote_issue: daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.credential.remote_install
	@test "$${SC_CONFIRM_PLATFORM_SECURITY_ADMIN_CREDENTIAL:-}" = "ISSUE_ONE_TIME_PLATFORM_SECURITY_ADMIN_CREDENTIAL" || { echo "exact platform security administrator credential issue confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'SC_CONFIRM_PLATFORM_SECURITY_ADMIN_CREDENTIAL=ISSUE_ONE_TIME_PLATFORM_SECURITY_ADMIN_CREDENTIAL python3 "$(DAILY_SECURITY_ADMIN_CREDENTIAL_TOOL)" issue --login "$(DAILY_SECURITY_ADMIN_LOGIN)" --name "$(DAILY_SECURITY_ADMIN_NAME)" --evidence "$(DAILY_SECURITY_ADMIN_EVIDENCE)"'

daily.runtime.platform.security_admin.credential.remote_clear: daily.runtime.security_admin.payload_inputs daily.runtime.platform.security_admin.credential.remote_install
	@test "$${SC_CONFIRM_PLATFORM_SECURITY_ADMIN_CREDENTIAL:-}" = "CLEAR_PLATFORM_SECURITY_ADMIN_CREDENTIAL" || { echo "exact platform security administrator credential clear confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'SC_CONFIRM_PLATFORM_SECURITY_ADMIN_CREDENTIAL=CLEAR_PLATFORM_SECURITY_ADMIN_CREDENTIAL python3 "$(DAILY_SECURITY_ADMIN_CREDENTIAL_TOOL)" clear --login "$(DAILY_SECURITY_ADMIN_LOGIN)" --name "$(DAILY_SECURITY_ADMIN_NAME)" --evidence "$(DAILY_SECURITY_ADMIN_EVIDENCE)"'

daily.candidate.sentinel.remote_capture: daily.candidate.continuity.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_sentinel.py" capture --output "/tmp/daily-candidate-data-sentinel-$$(date -u +%Y%m%dT%H%M%SZ).json"'

daily.candidate.sentinel.remote_verify: daily.candidate.continuity.remote_install
	@test "$(DAILY_CONTINUITY_BACKUP_DIR)" = "/data/backups/daily_candidate/sc_demo-20260724T032145Z-6eb277d1" || { echo "fixed continuity backup directory is required" >&2; exit 2; }
	@test "$${CONFIRM_DAILY_SENTINEL_VERIFY:-}" = "READ_ONLY_CAPTURE_AND_ISOLATED_RESTORE" || { echo "exact daily sentinel verification confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_DAILY_SENTINEL_VERIFY=READ_ONLY_CAPTURE_AND_ISOLATED_RESTORE python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_sentinel.py" verify --backup-dir "$(DAILY_CONTINUITY_BACKUP_DIR)"'

daily.candidate.sentinel.remote_cleanup_temp: guard.prod.forbid
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_SENTINEL_TEMP_FILE)" =~ ^/tmp/daily-candidate-data-sentinel-[0-9]{8}T[0-9]{6}Z[.]json$$ ]] || { echo "invalid exact sentinel temporary file" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'test -f "$(DAILY_SENTINEL_TEMP_FILE)"; rm -- "$(DAILY_SENTINEL_TEMP_FILE)"'

daily.candidate.clone_rehearsal.remote_image_import: guard.prod.forbid
	@test -n "$(DAILY_CANDIDATE_SSH_HOST)" || { echo "DAILY_CANDIDATE_SSH_HOST is required" >&2; exit 2; }
	@[[ "$(DAILY_CANDIDATE_SSH_HOST)" =~ ^[A-Za-z0-9._-]+$$ ]] || { echo "invalid daily candidate SSH host" >&2; exit 2; }
	@test "$${CONFIRM_RC6_OFFLINE_IMAGE_IMPORT:-}" = "IMPORT_FROZEN_RC6_IMAGE_OFFLINE" || { echo "exact RC6 offline image import confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/release_candidate_eligibility.py verify-eligibility \
		--candidate config/releases/rc6_candidate.json \
		--supersession config/releases/rc6_candidate_supersession_legacy_projection.json
	@docker image inspect "$(DAILY_CLONE_RC6_IMAGE_REF)" >/dev/null
	@set -eu; archive="$$(mktemp /tmp/rc6-candidate-image.XXXXXXXX.tar)"; \
	  trap 'rm -f -- "$$archive"' EXIT INT TERM; \
	  docker save --output "$$archive" "$(DAILY_CLONE_RC6_IMAGE_REF)"; \
	  python3 scripts/ops/daily_candidate_clone_upgrade_executor.py verify-offline-archive --archive "$$archive"; \
	  if ssh "$(DAILY_CANDIDATE_SSH_HOST)" 'docker image inspect "$(DAILY_CLONE_RC6_CONFIG_DIGEST)" >/dev/null 2>&1'; then \
	    echo "[daily.clone.image] target config digest already available; import skipped"; \
	  else \
	    ssh "$(DAILY_CANDIDATE_SSH_HOST)" 'docker load >/dev/null' < "$$archive"; \
	  fi; \
	  ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
	    'test "$$(docker image inspect "$(DAILY_CLONE_RC6_CONFIG_DIGEST)" --format "{{.Id}}")" = "$(DAILY_CLONE_RC6_CONFIG_DIGEST)"; test "$$(docker image inspect "$(DAILY_CLONE_RC6_CONFIG_DIGEST)" --format "{{index .Config.Labels \"org.opencontainers.image.revision\"}}")" = "fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8"; tags="$$(docker image inspect "$(DAILY_CLONE_RC6_CONFIG_DIGEST)" --format "{{json .RepoTags}}")"; test "$$tags" = "null" -o "$$tags" = "[]"; echo "[daily.clone.image] PASS immutable config and OCI revision"'

daily.candidate.clone_rehearsal.remote_preflight: daily.candidate.continuity.remote_install
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_clone_upgrade_executor.py" preflight'

daily.candidate.clone_rehearsal.remote_execute: daily.candidate.continuity.remote_install
	@test "$${CONFIRM_RC6_DAILY_CLONE_REHEARSAL:-}" = "RUN_FROZEN_RC6_ISOLATED_CLONE_REHEARSAL" || { echo "exact RC6 clone rehearsal confirmation is required" >&2; exit 2; }
	@ssh "$(DAILY_CANDIDATE_SSH_HOST)" \
		'CONFIRM_RC6_DAILY_CLONE_REHEARSAL=RUN_FROZEN_RC6_ISOLATED_CLONE_REHEARSAL python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_clone_upgrade_executor.py" execute'
