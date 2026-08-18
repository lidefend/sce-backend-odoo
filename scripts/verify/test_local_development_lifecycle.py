from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "scripts/dev/local_clean_env_prepare.sh"
SAMPLE_PREPARE = ROOT / "scripts/dev/local_sample_env_prepare.sh"


class LocalDevelopmentLifecycleTest(unittest.TestCase):
    def test_demo_verifier_uses_registered_company_tax_contract(self):
        verifier = (ROOT / "scripts/verify/demo.sh").read_text(encoding="utf-8")
        self.assertIn("legacy global tax XMLIDs absent", verifier)
        self.assertIn("bootstrap company contract taxes absent", verifier)
        self.assertIn("registered business company tax defaults complete", verifier)
        self.assertIn("sc_tenant_company_registration", verifier)
        self.assertIn("sc_demo_settlement_069_payment", verifier)
        self.assertIn("sc_demo_payment_request_069_pay", verifier)
        self.assertNotIn("seed tax sale exists", verifier)
        self.assertNotIn("seed tax purchase exists", verifier)
        self.assertNotIn("name LIKE 'DEMO-SO-%'", verifier)
        self.assertNotIn("name LIKE 'DEMO-PR-%'", verifier)

    def _run_prepare(self, *, volumes_exist: bool, rebuild: bool = False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        source = root / ".env.dev"
        target = root / ".env.local.clean"
        source.write_text("ENV=dev\n", encoding="utf-8")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1 $2\" == \"volume inspect\" ]]; then\n"
            f"  exit {0 if volumes_exist else 1}\n"
            "fi\n"
            "exit 99\n",
            encoding="utf-8",
        )
        docker.chmod(0o755)
        env = {
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "ROOT_DIR": str(root),
            "SOURCE_ENV_FILE": str(source),
            "TARGET_ENV_FILE": str(target),
        }
        if rebuild:
            env.update(
                LOCAL_CLEAN_PREPARE_FOR_REBUILD="1",
                CONFIRM_LOCAL_CLEAN_REBUILD="REBUILD_ISOLATED_REHEARSAL",
            )
        result = subprocess.run(
            ["bash", str(PREPARE)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return root, target, result

    def test_missing_credentials_with_existing_volumes_fails_without_side_effect(self):
        root, target, result = self._run_prepare(volumes_exist=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("credential authority is missing", result.stderr)
        self.assertFalse(target.exists())
        self.assertFalse((root / "frontend/apps/web/dist-clean").exists())

    def test_fresh_prepare_creates_restricted_canonical_identity(self):
        _root, target, result = self._run_prepare(volumes_exist=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode, 0o600)
        content = target.read_text(encoding="utf-8")
        for expected in (
            "COMPOSE_PROJECT_NAME=sc-local-clean",
            "DB_NAME=sc_clean",
            "DB_DATA=sc_local_clean_db_data",
            "REDIS_DATA=sc_local_clean_redis_data",
            "ODOO_DATA=sc_local_clean_odoo_data",
            "ISOLATED_REHEARSAL_DATABASE=1",
        ):
            self.assertIn(expected, content)

    def test_exact_rebuild_authority_allows_prepare_over_isolated_volumes(self):
        _root, target, result = self._run_prepare(volumes_exist=True, rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(target.exists())

    def test_repository_exposes_only_canonical_daily_commands(self):
        make_text = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        docs = (ROOT / "docs/ops/local_development_environment_v1.md").read_text(
            encoding="utf-8"
        )
        for target in (
            "local.dev.up",
            "local.dev.down",
            "local.dev.logs",
            "local.dev.ps",
            "local.dev.test",
            "local.dev.upgrade",
            "local.dev.sync_demo",
            "local.dev.rebuild_demo",
            "local.dev.verify_demo",
            "local.sample.prepare",
            "local.sample.up",
            "local.sample.down",
            "local.sample.logs",
            "local.sample.snapshot",
            "local.sample.restore",
            "local.sample.discard",
            "local.clean.prepare",
            "local.clean.up",
            "local.clean.down",
            "local.clean.logs",
            "local.clean.rebuild",
        ):
            self.assertIn(target, make_text)
            self.assertIn(target, docs)
        self.assertIn(
            "LOCAL_CLEAN_ENV_FILE ?= /home/lidefend/workspace/sce-backend-odoo/.env.local.clean",
            make_text,
        )
        health = (ROOT / "scripts/dev/local_environment_health.sh").read_text(
            encoding="utf-8"
        )
        doctor = (ROOT / "scripts/dev/local_environment_doctor.sh").read_text(
            encoding="utf-8"
        )
        snapshot = (ROOT / "scripts/dev/local_dev_snapshot.sh").read_text(
            encoding="utf-8"
        )
        for source in (docs, health, doctor, snapshot):
            self.assertIn("sc_dev_demo", source)
            self.assertIn("sc_dev_sample", source)
        self.assertIn("不是 demo fixture 库", docs)
        self.assertIn("不保证", docs)
        self.assertIn("REBUILD_ISOLATED_REHEARSAL", docs)
        self.assertNotIn("REBUILD_SC_CLEAN", docs)

    def test_sample_prepare_creates_distinct_technical_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".env.dev"
            target = root / ".env.local.sample"
            source.write_text("ENV=dev\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            docker = bin_dir / "docker"
            docker.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            docker.chmod(0o755)
            result = subprocess.run(
                ["bash", str(SAMPLE_PREPARE)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PATH": f"{bin_dir}:{os.environ['PATH']}",
                    "ROOT_DIR": str(root),
                    "SOURCE_ENV_FILE": str(source),
                    "TARGET_ENV_FILE": str(target),
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            content = target.read_text(encoding="utf-8")
            for expected in (
                "COMPOSE_PROJECT_NAME=sc-local-sample",
                "DB_NAME=sc_dev_sample",
                "NGINX_PORT=18084",
                "ODOO_PORT=8073",
                "TECHNICAL_SAMPLE_DATABASE=1",
            ):
                self.assertIn(expected, content)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_local_make_targets_isolate_inherited_identity(self):
        make_text = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        local_block = make_text.split("FRONTEND_DEV_LOG", 1)[0]
        nested = [line for line in local_block.splitlines() if "$(MAKE)" in line]
        self.assertTrue(nested)
        self.assertTrue(
            all("$(LOCAL_ENV_ISOLATE)" in line for line in nested), nested
        )
        self.assertNotIn("local.sample.down: guard.prod.forbid local.sample.prepare", make_text)
        self.assertNotIn("local.clean.down: guard.prod.forbid local.clean.prepare", make_text)
        self.assertIn("local.sample.up: guard.prod.forbid local.sample.ready", make_text)
        self.assertIn("local.dev.up: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.health: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.test: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.upgrade: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.snapshot: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn(
            "local.dev.rebuild_demo: guard.prod.forbid local.dev.demo_credentials.prepare",
            make_text,
        )
        runtime_ops = (ROOT / "make/runtime_ops.mk").read_text(encoding="utf-8")
        verify_demo = runtime_ops.split("verify.demo:", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("DB_NAME=sc_demo", verify_demo)
        status_block = make_text.split("local.env.status:", 1)[1].split(
            "FRONTEND_DEV_LOG", 1
        )[0]
        self.assertIn("persistent || status=1", status_block)
        self.assertIn("sample || status=1", status_block)
        self.assertIn("clean || status=1", status_block)
        self.assertIn("exit $$status", status_block)

    def test_technical_sample_discard_is_exact_and_fail_closed(self):
        source = (ROOT / "scripts/dev/local_sample_discard.sh").read_text(
            encoding="utf-8"
        )
        for exact in (
            "sc-local-sample",
            "sc_dev_sample",
            "^sc_dev_sample$",
            "sc_local_sample_db_data",
            "sc_local_sample_redis_data",
            "sc_local_sample_odoo_data",
            "DISCARD_LOCAL_TECHNICAL_SAMPLE",
        ):
            self.assertIn(exact, source)
        self.assertIn('compose_dev down --volumes --remove-orphans', source)
        self.assertNotIn("sc_local_dev_", source)
        self.assertNotIn("sc_local_clean_", source)

    def test_feature_demo_rebuild_bootstraps_infrastructure_before_reset(self):
        source = (ROOT / "scripts/dev/local_dev_demo_rebuild.sh").read_text(
            encoding="utf-8"
        )
        self.assertLess(source.index("compose_dev up -d db redis"), source.index("scripts/demo/reset.sh"))
        self.assertLess(source.index("scripts/demo/reset.sh"), source.index("scripts/demo/load_full.sh"))
        self.assertLess(source.index("scripts/demo/load_full.sh"), source.index("compose_dev up -d\n"))
        for exact in (
            "sc-local-dev",
            "sc_dev_demo",
            "^sc_dev_demo$",
            "sc_local_dev_db_data",
            "sc_local_dev_redis_data",
            "sc_local_dev_odoo_data",
            "REBUILD_CURRENT_FEATURE_DEMO",
        ):
            self.assertIn(exact, source)

        reset = (ROOT / "scripts/demo/reset.sh").read_text(encoding="utf-8")
        self.assertIn("/var/lib/odoo/demo_install.log", reset)
        self.assertLess(reset.index("set +e"), reset.index("odoo --config"))
        self.assertLess(reset.index("rc=${PIPESTATUS[0]}"), reset.index("set -e\nif"))

        hook = (ROOT / "addons/smart_construction_demo/hooks.py").read_text(
            encoding="utf-8"
        )
        registry = (
            ROOT / "addons/smart_construction_demo/seed/registry.py"
        ).read_text(encoding="utf-8")
        for guard_source in (hook, registry):
            self.assertIn('"sc_dev_demo"', guard_source)
            self.assertNotIn('"sc_dev_sample"', guard_source)
        for required_step in ('"project_skeleton"', '"boq_sample"', '"metrics_smoke"'):
            self.assertIn(required_step, registry)

        credentials = (
            ROOT / "scripts/dev/local_dev_demo_credentials_prepare.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("openssl rand -hex 32", credentials)
        self.assertIn("value not printed", credentials)
        self.assertNotIn("DB_PASSWORD}", credentials)
        self.assertNotIn("JWT_SECRET}", credentials)

        scenario_loader = (
            ROOT / "addons/smart_construction_demo/tools/scenario_loader.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("allow_payment_ledger_create", scenario_loader)
        self.assertIn("._ensure_payment_ledger(", scenario_loader)

        project_seed = (
            ROOT
            / "addons/smart_construction_demo/seed/steps/step_20_projects_demo.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"line_type": "heading"', project_seed)
        self.assertIn('"line_type": "group"', project_seed)
        self.assertIn('update_vals["project_code"] = code', project_seed)
        self.assertIn("Demo project identity drift", project_seed)
        self.assertIn(
            'owned_xmlid="smart_construction_demo.sc_demo_project"', project_seed
        )
        self.assertIn('version.state in ("published", "superseded")', project_seed)
        self.assertIn("Demo BOQ immutable snapshot is incomplete", project_seed)
        self.assertNotIn(
            'if not Boq.search_count([("project_id", "=", project.id)])',
            project_seed,
        )


if __name__ == "__main__":
    unittest.main()
