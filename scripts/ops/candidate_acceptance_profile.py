#!/usr/bin/env python3
"""Isolated candidate acceptance profile guard and provisioning contract.

The shared frontend acceptance carrier (sc-fe-r2-p1-01 / sc_frontend_acceptance)
belongs to another candidate. This module resolves and validates a distinct
``candidate`` profile that must never target the shared resources, and exposes
the fail-closed provisioning contract used to create the isolated candidate
instance only after independent review and explicit resource authorization.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ROOT / "config/frontend/acceptance_environments_v1.json"
TOOL_MATRIX = ROOT / "config/frontend/acceptance_tool_matrix_v1.json"
CONFIRMATION = "PROVISION_ISOLATED_CANDIDATE_ACCEPTANCE"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CandidateProfileError(RuntimeError):
    """Any fail-closed refusal of the isolated candidate profile."""


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateProfileError(f"unreadable acceptance config: {path}") from exc
    if not isinstance(payload, dict):
        raise CandidateProfileError(f"acceptance config must be an object: {path}")
    return payload


def resolve_candidate_profile(
    environments_path: Path = ENVIRONMENTS,
    tool_matrix_path: Path = TOOL_MATRIX,
) -> dict:
    environments = load_json(environments_path)
    matrix = load_json(tool_matrix_path)
    profiles = environments.get("profiles")
    if not isinstance(profiles, dict):
        raise CandidateProfileError("acceptance environments must declare profiles")
    profile = profiles.get("candidate")
    if not isinstance(profile, dict):
        raise CandidateProfileError("candidate profile is missing")

    if profile.get("target_mode") != "external":
        raise CandidateProfileError("candidate profile must be external-only")
    for key in ("base_url_required", "database_required", "expected_sha_required", "target_identity_required"):
        if profile.get(key) is not True:
            raise CandidateProfileError(f"candidate profile must require {key}")
    if profile.get("allowed_operations") != ["readonly"]:
        raise CandidateProfileError("candidate profile must be readonly-only")
    if profile.get("database") == "sc_frontend_acceptance":
        raise CandidateProfileError("candidate profile must not declare the shared acceptance database")

    resource = profile.get("resource_contract")
    if not isinstance(resource, dict):
        raise CandidateProfileError("candidate profile must declare resource_contract")
    project = str(resource.get("compose_project") or "")
    database = str(resource.get("database") or "")
    dbfilter = str(resource.get("database_filter") or "")
    volumes = resource.get("volumes") or {}
    services = resource.get("services") or {}
    if not project or project == "sc-fe-r2-p1-01":
        raise CandidateProfileError("candidate compose project must be distinct from the shared carrier")
    if not database or database == "sc_frontend_acceptance":
        raise CandidateProfileError("candidate database must be distinct from sc_frontend_acceptance")
    if dbfilter != f"^{database}$":
        raise CandidateProfileError("candidate database_filter must exactly lock the candidate database")
    volume_names = [str(volumes.get(k) or "") for k in ("database", "redis", "odoo")]
    if len(set(volume_names)) != 3 or not all(volume_names):
        raise CandidateProfileError("candidate volumes must be three distinct non-empty identities")
    if any(name.startswith("sc_fe_r2_p1_01_") for name in volume_names):
        raise CandidateProfileError("candidate volumes must not reuse shared acceptance volumes")
    ports = [services.get("compose_backend_port"), services.get("backend_port"), services.get("frontend_port")]
    if not all(isinstance(port, int) and port > 0 for port in ports) or len(set(ports)) != 3:
        raise CandidateProfileError("candidate services must declare three distinct ports")
    if services.get("frontend_port") == 5175 or services.get("backend_port") == 18082:
        raise CandidateProfileError("candidate ports must not collide with the shared acceptance carrier")

    guard = profile.get("isolation_guard") or {}
    never_target = guard.get("never_target")
    if not isinstance(never_target, list) or not all(isinstance(x, str) for x in never_target):
        raise CandidateProfileError("candidate isolation_guard must list never-target resources")
    declared = [project, database, *volume_names, *[str(p) for p in ports]]
    overlap = sorted(set(declared).intersection(never_target))
    if overlap:
        raise CandidateProfileError(f"candidate resources overlap shared resources: {overlap}")

    return {
        "profile": "candidate",
        "target_mode": "external",
        "resource_contract": resource,
        "isolation_guard": {"never_target": never_target},
        "required_identity": {
            "sha": "required 40-char full commit",
            "database": database,
            "served_identity_checked": True,
        },
    }


def validate_candidate_sha(value: str) -> str:
    value = str(value or "").strip()
    if not SHA_RE.fullmatch(value):
        raise CandidateProfileError("candidate SHA must be a full 40-character lowercase commit")
    return value


def provision_plan(sha: str) -> dict:
    validate_candidate_sha(sha)
    resolved = resolve_candidate_profile()
    return {
        "mode": "plan",
        "profile": resolved["profile"],
        "candidate_sha": sha,
        "resource_contract": resolved["resource_contract"],
        "required_inputs": [
            "isolated resource registration receipt (owner/host/volumes/network/ports/lease/cleanup)",
            "acceptance fixture paired artifact manifest + recovery receipt",
            "frontend build identity bound to the candidate SHA",
            "candidate contract receipt (action/view/create/edit/delete/form defaults)",
        ],
        "shared_resources_forbidden": resolved["isolation_guard"]["never_target"],
        "creates_resources": False,
    }


def provision_apply(sha: str, confirm: str, registration: Path | None) -> dict:
    if confirm != CONFIRMATION:
        raise CandidateProfileError(
            f"exact confirmation {CONFIRMATION!r} is required to provision the isolated candidate"
        )
    if registration is None or not registration.is_file():
        raise CandidateProfileError(
            "a registered isolated-resource receipt is required before provisioning"
        )
    plan = provision_plan(sha)
    # Phase C implementation attaches the real carrier provisioning here; until
    # then the entry refuses any actual resource mutation.
    raise CandidateProfileError(
        "isolated candidate provisioning is not implemented until the Phase-C "
        "resource authority is granted; no resources were created"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--registration", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.apply:
            result = provision_apply(args.sha, args.confirm, args.registration)
        else:
            result = provision_plan(args.sha)
    except CandidateProfileError as exc:
        print(f"[candidate.acceptance] REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
