R10_PERF_PROFILE ?= config/ops/r10_performance_ab_profile.v1.json
R10_PERF_SSH_HOST ?= sc-root
R10_PERF_REPORT_ROOT ?= .runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r10/runtime
R10_PERF_CONTINUITY_CONTRACT ?= scripts/ops/r10_performance_ab_continuity_contract_v1.json
R10_PERF_SNAPSHOT_ROOT ?= /data/backups/daily-demo-dev
R10_PERF_SNAPSHOT_DIR ?=
R10_PERF_REMOTE_CONTRACT ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/$(R10_PERF_CONTINUITY_CONTRACT)

.PHONY: verify.r10.performance_ab.profile r10.performance_ab.plan r10.performance_ab.preflight r10.performance_ab.snapshot r10.performance_ab.snapshot.validate r10.performance_ab.snapshot.restore_drill

verify.r10.performance_ab.profile: guard.prod.forbid
	@python3 -m py_compile scripts/ops/r10_performance_ab_profile.py scripts/ops/test_r10_performance_ab_profile.py
	@python3 -m unittest scripts.ops.test_r10_performance_ab_profile

r10.performance_ab.plan: verify.r10.performance_ab.profile
	@python3 scripts/ops/r10_performance_ab_profile.py plan \
		--profile "$(R10_PERF_PROFILE)" \
		--report "$(R10_PERF_REPORT_ROOT)/plan.json"

r10.performance_ab.preflight: verify.r10.performance_ab.profile
	@python3 scripts/ops/r10_performance_ab_profile.py preflight \
		--profile "$(R10_PERF_PROFILE)" \
		--ssh-host "$(R10_PERF_SSH_HOST)" \
		--report "$(R10_PERF_REPORT_ROOT)/preflight.json"

r10.performance_ab.snapshot: guard.prod.forbid verify.r10.performance_ab.profile
	@test "$${CONFIRM_R10_PERFORMANCE_SNAPSHOT:-}" = "SNAPSHOT_CURRENT_DUTY_FOR_R10_PERFORMANCE_AB" || { echo "exact R10 performance snapshot confirmation is required" >&2; exit 2; }
	@$(MAKE) --no-print-directory DAILY_CANDIDATE_SSH_HOST="$(R10_PERF_SSH_HOST)" daily.candidate.continuity.remote_install
	@ssh -o BatchMode=yes -o ConnectTimeout=10 "$(R10_PERF_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE DAILY_CONTINUITY_EVIDENCE=/tmp/r10-performance-ab-snapshot.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" backup --contract "$(R10_PERF_REMOTE_CONTRACT)"'

r10.performance_ab.snapshot.validate: guard.prod.forbid verify.r10.performance_ab.profile
	@test -n "$(R10_PERF_SNAPSHOT_DIR)" || { echo "R10_PERF_SNAPSHOT_DIR is required" >&2; exit 2; }
	@[[ "$(R10_PERF_SNAPSHOT_DIR)" =~ ^$(R10_PERF_SNAPSHOT_ROOT)/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$ ]] || { echo "invalid R10 performance snapshot directory" >&2; exit 2; }
	@$(MAKE) --no-print-directory DAILY_CANDIDATE_SSH_HOST="$(R10_PERF_SSH_HOST)" daily.candidate.continuity.remote_install
	@ssh -o BatchMode=yes -o ConnectTimeout=10 "$(R10_PERF_SSH_HOST)" \
		'DAILY_CONTINUITY_EVIDENCE=/tmp/r10-performance-ab-snapshot-validate.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" validate --contract "$(R10_PERF_REMOTE_CONTRACT)" --backup-dir "$(R10_PERF_SNAPSHOT_DIR)"'

r10.performance_ab.snapshot.restore_drill: guard.prod.forbid verify.r10.performance_ab.profile
	@test -n "$(R10_PERF_SNAPSHOT_DIR)" || { echo "R10_PERF_SNAPSHOT_DIR is required" >&2; exit 2; }
	@[[ "$(R10_PERF_SNAPSHOT_DIR)" =~ ^$(R10_PERF_SNAPSHOT_ROOT)/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$$ ]] || { echo "invalid R10 performance snapshot directory" >&2; exit 2; }
	@test "$${CONFIRM_R10_PERFORMANCE_RESTORE_DRILL:-}" = "RESTORE_R10_CURRENT_DUTY_SNAPSHOT_IN_ISOLATION" || { echo "exact R10 restore drill confirmation is required" >&2; exit 2; }
	@$(MAKE) --no-print-directory DAILY_CANDIDATE_SSH_HOST="$(R10_PERF_SSH_HOST)" daily.candidate.continuity.remote_install
	@ssh -o BatchMode=yes -o ConnectTimeout=10 "$(R10_PERF_SSH_HOST)" \
		'CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY DAILY_CONTINUITY_EVIDENCE=/tmp/r10-performance-ab-restore.json python3 "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/daily_candidate_data_continuity.py" restore-drill --contract "$(R10_PERF_REMOTE_CONTRACT)" --backup-dir "$(R10_PERF_SNAPSHOT_DIR)"'
