# Executed through scripts/ops/odoo_shell_exec.sh; ``env`` is provided by Odoo shell.
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

from odoo.exceptions import ValidationError

from odoo.addons.smart_core.core.contract_lifecycle import payload_sha256


def _source_manifest_version():
    """Read the version from the mounted smart_core source manifest.

    The installed module version is only "current" when it matches the source
    the probe actually exercises, so the expectation is derived from the
    manifest on the Odoo addons path instead of a hand-synced literal. A frozen
    literal silently rots every time a batch legitimately upgrades the module,
    which turns the runtime lane red for reasons that are not a defect.
    """
    from odoo.tools import config as _odoo_config
    for base in str(_odoo_config.get("addons_path") or "").split(","):
        manifest_path = Path(base.strip()) / "smart_core" / "__manifest__.py"
        if manifest_path.is_file():
            manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
            return str(manifest.get("version") or "")
    return ""


# The declared assertion set is the producer half of the evidence contract. The
# offline guard (backend_contract_lifecycle_runtime_schema_guard.py) owns the same
# set and must stay identical; the probe fails closed if it drifts from its own
# declaration so a truncated or renamed assertion can never be reported as a pass.
DECLARED_CHECKS = (
    "external_version_create_rejected",
    "first_publish_hash_bound",
    "first_publish_version_one",
    "module_version_current",
    "published_definition_mutation_uses_authority",
    "published_mutation_uses_authority",
    "published_population_digest_verified",
    "published_population_integrity_complete",
    "repeat_publish_idempotent",
    "rollback_is_append_only",
    "version_deletion_rejected",
    "version_mutation_rejected",
    "version_population_digest_verified",
    "version_population_integrity_complete",
)

Contract = env["ui.business.config.contract"].sudo()
Version = env["ui.business.config.contract.version"].sudo()
probe_name = "__contract_lifecycle_runtime_probe__"
Contract.search([("name", "=", probe_name)]).unlink()

checks = {}
errors = []
contract = Contract.create({
    "name": probe_name,
    "model": "res.company",
    "view_type": "form",
    "contract_json": {"probe": "v1", "fields": ["name"]},
    "status": "draft",
})

