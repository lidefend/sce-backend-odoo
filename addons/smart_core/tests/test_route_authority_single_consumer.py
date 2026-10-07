# -*- coding: utf-8 -*-
"""Every server-side publication decision consumes the one published authority.

``handlers/system_init.py`` fixes the product baseline: one navigation contract
owns both the rendered tree and its route authority.  ``sc.product.policy``
exposes that same published authority (``build_runtime_route_authority``) to
server-side consumers, and ``.agent/decisions/contract-first.yaml`` forbids
re-deriving release authorization from action declarations or native menu
existence.

Two consumers historically re-derived the authority on their own: the
``route.authority.validate`` gate and the context dispatch workspace carrier
pin.  A second derivation can answer a different question than the client asked
(the dispatch offered a menu the client then denied).  These checks execute the
real consumer bodies with the published authority injected, so going back to a
local derivation fails instead of silently drifting.
"""
import ast
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
HANDLER_PATH = ROOT / "handlers" / "route_authority_validate.py"
WORKSPACE_AUTHORITY_PATH = (
    REPO
    / "addons"
    / "smart_construction_core"
    / "models"
    / "support"
    / "context_workspace_entry_authority.py"
)


def _extract_method(path: Path, owner: str | None, name: str) -> ast.FunctionDef:
    body = ast.parse(path.read_text(encoding="utf-8")).body
    if owner is None:
        return next(
            node
            for node in body
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
    cls = next(
        node
        for node in body
        if isinstance(node, ast.ClassDef) and node.name == owner
    )
    return next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _compile(node: ast.FunctionDef, scope: dict):
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, "<consumer>", "exec"), scope)  # noqa: S102 - governed test harness
    return scope[node.name]


def _positive_int(value) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


