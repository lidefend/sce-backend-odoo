#!/usr/bin/env python3
"""Generate and/or validate the CAP-01B capability candidate catalog.

Read-only checker by default. ``--generate`` writes only after the in-memory
catalog passes every gate. ``--self-test`` runs negative test cases against the
gates to prove they fail closed. It never modifies the formal catalog, release
states, qualifications or runtime.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/product/capability_candidate_catalog_v1.json"
B2 = ROOT / "docs/product/capability_reconciliation_matrix_v1.md"

# disposition: keep / defer / exclude ; layer: atomic / composite ; canonical
# key overrides represent rename with the old key retained as compatibility alias.
CLASSIFICATION = {
    "project.initiation.enter": {"disposition": "keep", "layer": "atomic", "canonical_key": "project.initiation.create"},
    "project.lifecycle.transition": {"disposition": "keep", "layer": "atomic"},
    "construction.plan.manage": {"disposition": "keep", "layer": "composite"},
    "construction.plan.report": {"disposition": "keep", "layer": "atomic"},
    "cost.budget.manage": {"disposition": "keep", "layer": "composite"},
    "cost.boq.manage": {"disposition": "keep", "layer": "composite"},
    "cost.profit.compare": {"disposition": "keep", "layer": "composite"},
    "cost.progress.report": {"disposition": "keep", "layer": "atomic"},
    "contract.expense.track": {"disposition": "keep", "layer": "atomic"},
    "contract.income.track": {"disposition": "keep", "layer": "atomic"},
    "contract.settlement.audit": {"disposition": "keep", "layer": "atomic"},
    "equipment.plan.manage": {"disposition": "keep", "layer": "composite"},
    "labor.plan.manage": {"disposition": "keep", "layer": "composite"},
    "governance.runtime.audit": {"disposition": "keep", "layer": "atomic"},
    "project.list.open": {"disposition": "defer", "layer": "atomic"},
    "project.dashboard.enter": {"disposition": "defer", "layer": "atomic"},
    "project.risk.list": {"disposition": "defer", "layer": "atomic"},
    "project.structure.manage": {"disposition": "defer", "layer": "composite"},
    "project.plan_bootstrap.enter": {"disposition": "defer", "layer": "atomic"},
    "project.execution.enter": {"disposition": "defer", "layer": "atomic"},
    "project.execution.advance": {"disposition": "defer", "layer": "atomic"},
    "construction.diary.open": {"disposition": "defer", "layer": "atomic"},
    "equipment.request.list": {"disposition": "defer", "layer": "atomic"},
    "equipment.settlement.list": {"disposition": "defer", "layer": "atomic"},
    "equipment.usage.list": {"disposition": "defer", "layer": "atomic"},
    "labor.attendance.list": {"disposition": "defer", "layer": "atomic"},
    "labor.request.list": {"disposition": "defer", "layer": "atomic"},
    "labor.settlement.list": {"disposition": "defer", "layer": "atomic"},
    "quality.issue.list": {"disposition": "defer", "layer": "atomic"},
    "quality.recheck.list": {"disposition": "defer", "layer": "atomic"},
    "quality.rectification.list": {"disposition": "defer", "layer": "atomic"},
    "safety.issue.list": {"disposition": "defer", "layer": "atomic"},
    "safety.recheck.list": {"disposition": "defer", "layer": "atomic"},
    "safety.rectification.list": {"disposition": "defer", "layer": "atomic"},
    "material.procurement.list": {"disposition": "defer", "layer": "atomic"},
    "finance.exception.monitor": {"disposition": "defer", "layer": "atomic"},
    "finance.plan.funding": {"disposition": "defer", "layer": "atomic"},
    "finance.settlement.order": {"disposition": "defer", "layer": "atomic"},
    "analytics.lifecycle.monitor": {"disposition": "defer", "layer": "atomic"},
    "governance.scene.openability": {"disposition": "defer", "layer": "atomic"},
    # --- exclude (not capabilities; page/navigation entries) ---
    "project.lifecycle.open": {"disposition": "exclude", "layer": "atomic"},
    "project.dashboard.open": {"disposition": "exclude", "layer": "atomic"},
    "project.board.open": {"disposition": "exclude", "layer": "atomic"},
    "project.task.list": {"disposition": "exclude", "layer": "atomic"},
    "project.task.board": {"disposition": "exclude", "layer": "atomic"},
    "project.document.open": {"disposition": "exclude", "layer": "atomic"},
    "project.weekly_report.open": {"disposition": "exclude", "layer": "atomic"},
    "contract.center.open": {"disposition": "exclude", "layer": "atomic"},
    "cost.ledger.open": {"disposition": "exclude", "layer": "atomic"},
    "finance.approval.center": {"disposition": "exclude", "layer": "atomic"},
    "finance.invoice.list": {"disposition": "exclude", "layer": "atomic"},
    "finance.ledger.payment": {"disposition": "exclude", "layer": "atomic"},
    "finance.ledger.treasury": {"disposition": "exclude", "layer": "atomic"},
    "finance.metrics.operating": {"disposition": "exclude", "layer": "atomic"},
    "finance.payment_request.form": {"disposition": "exclude", "layer": "atomic"},
    "finance.payment_request.list": {"disposition": "exclude", "layer": "atomic"},
    "material.catalog.open": {"disposition": "exclude", "layer": "atomic"},
    "analytics.dashboard.executive": {"disposition": "exclude", "layer": "atomic"},
    "analytics.exception.list": {"disposition": "exclude", "layer": "atomic"},
    "analytics.project.focus": {"disposition": "exclude", "layer": "atomic"},
    "governance.capability.matrix": {"disposition": "exclude", "layer": "atomic"},
    "workspace.project.watch": {"disposition": "exclude", "layer": "atomic"},
    "workspace.today.focus": {"disposition": "exclude", "layer": "atomic"},
}

PROVIDERS = {
    "project.initiation.create": [
        {"provider_type": "odoo_intent", "provider_ref": "project.initiation.enter", "contract_ref": "addons/smart_construction_core/handlers/project_initiation_enter.py", "provider_status": "verified"},
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_project_initiation", "contract_ref": "addons/smart_construction_core/views/menu.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
    "project.list.open": [
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_sc_project_list", "contract_ref": "addons/smart_construction_core/actions/project_list_actions.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
    "project.lifecycle.transition": [
        {"provider_type": "unknown", "provider_ref": "", "contract_ref": "", "provider_status": "unverified", "pending_reason": "lifecycle transition contract not yet located as a code asset"},
    ],
}

COMPOSITE_DEPENDENCIES = {
    "construction.plan.manage": ["project.list.open", "construction.plan.report"],
    "cost.budget.manage": ["project.list.open"],
    "cost.boq.manage": ["project.list.open"],
    "cost.profit.compare": ["project.list.open"],
    "equipment.plan.manage": ["project.list.open"],
    "labor.plan.manage": ["project.list.open"],
}


def _canonical(key: str, meta: dict) -> str:
    return meta.get("canonical_key") or key


def _unknown_provider() -> list[dict]:
    return [{"provider_type": "unknown", "provider_ref": "", "contract_ref": "",
             "provider_status": "unverified", "pending_reason": "provider not yet reconciled"}]


def build_catalog() -> dict:
    capabilities = []
    seen = set()
    for old_key, meta in CLASSIFICATION.items():
        canonical = _canonical(old_key, meta)
        if meta["disposition"] == "exclude":
            continue
        if canonical in seen:
            raise ValueError("duplicate canonical key: " + canonical)
        seen.add(canonical)
        providers = PROVIDERS.get(canonical, _unknown_provider())
        dependencies = COMPOSITE_DEPENDENCIES.get(canonical, []) if meta["layer"] == "composite" else []
        capabilities.append({
            "capability_key": canonical,
            "layer": meta["layer"],
            "disposition": meta["disposition"],
            "qualification": "unreleased",
            "contract_status": "unverified",
            "release_state": "candidate",
            "providers": providers,
            "dependencies": dependencies,
            "source_refs": [old_key],
            "compatibility_aliases": [old_key] if old_key != canonical else [],
        })
    return {
        "schema": "capability.candidate.catalog.v1",
        "version": "v2",
        "stage": "CAP-01B candidate (not published)",
        "domain_vocabulary": ["project", "contract", "cost", "finance", "material", "construction", "quality", "safety", "labor", "equipment", "analytics", "governance", "workspace"],
        "domain_policy": "extensible via identity governance, not a permanently closed enum",
        "closure_note": "reference closure is verified here; qualification closure is deferred to CAP-01C",
        "capabilities": capabilities,
    }


def _b2_classification() -> dict[str, set[str]]:
    """Parse B2 markdown into per-disposition historical identity sets."""
    text = B2.read_text(encoding="utf-8")
    result = {"keep": set(), "defer": set(), "exclude": set()}
    for line in text.splitlines():
        m = re.match(r"^\| ([a-z][a-z0-9_.-]+) \| (keep|defer|exclude)", line.strip())
        if m:
            result[m.group(2)].add(m.group(1))
    return result


def _rg_files(patterns: list[str], path: str = "addons", globs: tuple[str, ...] = ("*.py", "*.xml")) -> list[str] | None:
    """Return matching file list, or None on tool failure (fail-closed)."""
    if not patterns:
        return []
    args = ["rg", "-l"]
    for g in globs:
        args.extend(["--glob", g])
    for pat in patterns:
        args.extend(["-e", pat])
    args.append(path)
    try:
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _file_contains(paths: list[str] | None, pattern: str) -> bool:
    if not paths:
        return False
    try:
        result = subprocess.run(
            ["rg", "-q", "-e", pattern, *paths], cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _intent_registration_count(intent: str) -> int | None:
    """Count registration-chain declarations for an intent (fail-closed)."""
    patterns = [
        r'\(\s*["\']' + re.escape(intent) + r'["\']\s*,',      # ("intent", Handler) tuple
        r'registry\[["\']' + re.escape(intent) + r'["\']\]\s*=',  # registry["intent"] = Handler
    ]
    reg_files = [
        ROOT / "addons/smart_construction_core/core_extension_intent_handlers.py",
        ROOT / "addons/smart_construction_core/core_extension.py",
    ]
    count = 0
    for f in reg_files:
        if not f.is_file():
            continue
        for pattern in patterns:
            try:
                result = subprocess.run(["rg", "-c", "-e", pattern, str(f)], cwd=ROOT, text=True, capture_output=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                return None
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    n = line.rsplit(":", 1)[-1].strip()
                    if n.isdigit():
                        count += int(n)
    # smart_core native handlers are auto-registered via register_all_handlers.
    if count == 0:
        native = _rg_files([r'INTENT_TYPE\s*=\s*["\']' + re.escape(intent) + r'["\']'], "addons/smart_core/handlers", ("*.py",))
        if native:
            count = 1
    return count


def _handler_class_name(intent: str) -> str | None:
    """Extract the BaseIntentHandler subclass name that declares this intent."""
    decl = _rg_files([r'INTENT_TYPE\s*=\s*["\']' + re.escape(intent) + r'["\']'])
    if not decl:
        return None
    handler_files = [f for f in decl if "/handlers/" in f and "/tests/" not in f]
    if len(handler_files) != 1:
        return None
    text = (ROOT / handler_files[0]).read_text(encoding="utf-8")
    m = re.search(r"class\s+(\w+)\s*\([^)]*BaseIntentHandler", text)
    return m.group(1) if m else None


def _intent_registration_binds_handler(intent: str, handler_class: str) -> bool | None:
    """Verify the registration declaration binds the exact handler class."""
    patterns = [
        r'\(\s*["\']' + re.escape(intent) + r'["\']\s*,\s*' + re.escape(handler_class) + r'\s*\)',
        r'registry\[["\']' + re.escape(intent) + r'["\']\]\s*=\s*' + re.escape(handler_class) + r'\b',
    ]
    files = _rg_files(patterns, "addons", ("*.py",))
    return files is not None and bool(files)


def _provider_ref_registered(provider_type: str, provider_ref: str) -> bool:
    """Type-specific exact registration-fact verification."""
    if not provider_ref or provider_ref in {"tbd", "unknown"}:
        return False
    if provider_type == "odoo_intent":
        # Must be a real handler: declared INTENT_TYPE inside a handlers/
        # package file that subclasses BaseIntentHandler, declared exactly once,
        # and actually wired into the runtime registration chain.
        decl = _rg_files([r'INTENT_TYPE\s*=\s*["\']' + re.escape(provider_ref) + r'["\']'])
        if decl is None:
            return False
        handler_files = [f for f in decl if "/handlers/" in f and "/tests/" not in f]
        if len(handler_files) != 1:
            return False
        if not _file_contains(handler_files, r"BaseIntentHandler"):
            return False
        handler_class = _handler_class_name(provider_ref)
        if not handler_class:
            return False
        count = _intent_registration_count(provider_ref)
        if count != 1:
            return False
        bound = _intent_registration_binds_handler(provider_ref, handler_class)
        return bound is True
    if provider_type == "odoo_action":
        module = provider_ref.split(".")[0]
        local = provider_ref.rsplit(".", 1)[-1]
        # The action record must be defined in the same module, as an
        # ir.actions record (not merely an id= string somewhere else).
        files = _rg_files([r'id="' + re.escape(local) + r'"\s+model="ir\.actions\.(act_window|client|server)"'], f"addons/{module}")
        if files is None:
            return False
        return bool(files)
    if provider_type == "odoo_model":
        files = _rg_files([
            r'_name\s*=\s*["\']' + re.escape(provider_ref) + r'["\']',
            r'_inherit\s*=\s*["\']' + re.escape(provider_ref) + r'["\']',
        ], "addons", ("*.py",))
        if files is None:
            return False
        return any("/models/" in f and "/tests/" not in f for f in files)
    # service / api / ai_provider / domain_provider have no offline registry in
    # this repository yet; they cannot be verified offline.
    return False


def _catalog_from_classification() -> dict[str, dict]:
    out = {}
    for old_key, meta in CLASSIFICATION.items():
        if meta["disposition"] == "exclude":
            continue
        canonical = _canonical(old_key, meta)
        out[canonical] = {"source_refs": [old_key], "aliases": [old_key] if old_key != canonical else []}
    return out


def validate(catalog: dict) -> list[str]:
    errors = []
    caps = catalog["capabilities"]
    keys = [c["capability_key"] for c in caps]
    if len(keys) != len(set(keys)):
        errors.append("duplicate capability_key")
    key_set = set(keys)

    # identity-level B2/B6 closure over all 63 historical identities.
    b2 = _b2_classification()
    expected_sources = {k for k, m in CLASSIFICATION.items() if m["disposition"] in {"keep", "defer"}}
    actual_sources = set()
    for c in caps:
        actual_sources.update(c.get("source_refs", []))
        actual_sources.update(c.get("compatibility_aliases", []))
    if actual_sources != expected_sources:
        errors.append("source identity set mismatch: missing=" + str(sorted(expected_sources - actual_sources))
                      + " extra=" + str(sorted(actual_sources - expected_sources)))
    if b2["keep"] != {k for k, m in CLASSIFICATION.items() if m["disposition"] == "keep"}:
        errors.append("B2 keep identities do not match classification")
    if b2["defer"] != {k for k, m in CLASSIFICATION.items() if m["disposition"] == "defer"}:
        errors.append("B2 defer identities do not match classification")
    if b2["exclude"] != {k for k, m in CLASSIFICATION.items() if m["disposition"] == "exclude"}:
        errors.append("B2 exclude identities do not match classification")
    if len(CLASSIFICATION) != 63:
        errors.append("classification must cover exactly 63 historical identities: " + str(len(CLASSIFICATION)))

    # cycle detection over composite dependency edges.
    deps = {c["capability_key"]: c.get("dependencies", []) for c in caps}
    color = {}
    def visit(n, stack):
        color[n] = 1
        for m in deps.get(n, []):
            if m in stack:
                errors.append("dependency cycle: " + " -> ".join(stack + [n, m]))
            elif color.get(m, 0) == 0 and m in deps:
                visit(m, stack + [n])
        color[n] = 2
    for n in deps:
        if color.get(n, 0) == 0:
            visit(n, [])

    for c in caps:
        if not c.get("source_refs"):
            errors.append("missing source_ref: " + c["capability_key"])
        if c.get("qualification") != "unreleased":
            errors.append("qualification not unreleased: " + c["capability_key"])
        if c.get("release_state") != "candidate":
            errors.append("release_state must be candidate: " + c["capability_key"])
        if c.get("contract_status") not in {"unverified", "verified"}:
            errors.append("invalid contract_status: " + c["capability_key"])
        for dep in c.get("dependencies", []):
            if dep not in key_set:
                errors.append("unresolved dependency: " + c["capability_key"] + " -> " + dep)
        if c.get("layer") == "composite" and c.get("disposition") == "keep" and not c.get("dependencies"):
            errors.append("kept composite without dependencies: " + c["capability_key"])
        for p in c.get("providers", []):
            st = p.get("provider_status")
            if st not in {"verified", "unverified"}:
                errors.append("invalid provider_status: " + c["capability_key"])
            if st == "verified":
                ref = p.get("contract_ref") or ""
                if not ref or ref.startswith(".") or not (ROOT / ref).is_file():
                    errors.append("verified provider contract_ref not locatable: " + c["capability_key"] + " -> " + ref)
                if not _provider_ref_registered(p.get("provider_type") or "", p.get("provider_ref") or ""):
                    errors.append("verified provider_ref not found as exact registration fact: " + c["capability_key"]
                                  + " -> " + str(p.get("provider_type")) + ":" + str(p.get("provider_ref")))
            if p.get("provider_type") == "unknown" and p.get("provider_ref"):
                errors.append("unknown provider must not carry provider_ref: " + c["capability_key"])
    return errors


def _self_test() -> int:
    """Negative cases prove the gates fail closed."""
    failures = []
    base = build_catalog()

    # 1. duplicate canonical key.
    bad = json.loads(json.dumps(base))
    bad["capabilities"].append(dict(bad["capabilities"][0]))
    if not validate(bad):
        failures.append("duplicate key not caught")

    # 2. missing source_ref.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["source_refs"] = []
    if not validate(bad):
        failures.append("missing source_ref not caught")

    # 3. non-unreleased qualification.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["qualification"] = "standard"
    if not validate(bad):
        failures.append("non-unreleased qualification not caught")

    # 4. wrong provider alias.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["compatibility_aliases"] = ["fake.old.key"]
    if not validate(bad):
        failures.append("wrong alias not caught")

    # 5. extra source identity.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["source_refs"] = ["invented.identity"]
    if not validate(bad):
        failures.append("invented source identity not caught")

    # 6. non-existent intent provider.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["providers"] = [
        {"provider_type": "odoo_intent", "provider_ref": "no.such.intent", "contract_ref": "addons/smart_construction_core/handlers/project_initiation_enter.py", "provider_status": "verified"}
    ]
    if not validate(bad):
        failures.append("non-existent intent provider not caught")

    # 7. action in wrong module.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["providers"] = [
        {"provider_type": "odoo_action", "provider_ref": "smart_core.action_project_initiation", "contract_ref": "addons/smart_construction_core/views/menu.xml", "provider_status": "verified"}
    ]
    if not validate(bad):
        failures.append("wrong-module action provider not caught")

    # 8. non-existent model provider.
    bad = json.loads(json.dumps(base))
    bad["capabilities"][0]["providers"] = [
        {"provider_type": "odoo_model", "provider_ref": "no.such.model", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"}
    ]
    if not validate(bad):
        failures.append("non-existent model provider not caught")

    # 9. rg tool failure must fail closed (verified provider becomes unverifiable).
    import sys
    mod = sys.modules[__name__]
    original = mod.subprocess.run
    def _boom(*a, **k):
        raise OSError("rg unavailable")
    mod.subprocess.run = _boom
    try:
        if not validate(base):
            failures.append("rg failure not fail-closed")
    finally:
        mod.subprocess.run = original

    # 10. duplicate intent identity (app.catalog declared in both smart_core and
    # smart_construction_core handlers) -> must FAIL.
    if mod._provider_ref_registered("odoo_intent", "app.catalog"):
        failures.append("duplicate intent identity passed registration-chain check")

    # 11. registration binding must name the exact handler class.
    if not mod._intent_registration_binds_handler("project.initiation.enter", "ProjectInitiationEnterHandler"):
        failures.append("correct intent-handler binding rejected")
    if mod._intent_registration_binds_handler("project.initiation.enter", "WrongHandler"):
        failures.append("wrong intent-handler binding accepted")

    if failures:
        print("SELF-TEST FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="write the candidate catalog after full in-memory validation")
    parser.add_argument("--check", action="store_true", help="run full semantic gates (read-only)")
    parser.add_argument("--self-test", action="store_true", help="run negative gate cases")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    if args.generate:
        catalog = build_catalog()
        errors = validate(catalog)
        if errors:
            print("FAIL (catalog not written)")
            for e in errors:
                print(" -", e)
            return 1
        OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("generated", OUT)
        return 0

    catalog = json.loads(OUT.read_text(encoding="utf-8"))
    errors = validate(catalog)
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    keep = sum(1 for c in catalog["capabilities"] if c["disposition"] == "keep")
    defer = sum(1 for c in catalog["capabilities"] if c["disposition"] == "defer")
    print(f"PASS keep={keep} defer={defer} total={len(catalog['capabilities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
