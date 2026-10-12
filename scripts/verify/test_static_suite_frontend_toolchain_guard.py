from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from static_suite_frontend_toolchain_guard import (  # noqa: E402
    FRONTEND_ANCHORS,
    LOCAL_QUICK_ANCHOR,
    REMOTE_BACKEND_ANCHOR,
    collect_frontend_toolchain_hits,
    enforcement_anchor_failures,
    frontend_toolchain_invocations,
    frontend_toolchain_node_loads,
    main,
)


def _texts(mapping):
    return lambda script: mapping.get(script, "")


class InvocationShapeTest(unittest.TestCase):
    """Execution is a workspace-anchored path; a bare token is declared data."""

    def test_workspace_anchored_tsc_invocation_is_detected(self) -> None:
        self.assertTrue(
            frontend_toolchain_invocations(
                '"${ROOT}/frontend/apps/web/node_modules/.bin/tsc" \\\n'
            )
        )

    def test_workspace_anchored_pnpm_exec_invocation_is_detected(self) -> None:
        self.assertTrue(
            frontend_toolchain_invocations(
                '"${ROOT}/scripts/dev/pnpm_exec.sh" -C "${ROOT}/frontend/apps/web" exec esbuild \\\n'
            )
        )

    def test_declared_command_constant_is_not_an_invocation(self) -> None:
        # baseline_iteration_execution_policy_guard.py carries this as expected
        # make text to compare against; it never runs it.
        self.assertEqual(
            frontend_toolchain_invocations('    "pnpm_exec.sh -C frontend/apps/web lint:src",\n'),
            [],
        )
        self.assertEqual(
            frontend_toolchain_invocations(
                'TYPECHECK_COMMAND = "pnpm_exec.sh -C frontend/apps/web typecheck:strict"\n'
            ),
            [],
        )


class NodeLoaderShapeTest(unittest.TestCase):
    """A Node harness loads the frontend toolchain; a bare path is declared data."""

    def test_commonjs_require_of_frontend_toolchain_is_detected(self) -> None:
        self.assertTrue(
            frontend_toolchain_node_loads(
                "const ts = require('../../frontend/apps/web/node_modules/typescript');\n"
            )
        )

    def test_esm_import_of_frontend_toolchain_is_detected(self) -> None:
        self.assertTrue(
            frontend_toolchain_node_loads(
                "import ts from '../../frontend/apps/web/node_modules/typescript/lib/typescript.js';\n"
            )
        )
        self.assertTrue(
            frontend_toolchain_node_loads(
                "import { build } from '../../frontend/apps/web/node_modules/esbuild/lib/main.js';\n"
            )
        )

    def test_module_search_path_and_alias_are_not_loads(self) -> None:
        # The frontend browser runners list the directory on a module search
        # path or alias it; that mentions the toolchain without loading it here.
        self.assertEqual(
            frontend_toolchain_node_loads(
                "    path.resolve('frontend/apps/web/node_modules'),\n"
            ),
            [],
        )
        self.assertEqual(
            frontend_toolchain_node_loads(
                "  alias:{vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`},\n"
            ),
            [],
        )


class ReachabilityTest(unittest.TestCase):
    def test_inline_recipe_token_under_the_backend_anchor_is_reported(self) -> None:
        graph = {REMOTE_BACKEND_ANCHOR: {"verify.suite"}, "verify.suite": set()}
        targets = {
            REMOTE_BACKEND_ANCHOR: "verify.suite",
            "verify.suite": "\t@frontend/apps/web/node_modules/.bin/tsc --build",
        }
        hits = collect_frontend_toolchain_hits(graph, targets, REMOTE_BACKEND_ANCHOR, _texts({}))
        self.assertTrue(hits, "an inline toolchain command in a reachable recipe must fail")

    def test_script_invocation_under_the_backend_anchor_is_reported(self) -> None:
        graph = {REMOTE_BACKEND_ANCHOR: {"verify.suite"}, "verify.suite": {"verify.behavior"}}
        targets = {
            REMOTE_BACKEND_ANCHOR: "verify.suite",
            "verify.suite": "verify.behavior",
            "verify.behavior": "\t@scripts/verify/frontend_thing_guard.sh",
        }
        scripts = {
            "scripts/verify/frontend_thing_guard.sh": (
                '"${ROOT}/frontend/apps/web/node_modules/.bin/tsc" \\\n'
            )
        }
        hits = collect_frontend_toolchain_hits(graph, targets, REMOTE_BACKEND_ANCHOR, _texts(scripts))
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("frontend_thing_guard.sh", hits[0])

    def test_node_harness_loading_frontend_toolchain_under_the_anchor_is_reported(self) -> None:
        graph = {REMOTE_BACKEND_ANCHOR: {"verify.suite"}, "verify.suite": {"verify.smoke"}}
        targets = {
            REMOTE_BACKEND_ANCHOR: "verify.suite",
            "verify.suite": "verify.smoke",
            "verify.smoke": "\t@node scripts/verify/action_view_route_runtime_smoke.js",
        }
        scripts = {
            "scripts/verify/action_view_route_runtime_smoke.js": (
                "const ts = require('../../frontend/apps/web/node_modules/typescript');\n"
            )
        }
        hits = collect_frontend_toolchain_hits(graph, targets, REMOTE_BACKEND_ANCHOR, _texts(scripts))
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("action_view_route_runtime_smoke.js", hits[0])

    def test_declared_only_script_is_not_reported(self) -> None:
        graph = {REMOTE_BACKEND_ANCHOR: {"verify.policy"}, "verify.policy": set()}
        targets = {
            REMOTE_BACKEND_ANCHOR: "verify.policy",
            "verify.policy": "\t@python3 scripts/verify/policy_guard.py",
        }
        scripts = {
            "scripts/verify/policy_guard.py": 'EXPECTED = "pnpm_exec.sh -C frontend/apps/web lint:src"\n'
        }
        self.assertEqual(
            collect_frontend_toolchain_hits(graph, targets, REMOTE_BACKEND_ANCHOR, _texts(scripts)),
            [],
        )


