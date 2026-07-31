#!/usr/bin/env python3
"""Validate final-image execution evidence before RC publication."""

from __future__ import annotations

import json
import re
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
SAFE_REHEARSAL_ENVIRONMENT = re.compile(
    r"^(?:sc_)?(?:release|rc)[a-z0-9_]*rehearsal[a-z0-9_]*$"
)
CONTRACT_VERSION = "final_image_real_plan.v2"
COMMAND_CONTRACT = "release.production.tenant_payload.plan"


class RealPlanEvidenceError(ValueError):
    pass


def load_and_validate(
    path: Path,
    *,
    expected_source_sha: str,
    expected_source_tree: str,
    expected_version: str,
    expected_image_content_id: str,
) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RealPlanEvidenceError("FINAL_IMAGE_REAL_PLAN_EVIDENCE_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RealPlanEvidenceError("FINAL_IMAGE_REAL_PLAN_EVIDENCE_INVALID") from exc
    required = {
        "schema_version",
        "status",
        "source_sha",
        "source_tree",
        "release_version",
        "image_content_id",
        "image_revision",
        "command_contract",
        "production_command_parity",
        "database_role",
        "environment_id",
        "runtime_isolation",
        "production_resource_overlap",
        "target_database",
        "tenant_key",
        "payload_digest",
        "plan_computation_completed",
        "planned_records",
        "planned_relationships",
        "database_write_count",
        "payload_batches_before",
        "payload_batches_after",
        "historical_facts_before",
        "historical_facts_after",
        "business_state_digest_before",
        "business_state_digest_after",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise RealPlanEvidenceError("FINAL_IMAGE_REAL_PLAN_SCHEMA_INVALID")
    if (
        payload["schema_version"] != CONTRACT_VERSION
        or payload["status"] != "PASS"
        or payload["source_sha"] != expected_source_sha
        or payload["source_tree"] != expected_source_tree
        or payload["release_version"] != expected_version
        or payload["image_content_id"] != expected_image_content_id
        or payload["image_revision"] != expected_source_sha
        or payload["command_contract"] != COMMAND_CONTRACT
        or payload["production_command_parity"] is not True
        or payload["database_role"] != "isolated_customer_tenant_rehearsal"
        or not SAFE_REHEARSAL_ENVIRONMENT.fullmatch(str(payload["environment_id"]))
        or payload["runtime_isolation"] is not True
        or payload["production_resource_overlap"] is not False
        # Preserve exact production command/config parity inside an isolated
        # runtime namespace. Isolation is an environment property, not a
        # reason to silently exercise a different logical database identity.
        or payload["target_database"] != "sc_production"
        or not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", str(payload["tenant_key"]))
        or not CHECKSUM.fullmatch(str(payload["payload_digest"]))
        or payload["plan_computation_completed"] is not True
        or not isinstance(payload["planned_records"], int)
        or payload["planned_records"] <= 0
        or not isinstance(payload["planned_relationships"], int)
        or payload["planned_relationships"] <= 0
        or payload["database_write_count"] != 0
        or payload["payload_batches_before"] != payload["payload_batches_after"]
        or payload["historical_facts_before"] != payload["historical_facts_after"]
        or payload["business_state_digest_before"]
        != payload["business_state_digest_after"]
        or not CHECKSUM.fullmatch(str(payload["business_state_digest_before"]))
    ):
        raise RealPlanEvidenceError("FINAL_IMAGE_REAL_PLAN_CONTRACT_FAILED")
    if not FULL_SHA.fullmatch(expected_source_sha) or not FULL_SHA.fullmatch(
        expected_source_tree
    ) or not IMAGE_ID.fullmatch(expected_image_content_id):
        raise RealPlanEvidenceError("FINAL_IMAGE_REAL_PLAN_EXPECTATION_INVALID")
    return payload
