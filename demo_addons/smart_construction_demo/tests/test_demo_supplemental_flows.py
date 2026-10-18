"""Offline orchestration tests; not proof of ORM authorization or installation."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def function_from(path, name, **bindings):
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(bindings)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def function(filename, name, **bindings):
    return function_from(ROOT / "seed/steps" / filename, name, **bindings)


class RetiredExperimentalSeeds(unittest.TestCase):
    def test_retired_financial_shortcuts_are_not_callable(self):
        import runpy
        registry = runpy.run_path(str(ROOT / "seed/registry.py"))
        imports = ast.parse((ROOT / "seed/steps/__init__.py").read_text())
        imported = {alias.name for node in ast.walk(imports)
                    if isinstance(node, ast.ImportFrom) for alias in node.names}
        for name in ("payment_ledger_p1", "phase2_payment_request_demo",
                     "phase2_settlement_order_demo"):
            with self.subTest(step=name):
                self.assertNotIn("step_" + name, imported)
                self.assertFalse((ROOT / "seed/steps" / ("step_" + name + ".py")).exists())
                with self.assertRaisesRegex(ValueError, "unknown demo steps"):
                    registry["_resolve"](name)
                self.assertNotIn(name, registry["_PROFILES"]["demo_full"])


class DemoCompanyIdentity(unittest.TestCase):
    def test_company_identity_is_first_in_the_full_profile(self):
        tree = ast.parse((ROOT / "seed/registry.py").read_text())
        profiles = next(ast.literal_eval(n.value) for n in tree.body
                        if isinstance(n, ast.AnnAssign) and n.target.id == "_PROFILES")
        steps = profiles["demo_full"]
        self.assertEqual(steps[0], "demo_company_identity")
        self.assertLess(steps.index("demo_company_identity"), steps.index("demo_20_projects"))

    def test_step_renames_company_and_partner_idempotently(self):
        partner = SimpleNamespace(name="My Company")
        company = SimpleNamespace(name="My Company", partner_id=partner)
        writes = []

        def write(values):
            writes.append(dict(values))
            for field, value in values.items():
                setattr(company, field, value)
                if field == "name":
                    partner.name = value

        company.write = write
        apply_identity = function_from(
            ROOT / "hooks.py",
            "apply_demo_company_identity",
            DEMO_COMPANY_NAME="Demo演示公司",
        )
        env = SimpleNamespace(ref=lambda xmlid: company)
        apply_identity(env)
        self.assertEqual(company.name, "Demo演示公司")
        self.assertEqual(partner.name, "Demo演示公司")
        self.assertEqual(writes, [{"name": "Demo演示公司"}])
        apply_identity(env)
        self.assertEqual(writes, [{"name": "Demo演示公司"}])
        run = function(
            "step_company_identity.py",
            "_run",
            apply_demo_company_identity=apply_identity,
        )
        self.assertIs(run(env), company)

    def test_password_step_runs_after_every_demo_identity(self):
        tree = ast.parse((ROOT / "seed/registry.py").read_text())
        profiles = next(ast.literal_eval(n.value) for n in tree.body
                        if isinstance(n, ast.AnnAssign) and n.target.id == "_PROFILES")
        steps = profiles["demo_full"]
        self.assertIn("demo_85_passwords", steps)
        self.assertLess(steps.index("demo_80_finalize_stages"), steps.index("demo_85_passwords"))
        self.assertLess(steps.index("demo_85_passwords"), steps.index("demo_90_verify"))

    def test_showroom_lookup_still_returns_the_project_search(self):
        projects = SimpleNamespace(
            search=lambda domain: ("searched", domain),
        )
        env = {"project.project": SimpleNamespace(sudo=lambda: projects)}
        lookup = function("step_90_verify_demo.py", "_get_showroom_projects")
        result = lookup(env)
        self.assertEqual(result[0], "searched")
        self.assertIn(("project_code", "ilike", "DEMO-"), result[1])

    def test_seeded_users_use_the_fixed_showcase_password(self):
        events = []
        fake_os = SimpleNamespace(environ={}, getenv=lambda key, default: default)
        run = function(
            "step_10_users_demo.py",
            "run",
            os=fake_os,
            DEMO_USER_PASSWORD="123456",
            _resolve_lang=lambda *args, **kwargs: "en_US",
            _ensure_user=lambda *args, **kwargs: events.append(kwargs["password"]),
            guard_demo_data_space=lambda env: None,
        )
        run(object())
        self.assertEqual(set(events), {"123456"})

    def test_demo_credentials_check_each_declared_principal(self):
        class AccessDenied(Exception):
            pass

        class UserError(Exception):
            pass

        users = [
            SimpleNamespace(id=1, login="wutao", active=True, share=False),
            SimpleNamespace(id=2, login="demo_full", active=True, share=False),
            SimpleNamespace(id=3, login="demo_role_project_read", active=True, share=False),
        ]
        checked = []
        verify = function(
            "step_90_verify_demo.py",
            "_verify_demo_credentials",
            DEMO_USER_PASSWORD="123456",
            DEMO_PRINCIPAL_LOGINS=("wutao", "demo_full"),
            UserError=UserError,
            AccessDenied=AccessDenied,
            demo_user_records=lambda env: users,
            _check_user_credential=lambda env, user: checked.append(user.login),
        )
        verify(object())
        self.assertEqual(checked, ["wutao", "demo_full", "demo_role_project_read"])

    def test_demo_credentials_require_every_named_principal(self):
        class AccessDenied(Exception):
            pass

        class UserError(Exception):
            pass

        verify = function(
            "step_90_verify_demo.py",
            "_verify_demo_credentials",
            DEMO_USER_PASSWORD="123456",
            DEMO_PRINCIPAL_LOGINS=("wutao", "demo_full"),
            UserError=UserError,
            AccessDenied=AccessDenied,
            demo_user_records=lambda env: [
                SimpleNamespace(login="wutao", active=True, share=False),
            ],
            _check_user_credential=lambda env, user: None,
        )
        with self.assertRaisesRegex(UserError, "demo_full"):
            verify(object())

    def test_credentials_read_the_target_user_not_the_seed_principal(self):
        seen = []

        class Api:
            @staticmethod
            def Environment(cr, uid, context):
                return SimpleNamespace(
                    user=SimpleNamespace(
                        _check_credentials=lambda password, env: seen.append((uid, password))
                    )
                )

        check = function(
            "step_90_verify_demo.py",
            "_check_user_credential",
            api=Api,
            DEMO_USER_PASSWORD="123456",
        )
        check(SimpleNamespace(cr="cursor", context={"lang": "zh_CN"}), SimpleNamespace(id=42))
        self.assertEqual(seen, [(42, "123456")])

    def test_password_step_reapplies_the_password(self):
        events = []
        run = function(
            "step_85_demo_passwords.py",
            "run",
            apply_demo_user_passwords=lambda env: events.append(env),
        )
        env = object()
        run(env)
        self.assertEqual(events, [env])

    def test_demo_user_records_include_seed_only_principals(self):
        class Users(list):
            def __init__(self, items=(), seed_only=None):
                super().__init__(items)
                self.seed_only = seed_only

            def sudo(self):
                return self

            def with_context(self, **kwargs):
                return self

            def browse(self, ids):
                return Users(
                    [SimpleNamespace(id=i, login="xmlid-%s" % i) for i in ids],
                    self.seed_only,
                )

            def search(self, domain, limit=None):
                return Users([self.seed_only], self.seed_only)

            def exists(self):
                return self

            def __or__(self, other):
                return Users(list(self) + list(other), self.seed_only)

        seed_only = SimpleNamespace(id=60, login="demo_full")
        users = Users(seed_only=seed_only)
        env = {
            "ir.model.data": SimpleNamespace(
                sudo=lambda: SimpleNamespace(
                    search=lambda domain: SimpleNamespace(
                        exists=lambda: [SimpleNamespace(res_id=39)]
                    )
                )
            ),
            "res.users": users,
        }
        records = function_from(
            ROOT / "hooks.py",
            "demo_user_records",
            DEMO_DATA_MODULE="smart_construction_demo",
            DEMO_PRINCIPAL_LOGINS=("demo_full",),
        )(env)
        self.assertEqual([record.login for record in records], ["xmlid-39", "demo_full"])


class AttachmentIdempotency(unittest.TestCase):
    class Attachments:
        def __init__(self, values):
            self.values = list(values)

        def filtered(self, predicate):
            return type(self)([value for value in self.values if predicate(value)])

        def __getitem__(self, index):
            if isinstance(index, slice):
                return type(self)(self.values[index])
            return self.values[index]

    def test_existing_named_attachment_is_reused(self):
        wanted = SimpleNamespace(name="合同附件清单 · DEMO-PJ-EXEC.txt")
        other = SimpleNamespace(name="其他附件.txt")
        document = SimpleNamespace(
            attachment_ids=self.Attachments([other, wanted]),
        )
        find = function("step_60_attachments_demo.py", "_find_document_attachment")
        self.assertEqual(list(find(document, wanted.name)), [wanted])

    def test_missing_named_attachment_is_not_fabricated(self):
        document = SimpleNamespace(
            attachment_ids=self.Attachments(
                [SimpleNamespace(name="其他附件.txt")]
            ),
        )
        find = function("step_60_attachments_demo.py", "_find_document_attachment")
        self.assertEqual(list(find(document, "合同附件清单 · DEMO-PJ-EXEC.txt")), [])


class DemoFullPrincipalMigration(unittest.TestCase):
    class Cursor:
        def __init__(self, user_ids=(), existing=None):
            self.user_ids = user_ids
            self.existing = existing
            self.inserted = []
            self.result = []

        def execute(self, statement, params):
            if "FROM res_users" in statement:
                self.result = [(user_id,) for user_id in self.user_ids]
            elif "FROM ir_model_data" in statement:
                self.result = [self.existing] if self.existing else []
            elif statement.strip().startswith("INSERT"):
                self.inserted.append(params)
                self.result = []

        def fetchall(self):
            return self.result

        def fetchone(self):
            return self.result[0] if self.result else None

    def migrate(self):
        import runpy
        return runpy.run_path(str(ROOT / "migrations/0.3.1/pre-migration.py"))["migrate"]

    def test_existing_seed_principal_is_bound_to_the_managed_xmlid(self):
        cursor = self.Cursor(user_ids=(60,))
        self.migrate()(cursor, "0.3.0")
        self.assertEqual(cursor.inserted, [("smart_construction_demo", "user_demo_full", 60)])

    def test_fresh_install_needs_no_migration_write(self):
        cursor = self.Cursor()
        self.migrate()(cursor, "0.3.0")
        self.assertEqual(cursor.inserted, [])

    def test_existing_xmlid_is_not_rewritten(self):
        cursor = self.Cursor(user_ids=(60,), existing=(60,))
        self.migrate()(cursor, "0.3.0")
        self.assertEqual(cursor.inserted, [])

    def test_conflicting_xmlid_stops_the_upgrade(self):
        cursor = self.Cursor(user_ids=(60,), existing=(61,))
        with self.assertRaisesRegex(RuntimeError, "different user"):
            self.migrate()(cursor, "0.3.0")


class Opening:
    def __init__(self):
        self.id = 7
        self.present = False

    def __bool__(self):
        return self.present

    def __len__(self):
        return int(self.present)

    def search(self, domain):
        return self

    def create(self, values):
        self.__dict__.update(values)
        self.present = True
        return self


class Bid:
    def __init__(self, state="prepare"):
        self.state = state
        self.id = 3
        self.name = "TEST"
        self.open_date = "2026-10-15"
        self.bid_amount = 100
        self.award_confirmed_at = False
        self.calls = []
        self.opening = Opening()
        self.env = {"tender.opening": self.opening}

    def write(self, values):
        if "state" in values:
            raise AssertionError("seed attempted direct state write")
        self.__dict__.update(values)

    def action_to_submitted(self):
        self.calls.append("submit")
        self.state = "submitted"

    def action_to_waiting(self):
        self.calls.append("wait")
        self.state = "waiting"

    def action_mark_lost(self):
        self.calls.append("lose")
        self.state = "lost"

    def action_mark_won(self):
        assert self.award_opening_id == self.opening.id
        assert self.award_source_reference == self.opening.remark
        self.calls.append("win")
        self.state = "won"
        self.award_confirmed_at = "confirmed"


class SupplementalFlows(unittest.TestCase):
    def advance(self, bid, target):
        function("step_30_tenders_demo.py", "_advance_bid")(bid, target)

    def test_each_declared_path_uses_actions(self):
        for target, calls in (("prepare", []), ("submitted", ["submit"]),
                              ("waiting", ["submit", "wait"]),
                              ("lost", ["submit", "lose"]),
                              ("won", ["submit", "win"])):
            with self.subTest(target=target):
                bid = Bid()
                self.advance(bid, target)
                self.assertEqual(bid.calls, calls)
                self.assertEqual(bid.state, target)

    def test_confirmed_award_replay_does_not_repeat_actions(self):
        bid = Bid()
        self.advance(bid, "won")
        self.advance(bid, "won")
        self.assertEqual(bid.calls, ["submit", "win"])

    def test_unconfirmed_legacy_award_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "snapshot"):
            self.advance(Bid("won"), "won")

    def test_submitted_bid_can_complete_without_resubmission(self):
        for target, expected in [("waiting", ["wait"]), ("won", ["win"]), ("lost", ["lose"])]:
            bid = Bid("submitted")
            self.advance(bid, target)
            self.assertEqual(bid.calls, expected)
            self.assertEqual(bid.state, target)

    def test_pending_bid_cannot_rewind(self):
        with self.assertRaises(ValueError):
            self.advance(Bid("waiting"), "submitted")

    def test_existing_outcome_cannot_be_rewritten(self):
        with self.assertRaisesRegex(ValueError, "existing business outcome"):
            self.advance(Bid("lost"), "won")

    def test_unknown_target_fails_before_actions(self):
        bid = Bid()
        with self.assertRaisesRegex(ValueError, "Undeclared"):
            self.advance(bid, "invented")
        self.assertFalse(bid.calls)

    def test_conflicting_opening_is_rejected(self):
        bid = Bid()
        bid.opening.create({"result": "won", "win_price": 200})
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.advance(bid, "won")
        self.assertNotIn("win", bid.calls)

    def test_contract_creation_never_receives_terminal_state(self):
        captured = []
        model = SimpleNamespace(search=lambda *a, **k: False,
                                create=lambda values: captured.append(values) or values)
        env = {"construction.contract": model}
        ensure = function("step_40_contracts_demo.py", "_ensure_contract",
                          _demo_action_record=lambda *a: model)
        ensure(env, {"project_id": 1, "subject": "test", "state": "confirmed"})
        self.assertNotIn("state", captured[0])

    def test_contract_confirmation_waits_for_product_approval(self):
        calls = []
        contract = SimpleNamespace(state="draft", invalidate_recordset=lambda: None)
        contract.action_confirm = lambda: calls.append("submit")
        def approve(record):
            calls.append("review")
            record.state = "confirmed"
        confirm = function("step_40_contracts_demo.py", "_confirm_contract",
                           approve_tier_chain=approve, UserError=ValueError)
        confirm(contract)
        confirm(contract)
        self.assertEqual(calls, ["submit", "review"])

    def test_contract_incomplete_approval_is_not_treated_as_success(self):
        contract = SimpleNamespace(state="draft", invalidate_recordset=lambda: None,
                                   action_confirm=lambda: None)
        confirm = function("step_40_contracts_demo.py", "_confirm_contract",
                           approve_tier_chain=lambda record: False, UserError=ValueError)
        with self.assertRaises(ValueError):
            confirm(contract)

    def test_standard_contract_reviewer_has_explicit_demo_seat(self):
        tree = ast.parse((ROOT / "tools/scenario_loader.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "_DEMO_APPROVAL_ACTORS"
                            for t in n.targets))
        seats = ast.literal_eval(node.value)
        self.assertEqual(seats["smart_construction_core.group_sc_cap_contract_manager"],
                         "smart_construction_demo.user_sc_contract_manager_cap")
        self.assertEqual(seats["smart_construction_core.group_sc_role_contract_admin"],
                         "smart_construction_demo.user_sc_contract_01")
        policy_path = ROOT.parents[1] / "addons/smart_construction_core/models/support/approval_policy.py"
        policy_tree = ast.parse(policy_path.read_text())
        assignments = {
            target.id: ast.literal_eval(node.value)
            for node in ast.walk(policy_tree) if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)
            and target.id in ("APPROVAL_SCOPE_GROUP_XMLIDS", "USER_VISIBLE_APPROVAL_TEMPLATES")
        }
        scopes = assignments["APPROVAL_SCOPE_GROUP_XMLIDS"]
        templates = assignments["USER_VISIBLE_APPROVAL_TEMPLATES"]
        for name in ("project_contract_approval", "general_contract_approval"):
            for _label, scope in templates[name]["steps"]:
                self.assertIn(scopes[scope], seats, (name, scope))

    def test_user_role_replacement_reenrolls_before_return(self):
        events = []
        fake_os = SimpleNamespace(environ={"SC_DEMO_USER_PASSWORD": "test-only"},
                                  getenv=lambda key, default: default)
        run = function("step_10_users_demo.py", "run", os=fake_os,
                       DEMO_USER_PASSWORD="123456",
                       _resolve_lang=lambda *args, **kwargs: "en_US",
                       _ensure_user=lambda *args, **kwargs: events.append(kwargs["login"]),
                       guard_demo_data_space=lambda env: events.append("native-enrollment"))
        run(object())
        self.assertEqual(events, ["demo_full", "wutao", "demo_pm", "demo_finance",
                                  "demo_cost", "demo_readonly", "native-enrollment"])

    def test_tender_guarantee_is_reviewed_before_native_confirmation(self):
        tree = ast.parse((ROOT / "tools/scenario_loader.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_ensure_s86_tender_guarantee_lifecycle")
        events = []
        record = SimpleNamespace(state="draft", treasury_ledger_id=False)
        def approve(env, rec, actor):
            self.assertEqual(actor, "smart_construction_demo.user_sc_project_user")
            events.append("public-submission-and-review")
            rec.state = "approved"
        def confirm():
            self.assertEqual(record.state, "approved")
            events.append("native-confirmation")
            record.state = "confirmed"
            record.treasury_ledger_id = 7
        record.action_confirm = confirm
        ns = {"_demo_drive_approval": approve, "_demo_action_record": lambda *args: record}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "guarantee", "exec"), ns)
        env = SimpleNamespace(ref=lambda xmlid: record)
        ns[node.name](env)
        ns[node.name](env)
        self.assertEqual(events, ["public-submission-and-review", "native-confirmation"])

    def test_base_seed_enrolls_declared_seats_before_commit(self):
        tree = ast.parse((ROOT / "tools/scenario_loader.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_base_seed")
        declaration = next(n for n in tree.body if isinstance(n, ast.AnnAssign)
                           and getattr(n.target, "id", None) == "BASE_SEED_FILES")
        self.assertIn("data/demo/sc_demo_users.xml", ast.literal_eval(declaration.value))
        events = []
        namespace = {
            "guard_demo_scope": lambda env: events.append("scope"),
            "apply_demo_company_identity": lambda env: events.append("identity"),
            "BASE_SEED_FILES": ["declared-users.xml"], "file_path": lambda path: path,
            "convert": SimpleNamespace(convert_file=lambda *args, **kwargs: events.append("users")),
            "guard_demo_data_space": lambda env: events.append("enroll"),
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), "load_base_seed", "exec"), namespace)
        namespace["load_base_seed"](SimpleNamespace(cr=SimpleNamespace(commit=lambda: events.append("commit"))))
        self.assertEqual(events, ["scope", "identity", "users", "enroll", "commit"])

    def test_payment_ledger_prepares_settlement_operator_and_reviewers(self):
        tree = ast.parse((ROOT / "tools/scenario_loader.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_prepare_scenario_organization")
        observed = []
        namespace = {
            "_DEMO_PAYMENT_SCOPED_SEATS": ("initiator", "finance_clerk"),
            "_demo_project_members": lambda env, project, seats: observed.append((project, set(seats))),
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), "organization", "exec"), namespace)
        namespace["_prepare_scenario_organization"](SimpleNamespace(ref=lambda xmlid: xmlid), "s69_payment_ledger_surface")
        self.assertEqual(observed[0][0], "smart_construction_demo.sc_demo_project_069_payment_ledger")
        for seat in ("user_sc_settlement_user_cap", "user_demo_project_manager", "user_sc_cost_manager_cap",
                     "user_sc_settlement_manager_cap", "user_sc_fin_mgr_01", "user_demo_role_executive"):
            self.assertIn("smart_construction_demo." + seat, observed[0][1])

    def test_payment_rejected_reenters_public_submission(self):
        tree = ast.parse((ROOT / "tools/scenario_loader.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_demo_drive_approval")
        for initial in ("draft", "rejected"):
            with self.subTest(initial=initial):
                calls = []
                record = SimpleNamespace(state=initial, invalidate_recordset=lambda: None)
                record.sudo = lambda: record
                def submit():
                    calls.append("submit")
                    record.state = "submit"
                record.action_submit = submit
                def actor(env, rec, action, seat):
                    self.assertEqual((action, seat), ("action_submit", "declared_initiator"))
                    return rec
                def review(env, rec):
                    self.assertEqual(rec.state, "submit")
                    calls.append("review")
                    rec.state = "approved"
                namespace = {"_demo_action_record": actor, "_demo_finish_reviews": review,
                             "_DEMO_DOCUMENT_SUBMITTER": "declared_initiator"}
                exec(compile(ast.Module(body=[node], type_ignores=[]), "driver", "exec"), namespace)
                namespace["_demo_drive_approval"](None, record)
                self.assertEqual(calls, ["submit", "review"])
                self.assertEqual(record.state, "approved")

    def test_business_seats_are_declared_demo_users(self):
        import xml.etree.ElementTree as ET
        tree = ast.parse((ROOT / "seed/business_roles.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "MODEL_SEATS" for t in n.targets))
        seats = ast.literal_eval(node.value)
        users = {record.get("id") for path in (ROOT / "data").rglob("*.xml")
                 for record in ET.parse(path).iter("record")
                 if record.get("model") == "res.users"}
        self.assertTrue(seats)
        self.assertFalse(set(seats.values()) - users)
        self.assertNotIn("base.user_root", seats.values())

    def test_stage_reconciliation_has_no_external_writes(self):
        run = function("step_project_stage_sync.py", "run")
        result = run(None)
        self.assertEqual((result["updated"], result["archived"]), (0, 0))

    def test_supplemental_workflows_do_not_write_sql_or_private_projection(self):
        for name in ("step_20_projects_demo.py", "step_demo_showroom.py",
                     "step_50_boq_wbs_demo.py", "step_payment_request_floorplan_demo.py"):
            with self.subTest(name=name):
                source = (ROOT / "seed/steps" / name).read_text()
                self.assertNotIn(".execute(", source)
                self.assertNotIn("skip_cost_tree_sync", source)
                self.assertNotIn("._rebuild_cost_tree(", source)
                self.assertNotIn("allow_transition=True", source)
                self.assertNotIn("._ensure_initial_plan(", source)

    def test_cost_plan_uses_public_generation_and_keeps_analysis_link(self):
        calls = []
        version = SimpleNamespace(id=4)
        plan = SimpleNamespace(line_ids=[])
        def generate():
            calls.append("generate")
            plan.line_ids = [SimpleNamespace(analysis_id=9)]
        plan.action_generate_from_boq = generate
        models = {"project.boq.version": SimpleNamespace(search=lambda *a, **k: version),
                  "project.cost.plan": SimpleNamespace(search=lambda *a, **k: plan)}
        ensure = function("step_50_boq_wbs_demo.py", "_ensure_cost_plan",
                          business_model=lambda env, name: models[name])
        ensure(None, SimpleNamespace(id=3))
        ensure(None, SimpleNamespace(id=3))
        self.assertEqual(calls, ["generate"])
        plan.line_ids = [SimpleNamespace(analysis_id=False)]
        with self.assertRaisesRegex(ValueError, "real analysis source"):
            ensure(None, SimpleNamespace(id=3))

    def test_manual_analysis_is_not_backfilled_after_publication(self):
        tree = ast.parse((ROOT / "seed/business_roles.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "ensure_manual_boq_analysis")
        created = []
        namespace = {"business_model": lambda *args: SimpleNamespace(create=lambda value: created.append(value))}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "manual-analysis", "exec"), namespace)
        ensure = namespace[node.name]
        line = SimpleNamespace(analysis_id=[], version_id=SimpleNamespace(state="published"))
        with self.assertRaisesRegex(ValueError, "rebuild rather than backfill"):
            ensure(None, line, 120)
        self.assertFalse(created)
        line.version_id.state = "draft"
        line.id = 1
        line.quantity = 10
        line.uom_id = SimpleNamespace(name="unit")
        ensure(None, line, 120)
        self.assertEqual(created[0]["source_unit_price"], 120)
        self.assertNotIn("import_batch_id", created[0])
        self.assertNotIn("source_sheet_name", created[0])

    def test_guidance_contract_does_not_copy_approved_business_state(self):
        source = (ROOT / "seed/steps/step_payment_request_floorplan_demo.py").read_text()
        tree = ast.parse(source)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_guidance_fixture")
        calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(c.func, ast.Attribute) and c.func.attr == "copy" for c in calls))
        self.assertTrue(any(isinstance(c.func, ast.Name) and c.func.id == "_confirm_contract" for c in calls))

    def test_unchanged_published_wbs_replay_does_not_write(self):
        tree = ast.parse((ROOT / "seed/business_roles.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "write_if_changed")
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "idempotent-input", "exec"), namespace)
        class Record(dict):
            _fields = {"name": SimpleNamespace(type="char")}
            def write(self, values):
                raise ValueError("published record rejects edits")
        record = Record(name="existing")
        namespace[node.name](record, {"name": "existing"})
        with self.assertRaisesRegex(ValueError, "rejects edits"):
            namespace[node.name](record, {"name": "changed"})


class StageFinalizationTests(unittest.TestCase):
    def drive(self, initial, target):
        calls = []
        project = SimpleNamespace(lifecycle_state=initial, env=object())
        def action(state):
            calls.append(state)
            project.lifecycle_state = state
        project.action_set_lifecycle_state = action
        def actor(env, record, action, xmlid):
            self.assertEqual(action, "action_set_lifecycle_state")
            self.assertEqual(xmlid, "smart_construction_demo.user_demo_project_manager")
            return record
        run = function("step_20_projects_demo.py", "_apply_lifecycle",
                       _demo_action_record=actor, UserError=ValueError,
                       ensure_project_initiation_approved=lambda p: calls.append("approval"))
        run(project, target)
        return calls, project.lifecycle_state

    def test_draft_approval_and_native_forward_actions(self):
        self.assertEqual(self.drive("draft", "warranty"),
                         (["approval", "in_progress", "done", "warranty"], "warranty"))

    def test_prepared_project_resumes_and_terminal_replay_is_noop(self):
        self.assertEqual(self.drive("in_progress", "closed"), (["closed"], "closed"))
        self.assertEqual(self.drive("closed", "closed"), ([], "closed"))

    def test_wrong_stage_never_silently_passes_or_reopens(self):
        for initial, target in [("closed", "in_progress"), ("paused", "warranty"), ("draft", "unknown")]:
            with self.subTest(initial=initial, target=target), self.assertRaises(ValueError):
                self.drive(initial, target)

    def test_stage_target_is_independent_of_preparation_state(self):
        resolve = function("step_20_projects_demo.py", "declared_stage",
                           STAGE_PROJECTS=[("sample", "name", "closed", "archive")])
        self.assertEqual(resolve(SimpleNamespace(project_code="sample", lifecycle_state="in_progress")), "closed")
        self.assertEqual(resolve(SimpleNamespace(project_code="other", lifecycle_state="paused")), "paused")

    def test_registered_finalizer_follows_business_facts(self):
        tree = ast.parse((ROOT / "seed/registry.py").read_text())
        profiles = next(ast.literal_eval(n.value) for n in tree.body
                        if isinstance(n, ast.AnnAssign) and n.target.id == "_PROFILES")
        steps = profiles["demo_full"]
        self.assertLess(steps.index("z_demo_full_my_work"), steps.index("demo_80_finalize_stages"))
        self.assertLess(steps.index("demo_80_finalize_stages"), steps.index("demo_90_verify"))


class DemoSeedReproducibility(unittest.TestCase):
    """The demo tenant must reproduce its identity and demo-only payload."""

    PROFILE = "demo_full"
    DEMO_ENV = {
        "SC_ENVIRONMENT": "demo",
        "SC_ALLOW_DEMO_DATA": "1",
        "SC_DEMO_USER_PASSWORD": "123456",
    }

    def registry(self):
        import runpy
        return runpy.run_path(str(ROOT / "seed/registry.py"))

    class Env(dict):
        def __init__(self, values=None, company=None):
            super().__init__(values or {})
            self.company = company or SimpleNamespace(id=1)

        def ref(self, xmlid, raise_if_not_found=False):
            return self.company

    def guarded(self, dbname, **overrides):
        registry = self.registry()
        values = dict(self.DEMO_ENV)
        values.update(overrides)
        with patch.dict(os.environ, values, clear=False):
            return registry["_guard_demo_scope"](SimpleNamespace(cr=SimpleNamespace(dbname=dbname)))

    def test_seed_guard_rejects_non_demo_databases(self):
        for dbname in ("production", "sc_production", "sc_dev_sample", ""):
            with self.subTest(dbname=dbname):
                with self.assertRaisesRegex(RuntimeError, "authorized demo database"):
                    self.guarded(dbname)

    def test_seed_guard_rejects_non_demo_environment(self):
        with self.assertRaisesRegex(RuntimeError, "SC_ENVIRONMENT"):
            self.guarded("sc_demo", SC_ENVIRONMENT="production")
        with self.assertRaisesRegex(RuntimeError, "SC_ALLOW_DEMO_DATA"):
            self.guarded("sc_demo", SC_ALLOW_DEMO_DATA="0")

    def test_seed_guard_rejects_missing_demo_password(self):
        with self.assertRaisesRegex(RuntimeError, "SC_DEMO_USER_PASSWORD"):
            self.guarded("sc_demo", SC_DEMO_USER_PASSWORD="")

    def test_seed_guard_accepts_declared_demo_databases(self):
        for dbname in ("sc_demo", "sc_dev_demo", "sc_demo_rehearsal"):
            with self.subTest(dbname=dbname):
                self.guarded(dbname)

    def test_profile_starts_with_identity_and_ends_with_verify(self):
        registry = self.registry()
        steps = registry["_PROFILES"][self.PROFILE]
        self.assertEqual(steps[0], "demo_company_identity")
        self.assertEqual(steps[-1], "demo_90_verify")
        self.assertLess(steps.index("demo_85_passwords"), steps.index("demo_90_verify"))

    def test_replaying_the_profile_repeats_each_step_once_in_order(self):
        registry = self.registry()
        executed = []
        registry["_REGISTRY"].update({
            name: registry["SeedStep"](name, name, lambda env, name=name: executed.append(name))
            for name in registry["_PROFILES"][self.PROFILE]
        })
        env = SimpleNamespace(cr=SimpleNamespace(dbname="sc_demo"))
        with patch.dict(os.environ, self.DEMO_ENV, clear=False):
            first = registry["run_steps"](env, "profile:" + self.PROFILE)
            second = registry["run_steps"](env, "profile:" + self.PROFILE)
        self.assertEqual(first, registry["_PROFILES"][self.PROFILE])
        self.assertEqual(second, first)
        self.assertEqual(executed, first + second)

    def test_reseed_entries_restore_company_identity_before_loading(self):
        source = (ROOT / "tools/scenario_loader.py").read_text()
        tree = ast.parse(source)
        for name in ("load_base_seed", "load_scenario"):
            with self.subTest(function=name):
                node = next(n for n in tree.body
                            if isinstance(n, ast.FunctionDef) and n.name == name)
                body = ast.get_source_segment(source, node)
                self.assertIn("apply_demo_company_identity(env)", body)
                self.assertLess(body.index("apply_demo_company_identity(env)"),
                                body.index("convert_file") if "convert_file" in body else len(body))

    def test_only_the_identity_step_writes_the_company_name(self):
        for path in sorted((ROOT / "seed/steps").glob("*.py")):
            source = path.read_text()
            if path.name == "step_company_identity.py":
                continue
            self.assertNotIn('{"name": "Demo演示公司"}', source, path.name)
            self.assertNotIn('company.write({"name"', source, path.name)

    def test_existing_user_is_updated_instead_of_duplicated(self):
        class Users:
            def __init__(self, existing):
                self.existing = existing
                self.created = []
                self.updated = []

            def sudo(self):
                return self

            def search(self, domain, limit=None):
                return self.existing

            def create(self, values):
                self.created.append(values)
                return SimpleNamespace(id=99)

        user = SimpleNamespace(write=lambda values: updated.append(values))
        updated = []
        users = Users(user)
        env = self.Env({"res.users": users})
        ensure = function("step_10_users_demo.py", "_ensure_user",
                          _resolve_groups=lambda env, xmlids: [])
        ensure(env, "demo_full", "Demo", [], "123456", "zh_CN", "Asia/Shanghai")
        self.assertEqual(users.created, [])
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["password"], "123456")
        self.assertEqual(updated[0]["login"], "demo_full")
        self.assertEqual(users.search([("login", "=", "demo_full")], limit=1), user)

    def test_missing_user_is_created_with_the_demo_password(self):
        class Users:
            def __init__(self):
                self.created = []

            def sudo(self):
                return self

            def search(self, domain, limit=None):
                return False

            def create(self, values):
                self.created.append(values)
                return SimpleNamespace(id=100)

        users = Users()
        env = self.Env({"res.users": users})
        ensure = function("step_10_users_demo.py", "_ensure_user",
                          _resolve_groups=lambda env, xmlids: [])
        ensure(env, "demo_full", "Demo", [], "123456", "zh_CN", "Asia/Shanghai")
        self.assertEqual(len(users.created), 1)
        self.assertEqual(users.created[0]["password"], "123456")

    def test_existing_project_is_updated_instead_of_duplicated(self):
        company = SimpleNamespace(id=1)
        writes = []
        project = SimpleNamespace(
            id=7, company_id=company, project_code="DEMO-PJ-INIT",
            display_name="Demo", write=lambda values: writes.append(values),
        )
        created = []

        class Projects:
            @staticmethod
            def search(domain, limit=None):
                return project if domain[0] == ("project_code", "=", "DEMO-PJ-INIT") else False

            @staticmethod
            def create(values):
                created.append(values)
                return project

        env = self.Env(company=company)
        ensure = function("step_20_projects_demo.py", "_ensure_project",
                          business_model=lambda env, model: Projects,
                          prepare_project=lambda env, record: record,
                          UserError=ValueError)
        ensure(env, "DEMO-PJ-INIT", {"name": "Demo", "lifecycle_state": "closed"})
        self.assertEqual(created, [])
        self.assertEqual(len(writes), 1)
        self.assertNotIn("lifecycle_state", writes[0])
        self.assertEqual(writes[0]["project_code"], "DEMO-PJ-INIT")

    def test_new_project_enters_through_draft_lifecycle(self):
        company = SimpleNamespace(id=1)
        created = []
        project = SimpleNamespace(id=8, company_id=company, project_code="DEMO-PJ-NEW",
                                  display_name="Demo", write=lambda values: None)

        class Projects:
            @staticmethod
            def search(domain, limit=None):
                return False

            @staticmethod
            def create(values):
                created.append(values)
                return project

        env = self.Env(company=company)
        ensure = function("step_20_projects_demo.py", "_ensure_project",
                          business_model=lambda env, model: Projects,
                          prepare_project=lambda env, record: record,
                          UserError=ValueError)
        ensure(env, "DEMO-PJ-NEW", {"name": "Demo"})
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["lifecycle_state"], "draft")


if __name__ == "__main__":
    unittest.main()
