#!/usr/bin/env python3
"""Fail-closed static guard for the v0.1 product form/list requirement topic."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "config/product_form_list_requirement_matrix_v01.json"
PAGES_PATH = ROOT / "config/representative_page_contracts_v01.json"
BENCHMARK_PATH = ROOT / "config/industry_benchmark_page_quality_v01.json"
EXPECTED_GROUP_COUNTS = {
    "工作台": 4,
    "招投标管理": 5,
    "客商管理": 3,
    "项目管理": 14,
    "合同结算": 7,
    "财务管理": 17,
    "会计模块": 7,
    "行政管理": 5,
    "税务管理": 9,
}
EXPECTED_REPRESENTATIVES = {
    "PFL-010",
    "PFL-019",
    "PFL-027",
    "PFL-035",
    "PFL-067",
    "DERIVED-COST-001",
}
FACT_DIMENSIONS = {
    "menu",
    "action",
    "model",
    "page_contract",
    "workflow",
    "permission",
    "runtime_evidence",
}


class ContractError(ValueError):
    """Raised when the topic assets drift from their frozen contract."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_data(
    matrix: dict[str, Any], pages: dict[str, Any], benchmark: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    items = matrix.get("items", [])
    derived = matrix.get("derived_requirements", [])
    page_items = pages.get("pages", [])

    if matrix.get("schema_version") != "product_form_list_requirement_matrix.v0.1":
        errors.append("unexpected matrix schema_version")
    if pages.get("schema_version") != "representative_page_contracts.v0.1":
        errors.append("unexpected representative page schema_version")
    if benchmark.get("schema_version") != "industry_benchmark_page_quality.v0.1":
        errors.append("unexpected industry benchmark schema_version")
    if len(items) != 71:
        errors.append(f"expected 71 source items, found {len(items)}")

    ids = [item.get("id") for item in items]
    if len(ids) != len(set(ids)):
        errors.append("source item ids must be unique")
    if ids != [f"PFL-{index:03d}" for index in range(1, 72)]:
        errors.append("source item ids must be the contiguous PFL-001..PFL-071 range")

    actual_groups = Counter(item.get("source_group") for item in items)
    if dict(actual_groups) != EXPECTED_GROUP_COUNTS:
        errors.append(f"source group counts drifted: {dict(actual_groups)}")
    if matrix.get("source_group_counts") != EXPECTED_GROUP_COUNTS:
        errors.append("declared source_group_counts drifted")

    allowed_dispositions = set(matrix.get("dispositions", []))
    allowed_recipes = set(matrix.get("recipes", []))
    if allowed_dispositions != {"implemented", "contract_gap", "planned", "merge"}:
        errors.append("four-state disposition vocabulary drifted")
    if allowed_recipes != {
        "dashboard",
        "master_data",
        "business_document",
        "complex_workspace",
        "ledger",
        "report",
        "configuration",
    }:
        errors.append("seven-recipe vocabulary drifted")

    for item in [*items, *derived]:
        item_id = item.get("id", "<missing>")
        missing = FACT_DIMENSIONS - set(item)
        if missing:
            errors.append(f"{item_id} missing fact dimensions: {sorted(missing)}")
        if item.get("disposition") not in allowed_dispositions:
            errors.append(f"{item_id} has invalid disposition")
        if item.get("recipe") not in allowed_recipes:
            errors.append(f"{item_id} has invalid recipe")
        if item.get("runtime_evidence") != "runtime_unverified":
            errors.append(f"{item_id} must remain runtime_unverified in this source-only topic")

    derived_ids = {item.get("id") for item in derived}
    if "DERIVED-COST-001" not in derived_ids:
        errors.append("missing derived Cost Center representative requirement")
    if len(page_items) != 6:
        errors.append(f"expected six representative pages, found {len(page_items)}")
    representative_ids = {page.get("requirement_id") for page in page_items}
    if representative_ids != EXPECTED_REPRESENTATIVES:
        errors.append(f"representative page set drifted: {sorted(representative_ids)}")

    valid_requirement_ids = set(ids) | derived_ids
    for page in page_items:
        page_id = page.get("requirement_id", "<missing>")
        if page_id not in valid_requirement_ids:
            errors.append(f"{page_id} does not resolve to a matrix requirement")
        authority = page.get("authority", {})
        for key in ("menu", "action", "model", "native_views", "permission_groups", "runtime_evidence"):
            if not authority.get(key):
                errors.append(f"{page_id} authority is missing {key}")
        if authority.get("runtime_evidence") != "pending_browser_acceptance":
            errors.append(f"{page_id} must not claim completed runtime evidence")
        acceptance = set(page.get("acceptance", []))
        for state in ("empty", "forbidden", "mobile_390"):
            if state not in acceptance:
                errors.append(f"{page_id} acceptance is missing {state}")

    if pages.get("ui_framework_policy", "").startswith("not_selected") is False:
        errors.append("this topic must not select a UI framework")
    product_stage = pages.get("product_stage", {})
    if product_stage.get("layer") != "P1_construction_industry_standard_product":
        errors.append("representative work must remain in the P1 standard-product layer")
    if product_stage.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope must remain forbidden")
    if product_stage.get("decision_authority") != "reusable_product_capability_and_repository_facts":
        errors.append("product decisions must be based on reusable capability and repository facts")
    if product_stage.get("sequence") != [
        "business_capability",
        "backend_and_native_contract",
        "runtime_acceptance",
        "component_evaluation",
    ]:
        errors.append("business capability must precede component evaluation")
    benchmark_contract = pages.get("benchmark_contract", {})
    if benchmark_contract.get("minimum_before_rollout") != 2:
        errors.append("representative rollout must require benchmark level 2")
    if benchmark_contract.get("runtime_level_requires_browser_evidence") is not True:
        errors.append("benchmark runtime level must require browser evidence")

    benchmark_rows = benchmark.get("benchmarks", [])
    vendors = {row.get("vendor") for row in benchmark_rows}
    if len(benchmark_rows) < 6 or len(vendors) < 4:
        errors.append("benchmark baseline must use at least six official sources across four vendors")
    for row in benchmark_rows:
        if not str(row.get("official_url", "")).startswith("https://"):
            errors.append("benchmark source must be an official HTTPS URL")
        if not row.get("observed_patterns"):
            errors.append("benchmark source is missing observed patterns")
    if len(benchmark.get("information_completeness_dimensions", [])) != 8:
        errors.append("information completeness must retain eight dimensions")
    if len(benchmark.get("handling_convenience_dimensions", [])) != 8:
        errors.append("handling convenience must retain eight dimensions")
    if set(benchmark.get("page_focus", {})) != EXPECTED_REPRESENTATIVES:
        errors.append("benchmark page_focus must cover the exact six representatives")
    if "score" in benchmark:
        errors.append("source-only benchmark must not claim a product score")
    source_hash = matrix.get("source", {}).get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        errors.append("source snapshot sha256 must be a lowercase 64-character digest")
    return errors


