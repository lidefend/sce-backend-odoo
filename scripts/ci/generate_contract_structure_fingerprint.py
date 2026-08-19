#!/usr/bin/env python3
"""Generate a contract structure fingerprint from code.

For each domain contract registered in contracts/registry.yaml, this script
statically extracts the contract-relevant structure from the Odoo model code:

1. Field declarations (name, Odoo field type, required, readonly, store,
   compute) for every field listed in the contract YAML.
2. State-machine states and transitions from state_machine.py (when the
   contract's model is registered there).

The extracted structure is canonicalised (sorted keys, stable ordering) and
written to contracts/generated/contract_structure_fingerprint.json.

When used together with enforce_contract_structure_lock.py in CI, this creates
a hard gate: if the contract-relevant code structure changes, the fingerprint
changes, and CI fails unless the developer also updated the contract YAML files
and re-generated the fingerprint.

Usage:
    python3 scripts/ci/generate_contract_structure_fingerprint.py            # check-only (exit 1 if stale)
    python3 scripts/ci/generate_contract_structure_fingerprint.py --write   # write updated fingerprint
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "contracts"
REGISTRY_PATH = CONTRACTS_DIR / "registry.yaml"
FINGERPRINT_PATH = CONTRACTS_DIR / "generated" / "contract_structure_fingerprint.json"
STATE_MACHINE_PATH = ROOT / "addons" / "smart_construction_core" / "models" / "support" / "state_machine.py"
ADDONS_DIR = ROOT / "addons"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_model_file_by_class(class_name: str) -> Optional[Path]:
    """Find the Python file that defines *class_name* by searching addons."""
    if not class_name:
        return None
    pattern = re.compile(rf'^class\s+{re.escape(class_name)}\s*\(')
    # Sort glob results for deterministic, cross-filesystem ordering
    for py_file in sorted(ADDONS_DIR.rglob("*.py")):
        try:
            for line in py_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if pattern.match(line):
                    return py_file
        except Exception:
            continue
    return None


def find_model_file(module: str, model_dot_name: str, entity: str) -> Tuple[Optional[Path], Optional[str]]:
    """Find the model file and return (path, odoo_model_name).

    Tries source_of_truth first, then class-name search.
    """
    # Try source_of_truth
    if module and model_dot_name:
        module_dir = ADDONS_DIR / module
        if module_dir.is_dir():
            # Try common conventions: derive file name from model name
            # payment.request -> payment_request.py, sc.payment.execution -> payment_execution.py
            underscore_name = model_dot_name.replace(".", "_")
            parts = model_dot_name.split(".")
            last_part = parts[-1]
            candidates = [
                module_dir / "models" / "core" / f"{underscore_name}.py",
                module_dir / "models" / "core" / f"{last_part}.py",
                module_dir / "models" / f"{underscore_name}.py",
                module_dir / "models" / f"{last_part}.py",
            ]
            for c in candidates:
                if c.is_file():
                    text = c.read_text(encoding="utf-8", errors="ignore")
                    if model_dot_name in text:
                        return c, model_dot_name

    # Fallback: search by entity class name
    if entity and entity != model_dot_name:
        model_path = find_model_file_by_class(entity)
        if model_path:
            # Extract _name from the file
            text = model_path.read_text(encoding="utf-8", errors="ignore")
            name_match = re.search(r'_name\s*=\s*["\']([\w.]+)["\']', text)
            odoo_name = name_match.group(1) if name_match else entity
            return model_path, odoo_name

    # Last resort: try model name directly
    if model_dot_name:
        model_path = find_model_file_by_class(model_dot_name)
        if model_path:
            return model_path, model_dot_name

    return None, None


# --- state machine parsing --------------------------------------------------

def parse_state_machine_file() -> Dict[str, Dict[str, Any]]:
    """Parse state_machine.py and return a map of model_name -> {states, transitions}."""
    if not STATE_MACHINE_PATH.is_file():
        return {}

    text = STATE_MACHINE_PATH.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    # Step 1: Extract constant name -> model_name mapping
    # Pattern:    CONSTANT_NAME = "model.name"
    const_map: Dict[str, str] = {}
    for line in lines:
        m = re.match(r'\s+([A-Z_]+)\s*=\s*"([\w.]+)"', line)
        if m:
            const_map[m.group(1)] = m.group(2)

    # Step 2: Extract each {CONSTANT}_STATES and {CONSTANT}_TRANSITIONS
    result: Dict[str, Dict[str, Any]] = {}

    for const_name, model_name in const_map.items():
        entry: Dict[str, Any] = {"constant": const_name, "model": model_name}

        # Find {CONSTANT}_STATES = [ ... ]
        states_key = f"{const_name}_STATES"
        states_block = _extract_balanced_block(lines, states_key, "[", "]")
        if states_block:
            # Extract state names: only match ("word" where word is ASCII lowercase)
            state_names = re.findall(r'\(\s*"([a-z_]+)"', states_block)
            entry["states"] = sorted(set(state_names))

        # Find {CONSTANT}_TRANSITIONS = { ... }
        trans_key = f"{const_name}_TRANSITIONS"
        trans_block = _extract_balanced_block(lines, trans_key, "{", "}")
        if trans_block:
            transitions: Dict[str, List[str]] = {}
            # Match "state": {"target1", "target2", ...}
            for tm in re.finditer(r'"([a-z_]+)"\s*:\s*\{([^}]*)\}', trans_block):
                src = tm.group(1)
                targets = sorted(re.findall(r'"([a-z_]+)"', tm.group(2)))
                transitions[src] = targets
            entry["transitions"] = dict(sorted(transitions.items()))

        result[model_name] = entry

    return result


def _extract_balanced_block(lines: List[str], key: str, open_ch: str, close_ch: str) -> Optional[str]:
    """Extract the content of a block like  KEY = { ... } or KEY = [ ... ].

    Handles nested braces/brackets by counting depth.
    """
    # Find the line that starts the block
    start_idx = None
    for i, line in enumerate(lines):
        if re.search(rf'\b{re.escape(key)}\s*=\s*[{re.escape(open_ch)}]', line):
            start_idx = i
            break

    if start_idx is None:
        return None

    # Collect text and track depth
    collected = []
    depth = 0
    for i in range(start_idx, len(lines)):
        line = lines[i]
        collected.append(line)
        depth += line.count(open_ch) - line.count(close_ch)
        if depth <= 0:
            break

    return "\n".join(collected)


# --- field extraction -------------------------------------------------------

FIELD_RE = re.compile(
    r"^(\s+)(\w+)\s*=\s*fields\.(\w+)\s*\("
)
FIELD_ATTR_RE = {
    "required": re.compile(r"required\s*=\s*(True|False)"),
    "readonly": re.compile(r"readonly\s*=\s*(True|False)"),
    "store": re.compile(r"store\s*=\s*(True|False)"),
    "compute": re.compile(r'compute\s*=\s*["\'](\w+)'),
    "relation": re.compile(r'relation\s*=\s*["\']([\w.]+)["\']'),
    "comodel": re.compile(r'comodel_name\s*=\s*["\']([\w.]+)["\']'),
}


def extract_field_info(model_path: Path, field_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """Extract field declarations for *field_names* from *model_path*."""
    result: Dict[str, Dict[str, Any]] = {}
    try:
        lines = model_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return result

    field_set = set(field_names)
    i = 0
    while i < len(lines):
        line = lines[i]
        m = FIELD_RE.match(line)
        if m and m.group(2) in field_set:
            fname = m.group(2)
            ftype = m.group(3)
            # Collect the full field definition (may span multiple lines)
            full_def = line
            paren_depth = line.count("(") - line.count(")")
            j = i + 1
            while paren_depth > 0 and j < len(lines):
                full_def += lines[j]
                paren_depth += lines[j].count("(") - lines[j].count(")")
                j += 1

            info: Dict[str, Any] = {"type": ftype}
            for attr, attr_re in FIELD_ATTR_RE.items():
                am = attr_re.search(full_def)
                if am:
                    val = am.group(1)
                    if attr in ("required", "readonly", "store"):
                        info[attr] = val == "True"
                    else:
                        info[attr] = val

            result[fname] = info
            i = j
            continue
        i += 1

    # Mark missing fields
    for fn in field_names:
        if fn not in result:
            result[fn] = {"_status": "missing"}
    return result


# --- domain contract fingerprint -------------------------------------------

def fingerprint_domain_contract(
    contract_path: Path,
    sm_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Extract the contract-relevant structure for a single domain contract."""
    contract = load_yaml(contract_path)
    contract_id = contract.get("id", contract_path.stem)
    entity = contract.get("entity", "")
    version = contract.get("version", 0)

    sot = contract.get("source_of_truth", {})
    module = sot.get("module", "")
    model_name_from_contract = sot.get("model", entity)
    sm_const = sot.get("state_machine", "")

    # Field names from the contract
    fields_block = contract.get("fields", {})
    field_names = list(fields_block.keys()) if isinstance(fields_block, dict) else []

    fp: Dict[str, Any] = {
        "id": contract_id,
        "version": version,
        "entity": entity,
        "model": model_name_from_contract,
        "module": module,
        "contract_fields": sorted(field_names),
    }

    # Find model file
    model_path, odoo_model_name = find_model_file(module, model_name_from_contract, entity)
    if model_path:
        fp["model_file"] = str(model_path.relative_to(ROOT))
        fp["odoo_model"] = odoo_model_name
        fp["model_fields"] = extract_field_info(model_path, field_names)
    else:
        fp["model_file"] = None
        fp["odoo_model"] = None
        fp["model_fields"] = {fn: {"_status": "model_file_not_found"} for fn in field_names}

    # State machine lookup
    sm_entry: Optional[Dict[str, Any]] = None

    # Try 1: explicit state_machine constant in source_of_truth
    if sm_const:
        suffix = sm_const.split(".")[-1] if "." in sm_const else sm_const
        # Look up by constant name in sm_map (keyed by model name, sorted for determinism)
        for _model, entry in sorted(sm_map.items()):
            if entry.get("constant") == suffix:
                sm_entry = entry
                break

    # Try 2: look up by Odoo model name in sm_map
    if not sm_entry and odoo_model_name and odoo_model_name in sm_map:
        sm_entry = sm_map[odoo_model_name]

    # Try 3: derive constant name from contract id (e.g. payment_request -> PAYMENT_REQUEST)
    if not sm_entry:
        derived = contract_id.upper()
        for _model, entry in sorted(sm_map.items()):
            if entry.get("constant") == derived:
                sm_entry = entry
                break

    if sm_entry:
        fp["state_machine"] = {
            "constant": sm_entry.get("constant"),
            "model": sm_entry.get("model"),
            "states": sm_entry.get("states", []),
            "transitions": sm_entry.get("transitions", {}),
        }

    # Contract's own states and transitions (for cross-reference)
    contract_states = contract.get("states", {})
    if isinstance(contract_states, dict):
        fp["contract_states"] = sorted(contract_states.keys())
    contract_transitions = contract.get("transitions", {})
    if isinstance(contract_transitions, dict):
        fp["contract_transitions"] = sorted(contract_transitions.keys())
    elif isinstance(contract_transitions, list):
        fp["contract_transitions"] = sorted(t.get("name", "") for t in contract_transitions if isinstance(t, dict))

    return fp


