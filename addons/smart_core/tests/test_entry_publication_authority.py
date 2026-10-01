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

    def handler(self, action_id, fail_closed=False):
        path = ROOT / "handlers/route_authority_validate.py"
        tree = ast.parse(path.read_text())
        class StripImports(ast.NodeTransformer):
            def visit_ImportFrom(self, node): return None
        nodes = [StripImports().visit(node) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        tests = self
        calls = []
        class Menus:
            def __init__(self, env): pass
            def build_route_authority(self, surface): return tests.authority
            filter_route_authority_by_publication = staticmethod(tests.project)
        class Policies:
            def __init__(self, env): pass
            def get_policy(self, **kwargs): calls.append(kwargs); return {"product_key": "construction.standard"}
        identity = {"product_key": "construction.standard", "base_product_key": "construction", "edition_key": "standard"}
        scope = {"BaseIntentHandler": object, "IntentExecutionResult": Result, "MenuService": Menus,
            "IdentityResolver": lambda env: SimpleNamespace(user_group_xmlids=lambda user: [], build_role_surface=lambda *args: {"role_code": "config"}),
            "ProductPolicyService": Policies, "_resolve_startup_delivery_identity": lambda *args: identity,
            "_load_platform_release_gate": lambda *args, **kwargs: {"applied": True, "fail_closed": fail_closed},
            "_filter_nav_by_release_gate": lambda nodes, *args, **kwargs: (tests.filter_nodes(nodes), {})}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
        handler = scope["RouteAuthorityValidateHandler"]()
        handler.env = SimpleNamespace(user=object()); handler.params = {"action_id": action_id}
        return handler.handle(), calls

    def test_runtime_validator_rejects_unpublished_declared_action(self):
        result, calls = self.handler(655)
        self.assertFalse(result.ok)
        self.assertEqual(result.error["reason_code"], "PRODUCT_ENTRY_NOT_RELEASED")
        self.assertTrue(calls[0]["enforce_release"] and calls[0]["enforce_access"])
        self.assertEqual(calls[0]["product_key"], "construction.standard")

    def test_runtime_validator_keeps_published_action(self):
        result, _ = self.handler(775)
        self.assertTrue(result.ok); self.assertEqual(result.data["model"], "payment")

    def test_runtime_validator_obeys_failed_publication_authority(self):
        result, _ = self.handler(775, fail_closed=True)
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
