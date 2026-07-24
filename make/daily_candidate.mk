DAILY_CONTINUITY_CONTRACT ?= scripts/ops/daily_candidate_data_continuity_contract_v1.json
DAILY_CONTINUITY_BACKUP_DIR ?=
DAILY_CONTINUITY_EVIDENCE ?= /tmp/daily-candidate-data-continuity.json
DAILY_CANDIDATE_SSH_HOST ?=
DAILY_CONTINUITY_TOOL_SHA ?= $(shell git rev-parse HEAD)
DAILY_CONTINUITY_REMOTE_ROOT ?= /opt/sce/deployment-tools/$(DAILY_CONTINUITY_TOOL_SHA)
DAILY_SENTINEL_TEMP_FILE ?=

.PHONY: daily.candidate.continuity.test daily.candidate.continuity.baseline daily.candidate.continuity.backup daily.candidate.continuity.validate daily.candidate.continuity.restore_drill daily.candidate.continuity.remote_install daily.candidate.continuity.remote_baseline daily.candidate.continuity.remote_backup daily.candidate.continuity.remote_restore_drill daily.candidate.continuity.remote_closeout daily.candidate.sentinel.test daily.candidate.sentinel.remote_capture daily.candidate.sentinel.remote_verify daily.candidate.sentinel.remote_cleanup_temp

daily.candidate.continuity.test: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_data_continuity.py
	@python3 scripts/ops/test_daily_candidate_data_continuity.py

daily.candidate.sentinel.test: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_data_sentinel.py
	@python3 scripts/ops/test_daily_candidate_data_sentinel.py

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
		scripts/ops/daily_candidate_data_sentinel_contract_v1.json | \
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