class EnforcementAnchorTest(unittest.TestCase):
    #: The relocated Node harness target, mirroring ``make/ci.mk``.
    SMOKE_TARGET = "verify.action_view_runtime_smoke.behavior"
    SMOKE_BODY = (
        "\t@node scripts/verify/action_view_route_runtime_smoke.js\n"
        "\t@node scripts/verify/action_view_contract_action_runtime_smoke.js\n"
        "\t@node scripts/verify/navigation_context_smoke.js"
    )
    BEHAVIOR_BODIES = {
        "verify.contract_form_runtime_state.behavior":
            "\t@scripts/verify/contract_form_runtime_state_behavior_guard.sh",
        "verify.menu_config_tree_editor.behavior":
            "\t@scripts/verify/menu_config_tree_editor_behavior_guard.sh",
        SMOKE_TARGET: SMOKE_BODY,
    }

    def _graph(self):
        relocated = {
            "verify.contract_form_runtime_state.behavior",
            self.SMOKE_TARGET,
        }
        return {
            LOCAL_QUICK_ANCHOR: set(relocated),
            FRONTEND_ANCHORS[0]: set(relocated),
            FRONTEND_ANCHORS[1]: set(relocated),
            "verify.contract_form_runtime_state.behavior": set(),
            "verify.menu_config_tree_editor.behavior": set(),
            self.SMOKE_TARGET: set(),
        }

    def _targets(self, graph):
        return {name: self.BEHAVIOR_BODIES.get(name, "") for name in graph}

    def test_relocating_enforcement_into_the_lanes_passes(self) -> None:
        graph = self._graph()
        graph[LOCAL_QUICK_ANCHOR].add("verify.menu_config_tree_editor.behavior")
        graph[FRONTEND_ANCHORS[0]].add("verify.menu_config_tree_editor.behavior")
        graph[FRONTEND_ANCHORS[1]].add("verify.menu_config_tree_editor.behavior")
        self.assertEqual(enforcement_anchor_failures(graph, self._targets(graph)), [])

    def test_dropping_enforcement_instead_of_relocating_fails(self) -> None:
        graph = self._graph()  # menu guard is wired nowhere
        targets = {
            name: body
            for name, body in self._targets(graph).items()
            if name != self.SMOKE_TARGET
        }
        targets["verify.contract_form_runtime_state.behavior"] = (
            "\t@scripts/verify/contract_form_runtime_state_behavior_guard.sh"
        )
        failures = enforcement_anchor_failures(graph, targets)
        self.assertTrue(
            any("menu_config_tree_editor" in failure for failure in failures), failures
        )
        self.assertTrue(
            any("action_view_route_runtime_smoke" in failure for failure in failures),
            failures,
        )


class SelfExclusionTest(unittest.TestCase):
    def test_only_this_guard_family_is_excluded(self) -> None:
        from static_suite_frontend_toolchain_guard import SELF_FILES

        self.assertEqual(
            SELF_FILES,
            {
                "static_suite_frontend_toolchain_guard.py",
                "test_static_suite_frontend_toolchain_guard.py",
            },
            "the self-reference exclusion must not grow beyond this guard's own files",
        )


class RealRepositoryTest(unittest.TestCase):
    def test_current_repository_is_clean_and_relocated(self) -> None:
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
