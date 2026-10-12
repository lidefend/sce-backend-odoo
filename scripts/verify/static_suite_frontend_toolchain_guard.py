#!/usr/bin/env python3
"""The remote required backend gate must not need the frontend toolchain.

``verify.contract.architecture.suite`` is a prerequisite of
``ci.professional.backend.shard-verify``, which ``professional_quality_gate.yml``
runs on the ``full`` lane. That lane installs **no** frontend dependencies, so a
guard reachable from it that shells out to the workspace toolchain can only fail
with "No such file or directory" instead of producing a real gate result.


Four instances of that boundary defect have already occurred:

* 2026-10-12 ``verify.menu_config_tree_editor.behavior`` (esbuild) wired into the
  shared suite -> ``ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL esbuild not found``.
* 2026-10-12 ``contract_form_runtime_state_behavior_guard.sh`` invoked inline in
  the shared suite -> ``node_modules/.bin/tsc: No such file or directory`` and
  ``make: *** [make/ci.mk:1039: verify.contract.architecture.suite] Error 127``.
* 2026-10-12 three inline ``node scripts/verify/*_smoke.js`` recipes in the shared
  suite; each harness compiles ``frontend/apps/web`` sources through
  ``require('../../frontend/apps/web/node_modules/typescript')`` ->
  ``Cannot find module .../frontend/apps/web/node_modules/typescript`` and
  ``make: *** [make/ci.mk:1095: verify.contract.architecture.suite] Error 1``.
  That instance was invisible to the two frames above: the recipe carries no
  toolchain *token* (a bare ``node <script>``), and the script is a ``.js`` file,
  which the ``.sh|.py`` script frame never opened. Both frames are widened here.

All of them are lane-coverage defects, not code defects. This guard makes the
boundary machine-checkable so the suite cannot silently regain such a wire, and
it also refuses a "fix" that merely deletes enforcement: each known
frontend-toolchain guard must stay reachable from the local exact-head lane and
from a frontend lane.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard_registry_audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

#: The remote required backend gate that installs no frontend dependencies.
REMOTE_BACKEND_ANCHOR = "ci.professional.backend.shard-verify"
#: The governed local exact-head lane, which does have frontend dependencies.
LOCAL_QUICK_ANCHOR = "ci.local.quick.run"
#: Frontend lanes that install the pinned pnpm toolchain and frontend deps.
FRONTEND_ANCHORS = ("verify.frontend.pr.unit", "verify.frontend.release.unit")

#: Tokens that mean "this make recipe needs the installed frontend toolchain".
#: Safe as a *recipe* rule because a make recipe line is a command; it is not
#: applied to script bodies, where the same words also appear as declared-string
#: constants (see FRONTEND_TOOLCHAIN_INVOCATIONS).
FRONTEND_TOOLCHAIN_TOKENS = (
    "node_modules/.bin/",
    "pnpm_exec.sh",
    "pnpm exec",
    "corepack",
)

#: Execution forms inside a guard script. A bare token is not enough: guards such
#: as baseline_iteration_execution_policy_guard.py legitimately carry
#: "pnpm_exec.sh -C frontend/apps/web ..." as an *expected declared command*
#: string, which is data, not execution. Only a workspace-anchored path is an
#: invocation. A guard using a different absolute form must extend this list.
FRONTEND_TOOLCHAIN_INVOCATIONS = (
    re.compile(r"""["']?\$\{ROOT\}[^"'\s]*?/(?:node_modules/\.bin/|scripts/dev/pnpm_exec\.sh)"""),
    re.compile(r"""["']?\$\(ROOT\)[^"'\s]*?/(?:node_modules/\.bin/|scripts/dev/pnpm_exec\.sh)"""),
)

#: Node harnesses load the workspace frontend toolchain through a module loader
#: instead of spawning a binary. ``node_modules`` alone is declared data (a
#: path on a module search list, an alias target, a quoted expectation); only a
#: loader keyword directly in front of the path is an execution. The ``.js``
#: frame matters because the third wire carried no toolchain token in its recipe
#: and was therefore invisible to both frames above.
FRONTEND_TOOLCHAIN_NODE_LOADS = (
    re.compile(r"""\b(?:require|import)\s*\(\s*[^);\n]*?frontend/apps/web/node_modules"""),
    re.compile(r"""\bfrom\s+["'][^"'\n]*?frontend/apps/web/node_modules"""),
)

#: Guards/harnesses that compile or bundle frontend sources with the workspace
#: toolchain. A make target reachable from REMOTE_BACKEND_ANCHOR must never run
#: one of these, and each must stay reachable from the lanes that do install the
#: toolchain.
FRONTEND_TOOLCHAIN_GUARDS = (
    "scripts/verify/menu_config_tree_editor_behavior_guard.sh",
    "scripts/verify/contract_form_runtime_state_behavior_guard.sh",
    "scripts/verify/action_view_route_runtime_smoke.js",
    "scripts/verify/action_view_contract_action_runtime_smoke.js",
    "scripts/verify/navigation_context_smoke.js",
)

