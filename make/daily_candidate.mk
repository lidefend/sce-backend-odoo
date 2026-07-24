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
	@python3 -m py_compile scripts/ops/daily_candidate_clone_upgrade_rehearsal.py scripts/ops/daily_candidate_clone_upgrade_executor.py
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
		scripts/ops/daily_candidate_data_continuity_contract_v1.json \
		scripts/ops/daily_candidate_data_sentinel.py \
		scripts/ops/daily_candidate_data_sentinel_contract_v1.json \
		scripts/ops/daily_candidate_clone_upgrade_rehearsal.py \
		scripts/ops/daily_candidate_clone_upgrade_contract_v1.json \
		scripts/ops/daily_candidate_clone_upgrade_executor.py \
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
