#!/usr/bin/env python3
from __future__ import annotations

import unittest

from frontend_professional_extension_guard import validate


VALID = """# component tests
.PHONY: verify.frontend.professional.wbs.unit verify.frontend.professional.extensions.unit
PROFESSIONAL_FRONTEND_EXTENSION_TARGETS := verify.frontend.professional.wbs.unit
verify.frontend.professional.wbs.unit: guard.prod.forbid
\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_wbs_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-wbs-test.mjs >/dev/null
\t@node /tmp/professional-wbs-test.mjs
\t@python3 -m unittest scripts.verify.test_frontend_professional_wbs
\t@python3 scripts/verify/frontend_professional_wbs_guard.py
verify.frontend.professional.extensions.unit: guard.prod.forbid
\t@python3 scripts/ci/frontend_professional_extension_guard.py
\t@if test -n "$(strip $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS))"; then $(MAKE) --no-print-directory $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS); fi
\t@echo "[verify.frontend.professional.extensions.unit] PASS targets=$(words $(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS))"
"""


class FrontendProfessionalExtensionGuardTests(unittest.TestCase):
    def test_valid_component_unit_contract_is_allowed(self) -> None:
        self.assertEqual(validate(VALID), [])

    def test_privileged_and_shell_commands_are_rejected(self) -> None:
        for command in (
            "\t@docker compose up",
            "\t@make db.reset",
            "\t@bash scripts/dev/run.sh",
            "\t@ENV_FILE=/tmp/forged node test.mjs",
            "\t@curl https://example.invalid",
        ):
            with self.subTest(command=command):
                self.assertTrue(validate(VALID + command + "\n"))

    def test_arbitrary_makefile_and_python_targets_are_rejected(self) -> None:
        self.assertTrue(validate(VALID + "include make/runtime_ops.mk\n"))
        self.assertTrue(validate(VALID + "\t@python3 scripts/release/publish.py\n"))


if __name__ == "__main__":
    unittest.main()