#: Every script suffix a make recipe names literally. The earlier ``.sh|.py``
#: frame was the reason the third wire stayed invisible: its recipe named a
#: ``.js`` harness, so the script was never opened and its toolchain load was
#: never seen.
SCRIPT_REFERENCE_RE = re.compile(
    r"\b(scripts/[A-Za-z0-9_./-]+\.(?:sh|py|js|mjs|cjs))\b"
)

#: This guard's own files carry toolchain paths as fixtures/patterns, not as
#: executions. Self-reference is the one exclusion: every other reachable script
#: is scanned, so a new wire still fails closed.
SELF_FILES = frozenset(
    {
        "static_suite_frontend_toolchain_guard.py",
        "test_static_suite_frontend_toolchain_guard.py",
    }
)


def _repo_script_text(script: str) -> str:
    path = ROOT / script
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def frontend_toolchain_invocations(text: str) -> list[str]:
    """Workspace-anchored toolchain invocations found in ``text``."""
    found: list[str] = []
    for pattern in FRONTEND_TOOLCHAIN_INVOCATIONS:
        match = pattern.search(text)
        if match:
            found.append(match.group(0).lstrip("\"'"))
    return found


def frontend_toolchain_node_loads(text: str) -> list[str]:
    """Frontend-toolchain module loads (``require``/``import``/``from``) in ``text``."""
    found: list[str] = []
    for pattern in FRONTEND_TOOLCHAIN_NODE_LOADS:
        match = pattern.search(text)
        if match:
            found.append(match.group(0).strip())
    return found


def collect_frontend_toolchain_hits(
    graph: dict[str, set[str]],
    targets: dict[str, str],
    anchor: str,
    script_text=_repo_script_text,
) -> list[str]:
    """Every reachable recipe/script under ``anchor`` that needs the toolchain."""
    hits: list[str] = []
    for target in sorted(guard_registry_audit.reachable_targets(graph, [anchor])):
        body = targets.get(target, "")
        for token in FRONTEND_TOOLCHAIN_TOKENS:
            if token in body:
                hits.append(f"{anchor} -> {target}: inline {token!r}")
        for script in sorted(set(SCRIPT_REFERENCE_RE.findall(body))):
            if Path(script).name in SELF_FILES:
                continue
            text = script_text(script)
            for invocation in frontend_toolchain_invocations(text):
                hits.append(f"{anchor} -> {target} -> {script}: {invocation!r}")
            for load in frontend_toolchain_node_loads(text):
                hits.append(f"{anchor} -> {target} -> {script}: {load!r}")
    return hits


def enforcement_anchor_failures(
    graph: dict[str, set[str]],
    targets: dict[str, str],
) -> list[str]:
    """Each frontend-toolchain guard stays enforced on the lanes that have deps."""
    failures: list[str] = []
    for guard in FRONTEND_TOOLCHAIN_GUARDS:
        referencing = {
            name for name, body in targets.items() if guard in body
        }
        if not referencing:
            failures.append(f"{guard} is referenced by no make target")
            continue
        for anchor in (LOCAL_QUICK_ANCHOR, *FRONTEND_ANCHORS):
            reachable = guard_registry_audit.reachable_targets(graph, [anchor])
            if not referencing & reachable:
                failures.append(
                    f"{guard} is not reachable from {anchor}: enforcement was "
                    "dropped instead of relocated"
                )
    return failures


def behavior_relocation_failures(
    graph: dict[str, set[str]],
    targets: dict[str, str],
) -> list[str]:
    """The static suite must not carry a frontend-toolchain guard itself."""
    suite = "verify.contract.architecture.suite"
    failures: list[str] = []
    for guard in FRONTEND_TOOLCHAIN_GUARDS:
        if guard in targets.get(suite, ""):
            failures.append(
                f"{suite} carries {guard}; it needs installed frontend "
                "dependencies and belongs to the frontend and local lanes"
            )
    return failures


def main() -> int:
    graph = guard_registry_audit.parse_make_graph()
    targets = guard_registry_audit.parse_make_targets()

    errors: list[str] = []
    errors.extend(
        collect_frontend_toolchain_hits(graph, targets, REMOTE_BACKEND_ANCHOR)
    )
    errors.extend(behavior_relocation_failures(graph, targets))
    errors.extend(enforcement_anchor_failures(graph, targets))

    if errors:
        print("[static_suite_frontend_toolchain_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[static_suite_frontend_toolchain_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
