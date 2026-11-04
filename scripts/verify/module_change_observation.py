#!/usr/bin/env python3
"""Offline validator for module.change.observation.v1.

Validates structure, enforces the baseline admission rules and verifies the
snapshot artifact digest. Read-only; it never grants qualifications or changes
release state.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "contracts/schemas/module.change.observation.v1.schema.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_observation(obs: dict) -> list[str]:
    """Return a list of structural violations (empty = valid)."""
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(obs, dict):
        return ["observation must be an object"]
    for field in schema.get("required", []):
        if field not in obs:
            errors.append(f"missing required field: {field}")
    if obs.get("schema") != "module.change.observation.v1":
        errors.append("schema must be module.change.observation.v1")
    if obs.get("result") not in {"success", "partial", "failed"}:
        errors.append("result must be success|partial|failed")
    if obs.get("operation_origin") not in {"cli_wrapper", "scheduled_observer", "unknown"}:
        errors.append("operation_origin must be cli_wrapper|scheduled_observer|unknown")
    observer = obs.get("observer") or {}
    for field in ("name", "version", "odoo_version", "schema_version"):
        if not observer.get(field):
            errors.append(f"observer.{field} is required")
    for side in ("before", "after"):
        digest = (obs.get(side) or {}).get("snapshot_sha256")
        if digest and not SHA256_RE.fullmatch(digest):
            errors.append(f"{side}.snapshot_sha256 is not a sha256")
        fact = (obs.get(side) or {}).get("fact_digest")
        if fact and not SHA256_RE.fullmatch(fact):
            errors.append(f"{side}.fact_digest is not a sha256")
        if not isinstance((obs.get(side) or {}).get("module_digests"), dict):
            errors.append(f"{side}.module_digests must be a dict")
    artifact = obs.get("snapshot_artifact") or {}
    if artifact and not SHA256_RE.fullmatch(str(artifact.get("sha256", ""))):
        errors.append("snapshot_artifact.sha256 is not a sha256")
    return errors


def baseline_admissible(obs: dict) -> tuple[bool, str]:
    """A formal after-baseline requires success + ready registry + db match + digest consistency."""
    if obs.get("result") != "success":
        return False, f"result={obs.get('result')} (only success forms a baseline)"
    registry = obs.get("registry") or {}
    if not registry.get("ready"):
        return False, "registry not ready"
    if registry.get("db_matches") is False:
        return False, "database mismatch"
    artifact = obs.get("snapshot_artifact") or {}
    after_sha = (obs.get("after") or {}).get("snapshot_sha256")
    if not artifact.get("sha256") or artifact.get("sha256") != after_sha:
        return False, "artifact sha256 does not match after snapshot sha256"
    return True, "admissible"


def verify_artifact(obs: dict, repository: Path = ROOT) -> tuple[bool, str]:
    """Verify the referenced snapshot artifact still exists and matches its digest."""
    artifact = obs.get("snapshot_artifact") or {}
    rel = artifact.get("path")
    if not rel:
        return False, "artifact path missing"
    path = (repository / rel).resolve()
    if not path.is_relative_to(repository.resolve()):
        return False, "artifact outside repository"
    if not path.is_file():
        return False, "artifact missing (no persisted snapshot)"
    actual = _sha256(path)
    if actual != artifact.get("sha256"):
        return False, f"artifact digest mismatch expected={artifact.get('sha256')} actual={actual}"
    return True, "artifact verified"


def assess(obs: dict, repository: Path = ROOT) -> dict:
    errors = validate_observation(obs)
    admissible, admit_reason = baseline_admissible(obs)
    artifact_ok, artifact_reason = verify_artifact(obs, repository)
    return {
        "structurally_valid": not errors,
        "errors": errors,
        "baseline_admissible": admissible,
        "admission_reason": admit_reason,
        "artifact_persisted": artifact_ok,
        "artifact_reason": artifact_reason,
    }


if __name__ == "__main__":
    import sys
    obs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(assess(obs), ensure_ascii=False, indent=2))
