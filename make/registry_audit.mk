REGISTRY_AUDIT_RUN_ID ?=
REGISTRY_AUDIT_OUTPUT_ROOT ?= /tmp/sc-admin-vis-p3-registry-audit
REGISTRY_AUDIT_MODULES ?= smart_construction_core
REGISTRY_AUDIT_ODOO_IMAGE ?= odoo17-odoo:latest
REGISTRY_AUDIT_POSTGRES_IMAGE ?= postgres:15
REGISTRY_AUDIT_COMPOSE_FILE ?= docker-compose.registry-audit.yml

REGISTRY_AUDIT_ENV = \
	ENV=test \
	REGISTRY_AUDIT_OUTPUT_ROOT="$(REGISTRY_AUDIT_OUTPUT_ROOT)" \
	REGISTRY_AUDIT_MODULES="$(REGISTRY_AUDIT_MODULES)" \
	REGISTRY_AUDIT_ODOO_IMAGE="$(REGISTRY_AUDIT_ODOO_IMAGE)" \
	REGISTRY_AUDIT_POSTGRES_IMAGE="$(REGISTRY_AUDIT_POSTGRES_IMAGE)" \
	REGISTRY_AUDIT_COMPOSE_FILE="$(REGISTRY_AUDIT_COMPOSE_FILE)"

.PHONY: admin-vis-p3.registry-audit.validate
admin-vis-p3.registry-audit.validate: guard.prod.forbid
	@$(REGISTRY_AUDIT_ENV) python3 scripts/ops/registry_audit_environment.py validate \
		$(if $(REGISTRY_AUDIT_RUN_ID),--run-id "$(REGISTRY_AUDIT_RUN_ID)",)

.PHONY: admin-vis-p3.registry-audit.export
admin-vis-p3.registry-audit.export: guard.prod.forbid
	@test -n "$(REGISTRY_AUDIT_RUN_ID)" || \
		(echo "REGISTRY_AUDIT_RUN_ID is required; run validate first or use admin-vis-p3.registry-audit" >&2; exit 2)
	@$(REGISTRY_AUDIT_ENV) python3 scripts/ops/registry_audit_environment.py export \
		--run-id "$(REGISTRY_AUDIT_RUN_ID)"

.PHONY: admin-vis-p3.registry-audit.cleanup
admin-vis-p3.registry-audit.cleanup: guard.prod.forbid
	@test -n "$(REGISTRY_AUDIT_RUN_ID)" || \
		(echo "REGISTRY_AUDIT_RUN_ID is required" >&2; exit 2)
	@$(REGISTRY_AUDIT_ENV) python3 scripts/ops/registry_audit_environment.py cleanup \
		--run-id "$(REGISTRY_AUDIT_RUN_ID)"

.PHONY: admin-vis-p3.registry-audit
admin-vis-p3.registry-audit: guard.prod.forbid
	@$(REGISTRY_AUDIT_ENV) python3 scripts/ops/registry_audit_environment.py audit \
		$(if $(REGISTRY_AUDIT_RUN_ID),--run-id "$(REGISTRY_AUDIT_RUN_ID)",)

.PHONY: verify.admin-vis-p3.registry-audit
verify.admin-vis-p3.registry-audit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_registry_audit_environment
	@python3 -m py_compile \
		scripts/ops/registry_audit_environment.py \
		scripts/ops/registry_audit/registry_export.py \
		scripts/verify/test_registry_audit_environment.py
	@REGISTRY_AUDIT_OUTPUT_ROOT="$${REGISTRY_AUDIT_OUTPUT_ROOT:-/tmp/sc-admin-vis-p3-registry-audit-tests}" \
		python3 scripts/ops/registry_audit_environment.py self-test
