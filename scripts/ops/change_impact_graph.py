#!/usr/bin/env python3
"""Build deterministic semantic dependency edges for change-impact planning.

The graph is evidence-graded. Compiler/AST-local imports are high confidence,
contract-family links are explicit static inferences, and unresolved dynamic
consumers remain unknown. The graph never decides that a mandatory gate may be
skipped.
"""

from __future__ import annotations

import ast
import hashlib
import json
import posixpath
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable


GRAPH_SCHEMA = "change_impact.semantic_graph.v1"
TS_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".mjs", ".cjs", ".vue"})
PY_SUFFIXES = frozenset({".py"})
SOURCE_SUFFIXES = TS_SUFFIXES | PY_SUFFIXES
TEST_MARKERS = ("_test.", ".test.", "test_")
RENDERER_REGISTRY_PATHS = frozenset(
    {
        "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
        "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts",
    }
)


def _digest(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_node(path: str) -> str:
    return f"file:{path}"


def _edge_id(source: str, kind: str, target: str, qualifier: str = "") -> str:
    raw = "\0".join((source, kind, target, qualifier))
    return f"edge:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def path_role(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("frontend/apps/web/scripts/") or any(
        marker in Path(normalized).name for marker in TEST_MARKERS
    ):
        return "verification_assertion"
    if normalized in RENDERER_REGISTRY_PATHS:
        return "renderer_registry"
    if "/app/contracts/v2/" in normalized:
        return "contract_decoder"
    if "/app/presentation/" in normalized or "/components/" in normalized:
        return "renderer_component"
    if normalized.startswith(
        (
            "frontend/apps/web/src/pages/",
            "frontend/apps/web/src/views/",
            "frontend/apps/web/src/layouts/",
        )
    ):
        return "page"
    if "/security/" in normalized or normalized.endswith(".csv"):
        return "acl_declaration"
    if "/migrations/" in normalized:
        return "migration"
    if "/handlers/" in normalized:
        return "intent_handler"
    if "/models/" in normalized or "/model/" in normalized:
        return "orm_model"
    if "/core/" in normalized and normalized.endswith((".py", ".xml")):
        return "contract_producer"
    if normalized.startswith("frontend/"):
        return "frontend_runtime"
    if normalized.startswith(("addons/", "customer_addons/", "demo_addons/")):
        return "backend_declaration"
    return "source"


def _module_capabilities(role: str) -> list[str]:
    return {
        "contract_decoder": ["contract.v2.decode"],
        "renderer_registry": ["presentation.renderer.selection"],
        "renderer_component": ["presentation.component.render"],
        "page": ["presentation.page"],
        "intent_handler": ["business.intent.execute"],
        "orm_model": ["business.orm.model"],
        "acl_declaration": ["business.permission"],
        "migration": ["business.persistence.migration"],
        "contract_producer": ["contract.v2.produce"],
        "verification_assertion": ["delivery.assertion"],
    }.get(role, [])


def _resolve_local_module(
    importer: str,
    specifier: str,
    available: set[str],
) -> str | None:
    if not specifier or not specifier.startswith((".", "@/")):
        return None
    if specifier.startswith("@/"):
        base = f"frontend/apps/web/src/{specifier[2:]}"
    else:
        base = posixpath.normpath(
            posixpath.join(posixpath.dirname(importer), specifier)
        )
    candidates = [base]
    suffixes = sorted(TS_SUFFIXES)
    candidates.extend(f"{base}{suffix}" for suffix in suffixes)
    candidates.extend(f"{base}/index{suffix}" for suffix in suffixes)
    for candidate in candidates:
        normalized = posixpath.normpath(Path(candidate).as_posix())
        if normalized in available:
            return normalized
    return None


