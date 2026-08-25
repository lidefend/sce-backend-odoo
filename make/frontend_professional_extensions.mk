# Standard-risk extension point for independently tested professional frontend
# component families. Keep release orchestration, environment handling, shell
# recipes, and privileged operations in their existing fail-closed Makefiles.

.PHONY: verify.frontend.professional.extensions.unit

PROFESSIONAL_FRONTEND_EXTENSION_TARGETS :=

verify.frontend.professional.extensions.unit: guard.prod.forbid
	@python3 scripts/ci/frontend_professional_extension_guard.py
	@if test -n "$(strip $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS))"; then $(MAKE) --no-print-directory $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS); fi
	@echo "[verify.frontend.professional.extensions.unit] PASS targets=$(words $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS))"
