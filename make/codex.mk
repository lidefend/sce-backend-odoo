# ======================================================
# ==================== Codex Targets ===================
# ======================================================
CODEX_ALLOWED_WRITE_BRANCH_REGEX := ^(feature|fix|refactor|audit|release|codex)/.+
CODEX_ALLOWED_WRITE_BRANCH_PREFIXES := feature/* fix/* refactor/* audit/* release/* codex/*

.PHONY: codex.fast codex.gate codex.print codex.pr codex.cleanup codex.sync-main codex.cli
.PHONY: verify.gitee.webhook.ci gitee.ci.server.install gitee.ci.server.status
.PHONY: gitee.github.mirror.install gitee.github.mirror.seed gitee.github.mirror.run
.PHONY: github.mirror.ruleset.configure github.mirror.non_mirror_push.test
.PHONY: gitee.pr.bot.create gitee.pr.bot.status gitee.pr.bot.merge gitee.pr.checks.fetch verify.gitee.pr_bot.unit verify.gitee.check_run_ids.unit
.PHONY: gitee.pr.bot.professional.run
.PHONY: gitee.ci.https.install gitee.ci.https.status gitee.ci.repository.configure
.PHONY: verify.codex.agent_controller agent.controller.install agent.controller.config.check
.PHONY: agent.controller.notify.test agent.controller.enable agent.controller.disable
.PHONY: agent.controller.status agent.controller.logs agent.controller.watch agent.controller.issue.create
.PHONY: agent.controller.linger.enable
.PHONY: agent.feishu_bridge.install agent.feishu_bridge.config.check agent.feishu_bridge.enable
.PHONY: agent.feishu_bridge.disable agent.feishu_bridge.status agent.feishu_bridge.logs

verify.codex.agent_controller: guard.prod.forbid
	@python3 -m py_compile scripts/ops/agent_progress.py scripts/ops/codex_agent_controller.py scripts/ops/codex_agent_watch.py scripts/ops/feishu_agent_bridge.py scripts/verify/test_codex_agent_controller.py scripts/verify/test_feishu_agent_bridge.py
	@python3 -m unittest scripts.verify.test_codex_agent_controller scripts.verify.test_feishu_agent_bridge
	@bash -n scripts/ops/install_codex_agent_controller.sh
	@unit="$$(mktemp --suffix=.service)"; \
	  trap 'rm -f "$$unit"' EXIT; \
	  sed 's|@@REPOSITORY_ROOT@@|$(CURDIR)|g' deploy/agent-controller/sce-agent-controller.service.in > "$$unit"; \
	  systemd-analyze --user verify "$$unit"
	@unit="$$(mktemp --suffix=.service)"; \
	  trap 'rm -f "$$unit"' EXIT; \
	  sed -e 's|@@REPOSITORY_ROOT@@|$(CURDIR)|g' -e 's|@@PYTHON_BIN@@|/usr/bin/python3|g' deploy/agent-controller/sce-agent-feishu-bridge.service.in > "$$unit"; \
	  systemd-analyze --user verify "$$unit"
	@echo "[verify.codex.agent_controller] PASS"

agent.controller.install: guard.prod.forbid
	@AGENT_CONTROLLER_INSTALL_CONFIRM="$(AGENT_CONTROLLER_INSTALL_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh install

agent.controller.config.check: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh check

agent.controller.notify.test: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh notify-test

agent.controller.enable: guard.prod.forbid
	@AGENT_CONTROLLER_ENABLE_CONFIRM="$(AGENT_CONTROLLER_ENABLE_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh enable

agent.controller.disable: guard.prod.forbid
	@AGENT_CONTROLLER_DISABLE_CONFIRM="$(AGENT_CONTROLLER_DISABLE_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh disable

agent.controller.linger.enable: guard.prod.forbid
	@AGENT_CONTROLLER_LINGER_CONFIRM="$(AGENT_CONTROLLER_LINGER_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh linger-enable

agent.controller.status: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh status

agent.controller.logs: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh logs

agent.controller.watch: guard.prod.forbid
	@python3 scripts/ops/codex_agent_watch.py

agent.controller.audit.command: guard.prod.forbid
	@test -n "$(AGENT_CONTROLLER_COMMAND_FILE)" || (echo "❌ command file is required"; exit 2)
	@test -n "$(AGENT_CONTROLLER_GITHUB_REPOSITORY)" || (echo "❌ repository is required"; exit 2)
	@test -n "$(AGENT_CONTROLLER_GITHUB_CONTROL_ISSUE)" || (echo "❌ issue is required"; exit 2)
	@AGENT_STATE_ROOT="$(CURDIR)/.runtime/agent-controller" \
	  python3 scripts/ops/feishu_agent_bridge.py validate-command-file --file "$(AGENT_CONTROLLER_COMMAND_FILE)"
	@gh issue comment "$(AGENT_CONTROLLER_GITHUB_CONTROL_ISSUE)" \
	  --repo "$(AGENT_CONTROLLER_GITHUB_REPOSITORY)" \
	  --body-file "$(AGENT_CONTROLLER_COMMAND_FILE)" >/dev/null

agent.feishu_bridge.install: guard.prod.forbid
	@AGENT_FEISHU_BRIDGE_INSTALL_CONFIRM="$(AGENT_FEISHU_BRIDGE_INSTALL_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh feishu-install

agent.feishu_bridge.config.check: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh feishu-check

agent.feishu_bridge.enable: guard.prod.forbid
	@AGENT_FEISHU_BRIDGE_ENABLE_CONFIRM="$(AGENT_FEISHU_BRIDGE_ENABLE_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh feishu-enable

agent.feishu_bridge.disable: guard.prod.forbid
	@AGENT_FEISHU_BRIDGE_DISABLE_CONFIRM="$(AGENT_FEISHU_BRIDGE_DISABLE_CONFIRM)" \
	  bash scripts/ops/install_codex_agent_controller.sh feishu-disable

agent.feishu_bridge.status: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh feishu-status

agent.feishu_bridge.logs: guard.prod.forbid
	@bash scripts/ops/install_codex_agent_controller.sh feishu-logs

agent.controller.issue.create: guard.prod.forbid
	@test "$(AGENT_CONTROLLER_ISSUE_CREATE_CONFIRM)" = "CREATE_AGENT_CONTROL_ISSUE" || \
	  (echo "❌ exact issue creation confirmation is required"; exit 2)
	@test -n "$(AGENT_CONTROLLER_GITHUB_REPOSITORY)" || \
	  (echo "❌ AGENT_CONTROLLER_GITHUB_REPOSITORY=owner/repository is required"; exit 2)
	@gh issue create --repo "$(AGENT_CONTROLLER_GITHUB_REPOSITORY)" \
	  --title "Codex 长期任务控制台" \
	  --body-file deploy/agent-controller/control_issue_body.md

verify.gitee.webhook.ci: guard.prod.forbid
	@python3 -m py_compile scripts/ci/gitee_webhook_ci.py scripts/verify/test_gitee_webhook_ci.py scripts/verify/test_gitee_to_github_mirror.py scripts/verify/test_controlled_main_cutover.py scripts/ops/configure_gitee_ci_repository.py scripts/ops/controlled_main_cutover.py scripts/ops/gitee_pr_bot.py
	@python3 scripts/verify/test_gitee_webhook_ci.py
	@python3 scripts/verify/test_gitee_to_github_mirror.py
	@python3 scripts/verify/test_controlled_main_cutover.py
	@bash -n scripts/ci/gitee_ci_run.sh scripts/ops/install_gitee_webhook_ci.sh scripts/ops/install_gitee_ci_https.sh scripts/ops/gitee_to_github_mirror.sh scripts/ops/install_gitee_to_github_mirror.sh scripts/ops/configure_github_mirror_ruleset.sh scripts/ops/run_gitee_pr_professional_gate.sh deploy/gitee-ci/install.sh deploy/gitee-ci/install_https.sh deploy/gitee-mirror/install.sh

gitee.ci.server.install: guard.prod.forbid
	@GITEE_CI_SERVER_CONFIRM="$(GITEE_CI_SERVER_CONFIRM)" bash scripts/ops/install_gitee_webhook_ci.sh

gitee.ci.server.status: guard.prod.forbid
	@ssh -o BatchMode=yes root@1.95.2.123 'systemctl --no-pager --full status gitee-webhook-ci.service gitee-ci-worker.service; curl --fail --silent http://127.0.0.1:9080/healthz'

gitee.github.mirror.install: guard.prod.forbid
	@GITEE_MIRROR_SERVER_CONFIRM="$(GITEE_MIRROR_SERVER_CONFIRM)" bash scripts/ops/install_gitee_to_github_mirror.sh

gitee.github.mirror.seed: guard.prod.forbid
	@GITEE_MIRROR_SEED_CONFIRM="$(GITEE_MIRROR_SEED_CONFIRM)" \
	 GITEE_MIRROR_SEED_SHA="$(GITEE_MIRROR_SEED_SHA)" \
	 bash scripts/ops/seed_gitee_to_github_mirror.sh

gitee.github.mirror.run: guard.prod.forbid
	@GITEE_MIRROR_RUN_CONFIRM="$(GITEE_MIRROR_RUN_CONFIRM)" bash scripts/ops/run_gitee_to_github_mirror.sh

github.mirror.ruleset.configure: guard.prod.forbid
	@GITHUB_AUTHORITY_RULESET_CONFIRM="$(GITHUB_AUTHORITY_RULESET_CONFIRM)" \
	 GITHUB_AUTHORITY_RULESET_EXPECTED_SHA="$(GITHUB_AUTHORITY_RULESET_EXPECTED_SHA)" \
	 GITHUB_MIRROR_PUBLIC_KEY_FILE="$(GITHUB_MIRROR_PUBLIC_KEY_FILE)" \
	 bash scripts/ops/configure_github_mirror_ruleset.sh

github.mirror.non_mirror_push.test: guard.prod.forbid
	@bash scripts/verify/github_non_mirror_push_denied.sh

gitee.pr.bot.create: guard.prod.forbid
	@test -n "$(GITEE_PR_BOT_TOKEN_FILE)" || (echo "GITEE_PR_BOT_TOKEN_FILE is required"; exit 2)
	@python3 scripts/ops/gitee_pr_bot.py create --token-file "$(GITEE_PR_BOT_TOKEN_FILE)"

gitee.pr.bot.status: guard.prod.forbid
	@test -n "$(GITEE_PR_BOT_TOKEN_FILE)" || (echo "GITEE_PR_BOT_TOKEN_FILE is required"; exit 2)
	@python3 scripts/ops/gitee_pr_bot.py status --token-file "$(GITEE_PR_BOT_TOKEN_FILE)"

# Parameterized protected-lane merge: the four required checks are read back from
# the platform and must belong to EXPECTED_HEAD. The token is only ever read from
# the private file; main is never pushed.
gitee.pr.bot.merge: guard.prod.forbid
	@test -n "$(GITEE_PR_BOT_TOKEN_FILE)" || (echo "GITEE_PR_BOT_TOKEN_FILE is required"; exit 2)
	@test -n "$(GITEE_PR_NUMBER)" || (echo "GITEE_PR_NUMBER is required"; exit 2)
	@test -n "$(EXPECTED_HEAD)" || (echo "EXPECTED_HEAD is required"; exit 2)
	@test -n "$(GITEE_EXPECTED_MAIN)" || (echo "GITEE_EXPECTED_MAIN is required"; exit 2)
	@python3 scripts/ops/gitee_pr_bot.py merge --token-file "$(GITEE_PR_BOT_TOKEN_FILE)" --number "$(GITEE_PR_NUMBER)" --expected-head "$(EXPECTED_HEAD)" --expected-main "$(GITEE_EXPECTED_MAIN)" $(if $(GITEE_EXPECTED_SOURCE),--expected-source "$(GITEE_EXPECTED_SOURCE)",) $(if $(GITEE_PR_MERGE_METHOD),--merge-method "$(GITEE_PR_MERGE_METHOD)",) $(if $(GITEE_PR_EVIDENCE_FILE),--evidence "$(GITEE_PR_EVIDENCE_FILE)",) $(foreach c,$(GITEE_PR_CHECK_RUNS),--check-run $(c))

.PHONY: verify.gitee.pr_bot.unit
verify.gitee.pr_bot.unit: guard.prod.forbid
	@python3 -m py_compile scripts/ops/gitee_pr_bot.py scripts/verify/test_gitee_pr_bot.py
	@python3 -m unittest scripts.verify.test_gitee_pr_bot

# The platform's commit check-run list is empty in this repository, so the merge
# entry needs the run ids observed by the trusted CI worker.  Read-only: it never
# merges, and it refuses rather than reporting a partial or stale set.
gitee.pr.checks.fetch: guard.prod.forbid
	@test -n "$(GITEE_PR_BOT_TOKEN_FILE)" || (echo "GITEE_PR_BOT_TOKEN_FILE is required"; exit 2)
	@test -n "$(EXPECTED_HEAD)" || (echo "EXPECTED_HEAD is required"; exit 2)
	@test -n "$(GITEE_EXPECTED_MAIN)" || (echo "GITEE_EXPECTED_MAIN is required"; exit 2)
	@python3 scripts/ops/gitee_check_run_ids.py --head "$(EXPECTED_HEAD)" --main "$(GITEE_EXPECTED_MAIN)" --token-file "$(GITEE_PR_BOT_TOKEN_FILE)" $(if $(GITEE_CI_HOST),--host "$(GITEE_CI_HOST)",) $(if $(GITEE_CI_USER),--user "$(GITEE_CI_USER)",) $(if $(GITEE_CI_LEDGER_DB),--db "$(GITEE_CI_LEDGER_DB)",)

verify.gitee.check_run_ids.unit: guard.prod.forbid
	@python3 -m py_compile scripts/ops/gitee_check_run_ids.py scripts/verify/test_gitee_check_run_ids.py
	@python3 -m unittest scripts.verify.test_gitee_check_run_ids

gitee.pr.bot.professional.run: guard.prod.forbid
	@GITEE_PR_PROFESSIONAL_CONFIRM="$(GITEE_PR_PROFESSIONAL_CONFIRM)" bash scripts/ops/run_gitee_pr_professional_gate.sh

gitee.ci.https.install: guard.prod.forbid
	@GITEE_CI_HTTPS_CONFIRM="$(GITEE_CI_HTTPS_CONFIRM)" bash scripts/ops/install_gitee_ci_https.sh

gitee.ci.https.status: guard.prod.forbid
	@curl --fail --silent --show-error https://1.95.2.123/healthz

gitee.ci.repository.configure: guard.prod.forbid
	@test -n "$(GITEE_TOKEN_FILE)" || (echo "GITEE_TOKEN_FILE is required"; exit 2)
	@python3 scripts/ops/configure_gitee_ci_repository.py --token-file "$(GITEE_TOKEN_FILE)"

codex.print:
	@echo "== Codex SOP =="
	@echo "CODEX_MODE=$(CODEX_MODE) CODEX_DB=$(CODEX_DB) CODEX_MODULES=$(CODEX_MODULES) CODEX_NEED_UPGRADE=$(CODEX_NEED_UPGRADE)"
	@echo "SC_GATE_STRICT=$(SC_GATE_STRICT) SC_SCENE_OBS_STRICT=$(SC_SCENE_OBS_STRICT) SCENE_OBSERVABILITY_PREFLIGHT_STRICT=$(SCENE_OBSERVABILITY_PREFLIGHT_STRICT)"
	@echo "BASELINE_FREEZE_ENFORCE=$(BASELINE_FREEZE_ENFORCE)"
	@echo "BUSINESS_INCREMENT_PROFILE=$(BUSINESS_INCREMENT_PROFILE)"
	@echo "fast: restart (optional upgrade only if CODEX_NEED_UPGRADE=1) ; forbid demo.reset/gate.full"
	@echo "gate: optional upgrade + demo.reset + contract.export_all + gate.full"

CODEX_CLI_ARGS ?=
codex.cli: guard.prod.forbid
	@bash scripts/ops/codex_cli.sh $(CODEX_CLI_ARGS)

codex.fast: guard.prod.forbid check-compose-project check-compose-env
	@echo "[codex.fast] mode=fast db=$(CODEX_DB) modules=$(CODEX_MODULES) need_upgrade=$(CODEX_NEED_UPGRADE)"
	@$(MAKE) restart CODEX_MODE=fast DB=$(CODEX_DB)
	@if [ "$(CODEX_NEED_UPGRADE)" = "1" ]; then \
	  echo "[codex.fast] upgrading modules (explicitly allowed) ..."; \
	  $(MAKE) mod.upgrade CODEX_MODE=fast CODEX_NEED_UPGRADE=1 MODULE="$(CODEX_MODULES)" DB="$(CODEX_DB)"; \
	else \
	  echo "[codex.fast] skip module upgrade (default)"; \
	fi
	@echo "[codex.fast] done. (No demo.reset / No gate.full)"

codex.gate: guard.prod.forbid check-compose-project check-compose-env
	@echo "[codex.gate] mode=gate db=$(CODEX_DB) modules=$(CODEX_MODULES) need_upgrade=$(CODEX_NEED_UPGRADE)"
	@if [ "$(CODEX_NEED_UPGRADE)" = "1" ]; then \
	  echo "[codex.gate] upgrading modules ..."; \
	  $(MAKE) mod.upgrade CODEX_MODE=gate CODEX_NEED_UPGRADE=1 MODULE="$(CODEX_MODULES)" DB="$(CODEX_DB)"; \
	else \
	  echo "[codex.gate] skip module upgrade (not needed)"; \
	fi
	@$(MAKE) demo.reset CODEX_MODE=gate DB="$(CODEX_DB)"
	@$(MAKE) contract.export_all DB="$(CODEX_DB)"
	@$(MAKE) gate.full CODEX_MODE=gate BD="$(CODEX_DB)"
	@echo "[codex.gate] ✅ gate flow done."

codex.snapshot: guard.prod.forbid check-compose-project check-compose-env
	@echo "[codex.snapshot] db=$(CODEX_DB)"
	@$(MAKE) contract.export_all DB="$(CODEX_DB)"

.PHONY: codex.snapshot.export verify.backend.guard verify.portal.smoke
codex.snapshot.export: guard.prod.forbid
	@$(MAKE) --no-print-directory codex.snapshot

verify.backend.guard: guard.prod.forbid verify.execute_button.authority.unit
	@$(MAKE) --no-print-directory verify.boundary.guard

.PHONY: verify.execute_button.authority.unit
verify.execute_button.authority.unit: guard.prod.forbid
	@python3 addons/smart_core/tests/test_execute_button_server_action_boundaries.py

verify.portal.smoke: guard.prod.forbid check-compose-project check-compose-env
	@$(MAKE) --no-print-directory verify.portal.fe_smoke.container

.PHONY: codex.pr codex.cleanup codex.sync-main

codex.pr: guard.prod.forbid
	@$(MAKE) codex.pr.body
	@$(MAKE) pr.push
	@$(MAKE) pr.create

codex.cleanup: guard.prod.forbid
	@$(MAKE) branch.cleanup

codex.sync-main: guard.prod.forbid
	@$(MAKE) main.sync

.PHONY: codex.run
codex.run: guard.prod.forbid
	@if [ -z "$(FLOW)" ]; then \
	  echo "❌ FLOW is required (fast|snapshot|gate|pr|merge|cleanup|rollback|release|main)"; exit 2; \
	fi
	@case "$(FLOW)" in \
	  fast) FLOW=fast bash scripts/ops/codex_run.sh ;; \
	  snapshot) FLOW=snapshot bash scripts/ops/codex_run.sh ;; \
	  gate) FLOW=gate bash scripts/ops/codex_run.sh ;; \
	  pr) $(MAKE) codex.pr ;; \
	  merge) $(MAKE) codex.merge ;; \
	  rollback) $(MAKE) codex.rollback ;; \
	  release) $(MAKE) codex.release.note ;; \
	  cleanup) $(MAKE) codex.cleanup ;; \
	  main) $(MAKE) codex.sync-main ;; \
	  *) echo "❌ unknown FLOW=$(FLOW)"; exit 2 ;; \
	esac

# ------------------ PR (Codex-safe) ------------------
.PHONY: pr.create pr.status pr.push pr.update pr.ready pr.merge pr.merge.local_quick_gate verify.pr.push.unit

PR_BASE ?= main
PR_TITLE ?=
PR_BODY_FILE ?= artifacts/pr_body.md
PR_DRAFT ?= 0
PR_MERGE_METHOD ?= squash
PR_MERGE_SUBJECT ?=
PR_MERGE_BODY ?= Merged by Codex through make pr.merge.
EXPECTED_HEAD ?=

export PR PR_MERGE_METHOD PR_MERGE_SUBJECT PR_MERGE_BODY EXPECTED_HEAD

pr.create: guard.prod.forbid
	@branch="$$(git rev-parse --abbrev-ref HEAD)"; \
	if ! echo "$$branch" | grep -qE "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)"; then \
	  echo "❌ pr.create only allowed on $(CODEX_ALLOWED_WRITE_BRANCH_PREFIXES) (current=$$branch)"; exit 2; \
	fi; \
	if [ -z "$(PR_TITLE)" ]; then \
	  echo "❌ PR_TITLE is required"; exit 2; \
	fi; \
	if [ ! -f "$(PR_BODY_FILE)" ]; then \
	  echo "❌ PR_BODY_FILE not found: $(PR_BODY_FILE)"; exit 2; \
	fi; \
	case "$(PR_DRAFT)" in 0) draft_arg="" ;; 1) draft_arg="--draft" ;; \
	  *) echo "❌ PR_DRAFT must be 0 or 1"; exit 2 ;; \
	esac; \
	echo "[pr.create] base=$(PR_BASE) head=$$branch title=$(PR_TITLE) body=$(PR_BODY_FILE) draft=$(PR_DRAFT)"; \
	gh pr create --base "$(PR_BASE)" --head "$$branch" --title "$(PR_TITLE)" --body-file "$(PR_BODY_FILE)" $$draft_arg

pr.update: guard.prod.forbid
	@bash -lc '\
	set -euo pipefail; \
	BR="$$(git rev-parse --abbrev-ref HEAD)"; \
	if ! echo "$$BR" | grep -Eq "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)"; then \
	  echo "[DENY] pr.update: branch not allowed: $$BR"; exit 2; \
	fi; \
	ENV_NAME="$${ENV:-dev}"; \
	if [ "$$ENV_NAME" = "prod" ]; then \
	  echo "[DENY] pr.update: ENV=prod is forbidden"; exit 3; \
	fi; \
	if [ -n "$${PROD_DANGER:-}" ]; then \
	  echo "[DENY] pr.update: PROD_DANGER is set (forbidden)"; exit 4; \
	fi; \
	if ! command -v gh >/dev/null 2>&1; then \
	  echo "[DENY] pr.update: gh CLI not found"; exit 5; \
	fi; \
	PR="$${PR:-}"; \
	if [ -z "$$PR" ]; then \
	  echo "[DENY] pr.update: missing PR=<number>"; exit 6; \
	fi; \
	ARGS=""; \
	if [ -n "$${TITLE:-}" ]; then ARGS="$$ARGS --title \"$${TITLE}\""; fi; \
	if [ -n "$${BODY:-}" ]; then ARGS="$$ARGS --body \"$${BODY}\""; fi; \
	if [ -n "$${BODY_FILE:-}" ]; then ARGS="$$ARGS --body-file \"$${BODY_FILE}\""; fi; \
	if [ -n "$${LABELS:-}" ]; then ARGS="$$ARGS --add-label \"$${LABELS}\""; fi; \
	if [ -n "$${REMOVE_LABELS:-}" ]; then ARGS="$$ARGS --remove-label \"$${REMOVE_LABELS}\""; fi; \
	if [ -z "$$ARGS" ]; then \
	  echo "[DENY] pr.update: nothing to update (set TITLE/BODY/BODY_FILE/LABELS/REMOVE_LABELS)"; exit 7; \
	fi; \
	echo "[pr.update] branch=$$BR ENV=$$ENV_NAME PR=$$PR"; \
	eval "gh pr edit $$PR $$ARGS"; \
	'

pr.ready: guard.prod.forbid
	@bash -c '\
	set -euo pipefail; \
	BR="$$(git rev-parse --abbrev-ref HEAD)"; \
	if ! echo "$$BR" | grep -Eq "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)"; then \
	  echo "[DENY] pr.ready: branch not allowed: $$BR"; exit 2; \
	fi; \
	ENV_NAME="$${ENV:-dev}"; \
	if [ "$$ENV_NAME" = "prod" ]; then \
	  echo "[DENY] pr.ready: ENV=prod is forbidden"; exit 3; \
	fi; \
	if [ -n "$${PROD_DANGER:-}" ]; then \
	  echo "[DENY] pr.ready: PROD_DANGER is set (forbidden)"; exit 4; \
	fi; \
	if ! command -v gh >/dev/null 2>&1; then \
	  echo "[DENY] pr.ready: gh CLI not found"; exit 5; \
	fi; \
	PR="$${PR:-}"; \
	if ! [[ "$$PR" =~ ^[0-9]+$$ ]]; then \
	  echo "[DENY] pr.ready: PR must be a numeric pull request number"; exit 6; \
	fi; \
	EXPECTED="$${EXPECTED_HEAD:-}"; \
	if ! [[ "$$EXPECTED" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.ready: EXPECTED_HEAD must be a full 40-character lowercase commit SHA"; exit 7; \
	fi; \
	read -r ACTUAL DRAFT < <(gh pr view "$$PR" --json headRefOid,isDraft --jq "[.headRefOid, (.isDraft|tostring)] | @tsv"); \
	if ! [[ "$$ACTUAL" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.ready: live PR head is invalid"; exit 8; \
	fi; \
	echo "[pr.ready] expected_head=$$EXPECTED actual_head=$$ACTUAL draft=$$DRAFT"; \
	if [ "$$ACTUAL" != "$$EXPECTED" ]; then \
	  echo "[DENY] pr.ready: live PR head does not match EXPECTED_HEAD"; exit 9; \
	fi; \
	if [ "$$DRAFT" != "true" ]; then \
	  echo "[DENY] pr.ready: PR is not draft"; exit 10; \
	fi; \
	echo "[pr.ready] branch=$$BR ENV=$$ENV_NAME PR=$$PR expected_head=$$EXPECTED"; \
	gh pr ready "$$PR"; \
	'

pr.push: guard.prod.forbid
	@GITHUB_AUTH_REMOTE="$(or $(GITHUB_AUTH_REMOTE),origin)" bash scripts/ops/git_safe_push.sh

# Temporary outage lane. The default is read-only; origin is never rewritten.
.PHONY: gitee.integration.inspect main.gitee.catchup pr.push.gitee verify.gitee.integration.unit
gitee.integration.inspect: guard.prod.forbid
	@python3 scripts/ops/gitee_temporary_integration.py inspect --expected-head "$(EXPECTED_HEAD)" --expected-main "$(GITEE_EXPECTED_MAIN)"

main.gitee.catchup: guard.prod.forbid
	@python3 scripts/ops/gitee_temporary_integration.py catchup --expected-head "$(EXPECTED_HEAD)" --expected-main "$(GITEE_EXPECTED_MAIN)" $(if $(filter 1,$(APPLY)),--apply,) --confirm "$(GITEE_INTEGRATION_CONFIRM)"

GITEE_PUBLICATION_PURPOSE ?= integration
pr.push.gitee: guard.prod.forbid
	@GITEE_CI_EVIDENCE="$(GITEE_CI_EVIDENCE)" GITEE_CI_EVIDENCE_SHA256="$(GITEE_CI_EVIDENCE_SHA256)" python3 scripts/ops/gitee_temporary_integration.py publish --purpose "$(GITEE_PUBLICATION_PURPOSE)" --expected-head "$(EXPECTED_HEAD)" --expected-main "$(GITEE_EXPECTED_MAIN)" $(if $(filter 1,$(APPLY)),--apply,) --confirm "$(GITEE_INTEGRATION_CONFIRM)"

verify.gitee.integration.unit: guard.prod.forbid
	@python3 -m unittest scripts.ops.test_gitee_temporary_integration

.PHONY: verify.gitee.publication_gate.unit
verify.gitee.publication_gate.unit: guard.prod.forbid
	@python3 -m unittest scripts.ops.test_gitee_ci_publication_gate

verify.pr.push.unit: guard.prod.forbid
	@bash scripts/ops/git_safe_push.sh --self-test

# Exact-head local quick evidence gate before pr.merge.
#
# The remote PR gates do not run the local quick suite, so guard drift
# (stale split-guard tokens, line budgets, evidence locks) used to
# accumulate silently on main. A clean exact-head ci.local.quick run now records
# worktree-local evidence. This gate reuses that evidence when available and
# otherwise runs the suite once as a fail-closed fallback. The local checkout
# must always be clean and equal to EXPECTED_HEAD.
pr.merge.local_quick_gate:
	@bash -c '\
	set -euo pipefail; \
	EXPECTED="$${EXPECTED_HEAD:-}"; \
	if ! [[ "$$EXPECTED" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.merge.local_quick_gate: EXPECTED_HEAD must be a full 40-character lowercase commit SHA"; exit 7; \
	fi; \
	LOCAL_HEAD="$$(git rev-parse HEAD)"; \
	if [ "$$LOCAL_HEAD" != "$$EXPECTED" ]; then \
	  echo "[DENY] pr.merge.local_quick_gate: local HEAD $$LOCAL_HEAD does not match EXPECTED_HEAD $$EXPECTED; checkout the PR head first"; exit 11; \
	fi; \
	if [ -n "$$(git status --porcelain)" ]; then \
	  echo "[DENY] pr.merge.local_quick_gate: working tree must be clean (ci.local.quick must run on the exact PR head)"; \
	  git status --porcelain; exit 12; \
	fi; \
	if [ "$${PR_MERGE_LOCAL_QUICK_GATE_SKIP:-0}" = "1" ]; then \
	  echo "[pr.merge.local_quick_gate] SKIP: PR_MERGE_LOCAL_QUICK_GATE_SKIP=1 (unit-test harness; quick suite not run)"; exit 0; \
	fi; \
	if python3 scripts/ops/local_quick_evidence.py verify --expected-head "$$EXPECTED" >/dev/null 2>&1; then \
	  echo "[pr.merge.local_quick_gate] REUSE: exact-head ci.local.quick evidence verified for $$EXPECTED"; exit 0; \
	fi; \
	if [ -n "$${PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE:-}" ]; then \
	  echo "[pr.merge.local_quick_gate] BOOKKEEPING TERMINAL RETIRE acknowledged reason=$${PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE}"; \
	else \
	  BB_REF="$${PR_MERGE_BOOKKEEPING_BASE_REF:-origin/main}"; \
	  BB_BASE="$$(git merge-base "$$EXPECTED" "$$BB_REF" 2>/dev/null || true)"; \
	  BB_CHANGED=""; \
	  if [ -n "$$BB_BASE" ]; then BB_CHANGED="$$(git diff --name-only "$$BB_BASE" "$$EXPECTED" 2>/dev/null || true)"; fi; \
	  if [ -n "$$BB_CHANGED" ] && [ -z "$$(printf "%s\n" "$$BB_CHANGED" | grep -vE "^(\.agent/|docs/)" || true)" ]; then \
	    echo "[pr.merge.local_quick_gate] DENY: bookkeeping-only candidate (diff vs $$BB_BASE is confined to .agent/ and docs/)"; \
	    printf "%s\n" "$$BB_CHANGED" | sed "s|^|  bookkeeping-path: |"; \
	    echo "[pr.merge.local_quick_gate] run/goal/docs bookkeeping must ride along with the adjacent product candidate: ci.local.quick produces one receipt per frozen commit, so a standalone bookkeeping candidate buys a full suite run and no new coverage."; \
	    echo "[pr.merge.local_quick_gate] for an actual terminal goal retirement, rerun with PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE=<reason>."; \
	    exit 13; \
	  fi; \
	fi; \
	echo "[pr.merge.local_quick_gate] evidence miss; running fail-closed fallback"; \
	echo "[pr.merge.local_quick_gate] running make ci.local.quick on $$EXPECTED (this takes several minutes)"; \
	$(MAKE) --no-print-directory ci.local.quick; \
	python3 scripts/ops/local_quick_evidence.py verify --expected-head "$$EXPECTED" >/dev/null; \
	echo "[pr.merge.local_quick_gate] PASS"; \
	'

pr.merge: guard.prod.forbid pr.merge.local_quick_gate
	@bash -c '\
	set -euo pipefail; \
	BR="$$(git rev-parse --abbrev-ref HEAD)"; \
	if ! echo "$$BR" | grep -Eq "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)"; then \
	  echo "[DENY] pr.merge: branch not allowed: $$BR"; exit 2; \
	fi; \
	ENV_NAME="$${ENV:-dev}"; \
	if [ "$$ENV_NAME" = "prod" ]; then \
	  echo "[DENY] pr.merge: ENV=prod is forbidden"; exit 3; \
	fi; \
	if [ -n "$${PROD_DANGER:-}" ]; then \
	  echo "[DENY] pr.merge: PROD_DANGER is set (forbidden)"; exit 4; \
	fi; \
	if ! command -v gh >/dev/null 2>&1; then \
	  echo "[DENY] pr.merge: gh CLI not found"; exit 5; \
	fi; \
	PR="$${PR:-}"; \
	if ! [[ "$$PR" =~ ^[0-9]+$$ ]]; then \
	  echo "[DENY] pr.merge: PR must be a numeric pull request number"; exit 6; \
	fi; \
	EXPECTED="$${EXPECTED_HEAD:-}"; \
	if ! [[ "$$EXPECTED" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.merge: EXPECTED_HEAD must be a full 40-character lowercase commit SHA"; exit 7; \
	fi; \
	METHOD="$${PR_MERGE_METHOD:-squash}"; \
	case "$$METHOD" in merge|squash|rebase) ;; *) echo "[DENY] pr.merge: invalid PR_MERGE_METHOD=$$METHOD"; exit 7 ;; esac; \
	MERGE_HELP="$$(gh pr merge --help 2>&1)" || { echo "[DENY] pr.merge: unable to inspect gh merge capabilities"; exit 8; }; \
	if [[ "$$MERGE_HELP" != *"--match-head-commit"* ]]; then \
	  echo "[DENY] pr.merge: gh CLI lacks --match-head-commit support"; exit 8; \
	fi; \
	ACTUAL="$$(gh pr view "$$PR" --json headRefOid --jq .headRefOid)"; \
	if ! [[ "$$ACTUAL" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.merge: live PR head is invalid"; exit 9; \
	fi; \
	echo "[pr.merge] expected_head=$$EXPECTED actual_head=$$ACTUAL"; \
	if [ "$$ACTUAL" != "$$EXPECTED" ]; then \
	  echo "[DENY] pr.merge: live PR head does not match EXPECTED_HEAD"; exit 10; \
	fi; \
	SUBJECT="$${PR_MERGE_SUBJECT:-}"; \
	if [ -z "$$SUBJECT" ]; then SUBJECT="Merge PR #$$PR"; fi; \
	BODY="$${PR_MERGE_BODY:-Merged by Codex through make pr.merge.}"; \
	MERGE_ARGS=("$$PR" "--$$METHOD" "--match-head-commit" "$$EXPECTED" "--subject" "$$SUBJECT" "--body" "$$BODY"); \
	echo "[pr.merge] branch=$$BR ENV=$$ENV_NAME PR=$$PR method=$$METHOD expected_head=$$EXPECTED"; \
	gh pr merge "$${MERGE_ARGS[@]}"; \
	'

# Gate preparation before pr.merge.
#
# The merge-eligibility gates are dispatched via workflow_dispatch (the
# PR workflows deliberately omit `synchronize`, so pushes do not auto-run
# them). A workflow_dispatch run is NOT attached to the PR check suite, so
# the base-branch ruleset (required_status_checks: merge_policy_gate) cannot
# see it. This target verifies every gate is green on the exact PR head and
# then reports the merge_policy_gate commit status, unblocking pr.merge.
# Publication eligibility is separate and governed by release_candidate_gate.
pr.merge.prep:
	@bash -c '\
	set -euo pipefail; \
	PR="$${PR:-}"; \
	if ! [[ "$$PR" =~ ^[0-9]+$$ ]]; then \
	  echo "[DENY] pr.merge.prep: PR must be a numeric pull request number"; exit 1; \
	fi; \
	ACTUAL="$$(gh pr view "$$PR" --json headRefOid --jq .headRefOid)"; \
	if ! [[ "$$ACTUAL" =~ ^[0-9a-f]{40}$$ ]]; then \
	  echo "[DENY] pr.merge.prep: live PR head is invalid"; exit 2; \
	fi; \
	REPO="$$(gh repo view --json nameWithOwner --jq .nameWithOwner)"; \
	for WF in frontend_release_gate merge_policy_gate public_guard professional_quality_gate; do \
	  GATE_STATE="$$(gh api "repos/$$REPO/actions/workflows/$${WF}.yml/runs?head_sha=$${ACTUAL}&per_page=1" --jq ".workflow_runs[0].conclusion // \"missing\"" 2>/dev/null || echo missing)"; \
	  if [ "$$GATE_STATE" != "success" ]; then \
	    echo "[DENY] pr.merge.prep: gate $${WF} not success ($${GATE_STATE}) on PR#$$PR head=$${ACTUAL}; run the gates first"; exit 3; \
	  fi; \
	  echo "[pr.merge.prep] gate $${WF}=success"; \
	done; \
	gh api -X POST "repos/$$REPO/statuses/$${ACTUAL}" \
	  -f state=success -f context=merge_policy_gate \
	  -f description="merge_policy_gate passed (reported by make pr.merge.prep)" \
	  >/dev/null 2>&1 || { echo "[pr.merge.prep] WARN: merge_policy_gate status report failed (non-fatal)"; }; \
	echo "[pr.merge.prep] merge_policy_gate status reported; PR#$$PR ready to merge"; \
	'

pr.status:
	@gh pr status || true

# ------------------ Branch cleanup (Codex-safe) ------------------
.PHONY: branch.cleanup branch.cleanup.feature branch.retire.historical verify.branch.retire.historical workspace.worktree.create workspace.evidence.archive workspace.worktree.cleanup workspace.branch.sync-main workspace.branch.sync-main.extended verify.workspace.branch.sync-main verify.workspace.worktree.guard

CLEAN_BRANCH ?=
CLEAN_BRANCH_REMOTE ?= origin
CREATE_WORKTREE ?=
CREATE_WORKTREE_BRANCH ?=
CREATE_WORKTREE_BASE ?=
CREATE_WORKTREE_CONFIRM ?=
CANDIDATE_WORKTREE ?= $(ROOT_DIR)
EVIDENCE_ARCHIVE_MANIFEST ?=
EVIDENCE_ARCHIVE_ROOT ?=
EVIDENCE_ARCHIVE_CONFIRM ?=
CLEAN_WORKTREE_KEEP_BRANCH ?=
CLEAN_WORKTREE_EXPECTED_HEAD ?=
CLEAN_WORKTREE_CONFIRM ?=
CLEAN_WORKTREE_EVIDENCE_RECEIPT ?=
CLEAN_WORKTREE_RETIREMENT_RECORD ?=
CLEAN_WORKTREE_RECOVERY_BUNDLE ?=
CLEAN_WORKTREE_SUPERSEDED ?=
WORKSPACE_BRANCH_SYNC_ROOT ?= $(ROOT_DIR)
EXPECTED_BRANCH ?=
EXPECTED_OLD_BASE ?=
EXPECTED_MAIN ?=
CONFIRM_WORKSPACE_BRANCH_SYNC ?=
HISTORICAL_RETIREMENT_MANIFEST ?=
HISTORICAL_RETIREMENT_REPORT ?=
HISTORICAL_RETIREMENT_BUNDLE ?=
HISTORICAL_RETIREMENT_MANIFEST_SHA256 ?=
HISTORICAL_RETIREMENT_CONFIRM ?=
HISTORICAL_RETIREMENT_REMOTE ?= origin
HISTORICAL_RETIREMENT_EXPECTED_MAIN ?=
HISTORICAL_RETIREMENT_OPEN_PR_PROVIDER ?= github
HISTORICAL_RETIREMENT_EMIT_MANIFEST ?=
HISTORICAL_RETIREMENT_EMIT_INVENTORY ?=

branch.cleanup: guard.prod.forbid
	@if [ -z "$(CLEAN_BRANCH)" ]; then echo "❌ CLEAN_BRANCH is required"; exit 2; fi
	@if ! echo "$(CLEAN_BRANCH)" | grep -qE '^codex/'; then echo "❌ only codex/* can be deleted"; exit 2; fi
	@echo "[branch.cleanup] governed SHA-bound entry for $(CLEAN_BRANCH) on $(CLEAN_BRANCH_REMOTE)"
	@test -n "$$(git rev-parse --verify --quiet "refs/heads/$(CLEAN_BRANCH)^{commit}")" || { echo "❌ local branch not found: $(CLEAN_BRANCH)"; exit 2; }
	@git fetch "$(CLEAN_BRANCH_REMOTE)" main >/dev/null 2>&1 || true
	@EXPECTED_BRANCH_SHA="$$(git rev-parse --verify "refs/heads/$(CLEAN_BRANCH)^{commit}")" \
	 EXPECTED_MAIN_SHA="$$(git rev-parse --verify "refs/remotes/$(CLEAN_BRANCH_REMOTE)/main^{commit}" 2>/dev/null || git rev-parse --verify "refs/heads/main^{commit}")" \
	 CLEAN_BRANCH_REMOTE="$(CLEAN_BRANCH_REMOTE)" \
	 APPLY="$${APPLY:-0}" \
	 CLEAN_BRANCH_CONFIRM="$${CLEAN_BRANCH_CONFIRM:-}" \
	 bash scripts/ops/branch_cleanup_safe.sh "$(CLEAN_BRANCH)"

branch.cleanup.feature: guard.prod.forbid
	@bash scripts/ops/branch_cleanup_safe.sh "$(CLEAN_BRANCH)"

branch.retire.historical: guard.prod.forbid
	@if [ -z "$(HISTORICAL_RETIREMENT_MANIFEST)" ] && [ -z "$(HISTORICAL_RETIREMENT_EMIT_MANIFEST)$(HISTORICAL_RETIREMENT_EMIT_INVENTORY)" ]; then echo "❌ HISTORICAL_RETIREMENT_MANIFEST is required (or request a read-only --emit output)"; exit 2; fi
	@test -n "$(HISTORICAL_RETIREMENT_EXPECTED_MAIN)" || { echo "❌ HISTORICAL_RETIREMENT_EXPECTED_MAIN is required (full SHA of $(HISTORICAL_RETIREMENT_REMOTE)/main)"; exit 2; }
	@python3 scripts/ops/retire_historical_branch_refs.py \
		$(if $(HISTORICAL_RETIREMENT_MANIFEST),--manifest "$(HISTORICAL_RETIREMENT_MANIFEST)",) \
		--remote "$(HISTORICAL_RETIREMENT_REMOTE)" \
		--expected-main "$(HISTORICAL_RETIREMENT_EXPECTED_MAIN)" \
		--open-pr-provider "$(HISTORICAL_RETIREMENT_OPEN_PR_PROVIDER)" \
		$(if $(HISTORICAL_RETIREMENT_REPORT),--report "$(HISTORICAL_RETIREMENT_REPORT)",) \
		$(if $(HISTORICAL_RETIREMENT_EMIT_MANIFEST),--emit-manifest "$(HISTORICAL_RETIREMENT_EMIT_MANIFEST)",) \
		$(if $(HISTORICAL_RETIREMENT_EMIT_INVENTORY),--emit-inventory "$(HISTORICAL_RETIREMENT_EMIT_INVENTORY)",) \
		$(if $(filter 1,$(PREPARE_BUNDLE)),--prepare-bundle --bundle-output "$(HISTORICAL_RETIREMENT_BUNDLE)",) \
		$(if $(filter 1,$(APPLY)),--apply --bundle-output "$(HISTORICAL_RETIREMENT_BUNDLE)" --approved-manifest-sha256 "$(HISTORICAL_RETIREMENT_MANIFEST_SHA256)" --confirm "$(HISTORICAL_RETIREMENT_CONFIRM)",)

verify.branch.retire.historical: guard.prod.forbid
	@python3 -m py_compile scripts/ops/retire_historical_branch_refs.py scripts/ops/test_retire_historical_branch_refs.py
	@python3 -m unittest scripts/ops/test_retire_historical_branch_refs.py

workspace.worktree.create: guard.prod.forbid
	@test -n "$(CREATE_WORKTREE)" || { echo "❌ CREATE_WORKTREE is required"; exit 2; }
	@test -n "$(CREATE_WORKTREE_BRANCH)" || { echo "❌ CREATE_WORKTREE_BRANCH is required"; exit 2; }
	@test -n "$(CREATE_WORKTREE_BASE)" || { echo "❌ CREATE_WORKTREE_BASE is required"; exit 2; }
	@python3 scripts/ops/safe_worktree_create.py \
		--path "$(CREATE_WORKTREE)" \
		--branch "$(CREATE_WORKTREE_BRANCH)" \
		--base "$(CREATE_WORKTREE_BASE)" \
		$(if $(filter 1,$(APPLY)),--apply --confirm "$(CREATE_WORKTREE_CONFIRM)",)

workspace.evidence.archive: guard.prod.forbid
	@test -n "$(EVIDENCE_ARCHIVE_MANIFEST)" || { echo "❌ EVIDENCE_ARCHIVE_MANIFEST is required"; exit 2; }
	@python3 scripts/ops/archive_worktree_delivery_evidence.py \
		--worktree "$(CANDIDATE_WORKTREE)" \
		--manifest "$(EVIDENCE_ARCHIVE_MANIFEST)" \
		$(if $(EVIDENCE_ARCHIVE_ROOT),--archive-root "$(EVIDENCE_ARCHIVE_ROOT)",) \
		$(if $(filter 1,$(APPLY)),--apply --confirm "$(EVIDENCE_ARCHIVE_CONFIRM)",)

workspace.worktree.cleanup: guard.prod.forbid
	@if [ -z "$(CLEAN_WORKTREE)" ]; then echo "❌ CLEAN_WORKTREE is required"; exit 2; fi
	@python3 scripts/ops/safe_worktree_cleanup.py \
		--path "$(CLEAN_WORKTREE)" \
		$(if $(CLEAN_WORKTREE_EVIDENCE_RECEIPT),--evidence-receipt "$(CLEAN_WORKTREE_EVIDENCE_RECEIPT)",) \
		$(if $(CLEAN_WORKTREE_RETIREMENT_RECORD),--retirement-record "$(CLEAN_WORKTREE_RETIREMENT_RECORD)",) \
		$(if $(CLEAN_WORKTREE_RECOVERY_BUNDLE),--recovery-bundle "$(CLEAN_WORKTREE_RECOVERY_BUNDLE)",) \
		$(if $(filter 1,$(CLEAN_WORKTREE_SUPERSEDED)),--superseded-retirement,) \
		$(if $(filter 1,$(APPLY)),--apply,) \
		$(if $(filter 1,$(CLEAN_WORKTREE_KEEP_BRANCH)),--detach-keep-branch --expected-head "$(CLEAN_WORKTREE_EXPECTED_HEAD)",) \
		$(if $(CLEAN_WORKTREE_CONFIRM),--confirm "$(CLEAN_WORKTREE_CONFIRM)",)

workspace.branch.sync-main: guard.prod.forbid
	@test -d "$(WORKSPACE_BRANCH_SYNC_ROOT)" || { echo "❌ WORKSPACE_BRANCH_SYNC_ROOT is not a directory"; exit 2; }
	@cd "$(WORKSPACE_BRANCH_SYNC_ROOT)" && python3 "$(ROOT_DIR)/scripts/ops/safe_branch_sync_main.py" \
		--expected-root "$(WORKSPACE_BRANCH_SYNC_ROOT)" \
		--governance-root "$(ROOT_DIR)" \
		--expected-branch "$(EXPECTED_BRANCH)" \
		--expected-head "$(EXPECTED_HEAD)" \
		--expected-old-base "$(EXPECTED_OLD_BASE)" \
		--expected-main "$(EXPECTED_MAIN)" \
		$(if $(DEPENDENCY_PR),--dependency-pr "$(DEPENDENCY_PR)",) \
		$(if $(DEPENDENCY_HEAD),--dependency-head "$(DEPENDENCY_HEAD)",) \
		$(if $(DEPENDENCY_MERGE),--dependency-merge "$(DEPENDENCY_MERGE)",) \
		--confirm "$(CONFIRM_WORKSPACE_BRANCH_SYNC)"

workspace.branch.sync-main.extended: guard.prod.forbid
	@test -d "$(WORKSPACE_BRANCH_SYNC_ROOT)" || { echo "❌ WORKSPACE_BRANCH_SYNC_ROOT is not a directory"; exit 2; }
	@test -n "$(EXPECTED_COMMIT_COUNT)" || { echo "❌ EXPECTED_COMMIT_COUNT is required"; exit 2; }
	@cd "$(WORKSPACE_BRANCH_SYNC_ROOT)" && python3 "$(ROOT_DIR)/scripts/ops/safe_branch_sync_main.py" \
		--expected-root "$(WORKSPACE_BRANCH_SYNC_ROOT)" \
		--governance-root "$(ROOT_DIR)" \
		--expected-branch "$(EXPECTED_BRANCH)" \
		--expected-head "$(EXPECTED_HEAD)" \
		--expected-old-base "$(EXPECTED_OLD_BASE)" \
		--expected-main "$(EXPECTED_MAIN)" \
		$(if $(DEPENDENCY_PR),--dependency-pr "$(DEPENDENCY_PR)",) \
		$(if $(DEPENDENCY_HEAD),--dependency-head "$(DEPENDENCY_HEAD)",) \
		$(if $(DEPENDENCY_MERGE),--dependency-merge "$(DEPENDENCY_MERGE)",) \
		--expected-commit-count "$(EXPECTED_COMMIT_COUNT)" \
		--allow-extended-history \
		--confirm "$(CONFIRM_WORKSPACE_BRANCH_SYNC)"

verify.workspace.branch.sync-main: guard.prod.forbid
	@python3 -m py_compile scripts/ops/safe_branch_sync_main.py scripts/ops/test_safe_branch_sync_main.py
	@python3 -m unittest scripts/ops/test_safe_branch_sync_main.py

verify.workspace.worktree.guard: guard.prod.forbid
	@python3 -m py_compile scripts/ops/safe_worktree_create.py scripts/ops/test_safe_worktree_create.py scripts/ops/safe_worktree_cleanup.py scripts/ops/test_safe_worktree_cleanup.py
	@python3 -m unittest scripts/ops/test_safe_worktree_create.py scripts/ops/test_safe_worktree_cleanup.py

# ------------------ Main sync (safe) ------------------
.PHONY: main.sync daily.runtime.main.bundle_sync verify.daily.runtime.main.bundle_sync daily.runtime.candidate.bundle_sync verify.daily.runtime.candidate.bundle_sync mirror.main.gitee main.cutover.controlled candidate.required_checks.dispatch candidate.mirror.gitee daily.runtime.source_revision.align verify.daily.runtime.source_revision.align daily.runtime.frontend.build verify.daily.runtime.frontend.build

DAILY_RUNTIME_SSH_HOST ?= sc-root
DAILY_RUNTIME_EXPECTED_SHA ?=
DAILY_RUNTIME_EXPECTED_OLD_SHA ?=
DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA ?=
DAILY_RUNTIME_CANDIDATE_SHA_FLAG ?= $(if $(DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA), --expected-candidate-sha "$(DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA)")
DAILY_RUNTIME_BUNDLE_SYNC_REPORT ?= .runtime/final-acceptance/daily-deployed/bundle-sync.json
DAILY_CANDIDATE_SOURCE_BRANCH ?= $(shell git branch --show-current)
DAILY_CANDIDATE_SOURCE_REPOSITORY ?= $(CURDIR)
DAILY_CANDIDATE_EXPECTED_SHA ?= $(shell git rev-parse HEAD 2>/dev/null)
DAILY_CANDIDATE_EXPECTED_OLD_SHA ?=
DAILY_CANDIDATE_BUNDLE_SYNC_REPORT ?= .runtime/final-acceptance/daily-deployed/candidate-bundle-sync.json

main.sync: guard.prod.forbid
	@echo "[main.sync] checkout main + fast-forward pull"
	@git checkout main
	@git pull --ff-only origin main

verify.daily.runtime.main.bundle_sync: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_bundle_sync.py scripts/ops/test_daily_runtime_bundle_sync.py
	@python3 scripts/ops/test_daily_runtime_bundle_sync.py

daily.runtime.main.bundle_sync: guard.prod.forbid verify.daily.runtime.main.bundle_sync
	@test "$${CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC:-}" = "SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE" || { echo "exact daily runtime bundle sync confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_bundle_sync.py \
		--expected-sha "$(DAILY_RUNTIME_EXPECTED_SHA)" \
		--expected-old-sha "$(DAILY_RUNTIME_EXPECTED_OLD_SHA)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)"$(DAILY_RUNTIME_CANDIDATE_SHA_FLAG) \
		--report "$(DAILY_RUNTIME_BUNDLE_SYNC_REPORT)"

verify.daily.runtime.candidate.bundle_sync: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_candidate_bundle_sync.py scripts/ops/test_daily_candidate_bundle_sync.py
	@python3 scripts/ops/test_daily_candidate_bundle_sync.py

daily.runtime.candidate.bundle_sync: guard.prod.forbid verify.daily.runtime.candidate.bundle_sync
	@test "$${CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC:-}" = "SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE" || { echo "exact daily candidate bundle sync confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_candidate_bundle_sync.py \
		--source-repository "$(DAILY_CANDIDATE_SOURCE_REPOSITORY)" \
		--source-branch "$(DAILY_CANDIDATE_SOURCE_BRANCH)" \
		--expected-sha "$(DAILY_CANDIDATE_EXPECTED_SHA)" \
		--expected-old-sha "$(DAILY_CANDIDATE_EXPECTED_OLD_SHA)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--report "$(DAILY_CANDIDATE_BUNDLE_SYNC_REPORT)"

# The governed code-sync entry checks out an exact SHA but does not declare it.
# The daily runtime serves /api/runtime-version from the SC_SOURCE_REVISION env
# var, so the served identity can lag the deployed tree and make the acceptance
# identity check bind a stale value. This entry declares the exact running HEAD,
# restarts, readbacks the served endpoint and restores the env file on failure.
DAILY_RUNTIME_SOURCE_REVISION_SHA ?= $(DAILY_CANDIDATE_EXPECTED_SHA)
DAILY_RUNTIME_ENV_NAME ?= dev
DAILY_RUNTIME_ENV_FILE ?= .env.dev
DAILY_RUNTIME_SOURCE_REVISION_REPORT ?= .runtime/final-acceptance/daily-deployed/source-revision-align.json

verify.daily.runtime.source_revision.align: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_source_revision_align.py scripts/ops/test_daily_runtime_source_revision_align.py
	@python3 scripts/ops/test_daily_runtime_source_revision_align.py

daily.runtime.source_revision.align: guard.prod.forbid verify.daily.runtime.source_revision.align
	@test "$${CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN:-}" = "ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD" || { echo "exact daily runtime source-revision alignment confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_source_revision_align.py \
		--expected-sha "$(DAILY_RUNTIME_SOURCE_REVISION_SHA)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--env-name "$(DAILY_RUNTIME_ENV_NAME)" \
		--env-file "$(DAILY_RUNTIME_ENV_FILE)" \
		--report "$(DAILY_RUNTIME_SOURCE_REVISION_REPORT)"

# The daily runtime serves a prebuilt static frontend from the nginx bind mount
# (`FRONTEND_DIST_DIR`), but the governed code sync only fast-forwards the git
# tree. A mainline merge that changes frontend sources therefore leaves the
# *served* bundle one generation behind while `/api/runtime-version` reports the
# new commit, and user-level acceptance silently exercises the stale rendering
# surface. This entry builds the served bundle at the exact deployed HEAD with
# the existing governed `make verify.frontend.build`, computes the artifact
# fingerprint with the existing governed `frontend_build_fingerprint.sh`,
# declares that fingerprint as `FRONTEND_BUILD_SHA256` so the runtime revision
# endpoint exposes the served bundle, recreates the governed runtime, and
# readbacks both the declared identity and the served entry asset. A recorded
# receipt for the same exact commit lets an unchanged generation be reused
# without rebuilding.
DAILY_RUNTIME_FRONTEND_BUILD_SHA ?=
DAILY_RUNTIME_FRONTEND_BUILD_DATABASE ?= sc_demo
DAILY_RUNTIME_FRONTEND_BUILD_BASE_URL ?= http://127.0.0.1:18081
DAILY_RUNTIME_FRONTEND_BUILD_RECEIPT ?= .runtime/final-acceptance/daily-deployed/frontend-build.json
DAILY_RUNTIME_FRONTEND_BUILD_REPORT ?= $(DAILY_RUNTIME_FRONTEND_BUILD_RECEIPT)

verify.daily.runtime.frontend.build: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_frontend_build_align.py scripts/ops/test_daily_runtime_frontend_build_align.py
	@python3 -m unittest scripts.ops.test_daily_runtime_frontend_build_align

daily.runtime.frontend.build: guard.prod.forbid verify.daily.runtime.frontend.build
	@test "$${CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD:-}" = "BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD" || { echo "exact daily runtime frontend build confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_frontend_build_align.py \
		--expected-sha "$(DAILY_RUNTIME_FRONTEND_BUILD_SHA)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--env-name "$(DAILY_RUNTIME_ENV_NAME)" \
		--env-file "$(DAILY_RUNTIME_ENV_FILE)" \
		--database "$(DAILY_RUNTIME_FRONTEND_BUILD_DATABASE)" \
		--base-url "$(DAILY_RUNTIME_FRONTEND_BUILD_BASE_URL)" \
		--receipt "$(DAILY_RUNTIME_FRONTEND_BUILD_RECEIPT)" \
		--report "$(DAILY_RUNTIME_FRONTEND_BUILD_REPORT)"

# The daily runtime has no outgoing-mail sender declared, so product transitions
# that notify a reviewer fail inside mail.mail._send and roll the whole business
# transition back. This entry declares one sender identity through the existing
# governed `make odoo.shell.exec` entry and proves it with the existing read-only
# `make prod.guard.mail_from` guard. It writes only mail-sender configuration.
.PHONY: daily.runtime.mail_sender.prepare verify.daily.runtime.mail_sender.prepare
DAILY_RUNTIME_DATABASE ?= sc_demo
DAILY_RUNTIME_MAIL_SENDER_FROM ?= noreply@sc-daily.local
DAILY_RUNTIME_MAIL_SENDER_BASE_URL ?= http://1.95.85.92:18081
DAILY_RUNTIME_MAIL_SENDER_REPORT ?= .runtime/final-acceptance/daily-deployed/mail-sender-prepare.json

verify.daily.runtime.mail_sender.prepare: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_mail_sender_prepare.py scripts/ops/test_daily_runtime_mail_sender_prepare.py
	@python3 -m unittest scripts.ops.test_daily_runtime_mail_sender_prepare

daily.runtime.mail_sender.prepare: guard.prod.forbid verify.daily.runtime.mail_sender.prepare
	@test "$${CONFIRM_DAILY_RUNTIME_MAIL_SENDER_PREPARE:-}" = "PREPARE_DAILY_RUNTIME_OUTGOING_MAIL_SENDER" || { echo "exact daily runtime mail-sender preparation confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_mail_sender_prepare.py \
		--expected-sha "$(DAILY_RUNTIME_EXPECTED_SHA)" \
		--sender "$(DAILY_RUNTIME_MAIL_SENDER_FROM)" \
		--database "$(DAILY_RUNTIME_DATABASE)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--base-url "$(DAILY_RUNTIME_MAIL_SENDER_BASE_URL)" \
		--report "$(DAILY_RUNTIME_MAIL_SENDER_REPORT)"

# The project-lifecycle browser acceptance walks a dedicated fixture carrier from
# `draft` to its terminal `closed`. That carrier is a row of the existing
# `daily_dev` acceptance fixture scope, so it is materialised through the same
# governed `make odoo.shell.exec` entry and proven with a readback of the carrier
# identity and declared start state. It writes only fixture rows.
.PHONY: daily.runtime.lifecycle_fixture.prepare verify.daily.runtime.lifecycle_fixture.prepare
DAILY_RUNTIME_LIFECYCLE_FIXTURE_BASE_URL ?= http://1.95.85.92:18081
DAILY_RUNTIME_LIFECYCLE_FIXTURE_REPORT ?= .runtime/final-acceptance/daily-deployed/lifecycle-fixture-prepare.json

verify.daily.runtime.lifecycle_fixture.prepare: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_lifecycle_fixture_prepare.py scripts/ops/test_daily_runtime_lifecycle_fixture_prepare.py
	@python3 -m unittest scripts.ops.test_daily_runtime_lifecycle_fixture_prepare

daily.runtime.lifecycle_fixture.prepare: guard.prod.forbid verify.daily.runtime.lifecycle_fixture.prepare
	@test "$${CONFIRM_DAILY_RUNTIME_LIFECYCLE_FIXTURE:-}" = "DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE" || { echo "exact daily runtime lifecycle fixture confirmation is required" >&2; exit 2; }
	@test -n "$${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" || { echo "SC_ACCEPTANCE_FIXTURE_PASSWORD must be supplied through the environment" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_lifecycle_fixture_prepare.py \
		--expected-sha "$(DAILY_RUNTIME_EXPECTED_SHA)" \
		--database "$(DAILY_RUNTIME_DATABASE)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--base-url "$(DAILY_RUNTIME_LIFECYCLE_FIXTURE_BASE_URL)" \
		--password "$${SC_ACCEPTANCE_FIXTURE_PASSWORD}" \
		--report "$(DAILY_RUNTIME_LIFECYCLE_FIXTURE_REPORT)"

# Every browser acceptance lane binds the *served* identity of its fixture
# carrier, never a locally guessed database id. The daily runtime rebuilds its
# fixture rows whenever the lifecycle carrier is recreated, so a captured numeric
# id goes stale silently and the lane then opens a dead route. This entry drives
# the working tree's governed resolver through the existing `make odoo.shell.exec`
# entry and writes the resolved identity in the canonical governed envelope the
# repository's resolution consumers read. It writes only the identity artifact
# and its own report.
.PHONY: daily.runtime.record_identity.resolve verify.daily.runtime.record_identity.resolve
DAILY_RUNTIME_RECORD_IDENTITY_BASE_URL ?= http://1.95.85.92:18081
DAILY_RUNTIME_RECORD_IDENTITY_REPORT ?= .runtime/final-acceptance/daily-deployed/record-identity-resolve.json

verify.daily.runtime.record_identity.resolve: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_record_identity_resolve.py scripts/ops/test_daily_runtime_record_identity_resolve.py
	@python3 -m unittest scripts.ops.test_daily_runtime_record_identity_resolve

daily.runtime.record_identity.resolve: guard.prod.forbid verify.daily.runtime.record_identity.resolve
	@test "$${CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY:-}" = "RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY" || { echo "exact daily runtime record identity confirmation is required" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_record_identity_resolve.py \
		--expected-sha "$(DAILY_RUNTIME_EXPECTED_SHA)" \
		--database "$(DAILY_RUNTIME_DATABASE)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--base-url "$(DAILY_RUNTIME_RECORD_IDENTITY_BASE_URL)" \
		--output "$(ACCEPTANCE_RECORD_RESOLUTION)" \
		--report "$(DAILY_RUNTIME_RECORD_IDENTITY_REPORT)"

# The daily runtime has two independently released faces: the code/rendering face
# (`daily.runtime.*`: bundle sync, module upgrade, served revision, built
# frontend) and the published product face (the active edition-release snapshot
# that the navigation release gate actually reads). Only the published face
# decides whether an entry may be opened, so a locked-contract change could reach
# the served runtime while the published face still froze the previous contract:
# the gated navigation then silently served the older contract and a declared,
# user-visible menu entry disappeared with no failing deploy step. This entry
# owns both faces in one governed sequence - bind the exact candidate revision,
# re-freeze every published product snapshot from the locked contract, reload the
# served runtime, then re-prove the released face through the release-gate guard.
# `daily.runtime.candidate.release` is the single daily deploy entry; the two
# faces must not be released separately.  The served identity is declared before
# the published face is refreshed, because the face is frozen through the module
# code at that exact revision and the acceptance identity check reads the served
# revision back.
DAILY_RUNTIME_PUBLISHED_FACE_EXPECTED_SHA ?= $(DAILY_CANDIDATE_EXPECTED_SHA)
DAILY_RUNTIME_PUBLISHED_FACE_LOGIN ?= $(DAILY_PRODUCT_MENU_FULL_PRODUCT_LOGIN)
DAILY_RUNTIME_PUBLISHED_FACE_PRODUCT_KEYS ?= construction.standard,construction.preview
# The published face is frozen *from* the locked contract through the module code
# that projects it, so the projection code must be live before the freeze; a face
# frozen from stale projection code silently publishes the previous contract.
DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES ?= smart_core
DAILY_RUNTIME_PUBLISHED_FACE_REPORT ?= .runtime/final-acceptance/daily-deployed/published-face-converge.json

verify.daily.runtime.published_face.converge: guard.prod.forbid
	@python3 -m py_compile scripts/ops/daily_runtime_published_face_converge.py scripts/ops/test_daily_runtime_published_face_converge.py
	@python3 -m unittest scripts.ops.test_daily_runtime_published_face_converge

daily.runtime.published_face.converge: guard.prod.forbid verify.daily.runtime.published_face.converge
	@test "$${CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE:-}" = "REFRESH_DAILY_RUNTIME_PUBLISHED_FACE_FROM_LOCKED_CONTRACT" || { echo "exact daily runtime published-face confirmation is required" >&2; exit 2; }
	@test -n "$(DAILY_RUNTIME_PUBLISHED_FACE_LOGIN)" || { echo "DAILY_RUNTIME_PUBLISHED_FACE_LOGIN must name the daily full-product principal (set DAILY_PRODUCT_MENU_FULL_PRODUCT_LOGIN or ACCEPTANCE_LOGIN)" >&2; exit 2; }
	@python3 scripts/ops/daily_runtime_published_face_converge.py \
		--expected-sha "$(DAILY_RUNTIME_PUBLISHED_FACE_EXPECTED_SHA)" \
		--ssh-host "$(DAILY_RUNTIME_SSH_HOST)" \
		--login "$(DAILY_RUNTIME_PUBLISHED_FACE_LOGIN)" \
		--product-keys "$(DAILY_RUNTIME_PUBLISHED_FACE_PRODUCT_KEYS)" \
		--upgrade-modules "$(DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES)" \
		--report "$(DAILY_RUNTIME_PUBLISHED_FACE_REPORT)"

daily.runtime.candidate.release: guard.prod.forbid daily.runtime.candidate.bundle_sync daily.runtime.source_revision.align daily.runtime.published_face.converge

mirror.main.gitee: guard.prod.forbid
	@bash scripts/ops/mirror_main_gitee.sh

candidate.required_checks.dispatch: guard.prod.forbid
	@bash -c '\
	set -euo pipefail; \
	branch="$$(git branch --show-current)"; \
	echo "$$branch" | grep -Eq "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)" || { echo "[candidate.required_checks.dispatch] BLOCKED invalid_branch"; exit 2; }; \
	expected="$(CANDIDATE_EXPECTED_SHA)"; \
	[[ "$$expected" =~ ^[0-9a-f]{40}$$ ]] || { echo "[candidate.required_checks.dispatch] BLOCKED full_expected_sha_required"; exit 2; }; \
	[ -z "$$(git status --porcelain)" ] || { echo "[candidate.required_checks.dispatch] BLOCKED worktree_not_clean"; exit 2; }; \
	[ "$$(git rev-parse HEAD)" = "$$expected" ] || { echo "[candidate.required_checks.dispatch] BLOCKED local_sha_mismatch"; exit 2; }; \
	remote_sha="$$(git ls-remote origin "refs/heads/$$branch" | awk "{print \$$1}")"; \
	[ "$$remote_sha" = "$$expected" ] || { echo "[candidate.required_checks.dispatch] BLOCKED remote_sha_mismatch"; exit 2; }; \
	read -r pr_number live_head base_sha < <(gh pr list --head "$$branch" --state open --json number,headRefOid,baseRefOid --jq "if length == 1 then .[0] | [.number, .headRefOid, .baseRefOid] | @tsv else empty end"); \
	[ -n "$$pr_number" ] || { echo "[candidate.required_checks.dispatch] BLOCKED exactly_one_open_pr_required"; exit 2; }; \
	[ "$$live_head" = "$$expected" ] || { echo "[candidate.required_checks.dispatch] BLOCKED pr_head_mismatch"; exit 2; }; \
	[[ "$$base_sha" =~ ^[0-9a-f]{40}$$ ]] || { echo "[candidate.required_checks.dispatch] BLOCKED invalid_pr_base"; exit 2; }; \
	gh label create ci:candidate --color 1d76db --description "Run exact-head candidate publication qualification" --force >/dev/null; \
	if gh pr view "$$pr_number" --json labels --jq ".labels[].name" | grep -Fxq ci:candidate; then \
	  gh pr edit "$$pr_number" --remove-label ci:candidate >/dev/null; \
	fi; \
	[ "$$(gh pr view "$$pr_number" --json headRefOid --jq .headRefOid)" = "$$expected" ] || { echo "[candidate.required_checks.dispatch] BLOCKED pr_head_changed_before_dispatch"; exit 2; }; \
	gh pr edit "$$pr_number" --add-label ci:candidate >/dev/null; \
	echo "[candidate.required_checks.dispatch] PASS branch=$$branch pr=$$pr_number sha=$$expected base=$$base_sha trigger=ci:candidate"; \
	'

candidate.mirror.gitee: guard.prod.forbid
	@bash -c '\
	set -euo pipefail; \
	branch="$$(git branch --show-current)"; \
	echo "$$branch" | grep -Eq "$(CODEX_ALLOWED_WRITE_BRANCH_REGEX)" || { echo "[candidate.mirror.gitee] BLOCKED invalid_branch"; exit 2; }; \
	expected="$(CANDIDATE_EXPECTED_SHA)"; \
	[[ "$$expected" =~ ^[0-9a-f]{40}$$ ]] || { echo "[candidate.mirror.gitee] BLOCKED full_expected_sha_required"; exit 2; }; \
	[ -z "$$(git status --porcelain)" ] || { echo "[candidate.mirror.gitee] BLOCKED worktree_not_clean"; exit 2; }; \
	[ "$$(git rev-parse HEAD)" = "$$expected" ] || { echo "[candidate.mirror.gitee] BLOCKED local_sha_mismatch"; exit 2; }; \
	github_sha="$$(git ls-remote origin "refs/heads/$$branch" | awk "{print \$$1}")"; \
	[ "$$github_sha" = "$$expected" ] || { echo "[candidate.mirror.gitee] BLOCKED github_candidate_mismatch"; exit 2; }; \
	gitee_sha="$$(git ls-remote gitee-mirror "refs/heads/$$branch" | awk "{print \$$1}")"; \
	if [ -n "$$gitee_sha" ]; then \
	  git merge-base --is-ancestor "$$gitee_sha" "$$expected" || { echo "[candidate.mirror.gitee] BLOCKED non_fast_forward"; exit 2; }; \
	fi; \
	git push gitee-mirror "$$expected:refs/heads/$$branch"; \
	[ "$$(git ls-remote gitee-mirror "refs/heads/$$branch" | awk "{print \$$1}")" = "$$expected" ] || { echo "[candidate.mirror.gitee] BLOCKED post_push_mismatch"; exit 2; }; \
	echo "[candidate.mirror.gitee] PASS branch=$$branch sha=$$expected mode=fast_forward_only"; \
	'

main.cutover.controlled: guard.prod.forbid
	@test -n "$(CUTOVER_TARGET_SHA)" || (echo "CUTOVER_TARGET_SHA is required"; exit 2)
	@test -n "$(CUTOVER_TARGET_TREE)" || (echo "CUTOVER_TARGET_TREE is required"; exit 2)
	@test -n "$(CUTOVER_GITHUB_OLD_SHA)" || (echo "CUTOVER_GITHUB_OLD_SHA is required"; exit 2)
	@test -n "$(CUTOVER_GITEE_OLD_SHA)" || (echo "CUTOVER_GITEE_OLD_SHA is required"; exit 2)
	@test -n "$(CUTOVER_GITEE_TOKEN_FILE)" || (echo "CUTOVER_GITEE_TOKEN_FILE is required"; exit 2)
	@test -n "$(CUTOVER_RECOVERY_ROOT)" || (echo "CUTOVER_RECOVERY_ROOT is required"; exit 2)
	@test -n "$(CUTOVER_EVIDENCE_DIR)" || (echo "CUTOVER_EVIDENCE_DIR is required"; exit 2)
	@test -n "$(CUTOVER_AUTHORIZATION_ID)" || (echo "CUTOVER_AUTHORIZATION_ID is required"; exit 2)
	@python3 scripts/ops/controlled_main_cutover.py \
		--target-sha "$(CUTOVER_TARGET_SHA)" \
		--target-tree "$(CUTOVER_TARGET_TREE)" \
		--github-old-sha "$(CUTOVER_GITHUB_OLD_SHA)" \
		--gitee-old-sha "$(CUTOVER_GITEE_OLD_SHA)" \
		--gitee-token-file "$(CUTOVER_GITEE_TOKEN_FILE)" \
		--recovery-root "$(CUTOVER_RECOVERY_ROOT)" \
		--evidence-dir "$(CUTOVER_EVIDENCE_DIR)" \
		--authorization-id "$(CUTOVER_AUTHORIZATION_ID)" \
		$(if $(CUTOVER_RUN_ID),--run-id "$(CUTOVER_RUN_ID)",) \
		$(if $(filter 1,$(APPLY)),--apply --confirm CONTROLLED_MAIN_CUTOVER_APPLY,)

.PHONY: verify.gitee.ci_only.unit
verify.gitee.ci_only.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_ci_acceptance

.PHONY: gitee.ci.server.update verify.gitee.ci_update.unit
gitee.ci.server.update: guard.prod.forbid
	@python3 scripts/ops/gitee_ci_incremental_update.py --expected-head "$(EXPECTED_HEAD)" $(if $(filter 1,$(GITEE_FORMAL)),--formal --node-archive "$(GITEE_NODE_ARCHIVE)",) $(if $(filter 1,$(APPLY)),--apply,) --plan-sha256 "$(GITEE_UPDATE_PLAN_SHA256)" --confirm "$(GITEE_UPDATE_CONFIRM)" $(if $(GITEE_CHECKS_TOKEN_FILE),--checks-token-file "$(GITEE_CHECKS_TOKEN_FILE)",)

verify.gitee.ci_update.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_ci_incremental_update

.PHONY: gitee.ci.sandbox.probe
gitee.ci.sandbox.probe: guard.prod.forbid
	@python3 scripts/ops/gitee_ci_incremental_update.py --expected-head "$(EXPECTED_HEAD)" --probe-only

.PHONY: gitee.ci.secret.rotate
gitee.ci.secret.rotate: guard.prod.forbid
	@python3 scripts/ops/gitee_ci_rotate_secret.py --secret-file "$(GITEE_ROTATION_FILE)" --expected-env-sha256 "$(GITEE_RECEIVER_ENV_SHA256)" --confirm "$(GITEE_ROTATION_CONFIRM)"

.PHONY: verify.gitee.publication_scope.unit
verify.gitee.publication_scope.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_publication_scope

.PHONY: gitee.ci.mirror.isolate
gitee.ci.mirror.isolate: guard.prod.forbid
	@test "$(GITEE_ISOLATION_CONFIRM)" = "ISOLATE_EXISTING_REVERSE_MIRROR" || (echo 'exact isolation confirmation required'; exit 2)
	@ssh -o BatchMode=yes root@1.95.2.123 'set -eu; systemctl show gitee-to-github-mirror.timer gitee-to-github-mirror.service --property=Id,ActiveState,UnitFileState,MainPID; systemctl disable --now gitee-to-github-mirror.timer; systemctl stop gitee-to-github-mirror.service; test "$$(systemctl show gitee-to-github-mirror.timer --property=UnitFileState --value)" = disabled; test "$$(systemctl show gitee-to-github-mirror.timer --property=ActiveState --value)" = inactive; case "$$(systemctl show gitee-to-github-mirror.service --property=ActiveState --value)" in inactive|failed) ;; *) exit 2;; esac; test "$$(systemctl show gitee-to-github-mirror.service --property=MainPID --value)" = 0; systemctl show gitee-to-github-mirror.timer gitee-to-github-mirror.service --property=Id,ActiveState,UnitFileState,MainPID'

.PHONY: gitee.ci.sandbox.profile.install
gitee.ci.sandbox.profile.install: guard.prod.forbid
	@test "$(GITEE_SANDBOX_CONFIRM)" = "INSTALL_UPSTREAM_BWRAP_PROFILE" || (echo 'exact sandbox confirmation required'; exit 2)
	@ssh -o BatchMode=yes root@1.95.2.123 'set -eu; test ! -e /etc/apparmor.d/bwrap-userns-restrict; test ! -e /etc/apparmor.d/bwrap; umask 022; tmp=$$(mktemp /etc/apparmor.d/.gitee-bwrap.XXXXXX); trap '\''rm -f "$$tmp"'\'' EXIT; cat > "$$tmp"; apparmor_parser -Q -T "$$tmp"; install -m 0644 "$$tmp" /etc/apparmor.d/bwrap-userns-restrict; apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict; sha256sum /etc/apparmor.d/bwrap-userns-restrict' < deploy/gitee-ci/bwrap-userns-restrict

.PHONY: verify.gitee.checks.unit
verify.gitee.checks.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_ci_checks

.PHONY: gitee.ci.gates.plan verify.gitee.gates.unit
gitee.ci.gates.plan: guard.prod.forbid
	@python3 -m scripts.ci.gitee_gate_plan --head "$(EXPECTED_HEAD)" --base "$(GITEE_EXPECTED_MAIN)" --source-branch "$(GITEE_SOURCE_BRANCH)" --pr-number "$(GITEE_PR_NUMBER)" $(if $(filter 1,$(GITEE_CANDIDATE)),--candidate,) $(if $(GITEE_CHECKS_TOKEN_FILE),--token-file "$(GITEE_CHECKS_TOKEN_FILE)",)

verify.gitee.gates.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_gate_plan scripts.verify.test_gitee_pr_identity

.PHONY: gitee.ci.pr.inspect
gitee.ci.pr.inspect: guard.prod.forbid
	@python3 -m scripts.ci.gitee_pr_identity --token-file "$(GITEE_CHECKS_TOKEN_FILE)" --head "$(EXPECTED_HEAD)" --base "$(GITEE_EXPECTED_MAIN)" --source-branch "$(GITEE_SOURCE_BRANCH)" --pr-number "$(GITEE_PR_NUMBER)"

.PHONY: verify.gitee.formal_executor.unit
verify.gitee.formal_executor.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_formal_executor

.PHONY: verify.gitee.formal_queue.unit
verify.gitee.formal_queue.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_formal_queue

.PHONY: verify.gitee.formal_worker.unit
verify.gitee.formal_worker.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_formal_worker

.PHONY: gitee.ci.pr.create verify.gitee.formal_pr.unit
export GITEE_SOURCE_BRANCH GITEE_PR_TITLE GITEE_PR_BODY_FILE GITEE_PR_TOKEN_FILE
gitee.ci.pr.create: guard.prod.forbid
	@test -n "$$GITEE_PR_TOKEN_FILE" || { echo "GITEE_PR_TOKEN_FILE is required (independent owner integration token; no CI token fallback)"; exit 2; }
	@python3 -m scripts.ops.gitee_formal_pr --expected-head "$(EXPECTED_HEAD)" --expected-main "$(GITEE_EXPECTED_MAIN)" --token-file "$$GITEE_PR_TOKEN_FILE" --source-branch "$$GITEE_SOURCE_BRANCH" --title "$$GITEE_PR_TITLE" --body-file "$$GITEE_PR_BODY_FILE" $(if $(filter 1,$(APPLY)),--apply,)
verify.gitee.formal_pr.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_formal_pr

.PHONY: gitee.ci.frontend.prepare verify.gitee.frontend_cache.unit
gitee.ci.frontend.prepare: guard.prod.forbid
	@python3 -m scripts.ops.gitee_frontend_cache --output "$(GITEE_FRONTEND_OUTPUT)" --node-archive "$(GITEE_NODE_ARCHIVE)" --pnpm-archive "$(GITEE_PNPM_ARCHIVE)" --store "$(GITEE_PNPM_STORE)"
verify.gitee.frontend_cache.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_frontend_cache scripts/verify/test_gitee_frontend_reuse.py

.PHONY: gitee.ci.frontend.reuse.publish
gitee.ci.frontend.reuse.publish: guard.prod.forbid
	@python3 -m scripts.ops.gitee_frontend_reuse --head "$(EXPECTED_HEAD)" --base "$(GITEE_EXPECTED_MAIN)" --pr-number "$(GITEE_PR_NUMBER)" --prepared "$(GITEE_FRONTEND_OUTPUT)" --node-archive "$(GITEE_NODE_ARCHIVE)" $(if $(filter 1,$(APPLY)),--apply,) --confirm "$(GITEE_FRONTEND_REUSE_CONFIRM)"

.PHONY: gitee.ci.frontend.verify
gitee.ci.frontend.verify: guard.prod.forbid
	@python3 -m scripts.ops.gitee_frontend_cache --verify --output "$(GITEE_FRONTEND_OUTPUT)" --node-archive "$(GITEE_NODE_ARCHIVE)"

.PHONY: gitee.ci.frontend.cache.install verify.gitee.frontend_cache_install.unit
gitee.ci.frontend.cache.install: guard.prod.forbid
	@python3 -m scripts.ops.gitee_frontend_cache_install --expected-head "$(EXPECTED_HEAD)" --prepared "$(GITEE_FRONTEND_OUTPUT)" --archive-sha256 "$(GITEE_FRONTEND_ARCHIVE_SHA256)" $(if $(filter 1,$(APPLY)),--apply,) --confirm "$(GITEE_FRONTEND_CONFIRM)"
verify.gitee.frontend_cache_install.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_gitee_frontend_cache_install

# Published Gitee candidates keep their history: append exact main, never rebase.
.PHONY: workspace.branch.sync-gitee-published
workspace.branch.sync-gitee-published: guard.prod.forbid
	@python3 scripts/ops/gitee_published_branch_sync.py --root "$(SYNC_ROOT)" --branch "$(EXPECTED_BRANCH)" --head "$(EXPECTED_HEAD)" --main "$(GITEE_EXPECTED_MAIN)" $(if $(GITEE_EXPECTED_SOURCE),--remote-head "$(GITEE_EXPECTED_SOURCE)",) $(if $(filter 1,$(APPLY)),--apply --confirm "$(GITEE_SYNC_CONFIRM)",)

.PHONY: workspace.branch.sync-gitee-unpublished verify.workspace.branch.sync-gitee.unit
# Unpublished Gitee candidates have no same-name remote branch yet. Absence is
# proven by a successful ls-remote, exact main is appended, history is kept and
# nothing is pushed. Publication still uses pr.push.gitee, which re-checks the
# remote identity and stops if a same-name branch appeared meanwhile.
workspace.branch.sync-gitee-unpublished: guard.prod.forbid
	@python3 scripts/ops/gitee_published_branch_sync.py --root "$(SYNC_ROOT)" --branch "$(EXPECTED_BRANCH)" --head "$(EXPECTED_HEAD)" --main "$(GITEE_EXPECTED_MAIN)" --allow-absent $(if $(filter 1,$(APPLY)),--apply --confirm "$(GITEE_SYNC_CONFIRM)",)

verify.workspace.branch.sync-gitee.unit: guard.prod.forbid
	@python3 -m py_compile scripts/ops/gitee_published_branch_sync.py scripts/ops/test_gitee_published_branch_sync.py
	@cd scripts/ops && python3 -m unittest test_gitee_published_branch_sync

.PHONY: main.sync.gitee
main.sync.gitee: guard.prod.forbid
	@python3 scripts/ops/gitee_published_branch_sync.py --local-main --root "$(CURDIR)" --branch "$(EXPECTED_BRANCH)" --head "$(EXPECTED_HEAD)" --main "$(GITEE_EXPECTED_MAIN)" --old-main "$(EXPECTED_LOCAL_MAIN)" $(if $(filter 1,$(APPLY)),--apply --confirm "$(GITEE_SYNC_CONFIRM)",)

# Explicit abandonment is local-only and retains a verified external recovery bundle.
.PHONY: workspace.branch.discard-local
workspace.branch.discard-local: guard.prod.forbid
	@python3 scripts/ops/gitee_published_branch_sync.py --discard-local --root "$(CURDIR)" --branch "$(EXPECTED_BRANCH)" --head "$(EXPECTED_HEAD)" --main "$(EXPECTED_LOCAL_MAIN)" --target "$(DISCARD_BRANCH)" --target-head "$(DISCARD_HEAD)" --bundle "$(DISCARD_RECOVERY_BUNDLE)" $(if $(filter 1,$(APPLY)),--apply --confirm "$(DISCARD_CONFIRM)",)

.PHONY: workspace.retain-main-only
workspace.retain-main-only: guard.prod.forbid
	@python3 scripts/ops/gitee_published_branch_sync.py --retain-main-only --root "$(CURDIR)" --branch "$(EXPECTED_BRANCH)" --head "$(EXPECTED_HEAD)" --main "$(GITEE_EXPECTED_MAIN)" --bundle "$(LOCAL_CLEANUP_BUNDLE)" --plan-sha256 "$(LOCAL_CLEANUP_PLAN_SHA256)" $(if $(filter 1,$(APPLY)),--apply --confirm "$(LOCAL_CLEANUP_CONFIRM)",)

# P4 bounded run lookup and advisory local evidence; never a publication receipt.
.PHONY: agent.run.resume agent.run.record verify.agent.resume.unit
agent.run.resume: guard.prod.forbid
	@python3 scripts/ops/agent_run_context.py

agent.run.record: guard.prod.forbid
	@python3 scripts/ops/agent_run_context.py --record "$(AGENT_CHECK)" --status "$(AGENT_CHECK_STATUS)" --test-count "$(AGENT_TEST_COUNT)" --log "$(AGENT_TEST_LOG)"

verify.agent.resume.unit: guard.prod.forbid
	@python3 -m py_compile scripts/ops/agent_run_context.py scripts/verify/test_agent_run_context.py
	@python3 -m unittest scripts.verify.test_agent_run_context

# P4 ledger consistency: goal/run status drift, dangling active-run index entries
# and unreadable goal documents become mechanically detected defects instead of a
# manual ledger re-audit every round. Read-only over .agent; never mutates it.
.PHONY: verify.agent.ledger.unit
verify.agent.ledger.unit: guard.prod.forbid
	@python3 -m py_compile scripts/verify/agent_ledger_consistency_guard.py scripts/verify/test_agent_ledger_consistency_guard.py
	@python3 -m unittest scripts.verify.test_agent_ledger_consistency_guard
	@python3 scripts/verify/agent_ledger_consistency_guard.py

.PHONY: agent.run.begin
agent.run.begin: guard.prod.forbid
	@python3 scripts/ops/agent_run_context.py --begin "$(AGENT_CHECK)"

.PHONY: verify.trusted_scan.unit
verify.trusted_scan.unit: security.online_capture.unit

.PHONY: verify.ci.orm_selection.unit
verify.ci.orm_selection.unit:
	@python3 scripts/ci/test_ci_risk_classifier.py
	@python3 scripts/ci/test_ci_risk_workflow_contract.py
