#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from frontend_release_ci_guard import ROOT, findings


class FrontendReleaseCIGuardTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / ".github/workflows").mkdir(parents=True)
        (root / "config/ci").mkdir(parents=True)
        (root / "make").mkdir(parents=True)
        (root / "scripts/common").mkdir(parents=True)
        (root / "scripts/dev").mkdir(parents=True)
        (root / "scripts/ci").mkdir(parents=True)
        (root / "scripts/verify").mkdir(parents=True)
        shutil.copy(ROOT / ".github/workflows/frontend_release_gate.yml", root / ".github/workflows/")
        shutil.copy(ROOT / "config/ci/frontend_release_gate_v1.json", root / "config/ci/")
        shutil.copy(ROOT / "make/runtime_ops.mk", root / "make/")
        shutil.copy(ROOT / "make/dev.mk", root / "make/")
        shutil.copy(ROOT / "make/frontend.mk", root / "make/")
        shutil.copy(ROOT / "Makefile", root / "Makefile")
        shutil.copy(ROOT / "docker-compose.yml", root / "docker-compose.yml")
        shutil.copy(ROOT / "scripts/common/frontend_release_ci_identity.sh", root / "scripts/common/")
        shutil.copy(ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh", root / "scripts/dev/")
        shutil.copy(ROOT / "scripts/ci/self_hosted_runner_cleanup.sh", root / "scripts/ci/")
        shutil.copy(
            ROOT / "scripts/verify/frontend_static_release_audit.py",
            root / "scripts/verify/",
        )
        return temporary, root

    def test_repository_contract_passes(self):
        self.assertEqual(findings(), [])

    def test_dynamic_matrix_and_duplicate_check_are_rejected(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        workflow.write_text(workflow.read_text() + "\n    strategy:\n      matrix: {}\n", encoding="utf-8")
        (root / ".github/workflows/duplicate.yml").write_text(
            "permissions:\n  contents: read\njobs:\n  x:\n    name: frontend_release_gate\n",
            encoding="utf-8",
        )
        errors = findings(root)
        self.assertTrue(any(item.startswith("WORKFLOW_FORBIDDEN:matrix") for item in errors))
        self.assertTrue(any(item.startswith("CHECK_NAME_NOT_UNIQUE") for item in errors))

    def test_continue_on_error_and_historical_download_are_rejected(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        workflow.write_text(
            workflow.read_text()
            + "\n# continue-on-error: true\n# uses: actions/download-artifact@0000000000000000000000000000000000000000\n",
            encoding="utf-8",
        )
        errors = findings(root)
        self.assertIn("WORKFLOW_FORBIDDEN:continue-on-error:", errors)
        self.assertIn("WORKFLOW_FORBIDDEN:actions/download-artifact", errors)

    def test_release_browser_url_alias_alignment_is_required(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        runtime_make = root / "make/runtime_ops.mk"
        runtime_make.write_text(
            runtime_make.read_text(encoding="utf-8").replace(
                "verify.frontend.delivery_hardening.release.browser: "
                "ACCEPTANCE_BASE_URL := $(FRONTEND_ACCEPTANCE_BASE_URL)\n",
                "",
            ),
            encoding="utf-8",
        )
        self.assertIn("FRONTEND_ACCEPTANCE_URL_ALIASES_NOT_ALIGNED", findings(root))

    def test_isolated_compose_project_must_be_exported_to_file_and_runner(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        marker = "            printf 'COMPOSE_PROJECT_NAME=%s\\n' \"${CI_PROJECT_NAME}\"\n"
        workflow.write_text(workflow.read_text(encoding="utf-8").replace(marker, "", 1), encoding="utf-8")
        self.assertIn("ISOLATED_COMPOSE_PROJECT_NOT_EXPORTED", findings(root))

    def test_isolated_backend_port_must_be_exported_to_file_and_runner(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        marker = "            printf 'ODOO_PORT=18082\\n'\n"
        workflow.write_text(workflow.read_text(encoding="utf-8").replace(marker, "", 1), encoding="utf-8")
        self.assertIn("ISOLATED_BACKEND_PORT_NOT_EXPORTED", findings(root))

    def test_isolated_source_revision_must_be_exported_to_file_and_runner(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        marker = "            printf 'SC_SOURCE_REVISION=%s\\n' \"${CHECKOUT_SHA}\"\n"
        workflow.write_text(workflow.read_text(encoding="utf-8").replace(marker, "", 1), encoding="utf-8")
        self.assertIn("ISOLATED_SOURCE_REVISION_NOT_EXPORTED", findings(root))

    def test_identity_must_freeze_before_tool_install_and_release(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        text = workflow.read_text(encoding="utf-8")
        freeze = text.index("      - name: Freeze isolated frontend release identity")
        end = text.index("\n      - name:", freeze + 8)
        freeze_block = text[freeze:end]
        text = text[:freeze] + text[end + 1:]
        release = text.index("      - name: Run the single authoritative frontend release command")
        text = text[:release] + freeze_block + "\n" + text[release:]
        workflow.write_text(text, encoding="utf-8")
        self.assertIn("CI_IDENTITY_NOT_FROZEN_BEFORE_RESOURCE_SIDE_EFFECTS", findings(root))

    def test_cleanup_must_verify_frozen_identity_before_removal(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        cleanup = root / "scripts/ci/self_hosted_runner_cleanup.sh"
        text = cleanup.read_text(encoding="utf-8")
        marker = '    verify_frozen_frontend_release_ci_identity "$root_dir"\n'
        cleanup.write_text(text.replace(marker, "", 1), encoding="utf-8")
        self.assertIn("CI_CLEANUP_NOT_BOUND_TO_FROZEN_IDENTITY", findings(root))

    def test_make_targets_cannot_call_local_runtime_directly(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        frontend_make = root / "make/frontend.mk"
        frontend_make.write_text(
            frontend_make.read_text(encoding="utf-8")
            + "\nforbidden.runtime.bypass:\n"
            + "\t@bash scripts/dev/frontend_acceptance_runtime.sh db-ensure\n",
            encoding="utf-8",
        )
        self.assertIn("FRONTEND_ACCEPTANCE_RUNTIME_DIRECT_MAKE_BYPASS", findings(root))


if __name__ == "__main__":
    unittest.main()