def _python_module_candidates(
    importer: str,
    module: str,
    level: int,
    available: set[str],
) -> list[str]:
    if level:
        base = Path(importer).parent
        for _ in range(max(0, level - 1)):
            base = base.parent
        base = base.joinpath(*[part for part in module.split(".") if part])
        candidates = [f"{base.as_posix()}.py", f"{base.as_posix()}/__init__.py"]
    elif module.startswith("odoo.addons."):
        parts = module.split(".")[2:]
        base = Path("addons", *parts)
        candidates = [f"{base.as_posix()}.py", f"{base.as_posix()}/__init__.py"]
    else:
        return []
    return [candidate for candidate in candidates if candidate in available]


def _python_facts(text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {"ok": False, "error": str(exc)}
    imports = []
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append(
                {
                    "module": node.module or "",
                    "level": node.level,
                    "names": [alias.name for alias in node.names],
                }
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "level": 0, "names": ["*"]})
    for class_node in [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]:
        for node in class_node.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            calls = [
                call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, (ast.Attribute, ast.Name))
            ]
            methods.append(
                {
                    "class_name": class_node.name,
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "calls": sorted(set(calls)),
                    "orm_operations": sorted(
                        set(calls) & {"create", "write", "unlink", "copy", "action_done"}
                    ),
                }
            )
    return {"ok": True, "import_bindings": imports, "methods": methods}


def _reachable(
    start: str,
    adjacency: dict[str, list[str]],
    *,
    depth: int = 6,
) -> list[str]:
    seen = {start}
    ordered: list[str] = []
    queue = deque([(start, 0)])
    while queue:
        node, distance = queue.popleft()
        if distance >= depth:
            continue
        for target in adjacency.get(node, []):
            if target in seen:
                continue
            seen.add(target)
            ordered.append(target)
            queue.append((target, distance + 1))
    return ordered


