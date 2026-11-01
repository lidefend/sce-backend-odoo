# -*- coding: utf-8 -*-
"""Controlled code-seed migration runner core (BNVA-02B-02C-02B-02).

Pure, offline-testable orchestration logic.  It never writes Odoo records
directly; execution delegates to the existing publication service
(``replace_and_publish`` / ``restore_published_version`` / change-set) so the
runner stays a thin layer and reuses the existing snapshot and digest authority.

Seed identity is ``module + external_id``, never the payload ``source`` stamp.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any


class MigrationState(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class SeedClassification(str, Enum):
    IMMUTABLE_CODE_SEED = "IMMUTABLE_CODE_SEED"
    VERSIONED_CODE_TEMPLATE = "VERSIONED_CODE_TEMPLATE"
    GENERATED_BASELINE = "GENERATED_BASELINE"
    USER_OWNED_CONFIGURATION = "USER_OWNED_CONFIGURATION"
    RETIRED_CONFIGURATION = "RETIRED_CONFIGURATION"


@dataclass(frozen=True)
class SeedIdentity:
    module: str
    external_id: str


def _stable_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def migration_id(
    module: str,
    external_id: str,
    seed_version: str,
    target_digest: str,
) -> str:
    """Cross-module-unique migration identity.

    module is part of the hash so two modules sharing an External ID, seed
    version and target digest cannot collide.
    """
    return _stable_digest({
        "module": str(module or ""),
        "external_id": str(external_id or ""),
        "seed_version": str(seed_version or ""),
        "target_digest": str(target_digest or ""),
    })


def plan_migration(
    identity: SeedIdentity,
    classification: str,
    *,
    seed_version: str,
    current_digest: str,
    target_digest: str,
    expected_source_digest: str | None = None,
) -> dict[str, Any]:
    """Compute one migration plan without mutating anything."""
    kind = SeedClassification(classification)
    if kind is SeedClassification.USER_OWNED_CONFIGURATION:
        return {"outcome": "skip", "reason": "user_owned"}
    if kind is SeedClassification.RETIRED_CONFIGURATION:
        return {"outcome": "skip", "reason": "retired"}
    if kind is SeedClassification.GENERATED_BASELINE:
        return {"outcome": "skip", "reason": "generator_managed"}
    if kind is SeedClassification.IMMUTABLE_CODE_SEED:
        return {"outcome": "skip", "reason": "immutable_frozen"}
    if not current_digest:
        return {"outcome": "error", "reason": "source_digest_missing"}
    if expected_source_digest and current_digest != expected_source_digest:
        return {"outcome": "error", "reason": "source_digest_mismatch"}
    if current_digest == target_digest:
        return {"outcome": "skip", "reason": "no_change"}
    return {
        "outcome": "migrate",
        "identity": {
            "module": identity.module,
            "external_id": identity.external_id,
        },
        "seed_version": seed_version,
        "source_digest": current_digest,
        "target_digest": target_digest,
        "migration_id": migration_id(
            identity.module, identity.external_id, seed_version, target_digest,
        ),
    }


def decide_execution(
    state: str,
    *,
    cleanup_verified: bool = False,
) -> dict[str, Any]:
    """Decide whether a migration may run from its persisted state."""
    current = MigrationState(state)
    if current is MigrationState.PLANNED:
        return {"allowed": True, "action": "execute"}
    if current is MigrationState.RUNNING:
        return {"allowed": False, "action": "reject_concurrent"}
    if current is MigrationState.APPLIED:
        return {"allowed": False, "action": "skip_idempotent"}
    if current is MigrationState.ROLLED_BACK:
        return {"allowed": True, "action": "re_execute"}
    if current is MigrationState.FAILED:
        if cleanup_verified:
            return {"allowed": True, "action": "retry"}
        return {"allowed": False, "action": "require_cleanup_verification"}
    return {"allowed": False, "action": "unknown_state"}


def verify_target_digest(actual_payload: dict[str, Any], target_digest: str) -> bool:
    return _stable_digest(actual_payload) == target_digest


def rollback_reference(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Reference a pre-migration snapshot without copying the config into an overlay."""
    return {
        "kind": "version_snapshot",
        "definition_digest": snapshot.get("definition_sha256", ""),
        "payload_digest": snapshot.get("payload_sha256", ""),
    }


def classify_record(
    *,
    source: str,
    active: bool,
    view_type: str,
    composition_mode: str = "",
    has_sections: bool = False,
    name: str = "",
) -> str:
    """Preliminary seed classification (final ownership is per-record in 03B/03C)."""
    if not active:
        return SeedClassification.RETIRED_CONFIGURATION.value
    if str(source or "").startswith("smart_core.lowcode."):
        return SeedClassification.USER_OWNED_CONFIGURATION.value
    if "_generated_" in str(name or "") or "generated" in str(source or "").lower():
        return SeedClassification.GENERATED_BASELINE.value
    if str(view_type or "") == "form" and (
        composition_mode == "entry_semantic_surface" or has_sections
    ):
        return SeedClassification.VERSIONED_CODE_TEMPLATE.value
    return SeedClassification.IMMUTABLE_CODE_SEED.value


def run_migration(
    record: Any,
    *,
    module: str,
    external_id: str,
    seed_version: str,
    target_payload: dict[str, Any],
    expected_source_digest: str | None = None,
) -> dict[str, Any]:
    """Orchestrate one migration through the existing publication service.

    ``record`` is an already-resolved Odoo record (or a test double) exposing:
    definition_sha256, contract_json, latest_published_version(),
    replace_and_publish(payload), restore_published_version(version).
    """
    classification = classify_record(
        source=str(getattr(record, "source", "") or ""),
        active=bool(getattr(record, "active", True)),
        view_type=str(getattr(record, "view_type", "form") or "form"),
        composition_mode=str(getattr(record, "composition_mode", "") or ""),
        has_sections=bool(getattr(record, "has_sections", False)),
        name=str(getattr(record, "name", "") or ""),
    )
    current_digest = str(getattr(record, "definition_sha256", "") or "")
    target_digest = _stable_digest(target_payload)
    plan = plan_migration(
        SeedIdentity(module=module, external_id=external_id),
        classification,
        seed_version=seed_version,
        current_digest=current_digest,
        target_digest=target_digest,
        expected_source_digest=expected_source_digest,
    )
    if plan["outcome"] != "migrate":
        return plan
    snapshot = record.latest_published_version()
    record.replace_and_publish(target_payload)
    if not verify_target_digest(
        getattr(record, "contract_json", {}) if isinstance(getattr(record, "contract_json", None), dict) else {},
        target_digest,
    ):
        record.restore_published_version(snapshot)
        return {
            "outcome": "error",
            "reason": "target_digest_mismatch",
            "migration_id": plan["migration_id"],
        }
    return {"outcome": "applied", "migration_id": plan["migration_id"]}
