import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]
for package_name, package_path in (
    ("odoo", SMART_CORE_DIR.parent),
    ("odoo.addons", SMART_CORE_DIR.parent),
    ("odoo.addons.smart_core", SMART_CORE_DIR),
    ("odoo.addons.smart_core.delivery", SMART_CORE_DIR / "delivery"),
):
    package = sys.modules.setdefault(package_name, types.ModuleType(package_name))
    package.__path__ = [str(package_path)]


def _load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_load_module(
    "odoo.addons.smart_core.delivery.scene_shell_compiler",
    SMART_CORE_DIR / "delivery" / "scene_shell_compiler.py",
)
MODULE = _load_module(
    "odoo.addons.smart_core.delivery.navigation_contract_compiler",
    SMART_CORE_DIR / "delivery" / "navigation_contract_compiler.py",
)
NavigationContractCompiler = MODULE.NavigationContractCompiler


def _authority(*pairs):
    buckets = {
        "primary_actions": [],
        "role_home_actions": [],
        "contextual_actions": [],
        "admin_actions": [],
        "menu_containers": [],
        "denied_actions": [],
    }
    for menu_id, action_id in pairs:
        buckets["primary_actions"].append(
            {"menu_id": menu_id, "action_id": action_id}
        )
    return buckets


def _walk_pairs(nav):
    pairs = []

    def walk(nodes):
        for node in nodes:
            if node.get("action_id"):
                pairs.append((int(node.get("menu_id") or 0), int(node["action_id"])))
            walk(node.get("children") or [])

    walk(nav)
    return pairs


class FakeMenuService:
    def __init__(self, authority):
        self.authority = authority
        self.filter_calls = 0
        self.canonical_calls = 0
        self.authority_at_filter = None

    def build_route_authority(self, role_surface, *, nav):
        return copy.deepcopy(self.authority)

    def filter_route_authority_by_publication(self, authority, *, filter_nodes):
        result = copy.deepcopy(authority)
        filter_nodes(authority.get("primary_actions") or [])
        return result

    def filter_nav_by_route_authority(self, nav, authority):
        self.filter_calls += 1
        self.authority_at_filter = copy.deepcopy(authority)
        allowed = {
            (int(row["menu_id"]), int(row["action_id"]))
            for bucket in (
                "primary_actions",
                "role_home_actions",
                "contextual_actions",
                "admin_actions",
            )
            for row in authority.get(bucket) or []
        }
        return [
            copy.deepcopy(node)
            for node in nav
            if (int(node.get("menu_id") or 0), int(node.get("action_id") or 0))
            in allowed
        ]

    def project_canonical_navigation(self, nav, authority):
        self.canonical_calls += 1
        return copy.deepcopy(nav)

    def project_final_navigation_routes(self, nav, authority):
        result = copy.deepcopy(nav)
        for node in result:
            scene_key = node.get("scene_key")
            if scene_key:
                node["route"] = f"/s/{scene_key}"
                for bucket in (
                    "primary_actions",
                    "role_home_actions",
                    "contextual_actions",
                    "admin_actions",
                ):
                    for row in authority.get(bucket) or []:
                        if (
                            int(row.get("menu_id") or 0),
                            int(row.get("action_id") or 0),
                        ) == (
                            int(node.get("menu_id") or 0),
                            int(node.get("action_id") or 0),
                        ):
                            row["route"] = node["route"]
                            row["scene_key"] = scene_key
        return result, authority

    def project_navigation_product_policy(
        self,
        nav,
        *,
        product_key,
        edition_key,
        role_code,
        role_codes,
    ):
        return {
            "source": "scenarioized_navigation.nav",
            "entries": [
                {
                    "menu_id": int(node.get("menu_id") or 0),
                    "action_id": int(node.get("action_id") or 0),
                    "scene_key": str(node.get("scene_key") or ""),
                    "route": str(node.get("route") or ""),
                }
                for node in nav
            ],
        }


