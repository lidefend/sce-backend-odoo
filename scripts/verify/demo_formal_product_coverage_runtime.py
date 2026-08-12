# -*- coding: utf-8 -*-
"""Audit the isolated Demo tenant against the locked formal product surface.

Run inside ``odoo shell``.  The report deliberately separates entry
availability from sample-data coverage: a menu can be structurally valid while
still being an empty and therefore poor Demo experience.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


POLICY_PATH = Path(
    os.getenv(
        "DEMO_FORMAL_PRODUCT_POLICY_PATH",
        "/mnt/scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
    )
)
OUTPUT_PATH = Path(
    os.getenv(
        "DEMO_FORMAL_PRODUCT_COVERAGE_PATH",
        "/mnt/artifacts/demo/formal_product_coverage_v1.json",
    )
)
PRODUCT_KEY = "construction.standard"

# These are the product's new governed planning backbone.  A Demo reset is
# invalid unless the complete chain exists; menu/model resolution alone cannot
# prove the feature can be demonstrated.
REQUIRED_CORE_MODELS = (
    "project.boq.version",
    "project.boq.line",
    "construction.wbs.plan",
    "construction.work.breakdown",
    "construction.location.breakdown",
    "construction.contract.section",
    "construction.execution.scope",
    "project.boq.allocation",
    "project.cost.plan",
    "project.cost.plan.line",
    "project.cost.plan.node",
)

# An empty result is the correct product state for these surfaces.  Optional
# projections are intentionally owned by tenant/user data modules, while field
# policies are overlays created only when an administrator configures one.
INTENTIONALLY_EMPTY_MODELS = {
    "sc.comprehensive.cost.summary": "optional_projection_requires_tenant_fact_provider",
    "sc.fund.daily.summary": "optional_projection_requires_tenant_fact_provider",
    "sc.operating.metrics.project": "optional_projection_requires_tenant_fact_provider",
    "ui.form.field.policy": "no_overlay_is_the_safe_product_default",
}


def _text(value):
    return str(value or "").strip()


def _xmlid(record):
    if not record:
        return ""
    return record.get_external_id().get(record.id, "") or ""


policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
product = next(
    item
    for item in policy.get("products", [])
    if item.get("product_key") == PRODUCT_KEY and item.get("active") is True
)
capabilities = [item for item in product.get("capabilities", []) if item.get("enabled") is True]

rows = []
errors = []
model_facts = {}

for capability in capabilities:
    menu_xmlid = _text(capability.get("menu_xmlid"))
    model_name = _text(capability.get("res_model"))
    menu = env.ref(menu_xmlid, raise_if_not_found=False)  # noqa: F821
    model_available = bool(model_name and model_name in env)  # noqa: F821
    sample_present = False
    model_kind = "missing"
    probe_error = ""
    if model_available:
        Model = env[model_name].sudo().with_context(active_test=False)  # noqa: F821
        if getattr(Model, "_transient", False):
            model_kind = "transient"
            sample_present = True
        elif getattr(Model, "_auto", True) is False:
            model_kind = "projection"
            try:
                sample_present = bool(Model.search([], limit=1))
            except Exception as exc:  # pragma: no cover - runtime evidence
                probe_error = f"{type(exc).__name__}: {exc}"
        else:
            model_kind = "persistent"
            try:
                sample_present = bool(Model.search([], limit=1))
            except Exception as exc:  # pragma: no cover - runtime evidence
                probe_error = f"{type(exc).__name__}: {exc}"
        model_facts.setdefault(
            model_name,
            {
                "model": model_name,
                "kind": model_kind,
                "sample_present": sample_present,
                "probe_error": probe_error,
                "labels": [],
            },
        )["labels"].append(_text(capability.get("label")))

    row = {
        "capability_key": _text(capability.get("capability_key")),
        "label": _text(capability.get("label")),
        "group_label": _text(capability.get("group_label")),
        "menu_xmlid": menu_xmlid,
        "menu_resolved": bool(menu),
        "runtime_menu_xmlid": _xmlid(menu) if menu else "",
        "model": model_name,
        "model_available": model_available,
        "model_kind": model_kind,
        "sample_present": sample_present,
        "probe_error": probe_error,
    }
    if not menu:
        errors.append(f"menu_missing:{menu_xmlid}")
    if not model_available:
        errors.append(f"model_missing:{model_name}")
    if probe_error:
        errors.append(f"model_probe_failed:{model_name}")
    rows.append(row)

core_rows = []
for model_name in REQUIRED_CORE_MODELS:
    available = model_name in env  # noqa: F821
    count = 0
    if available:
        count = env[model_name].sudo().with_context(active_test=False).search_count([])  # noqa: F821
    core_rows.append({"model": model_name, "available": available, "record_count": int(count)})
    if not available:
        errors.append(f"core_model_missing:{model_name}")
    elif count < 1:
        errors.append(f"core_demo_data_missing:{model_name}")

empty_models = sorted(
    item["model"]
    for item in model_facts.values()
    if item["kind"] in {"persistent", "projection"} and not item["sample_present"]
)
unexpected_empty_models = sorted(set(empty_models) - set(INTENTIONALLY_EMPTY_MODELS))
for model_name in unexpected_empty_models:
    errors.append(f"formal_demo_sample_missing:{model_name}")

payload = {
    "schema": "sc.demo.formal_product_coverage.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,  # noqa: F821
    "authority": str(POLICY_PATH),
    "product_key": PRODUCT_KEY,
    "ok": not errors,
    "summary": {
        "formal_capability_count": len(rows),
        "resolved_menu_count": sum(1 for item in rows if item["menu_resolved"]),
        "resolved_model_count": sum(1 for item in rows if item["model_available"]),
        "unique_model_count": len(model_facts),
        "sampled_unique_model_count": sum(1 for item in model_facts.values() if item["sample_present"]),
        "empty_unique_model_count": len(empty_models),
        "intentionally_empty_model_count": len(set(empty_models) & set(INTENTIONALLY_EMPTY_MODELS)),
        "unexpected_empty_model_count": len(unexpected_empty_models),
        "required_core_model_count": len(core_rows),
        "required_core_ready_count": sum(1 for item in core_rows if item["available"] and item["record_count"] > 0),
        "error_count": len(errors),
    },
    "capabilities": rows,
    "models": sorted(model_facts.values(), key=lambda item: item["model"]),
    "empty_models": empty_models,
    "intentionally_empty_models": {
        name: reason for name, reason in INTENTIONALLY_EMPTY_MODELS.items() if name in empty_models
    },
    "unexpected_empty_models": unexpected_empty_models,
    "required_core_models": core_rows,
    "errors": sorted(set(errors)),
}
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
print(f"[demo.formal_product_coverage] report={OUTPUT_PATH} ok={payload['ok']}")
if errors:
    raise RuntimeError("demo formal product coverage failed: " + ", ".join(sorted(set(errors))))