def build_semantic_graph(
    files: dict[str, str],
    *,
    revision: str,
    ts_facts: dict[str, Any] | None = None,
    changed_paths: Iterable[str] = (),
) -> dict[str, Any]:
    """Build file-level semantic edges from compiler and AST facts."""

    ts_facts = ts_facts or {}
    paths = {
        Path(path).as_posix()
        for path in files
        if Path(path).suffix.lower() in SOURCE_SUFFIXES
    }
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    unknowns: set[str] = set()

    def add_node(path: str) -> None:
        role = path_role(path)
        node_id = _file_node(path)
        nodes[node_id] = {
            "id": node_id,
            "path": path,
            "kind": role,
            "capabilities": _module_capabilities(role),
            "confidence": "observed",
            "basis": ["repository_path_and_parsed_source"],
        }

    def add_edge(
        source: str,
        target: str,
        kind: str,
        *,
        confidence: str,
        basis: list[str],
        reason: str,
        bindings: list[str] | None = None,
    ) -> None:
        identifier = _edge_id(source, kind, target, "|".join(bindings or []))
        edges[identifier] = {
            "id": identifier,
            "source": source,
            "target": target,
            "kind": kind,
            "confidence": confidence,
            "basis": sorted(set(basis)),
            "reason": reason,
            "bindings": sorted(bindings or []),
        }

    for path in sorted(paths):
        add_node(path)

    import_adjacency: dict[str, list[str]] = {}
    reverse_imports: dict[str, list[str]] = {}
    python_facts_by_path: dict[str, dict[str, Any]] = {}
    for path in sorted(paths):
        text = files[path]
        suffix = Path(path).suffix.lower()
        if suffix in TS_SUFFIXES:
            facts = ((ts_facts.get(path) or {}).get("after") or {})
            if not facts.get("ok", False):
                unknowns.add(f"{path}: typescript_graph_facts_unavailable")
                continue
            import_rows = list(facts.get("import_bindings") or [])
            for binding in import_rows:
                target = _resolve_local_module(path, str(binding.get("specifier") or ""), paths)
                if target is None:
                    continue
                source_node = _file_node(path)
                target_node = _file_node(target)
                imported = [
                    str(item.get("local") or item.get("imported") or "")
                    for item in binding.get("bindings", [])
                ]
                add_edge(
                    source_node,
                    target_node,
                    "imports",
                    confidence="high",
                    basis=["typescript_compiler_import"],
                    reason="compiler-resolved local module import",
                    bindings=imported,
                )
                import_adjacency.setdefault(source_node, []).append(target_node)
                reverse_imports.setdefault(target_node, []).append(source_node)
        elif suffix in PY_SUFFIXES:
            facts = _python_facts(text)
            python_facts_by_path[path] = facts
            if not facts.get("ok", False):
                unknowns.add(f"{path}: python_graph_facts_unavailable")
                continue
            for binding in facts.get("import_bindings") or []:
                targets = _python_module_candidates(
                    path,
                    str(binding.get("module") or ""),
                    int(binding.get("level") or 0),
                    paths,
                )
                for target in targets:
                    source_node = _file_node(path)
                    target_node = _file_node(target)
                    names = [str(name) for name in binding.get("names", [])]
                    add_edge(
                        source_node,
                        target_node,
                        "imports",
                        confidence="high",
                        basis=["python_ast_import"],
                        reason="AST-resolved local module import",
                        bindings=names,
                    )
                    import_adjacency.setdefault(source_node, []).append(target_node)
                    reverse_imports.setdefault(target_node, []).append(source_node)

    for source_node, targets in sorted(import_adjacency.items()):
        source_path = source_node.removeprefix("file:")
        if path_role(source_path) != "verification_assertion":
            continue
        for target_node in targets:
            add_edge(
                source_node,
                target_node,
                "asserts_consumer",
                confidence="high",
                basis=["verification_assertion_import"],
                reason="test module imports the exercised consumer",
            )

    producers = [
        path
        for path in paths
        if path_role(path) == "contract_producer"
        and (
            "contract" in Path(path).name
            or "action_view" in Path(path).name
            or "search" in Path(path).name
        )
    ]
    decoders = [path for path in paths if path_role(path) == "contract_decoder"]
    for producer in sorted(producers):
        for decoder in sorted(decoders):
            add_edge(
                _file_node(producer),
                _file_node(decoder),
                "contract_producer_to_decoder",
                confidence="medium",
                basis=["contract_family_identity"],
                reason="backend contract family is consumed by the v2 decoder",
            )

    renderer_imports: dict[str, str] = {}
    form_section = "frontend/apps/web/src/components/template/FormSection.vue"
    if form_section in paths:
        form_facts = ((ts_facts.get(form_section) or {}).get("after") or {})
        for binding in form_facts.get("import_bindings") or []:
            target = _resolve_local_module(form_section, str(binding.get("specifier") or ""), paths)
            if not target:
                continue
            for item in binding.get("bindings", []):
                local = str(item.get("local") or "")
                if local:
                    renderer_imports[local] = target
    registry_path = "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts"
    renderer_names = sorted(
        set(re.findall(r"renderer:\s*'([^']+)'", files.get(registry_path, "")))
    )
    for renderer in renderer_names:
        target = renderer_imports.get(renderer)
        if not target:
            continue
        add_edge(
            _file_node("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"),
            _file_node(target),
            "renderer_registry_to_component",
            confidence="high",
            basis=["semantic_registry_renderer_name", "typescript_component_import"],
            reason="declared renderer name resolves to an imported component",
            bindings=[renderer],
        )

    for path in sorted(paths):
        if path_role(path) not in {"renderer_component", "renderer_registry"}:
            continue
        source = _file_node(path)
        for consumer in _reachable(source, reverse_imports, depth=8):
            consumer_path = consumer.removeprefix("file:")
            if path_role(consumer_path) != "page":
                continue
            add_edge(
                source,
                consumer,
                "component_to_page",
                confidence="high",
                basis=["compiler_reverse_import_closure"],
                reason="page reaches the changed component through local imports",
            )

    for path in sorted(path for path in paths if Path(path).suffix == ".py"):
        facts = python_facts_by_path.get(path) or {}
        for method in facts.get("methods") or []:
            for operation in sorted(set(method.get("orm_operations") or [])):
                operation_node = f"operation:orm.{operation}"
                nodes.setdefault(
                    operation_node,
                    {
                        "id": operation_node,
                        "kind": "orm_operation",
                        "capabilities": ["business.orm.mutate"],
                        "confidence": "observed",
                        "basis": ["python_ast_call"],
                    },
                )
                add_edge(
                    _file_node(path),
                    operation_node,
                    "business_method_to_orm",
                    confidence="high",
                    basis=["python_ast_call"],
                    reason=f"method {method.get('name')} calls ORM {operation}",
                    bindings=[str(method.get("name") or "")],
                )

    adjacency: dict[str, list[str]] = {}
    reverse_adjacency: dict[str, list[str]] = {}
    for edge in edges.values():
        adjacency.setdefault(edge["source"], []).append(edge["target"])
        reverse_adjacency.setdefault(edge["target"], []).append(edge["source"])

    changed = sorted({Path(path).as_posix() for path in changed_paths})
    impact = [
        {
            "source": _file_node(path),
            "forward_consumers": sorted(_reachable(_file_node(path), adjacency)),
            "reverse_consumers": sorted(_reachable(_file_node(path), reverse_adjacency)),
        }
        for path in changed
    ]
    ordered_nodes = [nodes[key] for key in sorted(nodes)]
    ordered_edges = [edges[key] for key in sorted(edges)]
    edge_kinds: dict[str, int] = {}
    for edge in ordered_edges:
        edge_kinds[edge["kind"]] = edge_kinds.get(edge["kind"], 0) + 1
    graph = {
        "schema": GRAPH_SCHEMA,
        "identity": {"revision": revision},
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "impact": impact,
        "unknowns": sorted(unknowns),
        "summary": {
            "nodes": len(ordered_nodes),
            "edges": len(ordered_edges),
            "edge_kinds": dict(sorted(edge_kinds.items())),
            "unknowns": len(unknowns),
        },
    }
    graph["digest"] = _digest(
        {
            "identity": graph["identity"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "unknowns": graph["unknowns"],
        }
    )
    return graph


def trace_nodes_for_path(graph: dict[str, Any], path: str) -> dict[str, list[str]]:
    source = _file_node(path)
    for row in graph.get("impact") or []:
        if row.get("source") == source:
            return {
                "forward": list(row.get("forward_consumers") or []),
                "reverse": list(row.get("reverse_consumers") or []),
            }
    return {"forward": [], "reverse": []}


def reverse_evidence_trace(
    checks: list[dict[str, Any]],
    obligations: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    capabilities_by_obligation: dict[str, set[str]] = {}
    for fact in facts:
        for obligation in fact.get("obligation_ids") or []:
            capabilities_by_obligation.setdefault(obligation, set()).update(
                fact.get("capabilities") or []
            )
    obligations_by_assertion: dict[str, set[str]] = {}
    for obligation in obligations:
        for assertion in obligation.get("required_assertions") or []:
            obligations_by_assertion.setdefault(assertion, set()).add(obligation["id"])
    rows = []
    for check in checks:
        assertions = list(check.get("covered_assertions") or [])
        related_obligations = sorted(
            {
                obligation
                for assertion in assertions
                for obligation in obligations_by_assertion.get(assertion, set())
            }
        )
        invalidation_inputs = sorted(
            {
                fact["path"]
                for fact in facts
                if set(fact.get("obligation_ids") or []) & set(related_obligations)
            }
        )
        input_nodes = {_file_node(path) for path in invalidation_inputs}
        related_edges = [
            edge
            for edge in graph.get("edges") or []
            if edge.get("source") in input_nodes or edge.get("target") in input_nodes
        ]
        local_graph_digest = _digest(
            {
                "assertions": assertions,
                "inputs": invalidation_inputs,
                "edges": related_edges,
            }
        )
        rows.append(
            {
                "check_id": check["id"],
                "assertions": assertions,
                "obligations": related_obligations,
                "capabilities": sorted(
                    {
                        capability
                        for obligation in related_obligations
                        for capability in capabilities_by_obligation.get(obligation, set())
                    }
                ),
                "invalidation_inputs": invalidation_inputs,
                "invalidation_fingerprint": local_graph_digest,
            }
        )
    return rows
