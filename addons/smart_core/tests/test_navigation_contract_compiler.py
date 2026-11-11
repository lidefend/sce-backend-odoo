import copy
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "delivery"
    / "navigation_contract_compiler.py"
)
SPEC = importlib.util.spec_from_file_location(
    "navigation_contract_compiler_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
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
    def _compiler(self, service, *, scenario_provider=None):
        return NavigationContractCompiler(
            service,
            scenario_surface_provider=scenario_provider or (lambda nav, authority: None),
            platform_duty_merger=lambda authority, surface: {
                **authority,
                "admin_actions": list(authority.get("admin_actions") or [])
                + [{"menu_id": 50, "action_id": 60, "source": "platform_duty"}],
            },
            release_node_filter=lambda nodes: nodes,
            action_pair_walker=_walk_pairs,
        )

    def test_all_authority_producers_complete_before_one_nav_filter(self):
        service = FakeMenuService(_authority((10, 20)))
        nav = [
            {"menu_id": 10, "action_id": 20},
            {"menu_id": 30, "action_id": 40},
            {"menu_id": 50, "action_id": 60},
        ]
        compilation = self._compiler(service).compile(
            nav=nav,
            role_surface={"role_code": "project_member"},
            delivery_payload={"product_key": "construction.standard"},
            release_gate={},
            platform_duty={"user_id": 9},
            scene_internal_actions={
                "internal": {"menu_id": 30, "action_id": 40, "scene_key": "work"}
            },
            company_id=2,
        )
        self.assertEqual(service.filter_calls, 1)
        self.assertEqual(service.canonical_calls, 1)
        self.assertEqual(
            {(row["menu_id"], row["action_id"]) for row in service.authority_at_filter["contextual_actions"]},
            {(30, 40)},
        )
        self.assertEqual(
            {(row["menu_id"], row["action_id"]) for row in service.authority_at_filter["admin_actions"]},
            {(50, 60)},
        )
        self.assertEqual(
            [(row["menu_id"], row["action_id"]) for row in compilation.nav],
            [(10, 20), (30, 40), (50, 60)],
        )
        self.assertEqual(
            compilation.navigation["route_authority"]["principal_scope"]["company_id"],
            2,
        )

    def test_scenarioization_derives_route_and_product_policy_from_same_nav(self):
        service = FakeMenuService(_authority((10, 20)))
        nav = [{"menu_id": 10, "action_id": 20, "label": "My Work"}]

        def scenario_provider(current_nav, authority):
            scenario_nav = copy.deepcopy(current_nav)
            scenario_nav[0]["scene_key"] = "my_work.workspace"
            return {"ok": True, "nav": scenario_nav}

        compilation = self._compiler(
            service,
            scenario_provider=scenario_provider,
        ).compile(
            nav=nav,
            role_surface={"role_code": "business_full"},
            delivery_payload={
                "product_key": "construction.standard",
                "role_codes": ["business_full"],
            },
            release_gate={},
            platform_duty=None,
            scene_internal_actions=None,
            company_id=1,
        )
        self.assertEqual(compilation.nav[0]["route"], "/s/my_work.workspace")
        self.assertEqual(
            compilation.navigation["product_policy"]["entries"][0]["route"],
            "/s/my_work.workspace",
        )
        self.assertEqual(
            compilation.navigation["route_authority"]["primary_actions"][0]["route"],
            "/s/my_work.workspace",
        )

    def test_scenarioization_cannot_add_authority(self):
        service = FakeMenuService(_authority((10, 20)))

        def scenario_provider(current_nav, authority):
            return {
                "nav": [
                    {"menu_id": 10, "action_id": 20, "scene_key": "allowed"},
                    {"menu_id": 99, "action_id": 100, "scene_key": "forbidden"},
                ]
            }

        with self.assertRaisesRegex(
            RuntimeError,
            "scenario navigation contains unauthorized menu/action pairs",
        ):
            self._compiler(
                service,
                scenario_provider=scenario_provider,
            ).compile(
                nav=[{"menu_id": 10, "action_id": 20}],
                role_surface={"role_code": "business_full"},
                delivery_payload={"product_key": "construction.standard"},
                release_gate={},
                platform_duty=None,
                scene_internal_actions=None,
                company_id=1,
            )


if __name__ == "__main__":
    unittest.main()
