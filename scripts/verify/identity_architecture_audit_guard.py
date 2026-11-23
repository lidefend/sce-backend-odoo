#!/usr/bin/env python3
"""Validate the IDENTITY-ARCHITECTURE-01 audit artifacts."""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "docs" / "architecture" / "identity_architecture_01"
MATRIX_PATH = AUDIT_DIR / "identity_authority_matrix.json"
DOC_PATH = AUDIT_DIR / "identity_authority_audit_20261123.md"
GRAPH_PATH = AUDIT_DIR / "identity_relationship_graph.mmd"
BASELINE = "2a99f01c55af1c1cee01bc29d280fa5cc777b12f"

REQUIRED_DOMAINS = {
    "odoo.model",
    "odoo.record",
    "odoo.xmlid",
    "odoo.menu",
    "odoo.action",
    "navigation.entry",
    "product.scene",
    "contract.field",
    "contract.widget_occurrence",
    "contract.action_rule",
    "runtime.collection_row",
    "attachment.record",
    "security.principal",
    "security.authorization_subject",
    "transport.request",
    "observability.trace",
}
REQUIRED_FINDINGS = {
    "ID-F-001",
    "ID-F-002",
    "ID-F-003",
    "ID-F-004",
    "ID-F-005",
    "ID-F-006",
    "ID-F-007",
    "ID-F-008",
}
FRONTEND_CREATION_STATES = {
    "forbidden",
    "draft_local_only",
    "request_scoped_allowed",
}
FINDING_CLASSES = {
    "incomplete_mapping",
    "cross_domain_misuse",
    "frontend_inferred_identity",
    "policy_freeze",
}
FINDING_STATUSES = {
    "open",
    "scheduled",
    "remediation_candidate",
    "fixed",
    "frozen",
    "accepted_local_identity",
}
SEVERITIES = {"P0", "P1", "P2", "P3"}


def _unique(values: list[str]) -> bool:
    return len(values) == len(set(values))


def _evidence_path(value: str) -> str:
    return value.split("::", 1)[0].strip()


def parse_mermaid_graph(graph_text: str) -> tuple[dict[str, str], list[tuple[str, str, str]], list[str]]:
    errors: list[str] = []
    nodes: dict[str, str] = {}
    for alias, domain in re.findall(r'([A-Z][A-Z0-9_]*)\["([^"]+)"\]', graph_text):
        if alias in nodes:
            errors.append(f"graph node alias is duplicated: {alias}")
        nodes[alias] = domain
    edges: list[tuple[str, str, str]] = []
    for source_alias, kind, target_alias in re.findall(
        r'([A-Z][A-Z0-9_]*)\s*-->\|([^|]+)\|\s*([A-Z][A-Z0-9_]*)',
        graph_text,
    ):
        if source_alias not in nodes or target_alias not in nodes:
            errors.append(
                f"graph edge uses undeclared alias: {source_alias}->{target_alias}"
            )
            continue
        edges.append((nodes[source_alias], nodes[target_alias], kind.strip()))
    return nodes, edges, errors