# --- main -------------------------------------------------------------------

def generate_fingerprint() -> Dict[str, Any]:
    """Generate the full contract structure fingerprint."""
    registry = load_yaml(REGISTRY_PATH)
    contracts_list = registry.get("contracts", [])

    # Parse state machine file once
    sm_map = parse_state_machine_file()

    domains: List[Dict[str, Any]] = []
    for entry in contracts_list:
        if not isinstance(entry, dict):
            continue
        if entry.get("kind") != "domain":
            continue
        rel = entry.get("path", "")
        contract_path = CONTRACTS_DIR / rel
        if not contract_path.is_file():
            domains.append({"id": rel, "_status": "file_missing"})
            continue
        domains.append(fingerprint_domain_contract(contract_path, sm_map))

    # Also fingerprint schema, extension, and product files by content hash
    schemas: List[Dict[str, Any]] = []
    extensions: List[Dict[str, Any]] = []
    product_contracts: List[Dict[str, Any]] = []
    for entry in contracts_list:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("path", "")
        kind = entry.get("kind", "")
        contract_path = CONTRACTS_DIR / rel
        if not contract_path.is_file():
            continue
        # Normalise line endings before hashing (defensive: CRLF -> LF)
        content = contract_path.read_text(encoding="utf-8", errors="ignore")
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        entry_fp = {"path": rel, "version": entry.get("version"), "content_hash": content_hash}
        if kind == "schema":
            schemas.append(entry_fp)
        elif kind == "extension":
            extensions.append(entry_fp)
        elif kind == "product":
            product_contracts.append(entry_fp)

    # Sort output lists by their natural key for deterministic ordering
    domains.sort(key=lambda d: d.get("id", ""))
    schemas.sort(key=lambda d: d.get("path", ""))
    extensions.sort(key=lambda d: d.get("path", ""))
    product_contracts.sort(key=lambda d: d.get("path", ""))

    return {
        "generated_by": "scripts/ci/generate_contract_structure_fingerprint.py",
        "domains": domains,
        "schemas": schemas,
        "extensions": extensions,
        "product_contracts": product_contracts,
        "state_machine_file": str(STATE_MACHINE_PATH.relative_to(ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate contract structure fingerprint")
    parser.add_argument("--write", action="store_true", help="write fingerprint to file")
    parser.add_argument("--diff", action="store_true", help="show diff when fingerprint is stale")
    args = parser.parse_args()

    fingerprint = generate_fingerprint()
    canonical = json.dumps(fingerprint, ensure_ascii=False, indent=2, sort_keys=True)

    if args.write:
        FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        FINGERPRINT_PATH.write_text(canonical + "\n", encoding="utf-8")
        print(f"[OK] wrote {FINGERPRINT_PATH.relative_to(ROOT)}")
        return 0

    # Check-only mode
    if not FINGERPRINT_PATH.is_file():
        print("[ERROR] contract structure fingerprint not found. Run with --write to create it.")
        return 1

    committed = FINGERPRINT_PATH.read_text(encoding="utf-8")
    committed_canonical = json.dumps(json.loads(committed), ensure_ascii=False, indent=2, sort_keys=True)

    if canonical == committed_canonical:
        print("[OK] contract structure fingerprint is current")
        return 0

    print("[ERROR] contract structure fingerprint is stale.")
    print("  Run: python3 scripts/ci/generate_contract_structure_fingerprint.py --write")

    if args.diff:
        # Show unified diff between committed and freshly generated
        import difflib
        committed_lines = committed_canonical.splitlines(keepends=True)
        generated_lines = canonical.splitlines(keepends=True)
        diff = difflib.unified_diff(
            committed_lines, generated_lines,
            fromfile="committed (contracts/generated/contract_structure_fingerprint.json)",
            tofile="generated (fresh)",
            n=3,
        )
        diff_text = "".join(diff)
        if diff_text:
            print("\n--- DIFF ---")
            print(diff_text)
        else:
            print("\n[INFO] canonical JSON is identical but raw text differs (whitespace?)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
