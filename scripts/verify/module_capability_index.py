#!/usr/bin/env python3
"""Read-only module capability reverse index and repo technical facts baseline.

CAP-02B-02. Classifies modules by source, reverse-maps providers to modules,
reports the candidate/scene bidirectional diff, and emits a repository-level
module baseline. It never creates a registry, changes qualifications, modifies
business code or fabricates external module install state.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
SCENES = ROOT / "docs/product/scene_catalog_v2.json"

# Curated classification anchors. Anything external not listed here is unknown.
ODOO_NATIVE_MODULES = {
    "base", "web", "project", "purchase", "purchase_stock", "stock", "account",
    "hr", "mail", "product", "uom", "auth_signup", "sale", "crm", "base_setup",
}
OCA_MODULES = {"base_tier_validation", "base_tier_validation_server_action"}

FIELD_RE = re.compile(r'^\s*(\w+)\s*=\s*fields\.(\w+)\s*\((.*)\)', re.M)
MECHANISM_MIXINS = {
    "tier.validation": ("base_tier_validation", "oca"),
    "mail.thread": ("mail", "odoo_native"),
    "mail.activity.mixin": ("mail", "odoo_native"),
}


def _manifest(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Dict):
            keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
            vals = node.value.values
            manifest = dict(zip(keys, vals))
            return {k: ast.literal_eval(v) for k, v in manifest.items()}
    return {}


def _repo_modules() -> dict[str, dict]:
    modules: dict[str, dict] = {}
    for top, source in (("addons", "sce_custom"), ("customer_addons", "customer_custom"), ("demo_addons", "sce_custom")):
        for d in sorted((ROOT / top).glob("*/")) if (ROOT / top).exists() else []:
            m = d / "__manifest__.py"
            if not m.is_file():
                continue
            man = _manifest(m)
            modules[d.name] = {
                "technical_name": d.name,
                "name": man.get("name", d.name),
                "version": man.get("version", ""),
                "depends": man.get("depends", []),
                "category": man.get("category", ""),
                "source": source,
                "directory": str(d.relative_to(ROOT)),
                "in_repo": True,
            }
    return modules


def _classify_external(name: str) -> tuple[str, str]:
    if name in ODOO_NATIVE_MODULES:
        return "odoo_native", "curated_odoo_native_list"
    if name in OCA_MODULES:
        return "oca", "curated_oca_list"
    return "unknown", "not_in_curated_lists"


def _external_modules(repo: dict[str, dict]) -> dict[str, dict]:
    external: dict[str, dict] = {}
    for mod in repo.values():
        for dep in mod["depends"]:
            if dep in repo:
                continue
            if dep not in external:
                source, evidence = _classify_external(dep)
                external[dep] = {
                    "technical_name": dep,
                    "source": source,
                    "classification_evidence": evidence,
                    "in_repo": False,
                    "depended_by": [mod["technical_name"]],
                }
            else:
                external[dep]["depended_by"].append(mod["technical_name"])
    return external


def _module_facts(mod: dict) -> dict:
    d = ROOT / mod["directory"]
    def count(glob: str) -> int:
        return len(list(d.rglob(glob)))
    return {
        "models": count("models/**/*.py"),
        "handlers": count("handlers/*.py"),
        "services": count("services/**/*.py"),
        "views": count("views/**/*.xml"),
        "actions": count("actions/**/*.xml"),
        "security": count("security/**/*"),
    }


def _parse_fields(text: str) -> list[dict]:
    """Static field facts only; runtime effective fields are not claimed here."""
    fields: list[dict] = []
    for m in FIELD_RE.finditer(text):
        name, ftype, args = m.group(1), m.group(2), m.group(3)
        relation = ""
        if ftype in {"Many2one", "One2many", "Many2many", "Reference"}:
            rm = re.match(r'\s*["\']([^"\']+)["\']', args)
            if rm:
                relation = rm.group(1)
        fields.append({
            "name": name,
            "type": ftype,
            "relation": relation,
            "required": bool(re.search(r'\brequired\s*=\s*True', args)),
            "readonly": bool(re.search(r'\breadonly\s*=\s*True', args)),
            "compute": bool(re.search(r'\bcompute\s*=', args)),
            "related": bool(re.search(r'\brelated\s*=', args)),
        })
    return fields


def _model_facts(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = re.search(r'_name\s*=\s*["\']([^"\']+)["\']', text)
    inherit = re.findall(r'_inherit\s*=\s*\[([^\]]+)\]', text)
    return {
        "file": str(path.relative_to(ROOT)),
        "name": name.group(1) if name else "",
        "inherit": inherit[0] if inherit else "",
        "fields": _parse_fields(text),
    }


def _security_assets(mod: dict) -> dict:
    sec = ROOT / mod["directory"] / "security"
    groups = 0
    rules = 0
    acl_files = 0
    if sec.is_dir():
        for f in sec.rglob("*.xml"):
            text = f.read_text(encoding="utf-8", errors="ignore")
            groups += len(re.findall(r'<record[^>]*model="res\.groups"', text))
            rules += len(re.findall(r'<record[^>]*model="ir\.rule"', text))
        acl_files = len(list(sec.rglob("ir.model.access*.csv")))
    return {"groups": groups, "record_rules": rules, "acl_files": acl_files}


def _mechanism_dependencies(mod: dict) -> list[dict]:
    deps: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for f in (ROOT / mod["directory"]).rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for mixin, (module, source) in MECHANISM_MIXINS.items():
            if re.search(rf'_inherit\s*=\s*.*["\']{re.escape(mixin)}["\']', text) or mixin in text:
                key = (module, mixin)
                if key not in seen:
                    seen.add(key)
                    deps.append({"mechanism": mixin, "module": module, "module_source": source,
                                 "evidence": str(f.relative_to(ROOT))})
    return deps


def _file_digests(mod: dict) -> dict[str, str]:
    digests: dict[str, str] = {}
    for f in sorted((ROOT / mod["directory"]).rglob("*")):
        if f.is_file() and not any(p in f.parts for p in (".pyc", "__pycache__", "node_modules")):
            digests[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return digests


def _fact_digest(identity: dict, models: list[dict], security: dict) -> str:
    payload = json.dumps({"identity": identity, "models": models, "security": security},
                         sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _provider_module(provider_type: str, provider_ref: str) -> list[str]:
    """Resolve the repo module(s) that own a provider ref (fail-safe, no guess)."""
    if not provider_ref or provider_ref in {"", "tbd", "unknown"}:
        return []
    if provider_type == "odoo_action":
        module = provider_ref.split(".")[0]
        return [module] if (ROOT / "addons" / module).is_dir() else []
    if provider_type == "odoo_model":
        modules = set()
        for pattern in (rf'_name\s*=\s*["\']{re.escape(provider_ref)}["\']',
                        rf'_inherit\s*=\s*["\']{re.escape(provider_ref)}["\']'):
            proc = subprocess.run(
                ["rg", "-l", pattern, str(ROOT / "addons")],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
            for f in proc.stdout.splitlines():
                rel = Path(f.strip()).relative_to(ROOT).parts
                if rel[0] == "addons" and len(rel) > 1:
                    modules.add(rel[1])
        base = provider_ref.split(".")[0]
        if base in ODOO_NATIVE_MODULES or base in OCA_MODULES:
            modules.add(base)
        return sorted(modules)
    return []


def _reverse_index() -> dict[str, list[dict]]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    index: dict[str, list[dict]] = {}
    for c in cat:
        for p in c.get("providers", []):
            modules = _provider_module(p.get("provider_type") or "", p.get("provider_ref") or "")
            for m in modules:
                index.setdefault(m, []).append({
                    "capability_key": c["capability_key"],
                    "provider_type": p.get("provider_type"),
                    "provider_ref": p.get("provider_ref"),
                    "disposition": c.get("disposition"),
                })
    return index


def _mechanism_impact() -> dict[str, list[str]]:
    """Map a mechanism-providing module to capabilities whose provider uses it."""
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    impact: dict[str, set[str]] = {}
    for c in cat:
        for p in c.get("providers", []):
            if p.get("provider_type") != "odoo_model":
                continue
            ref = p.get("provider_ref") or ""
            proc = subprocess.run(
                ["rg", "-l", rf'_name\s*=\s*["\']{re.escape(ref)}["\']', str(ROOT / "addons/smart_construction_core/models")],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
            for f in proc.stdout.splitlines():
                text = Path(f.strip()).read_text(encoding="utf-8", errors="ignore")
                for mixin, (module, _source) in MECHANISM_MIXINS.items():
                    if re.search(rf'_inherit\s*=\s*.*["\']{re.escape(mixin)}["\']', text):
                        impact.setdefault(module, set()).add(c["capability_key"])
    return {m: sorted(caps) for m, caps in impact.items()}


def _scene_capabilities() -> set[str]:
    raw = SCENES.read_text(encoding="utf-8")
    caps: set[str] = set()
    for block in re.findall(r'"primary_capabilities":\s*\[([^\]]+)\]', raw):
        caps.update(re.findall(r'"([a-z][a-z0-9_.]+)"', block))
    return caps


def build() -> dict:
    repo = _repo_modules()
    external = _external_modules(repo)
    catalog_keys = {c["capability_key"] for c in json.loads(CATALOG.read_text())["capabilities"]}
    scene_caps = _scene_capabilities()
    reverse = _reverse_index()
    mechanism_impact = _mechanism_impact()
    acceptance = json.loads((ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json").read_text())["capabilities"]

    modules = {}
    for name, mod in repo.items():
        model_files = sorted((ROOT / mod["directory"] / "models").rglob("*.py"))
        models = [_model_facts(f) for f in model_files if "_name" in f.read_text(encoding="utf-8", errors="ignore") or "_inherit" in f.read_text(encoding="utf-8", errors="ignore")]
        security = _security_assets(mod)
        identity = {k: mod[k] for k in ("technical_name", "version", "source", "category")}
        modules[name] = {
            **mod,
            "facts": _module_facts(mod),
            "models": models,
            "security": security,
            "mechanism_dependencies": _mechanism_dependencies(mod),
            "capabilities": reverse.get(name, []),
            "file_digests": _file_digests(mod),
            "fact_digest": _fact_digest(identity, models, security),
        }
    for name, mod in external.items():
        modules[name] = {**mod, "capabilities": reverse.get(name, [])}

    # contract + scene reverse association per capability
    capability_scene = {}
    for cap in catalog_keys:
        capability_scene[cap] = {
            "has_contract": cap in acceptance,
            "in_scene": cap in scene_caps,
        }

    return {
        "schema": "module.capability.index.v1",
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "module_sources": {
            name: {"source": mod["source"], "capability_count": len(mod["capabilities"])}
            for name, mod in modules.items()
        },
        "reverse_index": reverse,
        "mechanism_impact": mechanism_impact,
        "candidate_scene_diff": {
            "candidate_not_in_scene": sorted(catalog_keys - scene_caps),
            "scene_not_in_candidate": sorted(scene_caps - catalog_keys),
            "both": sorted(catalog_keys & scene_caps),
        },
        "module_baseline": {
            name: {
                "technical_name": mod["technical_name"],
                "version": mod.get("version"),
                "source": mod["source"],
                "in_repo": mod.get("in_repo", False),
                "depends": mod.get("depends", []),
                "facts": mod.get("facts", {}),
            }
            for name, mod in modules.items()
        },
        "module_snapshot": {
            name: {
                "identity": {k: mod[k] for k in ("technical_name", "version", "source", "category") if k in mod},
                "models": mod.get("models", []),
                "security": mod.get("security", {}),
                "mechanism_dependencies": mod.get("mechanism_dependencies", []),
                "file_count": len(mod.get("file_digests", {})),
                "fact_digest": mod.get("fact_digest", ""),
            }
            for name, mod in modules.items()
        },
        "capability_relations": {
            cap: {
                "contract": cap in acceptance,
                "scene": cap in scene_caps,
            }
            for cap in sorted(catalog_keys)
        },
        "runtime_only_facts": [
            "ir.module.module install state",
            "live Registry model/field/action resolution",
            "effective ACL / record rules after inheritance",
            "intent handler runtime registration",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/backend/module_capability_index.json")
    args = parser.parse_args()
    payload = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "INDEXED",
        "head": payload["head"],
        "modules": len(payload["module_baseline"]),
        "candidate_not_in_scene": len(payload["candidate_scene_diff"]["candidate_not_in_scene"]),
        "scene_not_in_candidate": len(payload["candidate_scene_diff"]["scene_not_in_candidate"]),
        "output": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