def validate_matrix(
    matrix: dict[str, Any],
    *,
    doc_text: str,
    graph_text: str,
    root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    if matrix.get("schemaVersion") != "identity-architecture-01/v1":
        errors.append("schemaVersion must be identity-architecture-01/v1")
    if matrix.get("baselineMain") != BASELINE:
        errors.append(f"baselineMain must be {BASELINE}")
    decision = matrix.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
    else:
        if decision.get("globalIdentityRegistry") != "forbidden":
            errors.append("globalIdentityRegistry must be forbidden")
        if decision.get("identityFormatUniformityRequired") is not False:
            errors.append("identityFormatUniformityRequired must be false")
        if decision.get("crossLayerSemanticConsistencyRequired") is not True:
            errors.append("crossLayerSemanticConsistencyRequired must be true")

    domains = matrix.get("domains")
    if not isinstance(domains, list):
        return errors + ["domains must be an array"]
    domain_ids = [str(row.get("id") or "").strip() for row in domains if isinstance(row, dict)]
    if not _unique(domain_ids):
        errors.append("domain ids must be unique")
    missing_domains = sorted(REQUIRED_DOMAINS - set(domain_ids))
    extra_domains = sorted(set(domain_ids) - REQUIRED_DOMAINS)
    if missing_domains:
        errors.append(f"missing domains: {', '.join(missing_domains)}")
    if extra_domains:
        errors.append(f"unexpected domains: {', '.join(extra_domains)}")

    domain_by_id = {
        str(row.get("id") or "").strip(): row
        for row in domains
        if isinstance(row, dict)
    }
    for domain_id, row in domain_by_id.items():
        if not domain_id:
            errors.append("domain id must be non-empty")
            continue
        for field in (
            "definition",
            "authority",
            "representation",
            "uniquenessScope",
            "stability",
            "lifetime",
            "missingPolicy",
            "duplicatePolicy",
            "duplicateAuthority",
            "status",
        ):
            if not str(row.get(field) or "").strip():
                errors.append(f"{domain_id}.{field} is required")
        if row.get("frontendCreation") not in FRONTEND_CREATION_STATES:
            errors.append(f"{domain_id}.frontendCreation is invalid")
        references = row.get("allowedReferences")
        if not isinstance(references, list):
            errors.append(f"{domain_id}.allowedReferences must be an array")
        else:
            for reference in references:
                if reference not in domain_by_id:
                    errors.append(f"{domain_id} references unknown domain {reference}")
        forbidden = row.get("forbiddenMappings")
        if not isinstance(forbidden, list) or not forbidden:
            errors.append(f"{domain_id}.forbiddenMappings must be non-empty")
        elif not _unique([str(value) for value in forbidden]):
            errors.append(f"{domain_id}.forbiddenMappings must be unique")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{domain_id}.evidence must be non-empty")
        else:
            for item in evidence:
                if not (root / _evidence_path(str(item))).exists():
                    errors.append(f"{domain_id} evidence path does not exist: {item}")
        if domain_id not in doc_text:
            errors.append(f"audit document does not mention {domain_id}")

    edges = matrix.get("edges")
    if not isinstance(edges, list):
        errors.append("edges must be an array")
    else:
        edge_keys: list[str] = []
        for edge in edges:
            if not isinstance(edge, dict):
                errors.append("edge must be an object")
                continue
            source = str(edge.get("from") or "").strip()
            target = str(edge.get("to") or "").strip()
            kind = str(edge.get("kind") or "").strip()
            if source not in domain_by_id or target not in domain_by_id:
                errors.append(f"edge references unknown domain: {source}->{target}")
            if not kind:
                errors.append(f"edge {source}->{target} requires kind")
            edge_keys.append(f"{source}->{target}:{kind}")
        if not _unique(edge_keys):
            errors.append("edges must be unique")

    findings = matrix.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    finding_ids = [
        str(row.get("id") or "").strip()
        for row in findings
        if isinstance(row, dict)
    ]
    if not _unique(finding_ids):
        errors.append("finding ids must be unique")
    missing_findings = sorted(REQUIRED_FINDINGS - set(finding_ids))
    if missing_findings:
        errors.append(f"missing findings: {', '.join(missing_findings)}")
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("finding must be an object")
            continue
        finding_id = str(finding.get("id") or "").strip()
        if finding.get("class") not in FINDING_CLASSES:
            errors.append(f"{finding_id}.class is invalid")
        if finding.get("severity") not in SEVERITIES:
            errors.append(f"{finding_id}.severity is invalid")
        if finding.get("status") not in FINDING_STATUSES:
            errors.append(f"{finding_id}.status is invalid")
        if finding.get("baselineDomain") not in domain_by_id:
            errors.append(f"{finding_id}.baselineDomain is unknown")
        for field in ("title", "impact", "owner", "remediation"):
            if not str(finding.get(field) or "").strip():
                errors.append(f"{finding_id}.{field} is required")
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{finding_id}.evidence must be non-empty")
        else:
            for item in evidence:
                if not (root / _evidence_path(str(item))).exists():
                    errors.append(f"{finding_id} evidence path does not exist: {item}")
        if finding_id not in doc_text:
            errors.append(f"audit document does not mention {finding_id}")

    work_packages = matrix.get("workPackages")
    if not isinstance(work_packages, list) or not work_packages:
        errors.append("workPackages must be a non-empty array")
    else:
        for package in work_packages:
            if not isinstance(package, dict):
                errors.append("work package must be an object")
                continue
            package_id = str(package.get("id") or "").strip()
            if not package_id:
                errors.append("work package id is required")
            ids = package.get("findingIds")
            if not isinstance(ids, list) or not ids:
                errors.append(f"{package_id}.findingIds must be non-empty")
            else:
                for finding_id in ids:
                    if finding_id not in finding_ids:
                        errors.append(f"{package_id} references unknown finding {finding_id}")

    graph_nodes, graph_edges, graph_errors = parse_mermaid_graph(graph_text)
    errors.extend(graph_errors)
    graph_domains = set(graph_nodes.values())
    for domain_id in REQUIRED_DOMAINS:
        if domain_id not in graph_domains:
            errors.append(f"graph does not declare domain {domain_id}")
    if not _unique([f"{source}->{target}:{kind}" for source, target, kind in graph_edges]):
        errors.append("graph edges must be unique")

    expected_edges = {
        (
            str(edge.get("from") or "").strip(),
            str(edge.get("to") or "").strip(),
            str(edge.get("kind") or "").strip(),
        )
        for edge in edges or []
        if isinstance(edge, dict)
    }
    actual_edges = set(graph_edges)
    expected_by_pair = {(source, target): kind for source, target, kind in expected_edges}
    actual_by_pair = {(source, target): kind for source, target, kind in actual_edges}
    for pair in sorted(set(expected_by_pair) & set(actual_by_pair)):
        expected_kind = expected_by_pair[pair]
        actual_kind = actual_by_pair[pair]
        if expected_kind != actual_kind:
            errors.append(
                f"graph edge kind mismatch: {pair[0]}->{pair[1]} "
                f"expected {expected_kind}, got {actual_kind}"
            )
    for source, target, kind in sorted(expected_edges - actual_edges):
        if (source, target) not in actual_by_pair:
            errors.append(f"missing graph edge: {source}->{target}:{kind}")
    for source, target, kind in sorted(actual_edges - expected_edges):
        if (source, target) not in expected_by_pair:
            errors.append(f"unregistered graph edge: {source}->{target}:{kind}")
    return errors


def validate_product_source_read_only(
    *,
    root: Path = ROOT,
    baseline: str = BASELINE,
) -> list[str]:
    command = [
        "git",
        "diff",
        "--name-only",
        baseline,
        "--",
        "addons/smart_core",
        "addons/smart_construction_core",
        "frontend/apps/web/src",
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return [f"cannot verify read-only source scope: {completed.stderr.strip()}"]
    changed = [line for line in completed.stdout.splitlines() if line.strip()]
    return [f"product source changed during read-only audit: {path}" for path in changed]


def load_inputs() -> tuple[dict[str, Any], str, str]:
    return (
        json.loads(MATRIX_PATH.read_text(encoding="utf-8")),
        DOC_PATH.read_text(encoding="utf-8"),
        GRAPH_PATH.read_text(encoding="utf-8"),
    )


def main() -> int:
    matrix, doc_text, graph_text = load_inputs()
    errors = validate_matrix(
        matrix,
        doc_text=doc_text,
        graph_text=graph_text,
    )
    errors.extend(validate_product_source_read_only())
    if errors:
        print("Identity architecture audit guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Identity architecture audit guard passed: "
        f"domains={len(matrix['domains'])} findings={len(matrix['findings'])} "
        f"edges={len(matrix['edges'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
