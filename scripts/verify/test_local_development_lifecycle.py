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


class EnvironmentDoctorVolumeReadbackTest(unittest.TestCase):
    def run_doctor(self, mode="present", project="sc-local-clean"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = root / "scripts/common"
            common.mkdir(parents=True)
            (common / "env.sh").write_text("\n".join([
                f"COMPOSE_PROJECT_NAME={project}", "DB_NAME=sc_clean",
                "ODOO_DBFILTER='^sc_clean$'", "ISOLATED_REHEARSAL_DATABASE=1",
                "DB_DATA=sc_local_clean_db_data", "REDIS_DATA=sc_local_clean_redis_data",
                "ODOO_DATA=sc_local_clean_odoo_data",
            ]) + "\n")
            (common / "compose.sh").write_text(r'''
compose_dev() { printf 'compose %s\n' "$*" >> "$TRACE_FILE"; }
docker() {
  printf 'docker %s\n' "$*" >> "$TRACE_FILE"
  case "$1 $2" in
    'volume ls')
      [[ "$MOCK_MODE" != error ]] || return 17
      [[ "$MOCK_MODE" != absent ]] || return 0
      [[ "$MOCK_MODE" != mismatch ]] || { echo another_volume; return 0; }
      local name="${4#name=^}"
      printf '%s\n' "${name%\$}"
      ;;
    'volume inspect') printf '%s project=sc-local-clean volume=declared\n' "${@: -1}" ;;
    'ps -a') echo 'existing-container clean-odoo Exited project=sc-local-clean' ;;
    *) return 99 ;;
  esac
}
''')
            trace = root / "trace"
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/dev/local_environment_doctor.sh"), "clean"],
                env={**os.environ, "ROOT_DIR": str(root), "TRACE_FILE": str(trace), "MOCK_MODE": mode},
                text=True, capture_output=True,
            )
            return result, trace.read_text() if trace.exists() else ""

    def test_stopped_profile_reports_existing_exact_volumes_and_mount_users(self):
        result, trace = self.run_doctor()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("exists=true"), 3)
        self.assertEqual(result.stdout.count("existing-container"), 3)
        for kind in ("db", "redis", "odoo"):
            name = f"sc_local_clean_{kind}_data"
            self.assertIn(f"name=^{name}$", trace)
            self.assertIn(f"volume={name}", trace)
        self.assertNotIn("docker run", trace)
        self.assertNotIn("create", trace)
        self.assertNotIn("remove", trace)

    def test_absent_volumes_are_observations_not_created(self):
        result, trace = self.run_doctor("absent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("exists=false"), 3)
        self.assertNotIn("volume inspect", trace)
        self.assertNotIn("docker ps", trace)

    def test_docker_error_cannot_be_reported_as_absence(self):
        result, trace = self.run_doctor("error")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("exists=false", result.stdout)
        self.assertNotIn("compose", trace)

    def test_mismatched_volume_or_profile_stops_before_followup(self):
        result, trace = self.run_doctor("mismatch")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("volume inspect", trace)
        result, trace = self.run_doctor(project="another-project")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, "")


class LayoutAuthorityReadonlyProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ast, re
        source = (ROOT / "scripts/verify/local_dev_payment_request_native_parity_ids.py").read_text()
        tree = ast.parse(source)
        names = {"guidance_reference_paths", "split_layout_authority", "layout_differences", "validate_layout_observation", "select_authority_record"}
        namespace = {"re": re}
        exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[]), "actual-probe-functions", "exec"), namespace)
        cls.functions = namespace

    def test_fields_occurrences_order_and_span_are_not_removed(self):
        value = {"nodes": [{"nodeId": "one", "span": 12, "widgetList": [{"fieldCode": "name", "occurrenceIndex": 1, "visible": False}]}]}
        flags = []
        structure = self.functions["split_layout_authority"](value, permissions=flags)
        self.assertEqual(structure["nodes"][0]["widgetList"], [{"fieldCode": "name", "occurrenceIndex": 1}])
        self.assertEqual(structure["nodes"][0]["span"], 12)
        self.assertEqual(flags, [{"path": "$.nodes[0].widgetList[0].visible", "value": False}])
        self.assertFalse(value["nodes"][0]["widgetList"][0]["visible"])

    def test_real_layout_change_is_reported_separately_from_access(self):
        split = self.functions["split_layout_authority"]
        diff = self.functions["layout_differences"]
        self.assertEqual(diff(split({"span": 12, "readonly": True}), split({"span": 12, "readonly": False})), [])
        self.assertEqual(diff({"span": 12}, {"span": 24})[0]["path"], "$.span")
        self.assertTrue(diff({"fields": ["a", "b"]}, {"fields": ["b", "a"]}))

    def test_success_requires_nonempty_exact_form_declaration(self):
        import copy
        validate = self.functions["validate_layout_observation"]
        good = {"pageInfo": {"model": "example"}, "dataContract": {"mainData": {"id": 7}},
                "layoutContract": {"containerTree": [{"id": "root", "span": 24}]},
                "formStructureContract": {"source": "ui.contract.v2.form_structure_contract",
                    "model": "example", "viewType": "form", "structureAuthority": "native_form_slots"}}
        self.assertEqual(validate(good, "example", 7)["layoutContract"], good["layoutContract"])
        for path, value in [("layoutContract", None), ("layoutContract", {"containerTree": []}),
                            ("formStructureContract", {}), ("formStructureContract", {**good["formStructureContract"], "model": "other"})]:
            bad = copy.deepcopy(good); bad[path] = value
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                validate(bad, "example", 7)
        with self.assertRaises(ValueError):
            validate(good, "example", 8)

    def test_editable_selection_is_exact_draft_and_never_resets(self):
        from types import SimpleNamespace
        select = self.functions["select_authority_record"]
        old = SimpleNamespace(id=99, state="done")
        draft = SimpleNamespace(id=3, state="draft")
        self.assertIs(select("floorplan", old, draft), old)
        self.assertIs(select("editable", old, draft), draft)
        with self.assertRaises(ValueError):
            select("editable", draft, old)
        with self.assertRaises(ValueError):
            select("other", old, draft)
        self.assertEqual(old.state, "done")

    def test_reference_tokens_are_exact_and_nested(self):
        find = self.functions["guidance_reference_paths"]
        self.assertEqual(find({"fields": ["guide", "guide_suffix"]}, ["guide"]), [{"field": "guide", "path": "$.fields[0]"}])
        self.assertEqual(len(find('<field name="guide"/>', ["guide"])), 1)

    def test_authority_mode_exits_before_any_browser_or_approval(self):
        import json
        script = ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts/ops").mkdir(parents=True)
            (root / "scripts/verify").mkdir(parents=True)
            (root / "scripts/verify/local_dev_payment_request_native_parity_ids.py").write_text("# mock transport input")
            (root / "scripts/ops/odoo_shell_exec.sh").write_text("""#!/bin/bash
cat >/dev/null
printf 'LOCAL_DEV_PAYMENT_PARITY_JSON={"database":"sc_dev_demo","probe":"%s"}\\n' "$CONTRACT_REFERENCE_PREFLIGHT"
""")
            env_file = root / "env"
            env_file.write_text("COMPOSE_PROJECT_NAME=sc-local-dev\nDB_NAME=sc_dev_demo\nNGINX_PORT=18081\nSC_DEMO_USER_PASSWORD=synthetic-probe-only\n")
            result = subprocess.run(["bash", str(script)], env={**os.environ, "ROOT_DIR": str(root), "ENV_FILE": str(env_file), "SOURCE_SHA": "a" * 40, "LOCAL_DEV_FLOORPLAN_SCOPE": "authority"}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((root / "artifacts/playwright/local-dev-payment-request-floorplan/authority.json").read_text())
            self.assertEqual(payload["probe"], "authority")
            self.assertFalse((root / "artifacts/playwright/local-dev-payment-request-floorplan/declaration-edit.json").exists())


class FloorplanEvidenceRecordingTest(unittest.TestCase):
    def test_resolver_preserves_raw_diagnostics_and_exit_status(self):
        source = (ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.sh").read_text()
        function = "resolve_target() {" + source.split("resolve_target() {", 1)[1].split('\nbefore="$(resolve_target before)"', 1)[0]
        for status, payload in ((7, "upstream exact error"), (0, "LOCAL_DEV_PAYMENT_PARITY_JSON={}"), (0, "no identity")):
            with self.subTest(status=status, payload=payload), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "scripts/ops").mkdir(parents=True)
                (root / "scripts/verify").mkdir()
                (root / "scripts/verify/local_dev_payment_request_native_parity_ids.py").write_text("unused")
                (root / "scripts/ops/odoo_shell_exec.sh").write_text("printf '%s\\n' '" + payload + "'\necho resolver-stderr >&2\nexit " + str(status))
                result = subprocess.run(["bash", "-c", function + "\nresolve_target before"], env={**os.environ, "ROOT_DIR": directory, "output_dir": directory, "DB_NAME": "sc_dev_demo", "LOCAL_DEV_FLOORPLAN_SCOPE": "consumption"}, capture_output=True, text=True)
                self.assertEqual(result.returncode, status if status else (0 if "PARITY_JSON" in payload else 1))
                log = (root / "resolver-consumption-before.log").read_text()
                self.assertIn(payload, log)
                self.assertIn("resolver-stderr", log)
                if status:
                    self.assertIn("upstream exact error", result.stderr)
                    self.assertEqual(result.stdout, "")
                elif "PARITY_JSON" in payload:
                    self.assertEqual(result.stdout.strip(), "{}")

    def test_malformed_approval_diagnostic_preserves_original_failure(self):
        source = (ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.sh").read_text()
        body = source.split('  if [[ "$approval_status" -ne 0 ]]; then', 1)[1].split('\n  fi', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "approval-edit.json").write_text("{broken")
            result = subprocess.run(["bash", "-ec", body], env={**os.environ, "output_dir": directory, "profile": "edit", "approval_status": "9"}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 9)
            self.assertIn("malformed", result.stderr)

    def script(self, marker):
        source = (ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.sh").read_text()
        return source.split("<<'" + marker + "'", 1)[1].split("\n" + marker, 1)[0]

    def run_results(self, *, summary, after=None, status="0"):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / 'units.json').write_text(json.dumps({'units': [{'id': 'edit:1440', 'fingerprint': 'current'}, {'id': 'readonly:390', 'fingerprint': 'other'}]}))
            if summary is not None:
                (out / 'summary.json').write_text(json.dumps(summary))
            env = {'OUTPUT_DIR': directory, 'BEFORE_JSON': '{"business_fingerprint":"same"}',
                   'AFTER_JSON': json.dumps(after), 'READBACK_STATUS': status, 'BROWSER_STATUS': '0'}
            with patch.dict(os.environ, env):
                with self.assertRaises(SystemExit) as result:
                    exec(compile(self.script('PY_RESULTS'), 'actual-wrapper-results', 'exec'), {})
            return result.exception.code, json.loads((out / 'summary.json').read_text()), (json.loads((out / 'results.json').read_text()) if (out / 'results.json').exists() else None)

    def test_partial_records_only_actual_fingerprinted_keys(self):
        code, summary, result = self.run_results(summary={'pass': True, 'executed_keys': ['edit:1440'], 'unit_results': {'edit:1440': 'passed'}, 'unit_fingerprints': {'edit:1440': 'current'}}, after={'business_fingerprint': 'same'})
        self.assertEqual(code, 0)
        self.assertEqual(result['results'], {'edit:1440': 'passed'})
        self.assertEqual(result['not_executed'], ['readonly:390'])

    def test_partial_failure_records_through_real_engine_without_covering_siblings(self):
        from scripts.ops.evidence_scope import record_units, ScopeError
        code, summary, result = self.run_results(summary={'pass': False,
            'affected_keys': ['edit:1440', 'readonly:390'], 'executed_keys': ['edit:1440'],
            'unit_results': {'edit:1440': 'passed'}, 'unit_fingerprints': {'edit:1440': 'current'}}, after={'business_fingerprint': 'same'})
        self.assertEqual(code, 1)
        self.assertEqual(summary['affected_keys'], ['edit:1440', 'readonly:390'])
        document = {'schema':'evidence_scope.units.v1','check':'probe','identity':{},'units':[
            {'id':'edit:1440','fingerprint':'current'}, {'id':'readonly:390','fingerprint':'other'}]}
        ledger = record_units(document, {}, result, source='actual-partial')
        self.assertEqual(set(ledger['units']), {'edit:1440'})
        self.assertEqual(ledger['units']['edit:1440']['status'], 'passed')
        with self.assertRaises(ScopeError):
            record_units(document, {}, {**result, 'planned_affected': summary['affected_keys']})

    def test_global_browser_error_invalidates_completed_keys(self):
        _, _, result = self.run_results(summary={'pass': False, 'errors':['HTTP500'],
            'executed_keys':['edit:1440'], 'unit_results':{'edit:1440':'passed'}, 'unit_fingerprints':{'edit:1440':'current'}},
            after={'business_fingerprint':'same'})
        self.assertEqual(result['results'], {'edit:1440':'failed'})

    def test_failed_after_readback_cannot_pass_completed_keys(self):
        code, summary, result = self.run_results(summary={'pass': True, 'executed_keys': ['edit:1440'], 'unit_results': {'edit:1440': 'passed'}, 'unit_fingerprints': {'edit:1440': 'current'}}, after=None, status='1')
        self.assertEqual(code, 1)
        self.assertFalse(summary['pass'])
        self.assertEqual(result['results'], {'edit:1440': 'failed'})

    def test_old_summary_fingerprint_is_not_relabelled(self):
        for fingerprint in ('old', None):
            code, _, result = self.run_results(summary={'pass': True, 'executed_keys': ['edit:1440'], 'unit_results': {'edit:1440':'passed'}, 'unit_fingerprints': {'edit:1440': fingerprint}}, after={'business_fingerprint': 'same'})
            self.assertIn('do not match', str(code))
            self.assertIsNone(result)

    def test_startup_failure_leaves_no_executed_units(self):
        code, summary, result = self.run_results(summary=None, after={'business_fingerprint': 'same'})
        self.assertEqual(code, 1)
        self.assertEqual(result['executed_units'], [])
        self.assertFalse(summary['pass'])

    def test_approved_semantics_invalidate_only_own_profile_units(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            target = {'database': 'sc_dev_demo', 'user': {'id': 3, 'company_id': 1},
                      'contract_resolution': {'expected_sha': 'a' * 40, 'targets': {'payment_request': {'model': 'payment.request'}}},
                      'action': {'id': 10}, 'menu': {'id': 20}, 'record': {'id': 7, 'name': 'Sample'}}
            def receipt(profile, digest):
                return {'contract': {'status': 'PASS', 'approved_semantic_sha256': digest,
                    'recomputed_semantic_sha256': digest, 'request': {'render_profile': profile},
                    'identity': {'uid': 3, 'login': 'demo', 'company_id': 1, 'role_code': 'finance'}}}
            for profile in ('edit', 'readonly'):
                (out / f'declaration-{profile}.json').write_text(json.dumps({'profile': profile}))
                (out / f'approval-{profile}.json').write_text(json.dumps(receipt(profile, 'a' * 64)))
            env = {'ROOT_DIR': str(ROOT), 'OUTPUT_DIR': directory, 'BEFORE_JSON': json.dumps(target),
                   'SOURCE_SHA': 'a' * 40, 'LOCAL_DEV_FLOORPLAN_SCOPE': 'consumption'}
            def generate():
                with patch.dict(os.environ, env):
                    exec(compile(self.script('PY_UNITS'), 'actual-wrapper-units', 'exec'), {})
                return {row['id']: row['fingerprint'] for row in json.loads((out / 'units.json').read_text())['units']}
            before = generate()
            self.assertEqual(set(before), {'entry_click'} | {
                f'{surface}:{kind}:{width}'
                for surface, kinds in (('edit', ('auth_occurrence', 'span', 'guidance')),
                                       ('readonly', ('auth_occurrence',)))
                for kind in kinds for width in (1440, 390)
            })
            original_read_bytes = Path.read_bytes
            def changed_header(path):
                value = original_read_bytes(path)
                return value + b"\n// changed" if str(path).endswith("pages/contractForm/useRecordFormLayout.ts") else value
            with patch.object(Path, 'read_bytes', changed_header):
                header_changed = generate()
            self.assertEqual(header_changed['entry_click'], before['entry_click'])
            self.assertNotEqual(header_changed['edit:auth_occurrence:1440'], before['edit:auth_occurrence:1440'])
            def changed_navigation(path):
                value = original_read_bytes(path)
                return value + b"\n// changed" if str(path).endswith("app/runtime/recordEntryContract.ts") else value
            with patch.object(Path, 'read_bytes', changed_navigation):
                self.assertNotEqual(generate()['entry_click'], before['entry_click'])
            env['SOURCE_SHA'] = 'b' * 40
            self.assertEqual(generate(), before, 'revision alone is provenance')
            (out / 'approval-edit.json').write_text(json.dumps(receipt('edit', 'b' * 64)))
            after = generate()
            self.assertNotEqual(after['edit:auth_occurrence:1440'], before['edit:auth_occurrence:1440'])
            for width in (1440, 390):
                self.assertNotEqual(after[f'edit:guidance:{width}'], before[f'edit:guidance:{width}'])
            self.assertEqual(after['readonly:auth_occurrence:1440'], before['readonly:auth_occurrence:1440'])
            self.assertEqual(after['entry_click'], before['entry_click'], 'form semantic changes do not invalidate independent entry')
            bad = receipt('edit', 'b' * 64); bad['contract']['status'] = 'FAIL'
            (out / 'approval-edit.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(SystemExit, 'unverified'):
                generate()

    def test_cleanup_precedes_browser_and_removes_only_owned_outputs(self):
        source = (ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.sh").read_text()
        line = next(line for line in source.splitlines() if line.startswith('rm -f '))
        self.assertLess(source.index(line), source.index('node "$ROOT_DIR/scripts/verify/local_dev_payment_request_floorplan_readonly.mjs"'))
        with tempfile.TemporaryDirectory() as directory:
            for name in ('summary.json', 'results.json', 'record.json', 'before.json'):
                (Path(directory) / name).write_text('old')
            subprocess.run(['bash', '-c', line], env={**os.environ, 'output_dir': directory}, check=True)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['before.json'])

class LocalDevelopmentLifecycleTest(unittest.TestCase):
    def test_collaboration_journey_cleanup_commits_and_fails_closed(self):
        cleanup = (
            ROOT / "scripts/verify/local_dev_collaboration_fixture_cleanup.py"
        ).read_text(encoding="utf-8")
        scope = (
            ROOT / "scripts/verify/local_dev_project_create_contract_action_scope.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("env.cr.commit()", cleanup)
        self.assertIn("LOCAL_DEV_COLLABORATION_FIXTURE_CLEANUP_INCOMPLETE", cleanup)
        self.assertIn('"remaining": remaining', cleanup)
        self.assertNotIn(">/dev/null || true", scope)
        self.assertIn('trap - EXIT', scope)
        self.assertIn('exit "${cleanup_status}"', scope)
        self.assertIn('exit "${journey_status}"', scope)

    def test_safe_runner_includes_registered_demo_addons_mount(self):
        runner = (ROOT / "scripts" / "test" / "test_safe.sh").read_text(encoding="utf-8")
        self.assertIn(
            "/mnt/source-addons,/mnt/demo-addons,${ADDONS_EXTERNAL_MOUNT}",
            runner,
        )

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
            "local.dev.frontend",
            "local.dev.down",
            "local.dev.logs",
            "local.dev.ps",
            "local.dev.test",
            "local.dev.upgrade",
            "local.dev.sync_demo",
            "local.dev.contract_snapshot",
            "local.dev.rebuild_demo",
            "local.dev.verify_demo",
            "local.dev.reset_payment_request_fixture",
            "verify.local.dev.payment_request.native_parity.readonly",
            "verify.local.dev.payment_request.full_chain",
            "verify.local.dev.payment_request.settlement_component.journey",
            "verify.local.dev.payment_request.attachment_m2m.journey",
            "verify.local.dev.tender_award.unit",
            "verify.local.dev.tender_award.journey",
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

    def test_payment_submit_reset_keeps_canonical_env_authority(self):
        submit = (
            ROOT / "scripts/verify/local_dev_payment_request_floorplan_submit.sh"
        ).read_text(encoding="utf-8")
        submit_browser = (
            ROOT / "scripts/verify/local_dev_payment_request_floorplan_submit.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn('LOCAL_DEV_CANONICAL_ENV_FILE="$(readlink -f "$ENV_FILE")"', submit)
        self.assertIn('ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE"', submit)
        self.assertNotIn('local.dev.sync_demo', submit)
        self.assertIn('local.dev.reset_payment_request_fixture', submit)
        self.assertIn('JOURNEY_SCOPE="${PAYMENT_REQUEST_JOURNEY_SCOPE:-payment}"', submit)
        self.assertIn('PAYMENT_REQUEST_JOURNEY_SCOPE="$JOURNEY_SCOPE"', submit)
        self.assertIn("if (journeyScope === 'relation')", submit_browser)
        self.assertIn("payment_request_relation_lifecycle.v1", submit_browser)
        self.assertNotIn("report.projectRelationCreate =", submit_browser)
        self.assertIn("fillOptionalLoginDatabase", submit_browser)
        self.assertIn("count <= 1", submit_browser)
        self.assertIn("unique_response_auto_selected", submit_browser)
        self.assertIn("&& await visibleOptionPanel.count() === 0", submit_browser)
        self.assertEqual(
            submit_browser.count('[data-professional-relation-lifecycle="search"][role="dialog"]:visible'),
            2,
        )
        self.assertIn("targetId", submit_browser)
        self.assertIn("relation option action", submit_browser)
        self.assertIn("optionAction.click()", submit_browser)
        self.assertIn("managed project create dialog close action", submit_browser)
        self.assertIn("data-professional-relation-lifecycle", submit_browser)
        self.assertIn("project name input did not enter the child form state", submit_browser)
        self.assertIn("project.project.name has no such action", submit_browser)
        self.assertNotIn("projectNameOnchangePromise", submit_browser)
        self.assertNotIn("project name onchange failed before save", submit_browser)
        self.assertIn(
            "relation lifecycle must not emit a parent payment mutation",
            submit_browser,
        )
        self.assertNotIn("returned parent payment save action", submit_browser)
        self.assertNotIn("parent payment must emit exactly one create mutation", submit_browser)
        self.assertEqual(
            submit_browser.count(
                '[data-action-ref="form.save"][data-action-enabled="true"]'
            ),
            2,
        )
        self.assertNotIn(
            '[data-action-ref="form.save"][data-action-tier="primary"]',
            submit_browser,
        )
        self.assertIn(
            "page.locator('[data-list-surface-header]').getByRole('button', { name: /^新建$/ })",
            submit_browser,
        )
        self.assertNotIn(
            "listSurface.getByRole('button', { name: /^新建$/ })",
            submit_browser,
        )
        self.assertNotIn(
            '[data-product-primary-action][data-action-tier="primary"]',
            submit_browser,
        )
        self.assertIn(
            "JSON.stringify(['attachment_ids', 'outflow_line_ids'])",
            submit_browser,
        )
        self.assertIn(
            "metrics.duplicateFields.length === 0",
            submit_browser,
        )
        self.assertNotIn(
            "attachment capability was duplicated into the business relation region",
            submit_browser,
        )
        self.assertNotIn(
            "lost its backend-authorized search entry",
            submit_browser,
        )
        self.assertIn("project create action", submit_browser)
        self.assertIn("project search-more action", submit_browser)
        self.assertEqual(submit_browser.count("[data-disclosure-trigger]"), 1)
        self.assertNotIn("supplementaryDetails.locator('summary')", submit_browser)
        self.assertNotIn("auditRegion.locator('summary')", submit_browser)
        self.assertEqual(
            submit_browser.count('[data-dialog-purpose="intent-confirmation"][role="dialog"]:visible'),
            3,
        )
        self.assertIn(
            "submittedStatusbar.getAttribute('data-workflow-current')",
            submit_browser,
        )
        self.assertLess(
            submit_browser.index("const postSubmitRecordPromise = page.waitForResponse"),
            submit_browser.index("await submitConfirm.click()"),
        )
        self.assertIn(
            "await Promise.all([postSubmitContractPromise, postSubmitRecordPromise])",
            submit_browser,
        )
        self.assertIn("String(body?.params?.op || '') === 'action_open'", submit_browser)
        self.assertIn("Number(body?.params?.action_id || 0) === Number(expectedActionId)", submit_browser)
        self.assertIn("Number(body?.params?.record_id || 0) === Number(expectedRecordId)", submit_browser)
        self.assertNotIn("String(body?.params?.model || '') === 'payment.request';\n  } catch", submit_browser)
        self.assertLess(
            submit_browser.index("submittedRecordSurface.locator('[data-contract-form-driver]').waitFor"),
            submit_browser.index("const statusSummaryText ="),
        )
        self.assertNotIn('data-form-mode-action="edit"', submit_browser)
        self.assertNotIn("project login database", submit_browser)
        self.assertNotIn("payment login database", submit_browser)

    def test_payment_full_chain_is_bound_to_local_dev_and_retains_completed_facts(self):
        make_text = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        wrapper = (
            ROOT / "scripts/verify/local_dev_payment_request_full_chain.sh"
        ).read_text(encoding="utf-8")
        browser = (
            ROOT / "scripts/verify/local_dev_payment_request_full_chain.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "verify.local.dev.payment_request.full_chain: guard.prod.forbid local.dev.ready",
            make_text,
        )
        for authority in ("sc-local-dev", "sc_dev_demo", "18081"):
            self.assertIn(authority, wrapper)
        self.assertIn('[[ -n "${SOURCE_SHA:-}" ]]', wrapper)
        self.assertIn('[[ -n "${CANDIDATE_FINGERPRINT:-}" ]]', wrapper)
        self.assertEqual(wrapper.count("local.dev.reset_payment_request_fixture"), 2)
        self.assertNotIn("local.dev.sync_demo", wrapper)
        self.assertIn(
            "STEPS=payment_request_floorplan_demo",
            make_text,
        )
        self.assertIn("bash scripts/demo/run_seed.sh", make_text)
        self.assertIn("trap restore_on_exit EXIT", wrapper)
        self.assertIn("completed payment facts retained as immutable acceptance history", wrapper)
        self.assertNotIn("governed fixture restoration left payment facts behind", wrapper)
        self.assertIn("if (( browser_status == 0 && facts_status == 0 )); then", wrapper)
        self.assertIn("payment.request.execute", browser)
        self.assertIn("payload?.params?.action === 'approve'", browser)
        self.assertIn("`${baseUrl}/my-work`", browser)
        self.assertIn('.count-card[data-section-key="todo"]', browser)
        self.assertIn("for (const [index, review] of approvalChain.entries())", browser)
        self.assertIn("await login(approvalPage, review.actor_login)", browser)
        self.assertIn("LOCAL_DEV_PAYMENT_APPROVAL_CHAIN_JSON", wrapper)
        approval_resolver = (
            ROOT / "scripts/verify/local_dev_payment_request_approval_chain.py"
        ).read_text(encoding="utf-8")
        self.assertIn("request.review_ids", approval_resolver)
        self.assertIn("review.reviewer_ids", approval_resolver)
        self.assertIn("has no governed demo reviewer with record access", approval_resolver)
        self.assertIn('"sc.payment.execution", company=request.company_id', approval_resolver)
        self.assertIn('"payment_execution_policy"', approval_resolver)
        self.assertIn(
            'data-product-primary-action][data-action-key="payment_execution"]'
            '[data-action-method="action_create_payment_execution"]'
            '[data-action-enabled="true"]',
            browser,
        )
        self.assertIn(
            "submitted payment execution preserves the authoritative request amount and payee snapshot",
            browser,
        )
        self.assertIn("payment execution intake exposes one visible handler component input", browser)
        self.assertIn("name: /^保存草稿$/", browser)
        self.assertIn("group_sc_role_finance_user", browser)
        self.assertIn("finance_user_execution_submitter", browser)
        self.assertIn('[data-action-method="action_confirm"][data-action-enabled="true"]:visible', browser)
        self.assertIn('data-action-method="validate_tier"', browser)
        self.assertIn("optional payment execution approval confirms directly when disabled", browser)
        self.assertIn("configured payment execution approval creates tier reviews", browser)
        self.assertIn('data-action-method="action_paid"', browser)
        self.assertIn("exactly one posted ledger reconciles", browser)
        self.assertIn("successful paid request captures complete contract authority envelope", browser)
        self.assertIn("duplicate_payment_business_state_guard", browser)
        self.assertIn("duplicate_payment_contract_state_guard", browser)
        self.assertIn("duplicateBusinessStateGuard", browser)
        self.assertIn("duplicateContractStateGuard", browser)
        self.assertIn("duplicateMessage === 'ACTION_NOT_VISIBLE_IN_STATE'", browser)
        self.assertIn("duplicateMessage === 'ACTION_CONTRACT_AUTHORITY_MISSING'", browser)
        self.assertIn("authority_metadata_missing:", browser)
        self.assertIn("server_error: duplicate.status >= 500", browser)
        self.assertIn("exact authorized paid request replay is rejected by an explicit paid-state guard", browser)
        self.assertIn("duplicate payment replay leaves execution request and ledger facts unchanged", browser)
        self.assertIn("no unexpected browser console errors", browser)
        self.assertIn("390px final request has no horizontal overflow", browser)

    def test_payment_parity_resolver_fails_closed_on_runtime_authority_drift(self):
        resolver = (
            ROOT / "scripts/verify/local_dev_payment_request_native_parity_ids.py"
        ).read_text(encoding="utf-8")
        browser = (
            ROOT / "scripts/verify/local_dev_payment_request_native_parity_readonly.mjs"
        ).read_text(encoding="utf-8")
        floorplan_browser = (
            ROOT / "scripts/verify/local_dev_payment_request_floorplan_readonly.mjs"
        ).read_text(encoding="utf-8")
        for required in (
            "_visible_menu_ids",
            "expression.AND",
            "record_in_action_domain",
            "build_route_authority",
            "route_matches",
            "actionable_funding_baseline",
            "submit-ready payment request date is outside the active funding baseline",
            "smart_construction_demo.payment_request_floorplan_demo_record",
        ):
            self.assertIn(required, resolver)
        self.assertNotIn('search([("name", "=", "PRQ-2026-001")]', resolver)
        self.assertIn("catch (error)", browser)
        self.assertIn("report.failure", browser)
        self.assertIn("locateCollectionRecord", browser)
        self.assertIn('data-record-key=', browser)
        self.assertIn("全部展开", browser)
        self.assertIn("CollectionPaginationFooter", browser)
        self.assertIn("t-pagination__btn-next", browser)
        self.assertIn("api.data", browser)
        self.assertIn("previousRowSignature", browser)
        self.assertIn('url.pathname === `/f/${model}/${recordId}`', browser)
        self.assertIn("list_offset", browser)
        self.assertIn("collectContractStrings", browser)
        self.assertIn("report.projectionGaps", browser)
        self.assertIn("report.contractSemanticEvidence", browser)
        self.assertIn("renderedFieldCount", browser)
        self.assertIn("floorplanRegions", browser)
        self.assertIn("report.failureSurface", browser)
        self.assertIn("pagination:", browser)
        # Exact receipt and live contract authority replaced the retired fixed floorplan.
        for required in ('assertContractPrerequisite', 'observedContractBinding', 'formDeclaration',
                         'approved form contract diverged', 'readonly fields became editable',
                         'await actualRow.click()', 'page.waitForURL', 'business writes attempted',
                         'x2many_nondefault_page_size', 'x2many_cross_page_count'):
            self.assertIn(required, floorplan_browser)
        self.assertNotIn("data-object-task-page]\".waitFor", floorplan_browser)


    def test_payment_settlement_component_reset_keeps_canonical_env_authority(self):
        journey = (
            ROOT / "scripts/verify/local_dev_payment_settlement_component_journey.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('LOCAL_DEV_CANONICAL_ENV_FILE="$(readlink -f "$ENV_FILE")"', journey)
        self.assertIn('ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE"', journey)
        self.assertNotIn('make -C "$ROOT_DIR" --no-print-directory local.dev.sync_demo', journey)
        self.assertEqual(journey.count("local.dev.reset_payment_request_fixture"), 3)
        self.assertIn("local.dev.reset_payment_request_fixture", journey)
        self.assertIn("trap restore_on_exit EXIT", journey)
        self.assertIn("restore_needed=1", journey)
        self.assertIn("trap - EXIT", journey)
        self.assertIn("restoring governed fixture after interrupted journey", journey)
        self.assertIn("authoritative line and amount relationship created", journey)
        self.assertIn("confirmation removed it and preserved amount", journey)
        self.assertIn('FRONTEND_URL="http://127.0.0.1:5176"', journey)
        self.assertIn('[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$CANDIDATE_GIT_HEAD" ]]', journey)
        resolver = (
            ROOT / "scripts/verify/local_dev_payment_settlement_component_ids.py"
        ).read_text(encoding="utf-8")
        self.assertIn("smart_construction_demo.sc_demo_settlement_069_payment", resolver)
        self.assertIn("smart_construction_demo.sc_demo_settlement_line_069_payment", resolver)
        self.assertIn("with_user(user).with_company(user.company_id)", resolver)
        self.assertIn("selected_settlement.currency_id != request.currency_id", resolver)
        self.assertNotIn('order="id desc"', resolver)

    def test_payment_attachment_m2m_journey_reuses_governed_fixture_lifecycle(self):
        make_text = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        journey = (
            ROOT / "scripts/verify/local_dev_payment_attachment_m2m_journey.sh"
        ).read_text(encoding="utf-8")
        browser = (
            ROOT / "scripts/verify/local_dev_payment_attachment_m2m_journey.mjs"
        ).read_text(encoding="utf-8")
        resolver = (
            ROOT / "scripts/verify/local_dev_payment_attachment_m2m_ids.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "verify.local.dev.payment_request.attachment_m2m.journey: guard.prod.forbid",
            make_text,
        )
        self.assertIn('LOCAL_DEV_CANONICAL_ENV_FILE="$(readlink -f "$ENV_FILE")"', journey)
        self.assertEqual(journey.count("local.dev.reset_payment_request_fixture"), 3)
        self.assertIn("trap restore_on_exit EXIT", journey)
        self.assertIn("complete_worktree_fingerprint.py", journey)
        self.assertNotIn("local.dev.sync_demo", journey)
        self.assertIn("relationship detached; attachment object retained", journey)
        self.assertIn("fixture reset restored the governed baseline", journey)
        self.assertIn("解除关联", browser)
        self.assertIn("actualAttachmentProtocol", browser)
        self.assertIn("保存修改", browser)
        self.assertIn("放弃", browser)
        self.assertIn("smart_construction_demo.payment_request_floorplan_demo_record", resolver)
        self.assertIn("smart_construction_demo.payment_request_floorplan_demo_attachment", resolver)
        self.assertIn('field.type != "many2many"', resolver)
        self.assertIn("with_user(user).with_company(user.company_id)", resolver)

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
        self.assertIn("local.dev.frontend: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn(
            "verify.local.dev.payment_request.native_parity.readonly: guard.prod.forbid local.dev.ready",
            make_text,
        )
        self.assertIn("local.dev.test: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.upgrade: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn(
            "local.dev.verify_authority: guard.prod.forbid local.dev.ready",
            make_text,
        )
        upgrade = make_text.split("local.dev.upgrade:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("mod.upgrade", upgrade)
        self.assertIn("local.dev.verify_authority", upgrade)
        self.assertIn("local.dev.demo_credentials.prepare", upgrade)
        self.assertIn("SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1", upgrade)
        for entry in ("local.dev.demo.load", "local.dev.demo.seed"):
            wrapper = make_text.split(entry + ":", 1)[1].split("\n\n", 1)[0]
            self.assertIn("local.dev.ready local.dev.demo_credentials.prepare", wrapper)
            self.assertIn("$(LOCAL_ENV_ISOLATE)", wrapper)
            self.assertIn('ENV_FILE="$(LOCAL_DEV_ENV_FILE)"', wrapper)
        test_wrapper = make_text.split("local.dev.test:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("local.dev.demo_credentials.prepare", test_wrapper)
        self.assertIn("SC_ENVIRONMENT=demo SC_ALLOW_DEMO_DATA=1", test_wrapper)
        test_adapter = (ROOT / "scripts/test/test_safe.sh").read_text()
        for variable in ("SC_ENVIRONMENT", "SC_ALLOW_DEMO_DATA", "SC_DEMO_USER_PASSWORD"):
            self.assertIn("-e " + variable, test_adapter)
        self.assertNotIn("SC_ENVIRONMENT=demo", test_adapter)
        upgrade_adapter = (ROOT / "scripts/mod/upgrade.sh").read_text()
        for variable in ("SC_ENVIRONMENT", "SC_ALLOW_DEMO_DATA", "SC_DEMO_USER_PASSWORD"):
            self.assertIn("-e " + variable, upgrade_adapter)
        verify_authority = make_text.split(
            "local.dev.verify_authority:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("SC_ENVIRONMENT=demo", verify_authority)
        self.assertIn("SC_ALLOW_DEMO_DATA=1", verify_authority)
        self.assertIn("local.dev.snapshot: guard.prod.forbid local.dev.ready", make_text)
        self.assertIn("local.dev.contract_snapshot: guard.prod.forbid local.dev.ready", make_text)
        contract_snapshot = make_text.split("local.dev.contract_snapshot:", 1)[1].split("\n\n", 1)[0]
        self.assertIn('ENV_FILE="$(LOCAL_DEV_ENV_FILE)"', contract_snapshot)
        self.assertIn("$(LOCAL_ENV_ISOLATE)", contract_snapshot)
        self.assertIn("contract.export_all", contract_snapshot)
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
        self.assertIn("ensure_local_demo_product_baseline.py", reset)
        self.assertLess(
            reset.index("ensure_local_demo_product_baseline.py"),
            reset.index("-i smart_construction_demo"),
        )
        self.assertNotIn(
            "-i smart_construction_core,smart_construction_seed,smart_construction_demo",
            reset,
        )
        self.assertIn(
            'ODOO_ADDONS_PATH="/usr/lib/python3/dist-packages/odoo/addons,'
            '/mnt/source-addons,/mnt/demo-addons,/mnt/extra-addons,'
            '${ADDONS_EXTERNAL_MOUNT}"',
            reset,
        )
        self.assertNotIn('ODOO_ADDONS_PATH="${ODOO_ADDONS_PATH:-', reset)
        self.assertIn("local_dev_demo_authority_verify.sh", reset)
        self.assertLess(
            reset.rindex("-i smart_construction_demo"),
            reset.rindex("local_dev_demo_authority_verify.sh"),
        )

        load_full = (ROOT / "scripts/demo/load_full.sh").read_text(encoding="utf-8")
        self.assertIn("local_dev_demo_authority_verify.sh", load_full)
        self.assertLess(
            load_full.index("local_dev_demo_authority_verify.sh"),
            load_full.index("scripts/demo/load_release.sh"),
        )
        self.assertNotIn("scripts/demo/load_all.sh", load_full)
        authority_verify = (
            ROOT / "scripts/dev/local_dev_demo_authority_verify.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("guard_demo_data_scope", authority_verify)
        self.assertIn("guard_prod_forbid", authority_verify)
        self.assertIn("local_dev_demo_authority_preflight.py", authority_verify)
        self.assertIn("/mnt/source-addons,/mnt/demo-addons", authority_verify)
        authority = (
            ROOT / "scripts/dev/local_dev_demo_authority_preflight.py"
        ).read_text(encoding="utf-8")
        for required in (
            "DEMO_AUTHORITY_MODULE_MISSING",
            "DEMO_AUTHORITY_FINANCE_ROLE_XMLID_MISSING",
            "DEMO_AUTHORITY_FINANCE_ROLE_IDENTITY_INVALID",
            "DEMO_AUTHORITY_FINANCE_GROUP_XMLID_MISSING",
            "DEMO_AUTHORITY_FINANCE_ROLE_MEMBERSHIP_MISSING",
            "DEMO_AUTHORITY_COMPANY_CNY_MISSING",
            "DEMO_AUTHORITY_SALE_TAX_9_MISSING",
            'demo_module.state == "installed"',
            '"smart_construction_demo.user_demo_role_finance"',
            '"smart_construction_core.group_sc_role_finance_manager"',
        ):
            self.assertIn(required, authority)

        baseline = (
            ROOT / "scripts/ops/ensure_local_demo_product_baseline.py"
        ).read_text(encoding="utf-8")
        self.assertIn("ensure_core_taxes(env)", baseline)
        self.assertIn('env["res.company"]._sc_ensure_cny_currency()', baseline)
        self.assertIn("LOCAL_DEMO_PRODUCT_BASELINE_CNY_MISSING", baseline)
        self.assertLess(
            baseline.index("LOCAL_DEMO_PRODUCT_BASELINE_TAX_MISSING"),
            baseline.index("env.cr.commit()"),
        )
        self.assertNotIn(".create(", baseline)

        hook = (ROOT / "demo_addons/smart_construction_demo/hooks.py").read_text(
            encoding="utf-8"
        )
        registry = (
            ROOT / "demo_addons/smart_construction_demo/seed/registry.py"
        ).read_text(encoding="utf-8")
        for guard_source in (hook, registry):
            self.assertIn('"sc_dev_demo"', guard_source)
            self.assertNotIn('"sc_dev_sample"', guard_source)
        for required_step in ('"project_skeleton"', '"boq_sample"', '"metrics_smoke"'):
            self.assertIn(required_step, registry)

        credentials = (
            ROOT / "scripts/dev/local_dev_demo_credentials_prepare.sh"
        ).read_text(encoding="utf-8")
        make_text = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        self.assertIn("openssl rand -hex 32", credentials)
        self.assertIn("value not printed", credentials)
        self.assertNotIn("DB_PASSWORD}", credentials)
        self.assertNotIn("JWT_SECRET}", credentials)
        # Owner decision 2026-10-03: sc-local-dev defaults to one fixed, simple
        # demo credential; the random path stays available as an explicit opt-in
        # and the value is declared in exactly one governed place.
        self.assertIn('FIXED_DEV_DEMO_PASSWORD="scdevpass"', credentials)
        self.assertIn('MODE="${SC_DEV_DEMO_PASSWORD_MODE:-fixed}"', credentials)
        self.assertIn("sc-local-dev", credentials)
        self.assertNotIn("sc_dev_sample", credentials)
        self.assertNotIn("sc_clean", credentials)
        self.assertIn(
            "local.dev.demo_users.sync: guard.prod.forbid local.dev.ready "
            "local.dev.demo_credentials.prepare",
            make_text,
        )
        demo_users_sync = make_text.split("local.dev.demo_users.sync:", 1)[1].split(
            "\n\n", 1
        )[0]
        self.assertIn("STEPS=demo_users", demo_users_sync)
        self.assertIn('ENV_FILE="$(LOCAL_DEV_ENV_FILE)"', demo_users_sync)
        self.assertIn("$(LOCAL_ENV_ISOLATE)", demo_users_sync)

        scenario_loader = (
            ROOT / "demo_addons/smart_construction_demo/tools/scenario_loader.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("allow_payment_ledger_create", scenario_loader)
        self.assertNotIn("._ensure_payment_ledger(", scenario_loader)
        self.assertNotIn("._write_lifecycle(", scenario_loader)

        project_seed = (
            ROOT
            / "demo_addons/smart_construction_demo/seed/steps/step_20_projects_demo.py"
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
