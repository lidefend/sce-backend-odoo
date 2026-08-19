#!/usr/bin/env python3
"""Enforce the contract structure lock.

Regenerates the contract structure fingerprint from the current code and
compares it against the committed baseline in
``contracts/generated/contract_structure_fingerprint.json``.

If the fingerprint changed, this script checks whether any files under
``contracts/`` (excluding ``generated/``) were also modified in the working
tree compared to the base commit.  When the code structure changed but no
contract files were touched, the gate **fails** — the developer must update
the contract YAML and re-generate the fingerprint before the PR can merge.

Usage:
    python3 scripts/ci/enforce_contract_structure_lock.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT_PATH = ROOT / "contracts" / "generated" / "contract_structure_fingerprint.json"


def regenerate_fingerprint() -> dict:
    """Run the generator in check-only mode and return the computed fingerprint."""
    # Import the generator module directly to avoid subprocess overhead
    import importlib.util
    gen_path = ROOT / "scripts" / "ci" / "generate_contract_structure_fingerprint.py"
    spec = importlib.util.spec_from_file_location("fingerprint_gen", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate_fingerprint()


def get_changed_contract_files(base_ref: str = "origin/main") -> list[str]:
    """Return contract files (excluding generated/) that changed vs *base_ref*."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AMRC", base_ref, "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            # Fallback: use git diff against working tree
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=AMRC"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
    except Exception:
        return []

    changed = []
    for line in result.stdout.strip().splitlines():
        if line.startswith("contracts/") and not line.startswith("contracts/generated/"):
            changed.append(line)
    return changed


def main() -> int:
    if not FINGERPRINT_PATH.is_file():
        print("[ERROR] contract structure fingerprint baseline not found.")
        print(f"  Run: python3 scripts/ci/generate_contract_structure_fingerprint.py --write")
        return 2

    # Regenerate the fingerprint from current code
    current = regenerate_fingerprint()
    current_canonical = json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True)

    # Load committed baseline
    committed_text = FINGERPRINT_PATH.read_text(encoding="utf-8")
    committed = json.loads(committed_text)
    committed_canonical = json.dumps(committed, ensure_ascii=False, indent=2, sort_keys=True)

    if current_canonical == committed_canonical:
        # Fingerprint unchanged — code structure matches the locked contract.
        domains = len(current.get("domains", []))
        print(f"[contract_structure_lock] PASS domains={domains} fingerprint=current")
        return 0

    # Fingerprint changed — require that contract files were also updated
    changed_contracts = get_changed_contract_files()

    if not changed_contracts:
        print("[contract_structure_lock] FAIL")
        print("  Contract-relevant code structure changed but no contract files were updated.")
        print("  To fix:")
        print("    1. Update the relevant contract YAML under contracts/")
        print("    2. Bump the version in the contract file and registry.yaml")
        print("    3. Run: python3 scripts/ci/generate_contract_structure_fingerprint.py --write")
        print("    4. Commit the updated contracts/ and fingerprint together")
        return 1

    # Contract files were updated — but the fingerprint itself is stale.
    # The developer updated the contracts but forgot to re-generate the fingerprint.
    print("[contract_structure_lock] FAIL")
    print("  Contract files were updated but the structure fingerprint is stale.")
    print("  Run: python3 scripts/ci/generate_contract_structure_fingerprint.py --write")
    print(f"  Changed contract files: {', '.join(changed_contracts)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
