BLOCKER_RUNTIME_IMAGE ?= sce-blocker-runtime:test
BLOCKER_FRONTEND_IMAGE ?= sce-blocker-frontend:test
EXPECTED_IMAGE_DIGEST ?=
EXPECTED_FRONTEND_IMAGE_DIGEST ?=

.PHONY: verify.production_blocker.fresh_and_rollback verify.production_blocker.runtime_assets verify.production_blocker.image

verify.production_blocker.fresh_and_rollback: guard.prod.forbid
	@BLOCKER_RUNTIME_IMAGE="$(BLOCKER_RUNTIME_IMAGE)" bash scripts/verify/production_blocker_fresh_and_rollback.sh

verify.production_blocker.runtime_assets: guard.prod.forbid
	@BLOCKER_RUNTIME_IMAGE="$(BLOCKER_RUNTIME_IMAGE)" BLOCKER_FRONTEND_IMAGE="$(BLOCKER_FRONTEND_IMAGE)" \
		bash scripts/verify/production_blocker_runtime_assets.sh

verify.production_blocker.image: guard.prod.forbid
	@BLOCKER_RUNTIME_IMAGE="$(BLOCKER_RUNTIME_IMAGE)" BLOCKER_FRONTEND_IMAGE="$(BLOCKER_FRONTEND_IMAGE)" \
		EXPECTED_IMAGE_DIGEST="$(EXPECTED_IMAGE_DIGEST)" \
		EXPECTED_FRONTEND_IMAGE_DIGEST="$(EXPECTED_FRONTEND_IMAGE_DIGEST)" \
		bash scripts/verify/production_blocker_image.sh

.PHONY: verify.contract_retirement.declaration.unit
verify.contract_retirement.declaration.unit:
	python3 scripts/verify/test_contract_retirement_declaration.py
