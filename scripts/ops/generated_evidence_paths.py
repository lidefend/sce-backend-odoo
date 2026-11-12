"""Canonical tracked outputs owned by the generated-evidence refresh entry."""

GENERATED_EVIDENCE_PATHS = (
    "contracts/generated/contract_structure_fingerprint.json",
    "docs/audit/test_coverage_registry/test_coverage_registry.json",
    "docs/engineering_convergence/complexity_budget_report.md",
    "docs/engineering_convergence/e2e_journey_matrix.md",
    "docs/engineering_convergence/github_remote_execute.sh",
    "docs/engineering_convergence/github_remote_execution_plan.md",
    "docs/engineering_convergence/module_dependency_map.md",
    "docs/engineering_convergence/p4_p0_03_contract_form_split_evidence.md",
    "docs/engineering_convergence/split_plan_queue.md",
    "docs/engineering_convergence/test_inventory.csv",
    "docs/engineering_convergence/test_inventory_summary.md",
    "docs/frontend_productization/decision-authority-inventory-v1.json",
    "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json",
    "addons/smart_core/core/contract_runtime/domain_field_semantics_generated.py",
    "addons/smart_core/core/contract_runtime/semantic_registry_generated.py",
    "frontend/apps/web/src/app/presentation/industry_renderer_manifest.generated.ts",
    "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts",
)

GENERATED_EVIDENCE_PATH_SET = frozenset(GENERATED_EVIDENCE_PATHS)
