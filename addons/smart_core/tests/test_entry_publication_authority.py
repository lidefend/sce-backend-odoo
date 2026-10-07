"""Execute route projection/validation with bounded publication and ORM doubles."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


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

    def test_existing_configuration_exception_is_decided_by_shared_filter(self):
        result = self.project(self.authority, filter_nodes=self.filter_nodes)
        self.assertEqual(result["admin_actions"][0]["action_id"], 711)
        self.published.remove(711)
        self.assertEqual(self.project(self.authority, filter_nodes=self.filter_nodes)["admin_actions"], [])

    def test_filter_cannot_introduce_an_undeclared_route(self):
        result = self.project(self.authority, filter_nodes=lambda _: [{"key": "forged"}])
        self.assertEqual(result["primary_actions"], [])
        self.assertEqual(result["admin_actions"], [])

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
        scope = {"MenuService": menus}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), scope)
        menus._nav_target_index = scope[method.name]
        node = {"key": "published.aggregate", "menu_id": 42, "meta": {"action_id": 775,
                "business_category_options": [{"menu_id": 43, "menu_xmlid": "product.category"}]}}
        target = menus._nav_target_index([node])[(42, 775)]
        self.assertEqual(target["menu_key"], "published.aggregate")
        self.assertEqual(target["business_category_options"], node["meta"]["business_category_options"])
        # Execute the real publication key reader after route projection.
        path = ROOT / "handlers/system_init.py"
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
        scope = {"_text": lambda v: str(v or "").strip(), "_to_int": lambda v: int(v or 0)}
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
            self.assertEqual(result["meta"]["route"], route if route.startswith("/s/") else "/a/775?menu_id=42")
            self.assertEqual(result["meta"]["entry_target"]["scene_key"], "published.page")
            self.assertEqual(result["meta"]["entry_target"]["compatibility_refs"]["model"], "test.document")

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
