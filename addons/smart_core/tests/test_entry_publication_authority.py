"""Execute route projection/validation with bounded publication and ORM doubles."""
import ast
import importlib.util
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_entry_target_module():
    path = ROOT / "core/navigation_entry_target.py"
    spec = importlib.util.spec_from_file_location("navigation_entry_target_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_entry_target_projection():
    return load_entry_target_module().build_web_surface_entry_target


def load_projection():
    path = ROOT / "delivery/menu_service.py"
    cls = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef) and node.name == "MenuService")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "filter_route_authority_by_publication")
    method.decorator_list = []
    scope = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), scope)
    return scope[method.name]


class Result:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_legacy_dict(self):
        return self.__dict__


class EntryPublicationTest(unittest.TestCase):
    def setUp(self):
        self.project = load_projection()
        self.authority = {"primary_actions": [
            {"action_id": 655, "menu_id": 507, "model": "plan", "route_kind": "PRIMARY_NAV"},
            {"action_id": 775, "menu_id": 545, "model": "payment", "route_kind": "PRIMARY_NAV"}],
            "admin_actions": [{"action_id": 711, "menu_id": 412, "model": "policy", "route_kind": "ADMIN_ROUTE"}],
            "denied_actions": [{"action_id": 999, "reason_code": "ACL_DENIED"}],
            "principal_scope": {"user_id": 34, "company_id": 8}}
        self.published = {775, 711}
        self.filter_nodes = lambda nodes: [node for node in nodes if node["meta"]["action_id"] in self.published]

    def test_unpublished_declaration_is_denied_without_mutating_source(self):
        before = deepcopy(self.authority)
        result = self.project(self.authority, filter_nodes=self.filter_nodes)
        self.assertEqual([row["action_id"] for row in result["primary_actions"]], [775])
        self.assertEqual(result["denied_actions"][-1]["reason_code"], "PRODUCT_ENTRY_NOT_RELEASED")
        self.assertEqual(result["denied_actions"][0]["reason_code"], "ACL_DENIED")
        self.assertEqual(self.authority, before)

    def test_unpublished_declaration_is_republished_as_a_denied_record(self):
        # The entry leaves an executable bucket: its route_kind must be DENIED
        # as well, otherwise the consumer (which validates bucket membership
        # against route_kind) rejects a legitimately unpublished entry.
        result = self.project(self.authority, filter_nodes=self.filter_nodes)
        denied = next(
            row for row in result["denied_actions"]
            if row.get("reason_code") == "PRODUCT_ENTRY_NOT_RELEASED"
        )
        self.assertEqual(denied["route_kind"], "DENIED")
        self.assertEqual(denied["action_id"], 655)
        self.assertEqual(denied["menu_id"], 507)
        self.assertEqual(denied["model"], "plan")

    def test_existing_configuration_exception_is_decided_by_shared_filter(self):
        result = self.project(self.authority, filter_nodes=self.filter_nodes)
        self.assertEqual(result["admin_actions"][0]["action_id"], 711)
        self.published.remove(711)
        self.assertEqual(self.project(self.authority, filter_nodes=self.filter_nodes)["admin_actions"], [])

    def test_filter_cannot_introduce_an_undeclared_route(self):
        result = self.project(self.authority, filter_nodes=lambda _: [{"key": "forged"}])
        self.assertEqual(result["primary_actions"], [])
        self.assertEqual(result["admin_actions"], [])

    def test_native_execution_surface_is_not_filtered_by_product_page_release(self):
        path = ROOT / "delivery/effective_delivery_service.py"
        cls = next(
            node
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.ClassDef)
            and node.name == "EffectiveDeliveryService"
        )
        method = next(
            node
            for node in cls.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_native_execution_surface"
        )
        method.decorator_list = []
        scope = {"deepcopy": deepcopy}
        exec(
            compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"),
            scope,
        )
        payload = {
            "nav": [{"menu_id": 507, "action_id": 655}],
            "route_authority": deepcopy(self.authority),
        }

        nav, authority = scope[method.name](payload)

        self.assertEqual(nav, payload["nav"])
        self.assertEqual(
            [row["action_id"] for row in authority["primary_actions"]],
            [655, 775],
        )
        self.assertNotIn(
            "PRODUCT_ENTRY_NOT_RELEASED",
            {row.get("reason_code") for row in authority["denied_actions"]},
        )

    def test_delivery_engine_builds_native_authority_before_product_nav_intersection(self):
        source = (ROOT / "delivery" / "delivery_engine.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "role_surface, nav=execution_nav,",
            source,
        )
        self.assertIn(
            "route_authority = self._merge_execution_targets(",
            source,
        )
        self.assertIn(
            "nav = self.menu_service.filter_nav_by_route_authority(\n"
            "                nav,\n"
            "                product_authority,\n"
            "            )",
            source,
        )

    def test_native_discovery_receives_acl_and_role_filtered_navigation(self):
        path = ROOT / "delivery" / "delivery_engine.py"
        cls = next(node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == "DeliveryEngine")
        build = next(node for node in cls.body
                     if isinstance(node, ast.FunctionDef) and node.name == "build")
        statements = [node for node in build.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id in
                              {"execution_nav", "native_authority"} for target in node.targets)]
        self.assertEqual(len(statements), 2)
        visible = [{"menu_id": 10}, {"menu_id": 20}]
        role = {"exposure_policy_declared": True}
        class Menus:
            def _authorization_native_nav(inner, surface, supplied):
                self.assertIs(surface, role)
                self.assertEqual(supplied, [])
                return visible
            def _filter_primary_native_nodes(inner, rows, surface):
                self.assertIs(rows, visible)
                self.assertIs(surface, role)
                return [rows[0]]
            def build_route_authority(inner, surface, *, nav):
                self.assertIs(surface, role)
                return {"primary_actions": list(nav)}
        scope = {"self": SimpleNamespace(menu_service=Menus()),
                 "role_surface": role, "native_nav": None}
        exec(compile(ast.Module(body=statements, type_ignores=[]), str(path), "exec"), scope)
        self.assertEqual(scope["native_authority"]["primary_actions"], [{"menu_id": 10}])

    def test_native_authority_merge_keeps_actions_outside_product_nav(self):
        path = ROOT / "delivery" / "delivery_engine.py"
        cls = next(
            node
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.ClassDef) and node.name == "DeliveryEngine"
        )
        method = next(
            node
            for node in cls.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_merge_execution_targets"
        )
        method.decorator_list = []
        scope = {"deepcopy": deepcopy}
        exec(
            compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"),
            scope,
        )
        result = scope[method.name](
            self.authority,
            {
                "primary_actions": [{
                    "menu_id": 545,
                    "action_id": 775,
                    "route": "/a/775?menu_id=545",
                }],
            },
        )
        self.assertEqual(
            [row["action_id"] for row in result["primary_actions"]],
            [655, 775],
        )
        self.assertEqual(result["primary_actions"][1]["route"], "/a/775?menu_id=545")

    def test_projection_preserves_scene_and_target_identity(self):
        self.authority["primary_actions"][1].update(scene_key="published.page", entry_target={"type": "scene"})
        seen = []
        def inspect(nodes):
            seen.extend(nodes)
            return self.filter_nodes(nodes)
        self.project(self.authority, filter_nodes=inspect)
        self.assertEqual(seen[1]["meta"]["entry_target"], {"type": "scene"})
        self.assertEqual(seen[1]["meta"]["scene_key"], "published.page")

    def handler(self, action_id, fail_closed=False, *, params=None, env=None, contracts=None):
        path = ROOT / "handlers/route_authority_validate.py"
        tree = ast.parse(path.read_text())
        class StripImports(ast.NodeTransformer):
            def visit_ImportFrom(self, node): return None
        nodes = [StripImports().visit(node) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        tests = self
        calls = []
        class Base:
            def __init__(self, env=None, su_env=None, request=None, context=None, payload=None):
                self.env, self.su_env, self.request, self.context = env, su_env, request, context
                self.params = (payload or {}).get("params", {})
        class ContractReader(Base):
            def handle(self):
                tests.contract_reads.append(self.params)
                return {"ok": True, "data": contracts[self.params["model"]]}
        tests.contract_reads = []
        # The validator must consume the one published authority instead of
        # deriving its own projection.  This double *is* that authority:
        # release-gated and publication-filtered, or empty when fail-closed.
        def build_runtime_route_authority(env):
            authority = {} if fail_closed else tests.project(
                tests.authority, filter_nodes=tests.filter_nodes)
            calls.append({"env": env, "authority": authority})
            return authority
        relation_scope = {}
        exec(compile((ROOT / "core/relation_action_authority.py").read_text(), "relation_action_authority.py", "exec"), relation_scope)
        scope = {"BaseIntentHandler": Base, "UiContractV2Handler": ContractReader,
            "positive_relation_id": relation_scope["positive_relation_id"],
            "validate_relation_action_origin": relation_scope["validate_relation_action_origin"],
            "IntentExecutionResult": Result,
            "build_runtime_route_authority": build_runtime_route_authority}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
        handler = scope["RouteAuthorityValidateHandler"]()
        handler.env = env if env is not None else SimpleNamespace(user=object())
        handler.params = params if params is not None else {"action_id": action_id}
        return handler.handle(), calls

    def native_role_authority(self, *, batch_fails=False, released_policy=False,
                              returned_xmlid=None, singleton_fails=False,
                              allowed_xmlid_missing=False, policy_failure=None,
                              same_id_other_model=False, declared_bucket=None):
        """Real admission methods; doubles supply only native ORM facts."""
        import runpy
        path = ROOT / "delivery/menu_service.py"
        cls = next(n for n in ast.parse(path.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == "MenuService")
        scope = vars(load_entry_target_module()).copy()
        scope["MenuFactService"] = SimpleNamespace(ACTION_MODELS={"ir.actions.act_window", "ir.actions.server"})
        tree = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), cls], type_ignores=[])
        exec(compile(ast.fix_missing_locations(tree), str(path), "exec"), scope)
        role = deepcopy(runpy.run_path(str(ROOT.parent / "smart_construction_core/core_extension_policy_maps.py"))["ROLE_SURFACE_OVERRIDES"]["finance"])
        role.update(role_code="finance", exposure_policy_declared=True)
        self.assertIn("smart_construction_core.action_sc_plan", role["action_blocklist_xmlids"])

        class Record(SimpleNamespace):
            def sudo(self): return self
            def exists(self): return self
            def get_external_id(self):
                if singleton_fails: raise RuntimeError("singleton metadata unavailable")
                return {self.id: self.xmlid}
        actions = {
            ident: Record(id=ident, xmlid=xmlid, _name="ir.actions.act_window",
                          name="Plan", active=True, groups_id=[], res_model="sc.plan",
                          view_mode="tree,form", view_id=None, domain="[]", context="{}")
            for ident, xmlid in ((601, "smart_construction_core.action_sc_plan"),
                                (602, "tenant.action_allowed"))}
        class ActionModel:
            def sudo(self): return self
            def browse(self, ids):
                if isinstance(ids, int): return actions[ids]
                class Batch:
                    def get_external_id(self):
                        if batch_fails: raise RuntimeError("batch unavailable")
                        return {ident: actions[ident].xmlid for ident in ids}
                return Batch()
        class Env(dict):
            user = SimpleNamespace(id=34, groups_id=[])
            company = SimpleNamespace(id=8)
            def ref(self, xmlid, raise_if_not_found=False):
                if xmlid == "smart_construction_core.action_sc_plan_report" and policy_failure:
                    if policy_failure == "error": raise RuntimeError("policy identity unavailable")
                    if policy_failure == "missing": return None
                    return Record(id=900, _name="res.users")
                return refs.get(xmlid)
        facts = [dict(menu_id=mid, menu_xmlid=xmlid, name="Plan", action_id=aid,
                      action_model="ir.actions.act_window", action_exists=True,
                      action_meta=dict(res_model="sc.plan", view_mode="tree,form", context="{}"), children=[])
                 for mid, xmlid, aid in ((501, "smart_construction_core.menu_sc_plan", 601),
                                         (502, "tenant.menu_plan_alias", 601),
                                         (503, "tenant.menu_allowed_alias", 602))]
        refs = {row["menu_xmlid"]: Record(id=row["menu_id"], _name="ir.ui.menu", active=True,
                                         groups_id=[], action=actions[row["action_id"]]) for row in facts}
        refs.update({record.xmlid: record for record in actions.values()})
        refs["legacy.action_plan_original"] = actions[601]
        refs["smart_construction_core.action_sc_plan_report"] = Record(
            id=602 if same_id_other_model else 603,
            _name="ir.actions.server" if same_id_other_model else "ir.actions.act_window")
        if returned_xmlid is not None:
            actions[601].xmlid = returned_xmlid
        if allowed_xmlid_missing:
            actions[602].xmlid = ""

        env = Env({"ir.actions.act_window": ActionModel(), "ir.actions.actions": ActionModel(),
                   "res.groups": [], "sc.plan": SimpleNamespace(check_access_rights=lambda *a, **kw: True)})
        if declared_bucket == "role_home_actions":
            role["role_home_menu_xmlids"] = ["tenant.menu_plan_alias", "tenant.menu_allowed_alias"]
        elif declared_bucket:
            field = {"contextual_actions": "contextual_action_authorities",
                     "admin_actions": "admin_action_authorities"}[declared_bucket]
            role[field] = [
                {"menu_xmlid": "tenant.menu_plan_alias", "action_xmlid": "legacy.action_plan_original"},
                {"menu_xmlid": "tenant.menu_allowed_alias", "action_xmlid": "tenant.action_allowed"},
            ]
        service = scope["MenuService"].__new__(scope["MenuService"])
        service.env = env
        self.native_service, self.native_role = service, role
        service._menu_fact_cache = {kind: SimpleNamespace(tree=facts, flat=facts) for kind in ("visible", "authorized")}
        service._group_xmlid_cache = {}
        native = service._authorization_native_nav(role, [])
        nav = service._filter_primary_native_nodes(native, role)
        self.assertIn((502, 601), list(service._walk_nav_action_refs(nav)))
        if released_policy:
            # Released policy can carry inactive native menus with explicit
            # action identities. Force the separate policy admission path.
            service._menu_fact_cache["visible"] = SimpleNamespace(tree=[], flat=[])
            for node in nav:
                node["action_xmlid"] = ("legacy.action_plan_original" if node["action_id"] == 601
                                        else "tenant.action_allowed")
                refs[node["menu_xmlid"]].active = False
        authority = service.build_route_authority(role, nav=nav)
        scene = runpy.run_path(str(ROOT.parent / "smart_construction_scene/services/business_scene_enablement.py"))
        surface = {row["menu_xmlid"]: {"location": "scenario", "scenario_key": "published.plan",
                    "scenario_active": True, "menu_id": row["menu_id"]} for row in facts}
        self.authority = scene["filter_business_authority"](authority, surface_index=surface,
            enabled={"published.plan": True}, entries=[], company_id=8,
            menu_xmlids_by_id={row["menu_id"]: row["menu_xmlid"] for row in facts})
        # Both targets are published, so release filtering cannot mask a role grant.
        self.published = {601, 602}
        return self.authority

    def test_native_role_allows_unblocked_action_through_enabled_scene(self):
        authority = self.native_role_authority()
        allowed = next(row for row in authority["primary_actions"] if row["action_id"] == 602)
        self.assertEqual(allowed["route_kind"], "DISCOVERED_PRIMARY_NAV")
        result, _ = self.handler(602, params={"action_id": 602, "menu_id": 503})
        self.assertTrue(result.ok)
        self.assertTrue(result.data["allowed"])

    def test_native_role_blocks_action_alias_through_enabled_scene(self):
        for batch_fails in (False, True):
            with self.subTest(batch_fails=batch_fails):
                authority = self.native_role_authority(batch_fails=batch_fails)
                result, _ = self.handler(601, params={"action_id": 601, "menu_id": 502})
                self.assertFalse(result.ok)
                self.assertEqual(result.error["reason_code"], "ROUTE_ACTION_NOT_AUTHORIZED")
                for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
                    self.assertNotIn(601, [row["action_id"] for row in authority[bucket]])

    def test_released_policy_fallback_preserves_role_action_blocklist(self):
        authority = self.native_role_authority(released_policy=True)
        allowed = next(row for row in authority["primary_actions"] if row["action_id"] == 602)
        self.assertEqual(allowed["route_kind"], "PRIMARY_NAV")
        result, _ = self.handler(602, params={"action_id": 602, "menu_id": 503})
        self.assertTrue(result.ok)
        self.assertTrue(result.data["allowed"])
        result, _ = self.handler(601, params={"action_id": 601, "menu_id": 502})
        self.assertFalse(result.ok)
        self.assertEqual(result.error["reason_code"], "ROUTE_ACTION_NOT_AUTHORIZED")
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            self.assertNotIn(601, [row["action_id"] for row in authority[bucket]])

    def test_role_action_identity_survives_alias_and_metadata_failure(self):
        for released_policy in (False, True):
            for batch_fails, singleton_fails, xmlid in (
                (False, False, "legacy.action_plan_original"),
                (True, False, "legacy.action_plan_original"),
                (True, True, "legacy.action_plan_original"),
                (False, False, ""),
            ):
                with self.subTest(policy=released_policy, batch=batch_fails,
                                  singleton=singleton_fails, xmlid=xmlid):
                    authority = self.native_role_authority(
                        released_policy=released_policy, batch_fails=batch_fails,
                        singleton_fails=singleton_fails, returned_xmlid=xmlid,
                        allowed_xmlid_missing=True)
                    denied, _ = self.handler(601, params={"action_id": 601, "menu_id": 502})
                    self.assertFalse(denied.ok)
                    self.assertEqual(denied.error["reason_code"], "ROUTE_ACTION_NOT_AUTHORIZED")
                    for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
                        self.assertNotIn(601, [row["action_id"] for row in authority[bucket]])
                    self.assertTrue(any(row.get("reason_code") == "ROLE_ACTION_BLOCKED"
                                        and row["action_id"] == 601 for row in authority["denied_actions"]))
                    allowed, _ = self.handler(602, params={"action_id": 602, "menu_id": 503})
                    self.assertTrue(allowed.ok)
                    self.assertTrue(allowed.data["allowed"])
                    self.assertEqual(next(row for row in authority["primary_actions"]
                                          if row["action_id"] == 602)["action_model"], "ir.actions.act_window")

    def test_unresolved_role_action_policy_is_explicitly_denied(self):
        for released_policy in (False, True):
            for failure in ("missing", "error", "wrong_model"):
                with self.subTest(policy=released_policy, failure=failure):
                    authority = self.native_role_authority(
                        released_policy=released_policy, returned_xmlid="legacy.action_plan_original",
                        policy_failure=failure)
                    for action_id, menu_id in ((601, 502), (602, 503)):
                        result, _ = self.handler(action_id, params={"action_id": action_id, "menu_id": menu_id})
                        self.assertFalse(result.ok)
                        self.assertEqual(result.error["reason_code"], "ROUTE_ACTION_NOT_AUTHORIZED")
                    denied = next(row for row in authority["denied_actions"] if row["action_id"] == 602)
                    self.assertEqual(denied["reason_code"], "ROLE_ACTION_POLICY_UNRESOLVED")
                    self.assertIn("smart_construction_core.action_sc_plan_report", denied["unresolved_action_xmlids"])

    def test_role_action_identity_is_model_scoped(self):
        for released_policy in (False, True):
            with self.subTest(policy=released_policy):
                self.native_role_authority(released_policy=released_policy,
                                           same_id_other_model=True, allowed_xmlid_missing=True)
                result, _ = self.handler(602, params={"action_id": 602, "menu_id": 503})
                self.assertTrue(result.ok)
                self.assertTrue(result.data["allowed"])

    def test_declared_role_action_buckets_share_identity_admission(self):
        for bucket in ("role_home_actions", "contextual_actions", "admin_actions"):
            with self.subTest(bucket=bucket):
                authority = self.native_role_authority(
                    declared_bucket=bucket, returned_xmlid="legacy.action_plan_original")
                self.assertIn(602, [row["action_id"] for row in authority[bucket]])
                for executable in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
                    self.assertNotIn(601, [row["action_id"] for row in authority[executable]])
                result, _ = self.handler(601, params={"action_id": 601, "menu_id": 502})
                self.assertFalse(result.ok)
                self.assertEqual(result.error["reason_code"], "ROUTE_ACTION_NOT_AUTHORIZED")
                result, _ = self.handler(602, params={"action_id": 602, "menu_id": 503})
                self.assertTrue(result.ok)
                self.assertTrue(result.data["allowed"])

    def test_role_action_identity_closes_all_executable_buckets(self):
        self.native_role_authority(returned_xmlid="legacy.action_plan_original")
        buckets = {name: [
            {"action_id": 601, "action_model": "ir.actions.act_window", "action_xmlid": "legacy.action_plan_original"},
            {"action_id": 602, "action_model": "ir.actions.act_window", "action_xmlid": ""},
            {"action_id": 604},
            {"action_id": 0, "entry_target": {"type": "scene", "scene_key": "published.plan"}},
        ] for name in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")}
        buckets["denied_actions"] = []
        self.native_service._apply_role_action_blocklist(buckets, self.native_role)
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            self.assertEqual([row["action_id"] for row in buckets[bucket]], [602, 0])
        self.assertEqual([row["reason_code"] for row in buckets["denied_actions"]].count("ROLE_ACTION_BLOCKED"), 4)
        self.assertEqual([row["reason_code"] for row in buckets["denied_actions"]].count("ROLE_ACTION_IDENTITY_UNRESOLVED"), 4)
        self.assertTrue(all(row["allowed_operation"] == "none" for row in buckets["denied_actions"]))
        # An absent policy adds no implicit identity requirement.
        unrestricted = {name: [{"action_id": 602}] for name in buckets}
        before = deepcopy(unrestricted)
        self.native_service._apply_role_action_blocklist(unrestricted, {})
        self.assertEqual(unrestricted, before)

    def test_runtime_validator_rejects_unpublished_declared_action(self):
        result, calls = self.handler(655)
        self.assertFalse(result.ok)
        self.assertEqual(result.error["reason_code"], "PRODUCT_ENTRY_NOT_RELEASED")
        # A role-surface-declared action that the publication excludes is
        # denied through the one published authority, never a local
        # release-gate re-derivation (locked in the authority-owner test).
        self.assertEqual(len(calls), 1, "the validator must consume the published authority")

    def test_runtime_validator_keeps_published_action(self):
        result, _ = self.handler(775)
        self.assertTrue(result.ok); self.assertEqual(result.data["model"], "payment")

    def test_runtime_validator_consumes_the_single_published_authority(self):
        result, calls = self.handler(775)
        self.assertTrue(result.ok)
        self.assertEqual(len(calls), 1, "one published authority consumption per validate")
        # The consumed authority is the release-gated, publication-filtered
        # projection: 655 is declared in the role surface yet absent here.
        self.assertEqual([row["action_id"] for row in calls[0]["authority"]["primary_actions"]], [775])

    def test_navigation_projection_preserves_release_keys(self):
        path = ROOT / "delivery/menu_service.py"
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == "MenuService")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_nav_target_index")
        method.decorator_list = []
        menus = SimpleNamespace(_node_route_menu_id=lambda node: node.get("menu_id", 0))
        target_api = load_entry_target_module()
        scope = {
            "MenuService": menus,
            "derive_entry_route": target_api.derive_entry_route,
            "target_route": target_api.target_route,
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), scope)
        menus._nav_target_index = scope[method.name]
        node = {"key": "published.aggregate", "menu_id": 42, "meta": {"action_id": 775,
                "business_category_options": [{"menu_id": 43, "menu_xmlid": "product.category"}]}}
        target = menus._nav_target_index([node])[(42, 775)]
        self.assertEqual(target["menu_key"], "published.aggregate")
        self.assertEqual(target["business_category_options"], node["meta"]["business_category_options"])
        # Execute the real publication key reader after route projection.
        path = ROOT / "delivery/effective_delivery_inputs.py"
        key_reader = next(n for n in ast.parse(path.read_text()).body
                          if isinstance(n, ast.FunctionDef) and n.name == "_node_release_gate_keys")
        scope = {"_text": lambda value: str(value or "").strip()}
        exec(compile(ast.Module(body=[key_reader], type_ignores=[]), str(path), "exec"), scope)
        authority = {"primary_actions": [{"action_id": 775, "menu_id": 42, **target}]}
        for release_key in ("published.aggregate", "product.category", "system.menu_43"):
            result = self.project(authority, filter_nodes=lambda nodes: [
                row for row in nodes if release_key in scope["_node_release_gate_keys"](row)])
            self.assertEqual(len(result["primary_actions"]), 1, release_key)

    def test_shared_normalizer_resolves_current_refs_and_preserves_scene(self):
        path = ROOT / "delivery/delivery_engine.py"
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == "DeliveryEngine")
        names = {"_normalize_entry_target_refs", "_normalize_delivery_nav_node_refs", "_normalize_delivery_nav_refs"}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        target_api = load_entry_target_module()
        scope = {
            "_text": lambda v: str(v or "").strip(),
            "_to_int": lambda v: int(v or 0),
            "build_web_surface_entry_target": target_api.build_web_surface_entry_target,
            "derive_entry_route": target_api.derive_entry_route,
            "target_route": target_api.target_route,
        }
        target_class = ast.ClassDef(name="Normalizer", bases=[], keywords=[], body=methods, decorator_list=[])
        tree = ast.fix_missing_locations(ast.Module(body=[target_class], type_ignores=[]))
        exec(compile(tree, str(path), "exec"), scope)
        normalizer = scope["Normalizer"]()
        records = {"product.menu": SimpleNamespace(id=42, active=True),
                   "product.action": SimpleNamespace(id=775, _name="ir.actions.act_window", res_model="test.document", view_mode="tree,form")}
        normalizer._resolve_xmlid_record = lambda xmlid, **kwargs: records.get(xmlid)
        for route in ("/a/1", "/s/published.page"):
            node = {"meta": {"menu_xmlid": "product.menu", "action_xmlid": "product.action",
                    "menu_id": 1, "action_id": 1, "route": route,
                    "entry_target": {"type": "scene", "scene_key": "published.page"}}}
            result = normalizer._normalize_delivery_nav_refs([node])[0]
            self.assertEqual(result["menu_id"], 42)
            self.assertEqual(result["meta"]["action_id"], 775)
            # A resolved scene target owns the final route even when the incoming
            # node still carries a stale action route.
            self.assertEqual(result["meta"]["route"], "/s/published.page")
            self.assertEqual(result["meta"]["entry_target"]["scene_key"], "published.page")
            self.assertEqual(result["meta"]["entry_target"]["compatibility_refs"]["model"], "test.document")
            self.assertEqual(result["entry_target"], result["meta"]["entry_target"])

    def test_shared_normalizer_syncs_declared_admin_surface_to_node_target(self):
        path = ROOT / "delivery/delivery_engine.py"
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == "DeliveryEngine")
        names = {"_normalize_entry_target_refs", "_normalize_delivery_nav_node_refs", "_normalize_delivery_nav_refs"}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        target_api = load_entry_target_module()
        scope = {
            "_text": lambda v: str(v or "").strip(),
            "_to_int": lambda v: int(v or 0),
            "build_web_surface_entry_target": target_api.build_web_surface_entry_target,
            "derive_entry_route": target_api.derive_entry_route,
            "target_route": target_api.target_route,
        }
        target_class = ast.ClassDef(name="Normalizer", bases=[], keywords=[], body=methods, decorator_list=[])
        tree = ast.fix_missing_locations(ast.Module(body=[target_class], type_ignores=[]))
        exec(compile(tree, str(path), "exec"), scope)
        normalizer = scope["Normalizer"]()
        records = {
            "config.menu": SimpleNamespace(id=431, active=True),
            "config.action": SimpleNamespace(
                id=806, _name="ir.actions.act_window", res_model="ui.business.config.contract",
                view_mode="tree,form",
                context="{'sc_web_surface': 'business_config'}",
            ),
        }
        normalizer._resolve_xmlid_record = lambda xmlid, **kwargs: records.get(xmlid)
        stale = {"type": "compatibility", "route": "/a/806?menu_id=431",
                 "compatibility_refs": {"menu_id": 431, "action_id": 806}}
        node = {"menu_id": 431, "route": "/a/806?menu_id=431", "entry_target": dict(stale),
                "meta": {"menu_xmlid": "config.menu", "action_xmlid": "config.action",
                         "menu_id": 431, "action_id": 806, "route": "/a/806?menu_id=431",
                         "entry_target": dict(stale)}}
        result = normalizer._normalize_delivery_nav_refs([node])[0]
        self.assertEqual(result["entry_target"], result["meta"]["entry_target"])
        self.assertEqual(result["entry_target"]["type"], "admin_surface")
        self.assertEqual(result["entry_target"]["surface"], "business_config")
        self.assertEqual(result["entry_target"]["route"], "/admin/business-config")

    def test_runtime_validator_obeys_failed_publication_authority(self):
        result, _ = self.handler(775, fail_closed=True)
        self.assertFalse(result.ok)