try:
    contract.action_publish()
    first_version = contract.version_no
    first_snapshot = Version.search([("contract_id", "=", contract.id)], order="version_no", limit=1)
    checks["first_publish_version_one"] = first_version == 1 and bool(first_snapshot)
    checks["first_publish_hash_bound"] = (
        first_snapshot.payload_sha256 == payload_sha256(first_snapshot.snapshot_json)
        and first_snapshot.definition_sha256 == payload_sha256(first_snapshot.definition_json)
        and bool(first_snapshot.source_authority_json)
    )

    contract.action_publish()
    checks["repeat_publish_idempotent"] = (
        contract.version_no == first_version
        and Version.search_count([("contract_id", "=", contract.id)]) == 1
    )

    contract.write({"contract_json": {"probe": "v2", "fields": ["name", "email"]}})
    second_version = contract.version_no
    checks["published_mutation_uses_authority"] = (
        contract.status == "published"
        and second_version == first_version + 1
        and Version.search_count([("contract_id", "=", contract.id)]) == 2
    )

    contract.write({"priority": 77})
    definition_version = contract.version_no
    definition_snapshot = Version.search(
        [("contract_id", "=", contract.id)], order="version_no desc", limit=1
    )
    checks["published_definition_mutation_uses_authority"] = (
        definition_version == second_version + 1
        and definition_snapshot.definition_json.get("priority") == 77
        and definition_snapshot.definition_sha256 == payload_sha256(definition_snapshot.definition_json)
        and Version.search_count([("contract_id", "=", contract.id)]) == 3
    )

    contract.restore_published_version(first_snapshot)
    checks["rollback_is_append_only"] = (
        contract.version_no == definition_version + 1
        and contract.contract_json == first_snapshot.snapshot_json
        and contract.priority == first_snapshot.definition_json.get("priority")
        and contract.definition_sha256 == first_snapshot.definition_sha256
        and Version.search_count([("contract_id", "=", contract.id)]) == 4
    )

    try:
        Version.create({
            "contract_id": contract.id,
            "version_no": 99,
            "snapshot_json": {},
            "definition_json": {},
            "payload_sha256": payload_sha256({}),
            "definition_sha256": payload_sha256({}),
            "source_authority_json": {},
            "status": "published",
            "published_at": contract.published_at,
        })
        checks["external_version_create_rejected"] = False
    except ValidationError:
        checks["external_version_create_rejected"] = True

    try:
        first_snapshot.write({"snapshot_json": {"tampered": True}})
        checks["version_mutation_rejected"] = False
    except ValidationError:
        checks["version_mutation_rejected"] = True

    try:
        first_snapshot.unlink()
        checks["version_deletion_rejected"] = False
    except ValidationError:
        checks["version_deletion_rejected"] = True

    env.cr.execute(
        """
        SELECT count(*)
          FROM ui_business_config_contract
         WHERE status = 'published'
           AND (
                payload_sha256 IS NULL OR payload_sha256 !~ '^[0-9a-f]{64}$'
                OR definition_sha256 IS NULL OR definition_sha256 !~ '^[0-9a-f]{64}$'
                OR source_authority_json IS NULL OR source_authority_json = '{}'::jsonb
           )
        """
    )
    missing_contract_integrity = int(env.cr.fetchone()[0] or 0)
    env.cr.execute(
        """
        SELECT count(*)
          FROM ui_business_config_contract_version
         WHERE payload_sha256 IS NULL OR payload_sha256 !~ '^[0-9a-f]{64}$'
            OR definition_sha256 IS NULL OR definition_sha256 !~ '^[0-9a-f]{64}$'
            OR source_authority_json IS NULL OR source_authority_json = '{}'::jsonb
            OR published_at IS NULL
        """
    )
    missing_version_integrity = int(env.cr.fetchone()[0] or 0)
    checks["published_population_integrity_complete"] = missing_contract_integrity == 0
    checks["version_population_integrity_complete"] = missing_version_integrity == 0
    published_records = Contract.with_context(active_test=False).search([("status", "=", "published")])
    checks["published_population_digest_verified"] = all(
        row.payload_sha256 == payload_sha256(row.contract_json or {})
        and row.definition_sha256 == payload_sha256(row._definition_payload())
        for row in published_records
    )
    version_records = Version.search([])
    version_digest_mismatches = [
        {
            "id": int(row.id),
            "contractId": int(row.contract_id.id),
            "versionNo": int(row.version_no),
            "payloadDigestMatches": row.payload_sha256 == payload_sha256(row.snapshot_json or {}),
            "definitionDigestMatches": row.definition_sha256 == payload_sha256(row.definition_json or {}),
            "storedDefinitionSha256": row.definition_sha256,
            "actualDefinitionSha256": payload_sha256(row.definition_json or {}),
            "definitionBinding": {
                key: value for key, value in (row.definition_json or {}).items() if key != "contract_json"
            },
            "currentDefinitionSha256": row.contract_id.definition_sha256,
            "currentDefinitionBinding": {
                key: value for key, value in row.contract_id._definition_payload().items() if key != "contract_json"
            },
        }
        for row in version_records
        if row.payload_sha256 != payload_sha256(row.snapshot_json or {})
        or row.definition_sha256 != payload_sha256(row.definition_json or {})
    ]
    checks["version_population_digest_verified"] = not version_digest_mismatches

    env.cr.execute(
        "SELECT latest_version FROM ir_module_module WHERE name = 'smart_core'"
    )
    module_version = str((env.cr.fetchone() or [""])[0] or "")
    manifest_version = _source_manifest_version()
    checks["module_version_current"] = (
        bool(manifest_version) and module_version == manifest_version
    )
finally:
    contract.unlink()

for key, passed in checks.items():
    if passed is not True:
        errors.append(key)

missing_declared = [name for name in DECLARED_CHECKS if name not in checks]
undeclared = [name for name in checks if name not in DECLARED_CHECKS]
if missing_declared or undeclared:
    raise AssertionError(
        "declared assertion set drift: missing=%s undeclared=%s" % (missing_declared, undeclared)
    )

source_revision = ""
for _revision_candidate in (
    os.environ.get("SC_SOURCE_REVISION"),
    os.environ.get("CANDIDATE_GIT_HEAD"),
    os.environ.get("SC_ACCEPTANCE_SOURCE_REVISION"),
):
    # The compose default pins SC_SOURCE_REVISION to the placeholder "unknown"
    # inside the container, so only a full 40-hex SHA may be accepted; every
    # other value is skipped instead of poisoning the artifact identity.
    _value = str(_revision_candidate or "").strip()
    if len(_value) == 40 and all(c in "0123456789abcdef" for c in _value):
        source_revision = _value
        break

report = {
    "probe": "backend_contract_lifecycle_runtime_probe",
    "schemaVersion": "1.1.0",
    "database": env.cr.dbname,
    "moduleVersion": module_version,
    "manifestVersion": manifest_version,
    "sourceRevision": source_revision,
    "declaredChecks": sorted(DECLARED_CHECKS),
    "checkCount": len(checks),
    "passedCheckCount": sum(1 for value in checks.values() if value is True),
    "checks": {name: checks[name] for name in sorted(checks)},
    "versionDigestMismatchSample": version_digest_mismatches[:10],
    "errorCount": len(errors),
    "errors": errors,
}
with open("/tmp/backend_contract_lifecycle_runtime_probe.json", "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

if errors:
    raise AssertionError("backend contract lifecycle runtime probe failed: %s" % ", ".join(errors))
print(json.dumps(report, ensure_ascii=False, indent=2))
