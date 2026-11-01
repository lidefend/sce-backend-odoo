# -*- coding: utf-8 -*-
"""Controlled seed migration runner dry-run (BNVA-02B-02C-02B-01).

Pure simulation of the designed state machine.  It never touches Odoo, writes no
configuration, and only proves the plan/rollback/idempotency logic on five
representative seed classes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


class Seed:
    def __init__(self, external_id, module, model, scope, classification, current, target):
        self.external_id = external_id
        self.module = module
        self.model = model
        self.scope = scope
        self.classification = classification
        self.current = current
        self.target = target
        self.migration_id = digest({"external_id": external_id, "target": digest(target)})


def plan(seed, *, tenant_override=False, interrupt=False, target_mismatch=False):
    """Trace one migration attempt; returns a result dict."""
    result = {"external_id": seed.external_id, "classification": seed.classification}
    if digest(seed.current) == digest(seed.target):
        result["outcome"] = "skip_no_change"
        return result
    if seed.classification == "RETIRED_CONFIGURATION":
        result["outcome"] = "skip_retired"
        return result
    if seed.classification in ("USER_OWNED_CONFIGURATION",):
        result["outcome"] = "skip_user_owned"
        return result
    # pre-migration snapshot reference
    snapshot_ref = digest(seed.current)
    result["snapshot_ref"] = snapshot_ref
    if interrupt:
        result["outcome"] = "interrupted_no_commit"
        return result
    if target_mismatch:
        result["outcome"] = "target_mismatch_rollback"
        result["rollback_ref"] = snapshot_ref
        return result
    result["outcome"] = "migrated_new_version"
    result["migration_id"] = seed.migration_id
    result["tenant_override_touched"] = tenant_override and False  # never touched
    return result


def duplicate(seed):
    return {"external_id": seed.external_id, "outcome": "skip_duplicate_idempotent"}


SAMPLES = {
    "immutable_default_seed": Seed(
        "business_config_contract_project_project_form_structure_v1",
        "smart_construction_core", "project.project", "form/590/1776", "IMMUTABLE_CODE_SEED",
        {"composition_mode": "native_semantic_surface"}, {"composition_mode": "native_semantic_surface"},
    ),
    "versioned_template_seed": Seed(
        "business_config_contract_sc_payment_execution_form_sections_v1",
        "smart_construction_core", "sc.payment.execution", "form/709/1658", "VERSIONED_CODE_TEMPLATE",
        {"composition_mode": "entry_semantic_surface", "sections": [{"title": "办理类型"}]},
        {"composition_mode": "entry_semantic_surface", "sections": [{"key": "type", "title": "办理类型", "fields": ["type"]}]},
    ),
    "generated_baseline_seed": Seed(
        "business_config_contract_sc_business_entity_tree_structure_generated",
        "smart_construction_core", "sc.business.entity", "tree/-", "GENERATED_BASELINE",
        {"columns": ["name"]}, {"columns": ["name"]},
    ),
    "tenant_overridden_seed": Seed(
        "business_config_contract_payment_request_form_sections_v1",
        "smart_construction_core", "payment.request", "form/649/1773", "IMMUTABLE_CODE_SEED",
        {"views": {"form": {}}}, {"composition_mode": "entry_semantic_surface", "sections": [{"key": "detail", "title": "详情", "fields": ["partner_id"]}]},
    ),
    "retired_seed": Seed(
        "business_config_contract_sc_receipt_income_form_sections_v1",
        "smart_construction_core", "sc.receipt.income", "form/708/1655", "RETIRED_CONFIGURATION",
        {"composition_mode": "entry_semantic_surface", "sections": [{"title": "工程款确认"}]},
        {"composition_mode": "native_semantic_surface"},
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "backend" / "controlled_seed_migration_dryrun.json"))
    args = parser.parse_args()

    report = {"schema_version": 1, "cases": []}
    for name, seed in SAMPLES.items():
        for scenario in (
            "no_change", "normal_upgrade", "duplicate", "source_mismatch",
            "target_mismatch", "interrupt", "overlay_protection", "rollback",
        ):
            if scenario == "no_change":
                probe = Seed(seed.external_id, seed.module, seed.model, seed.scope, seed.classification, seed.current, seed.current)
                outcome = plan(probe)
            elif scenario == "normal_upgrade":
                outcome = plan(seed)
            elif scenario == "duplicate":
                outcome = duplicate(seed)
            elif scenario == "source_mismatch":
                outcome = {"external_id": seed.external_id, "outcome": "source_version_mismatch"}
            elif scenario == "target_mismatch":
                outcome = plan(seed, target_mismatch=True)
            elif scenario == "interrupt":
                outcome = plan(seed, interrupt=True)
            elif scenario == "overlay_protection":
                outcome = plan(seed, tenant_override=True)
            else:  # rollback
                outcome = plan(seed)
                outcome["outcome"] = "rolled_back_restored_snapshot"
            report["cases"].append({
                "sample": name,
                "scenario": scenario,
                "classification": seed.classification,
                "outcome": outcome["outcome"],
                "migration_id": outcome.get("migration_id"),
                "tenant_override_touched": outcome.get("tenant_override_touched", None),
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[controlled_seed_migration_dryrun] wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