def repository_corpus() -> str:
    roots = [
        ROOT / "addons/smart_construction_core",
        ROOT / "docs/product",
        ROOT / "config",
    ]
    suffixes = {".py", ".xml", ".json", ".md", ".csv"}
    chunks: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in suffixes:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def validate_repository_anchors(pages: dict[str, Any], corpus: str) -> list[str]:
    errors: list[str] = []
    external_models = {"res.partner"}
    for page in pages["pages"]:
        page_id = page["requirement_id"]
        authority = page["authority"]
        for key in ("menu", "action"):
            xmlid = authority[key]
            local_id = xmlid.rsplit(".", 1)[-1]
            if f'id="{local_id}"' not in corpus and f"id='{local_id}'" not in corpus:
                errors.append(f"{page_id} unresolved {key} anchor: {xmlid}")
        model = authority["model"]
        if model not in external_models and not re.search(
            rf"_name\s*=\s*['\"]{re.escape(model)}['\"]", corpus
        ):
            errors.append(f"{page_id} unresolved model anchor: {model}")
        product_contract = authority.get("product_contract")
        if product_contract:
            local_id = product_contract.rsplit(".", 1)[-1]
            if f'id="{local_id}"' not in corpus:
                errors.append(f"{page_id} unresolved product contract: {product_contract}")
    return errors


def main() -> int:
    matrix = load_json(MATRIX_PATH)
    pages = load_json(PAGES_PATH)
    benchmark = load_json(BENCHMARK_PATH)
    errors = validate_data(matrix, pages, benchmark)
    if not errors:
        errors.extend(validate_repository_anchors(pages, repository_corpus()))
    if errors:
        for error in errors:
            print(f"[product-form-list-v01] FAIL {error}", file=sys.stderr)
        return 1
    dispositions = Counter(item["disposition"] for item in matrix["items"])
    print(
        "[product-form-list-v01] PASS "
        f"source_items=71 representatives=6 dispositions={dict(sorted(dispositions.items()))} "
        "runtime=unverified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