class NavigationContractCompilerTests(unittest.TestCase):
    def compile(self, authority, nav, *, scenario_provider=None, designed=()):
        service = FakeMenuService(_authority((999, 999)))
        def forbidden(*args, **kwargs):
            self.fail("projection recomputed effective authority")
        service.build_route_authority = forbidden
        service.filter_route_authority_by_publication = forbidden
        result = NavigationContractCompiler(
            service, scenario_surface_provider=scenario_provider or (lambda nav, authority: None),
            action_pair_walker=_walk_pairs,
        ).compile(nav=nav, effective_authority=authority, company_id=2,
                  delivery_payload={"product_key": "construction.standard"},
                  designed_scene_keys=designed)
        self.assertEqual(service.filter_calls, 1)
        self.assertEqual(service.canonical_calls, 1)
        return result

    def test_shared_qualification_is_not_recomputed_or_mutated(self):
        shared = _authority((10, 20), (30, 40))
        original = copy.deepcopy(shared)
        result = self.compile(shared, [{"menu_id": 10, "action_id": 20}, {"menu_id": 50, "action_id": 60}])
        self.assertEqual(_walk_pairs(result.nav), [(10, 20)])
        self.assertEqual(MODULE._authority_pairs(result.route_authority), {(10, 20), (30, 40)})
        self.assertEqual(shared, original)

    def test_all_resolved_authority_buckets_are_consumed(self):
        shared = _authority((10, 20))
        shared["contextual_actions"] = [{"menu_id": 30, "action_id": 40}]
        shared["admin_actions"] = [{"menu_id": 50, "action_id": 60}]
        nav = [{"menu_id": menu, "action_id": action} for menu, action in [(10, 20), (30, 40), (50, 60)]]
        result = self.compile(shared, nav)
        self.assertEqual(_walk_pairs(result.nav), [(10, 20), (30, 40), (50, 60)])
        self.assertEqual(result.route_authority["principal_scope"]["company_id"], 2)

    def test_resolved_tenant_selection_precedes_navigation(self):
        shared = _authority((30, 40))
        shared["scenario_composition"] = {"selected_by_menu": {"30": {"location": "scenario"}}}
        result = self.compile(shared, [{"menu_id": 10, "action_id": 20}, {"menu_id": 30, "action_id": 40}])
        self.assertEqual(_walk_pairs(result.nav), [(30, 40)])
        self.assertEqual(result.route_authority["scenario_composition"], shared["scenario_composition"])

    def test_missing_authority_cannot_fall_back_to_native_facts(self):
        with self.assertRaisesRegex(RuntimeError, "effective delivery authority"):
            self.compile(None, [{"menu_id": 10, "action_id": 20}])

    def test_designed_scene_route_is_shared_by_final_projections(self):
        nav = [{"menu_id": 10, "action_id": 20, "scene_key": "my_work.workspace"}]
        result = self.compile(_authority((10, 20)), nav, designed={"my_work.workspace"})
        self.assertEqual(result.nav[0]["route"], "/s/my_work.workspace")
        self.assertEqual(result.navigation["product_policy"]["entries"][0]["route"], "/s/my_work.workspace")
        self.assertEqual(result.route_authority["primary_actions"][0]["route"], "/s/my_work.workspace")

    def test_scenarioization_cannot_add_authority(self):
        def project(nav, authority):
            return {"nav": [{"menu_id": 10, "action_id": 20, "scene_key": "allowed"},
                            {"menu_id": 99, "action_id": 100, "scene_key": "forbidden"}]}
        with self.assertRaisesRegex(RuntimeError, "scenario navigation contains unauthorized"):
            self.compile(_authority((10, 20)), [{"menu_id": 10, "action_id": 20}],
                         scenario_provider=project, designed={"allowed", "forbidden"})


if __name__ == "__main__":
    unittest.main()