class _Result:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Deny(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class RouteAuthoritySingleConsumerTest(unittest.TestCase):
    """Executes the consumer bodies against an injected published authority."""

    def setUp(self):
        self.published = {
            "primary_actions": [
                {
                    "action_id": 777,
                    "menu_id": 547,
                    "model": "sc.financing.loan",
                    "action_xmlid": "smart_construction_core.action_loan",
                    "route_kind": "PRIMARY_NAV",
                    "context_requirements": {},
                }
            ],
            "role_home_actions": [],
            "contextual_actions": [],
            "admin_actions": [],
            "menu_containers": [],
            "denied_actions": [],
        }
        self.calls = []

    # ------------------------------------------------------------------ #
    # route.authority.validate -- the client's runtime publication gate
    # ------------------------------------------------------------------ #
    def _handler(self):
        def build_runtime_route_authority(env):
            self.calls.append(env)
            return self.published

        scope = {
            "_positive_int": _positive_int,
            "IntentExecutionResult": _Result,
            "build_runtime_route_authority": build_runtime_route_authority,
            "params": None,
            "self": None,
        }
        handle = _compile(_extract_method(HANDLER_PATH, "RouteAuthorityValidateHandler", "handle"), scope)
        env = SimpleNamespace(companies=SimpleNamespace(ids=[21]), user=SimpleNamespace(id=210))
        owner = SimpleNamespace(
            env=env,
            params={},
            INTENT_TYPE="route.authority.validate",
            VERSION="1.0.0",
            SOURCE_KIND="route_authority_runtime_validation",
            _params=lambda payload: dict(payload or {}),
            _deny=lambda reason: _Result(ok=False, reason=reason),
        )

        def call(params):
            return handle(owner, params, None)

        return call

    def test_the_validate_gate_reads_the_published_authority(self):
        call = self._handler()
        result = call({"action_id": 777})
        self.assertEqual(len(self.calls), 1, "the gate must consume the published authority")
        self.assertTrue(result.ok)
        self.assertEqual(result.data["menu_id"], 547)
        self.assertEqual(result.data["model"], "sc.financing.loan")

    def test_the_validate_gate_denies_an_unreleased_entry_from_the_authority(self):
        call = self._handler()
        self.published["primary_actions"] = []
        self.published["denied_actions"] = [
            {"action_id": 777, "menu_id": 547, "reason_code": "PRODUCT_ENTRY_NOT_RELEASED"}
        ]
        result = call({"action_id": 777})
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "PRODUCT_ENTRY_NOT_RELEASED")

    def test_the_validate_gate_denies_an_action_the_authority_omits(self):
        call = self._handler()
        result = call({"action_id": 424242})
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "ROUTE_ACTION_NOT_AUTHORIZED")

    # ------------------------------------------------------------------ #
    # the dispatch carrier pin -- the workspace hands back one route
    # ------------------------------------------------------------------ #
    def _route_authority(self):
        module = types.ModuleType("odoo.addons.smart_core.delivery.runtime_route_authority")

        def build_runtime_route_authority(env):
            self.calls.append(env)
            return self.published

        module.build_runtime_route_authority = build_runtime_route_authority
        saved = sys.modules.get(module.__name__)
        sys.modules[module.__name__] = module
        self.addCleanup(
            lambda: sys.modules.__setitem__(module.__name__, saved)
            if saved is not None
            else sys.modules.pop(module.__name__, None)
        )
        scope = {
            "_ROUTE_AUTHORITY_BUCKETS": (
                "primary_actions",
                "role_home_actions",
                "contextual_actions",
                "admin_actions",
                "menu_containers",
            ),
            "self": None,
        }
        return _compile(
            _extract_method(
                WORKSPACE_AUTHORITY_PATH,
                "ScContextWorkspaceEntryAuthority",
                "_sc_route_authority",
            ),
            scope,
        )

    def test_the_dispatch_pin_reads_the_published_authority(self):
        route_authority = self._route_authority()
        owner = SimpleNamespace(env=SimpleNamespace(cr=SimpleNamespace(dbname="sc_test")))
        entries = route_authority(owner)
        self.assertEqual(len(self.calls), 1, "the pin must consume the published authority")
        self.assertEqual([row["menu_id"] for row in entries], [547])

    def test_the_dispatch_pin_offers_nothing_when_the_authority_is_denied(self):
        route_authority = self._route_authority()
        self.published["primary_actions"] = []
        self.published["denied_actions"] = [
            {"action_id": 777, "menu_id": 547, "reason_code": "PRODUCT_ENTRY_NOT_RELEASED"}
        ]
        owner = SimpleNamespace(env=SimpleNamespace(cr=SimpleNamespace(dbname="sc_test")))
        self.assertEqual(route_authority(owner), [])

    def test_the_dispatch_pin_offers_nothing_when_the_authority_is_unavailable(self):
        route_authority = self._route_authority()
        self.published = None
        owner = SimpleNamespace(env=SimpleNamespace(cr=SimpleNamespace(dbname="sc_test")))
        self.assertEqual(route_authority(owner), [])

    def test_the_dispatch_pin_does_not_derive_its_own_projection(self):
        source = WORKSPACE_AUTHORITY_PATH.read_text(encoding="utf-8")
        body = source.split("def _sc_route_authority", 1)[1].split("\n    def ", 1)[0]
        self.assertIn("build_runtime_route_authority", body)
        self.assertNotIn("DeliveryEngine", body)
        self.assertNotIn("IdentityResolver", body)

    def test_the_validate_gate_does_not_derive_its_own_projection(self):
        source = HANDLER_PATH.read_text(encoding="utf-8")
        body = source.split("    def handle(", 1)[1]
        self.assertIn("build_runtime_route_authority", body)
        for removed in (
            "_load_platform_release_gate",
            "filter_route_authority_by_publication",
            "ProductPolicyService",
        ):
            self.assertNotIn(removed, body)

    # ------------------------------------------------------------------ #
    # the shared authority owns release enforcement and publication
    # ------------------------------------------------------------------ #
    def test_the_shared_authority_enforces_release_and_publication(self):
        """The one authority carries the release gate the consumers dropped.

        The former inline derivation asked the product policy with
        ``enforce_release``/``enforce_access`` and filtered the route authority
        by publication.  That duty now lives only here, so it is locked here
        rather than in each consumer.
        """
        source = (ROOT / "delivery" / "runtime_route_authority.py").read_text(encoding="utf-8")
        builder = source.split("def _build_runtime_route_authority", 1)[1]
        self.assertIn("enforce_release=True", builder)
        self.assertIn("enforce_access=True", builder)
        self.assertIn("filter_route_authority_by_publication", builder)
        self.assertIn("fail_closed", builder)
        published = source.split("def published_route_authority", 1)[1].split(
            "def build_runtime_route_authority", 1
        )[0]
        self.assertIn("published_route_authority", published)
        self.assertIn("_build_runtime_route_authority(env)", published)


if __name__ == "__main__":
    unittest.main()