class RelationReadRouteTest(unittest.TestCase):
    handler = EntryPublicationTest.handler

    def setUp(self):
        EntryPublicationTest.setUp(self)
        self.calls = []
        calls = self.calls
        class Record:
            def __init__(self, model, record_id):
                self.model, self.id = model, record_id
                self._fields = {'partner': SimpleNamespace(type='many2one', comodel_name='partner')}
                self.link_ids = [56]
                self.denied = ''
                self.present = True
            def browse(self, record_id):
                if record_id != self.id: raise ValueError('wrong record')
                return self
            def exists(self): return self if self.present else None
            def check_access_rights(self, mode):
                calls.append((self.model, 'acl', mode))
                if self.denied == 'acl': raise PermissionError('denied')
            def check_access_rule(self, mode):
                calls.append((self.model, 'rule', mode))
                if self.denied == 'rule': raise PermissionError('denied')
            def check_field_access_rights(self, mode, fields):
                calls.append((self.model, 'fields', mode, fields))
                if self.denied == 'fields': raise PermissionError('denied')
            def __getitem__(self, name): return SimpleNamespace(ids=self.link_ids)
        class Env(dict):
            user = object()
        self.parent, self.child = Record('payment', 1813), Record('partner', 56)
        self.env = Env(payment=self.parent, partner=self.child)
        self.origin = dict(model='payment', record_id=1813, field='partner', action_id=775, menu_id=545)
        self.params = dict(model='partner', record_id=56, action_id=324, menu_id=164,
            route_path='/r/partner/56', access_mode='read', render_profile='readonly', relation_origin=self.origin)
        self.entry = dict(model='partner', action_id=324, menu_id=164, can_read=True, can_open=True)
        status = {'globalStatus': {'effectiveRecordCapabilities': {'read': True}}}
        self.contracts = {'payment': {'statusContract': deepcopy(status), 'layoutContract': {'children': [
            {'type':'field', 'name':'partner', 'fieldInfo':{'relation_entry':self.entry}}]}},
            'partner': {'statusContract':deepcopy(status)}}

    def validate(self):
        return self.handler(324, params=self.params, env=self.env, contracts=self.contracts)[0]

    def test_exact_unpublished_child_read_uses_fresh_published_parent_and_child_checks(self):
        before = deepcopy(self.authority)
        result = self.validate()
        self.assertTrue(result.ok)
        self.assertEqual(result.data, {key:value for key,value in self.params.items() if key != 'relation_origin'} | {'allowed':True})
        self.assertEqual([row['model'] for row in self.contract_reads], ['payment', 'partner'])
        self.assertTrue(all(row['render_profile'] == 'readonly' for row in self.contract_reads))
        for model in ('payment', 'partner'):
            self.assertIn((model, 'acl', 'read'), self.calls)
            self.assertIn((model, 'rule', 'read'), self.calls)
        self.assertIn(('payment', 'fields', 'read', ['partner']), self.calls)
        self.assertIn(('partner', 'fields', 'read', None), self.calls)
        self.assertEqual(self.authority, before)

    def test_non_read_record_paths_and_mixed_origins_never_load_contracts(self):
        for key, value in [('route_path','/f/partner/56'), ('route_path','/r/partner/new'),
                           ('route_path','/a/324'), ('access_mode','write'), ('render_profile','edit'),
                           ('work_item_origin',{}), ('model','other')]:
            with self.subTest(key=key):
                original = deepcopy(self.params)
                self.params[key] = value
                self.assertFalse(self.validate().ok)
                self.assertEqual(self.contract_reads, [])
                self.params = original

    def test_strict_target_and_origin_ids_reject_coercions(self):
        for value in [True, 56.0, 56.5, '56.0', '056', [], {}, 9007199254740992]:
            for location, key in [(self.params, 'record_id'), (self.origin, 'record_id')]:
                original = location[key]; location[key] = value
                self.assertFalse(self.validate().ok, (key, value))
                location[key] = original

    def test_target_menu_action_and_fresh_can_open_must_match(self):
        for key, value in [('action_id',999), ('menu_id',999), ('model','other'), ('can_open',False), ('can_read',False)]:
            original = self.entry[key]; self.entry[key] = value
            self.assertFalse(self.validate().ok, key)
            self.entry[key] = original

    def test_revoked_parent_link_acl_field_or_child_rights_fail_closed(self):
        self.parent.link_ids = [99]
        self.assertFalse(self.validate().ok)
        self.parent.link_ids = [56]
        for record in (self.parent, self.child):
            for reason in ('acl', 'rule', 'fields'):
                record.denied = reason
                self.assertFalse(self.validate().ok, (record.model, reason))
            record.denied = ''
        self.child.present = False
        self.assertFalse(self.validate().ok)
        self.child.present = True
        self.contracts['partner']['statusContract']['globalStatus']['effectiveRecordCapabilities']['read'] = False
        self.assertFalse(self.validate().ok)

    def test_unpublished_or_contextual_parent_cannot_borrow_target_context(self):
        self.published.remove(775)
        self.assertFalse(self.validate().ok)
        self.published.add(775)
        self.authority['primary_actions'][1]['context_requirements'] = {'required_query':['project_id']}
        self.params['project_id'] = 10
        self.assertFalse(self.validate().ok)
        self.assertEqual(self.contract_reads, [])


if __name__ == "__main__":
    unittest.main()
