import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DemoTenantLifecycleTest(unittest.TestCase):
    def test_lifecycle_is_fail_closed_and_customer_neutral(self):
        source = (ROOT / "scripts/demo/tenant_lifecycle.sh").read_text()
        for token in (
            "SC_DEMO_TENANT_LIFECYCLE",
            "ISOLATED_DEMO_TENANT",
            '"^${DB_NAME}$"',
            "DEMO_TENANT_CUSTOMER_ADDONS_FORBIDDEN",
            "name LIKE 'sce_customer_%'",
            "flock -n",
            "compose_dev stop nginx odoo",
            "DEMO_TENANT_ODOO_READY_TIMEOUT",
        ):
            self.assertIn(token, source)
        self.assertNotIn("SC_CUSTOMER_ADDONS_ROOT=/", source)

    def test_timer_uses_governed_make_entrypoint(self):
        service = (ROOT / "deploy/demo-tenant/scems-demo-tenant.service").read_text()
        timer = (ROOT / "deploy/demo-tenant/scems-demo-tenant.timer").read_text()
        self.assertIn("ExecStart=/usr/bin/make demo.tenant.reset", service)
        self.assertIn("OnCalendar=", timer)
        self.assertIn("Persistent=true", timer)

    def test_runtime_purge_is_exactly_scoped(self):
        source = (ROOT / "scripts/demo/purge_demo_runtime.py").read_text()
        self.assertIn('Path("/var/lib/odoo")', source)
        self.assertIn("sc_demo", source)
        self.assertIn("DEMO_RUNTIME_SYMLINK_FORBIDDEN", source)

    def test_explicit_demo_safety_context_wins_over_env_defaults(self):
        source = (ROOT / "scripts/common/env.sh").read_text()
        for variable in (
            "SC_ENVIRONMENT",
            "SC_ALLOW_DEMO_DATA",
            "SC_DEMO_USER_PASSWORD",
            "SC_DEMO_TENANT_LIFECYCLE",
            "ISOLATED_DEMO_TENANT",
        ):
            self.assertIn("_pre_%s" % variable, source)

    def test_demo_data_does_not_reference_retired_wbs_model(self):
        for path in (ROOT / "addons/smart_construction_demo").rglob("*.xml"):
            self.assertNotIn('model="project.wbs"', path.read_text())

    def test_reset_loads_and_verifies_release_grade_seed(self):
        source = (ROOT / "scripts/demo/tenant_lifecycle.sh").read_text()
        self.assertIn("demo.load.release", source)
        self.assertIn("verify.demo.release.seed", source)
        self.assertIn("verify.demo.formal_product_coverage", source)
        self.assertIn('install -d -m 0777 "${ROOT_DIR}/artifacts"', source)
        self.assertIn("DEMO_RESTART_AFTER_LOAD=0", source)

    def test_ci_prevents_formal_product_demo_coverage_drift(self):
        source = (ROOT / "scripts/demo/ci.sh").read_text()
        self.assertIn("demo.load.release", source)
        self.assertIn("verify.demo.release.seed", source)
        self.assertIn("verify.demo.formal_product_coverage", source)

    def test_demo_boq_lines_follow_version_governance(self):
        demo_root = ROOT / "addons/smart_construction_demo"
        for path in demo_root.rglob("*.xml"):
            source = path.read_text()
            if 'model="project.boq.line"' in source:
                records = source.split('<record ')[1:]
                for record in records:
                    if 'model="project.boq.line"' not in record.split(">", 1)[0]:
                        continue
                    body = record.split("</record>", 1)[0]
                    self.assertIn('name="version_id"', body, str(path))

        showroom = (
            demo_root / "seed/steps/step_demo_showroom.py"
        ).read_text()
        self.assertIn('env["project.boq.version"]', showroom)
        self.assertIn('"version_id": version.id', showroom)
        governed_seed = (
            demo_root / "seed/steps/step_50_boq_wbs_demo.py"
        ).read_text()
        self.assertNotIn('env["sc.project.structure"]', governed_seed)
        self.assertIn('env["construction.execution.scope"]', governed_seed)
        self.assertIn('env["project.boq.allocation"]', governed_seed)
        self.assertIn('env["project.cost.plan"]', governed_seed)
        self.assertIn('env["construction.wbs.plan"]', governed_seed)
        for relative in (
            "seed/steps/step_20_projects_demo.py",
            "seed/steps/step_90_verify_demo.py",
        ):
            self.assertNotIn(
                'env["sc.project.structure"]',
                (demo_root / relative).read_text(),
            )

    def test_release_demo_excludes_legacy_migration_carriers(self):
        demo_root = ROOT / "addons/smart_construction_demo"
        for path in demo_root.rglob("*.xml"):
            source = path.read_text()
            self.assertNotIn('model="sc.legacy.', source, str(path))
            self.assertNotIn('model="sc.project.member.staging"', source, str(path))
            self.assertNotIn('model="sc.partner.import.review"', source, str(path))
            self.assertNotIn('model="sc.project.structure"', source, str(path))


if __name__ == "__main__":
    unittest.main()
