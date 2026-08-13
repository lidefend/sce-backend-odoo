"""Retire historically published runtime view contracts that fail current authority checks."""

import json

from odoo import SUPERUSER_ID, api


SNAPSHOT_KEY = "smart_construction_core.17.0.0.83.runtime_view_contract_cleanup"


def _xmlid(record):
    if not record:
        return ""
    return record.get_external_id().get(record.id, "")


def _contributed_view_types(contract):
    payload = contract.contract_json if isinstance(contract.contract_json, dict) else {}
    orchestration = payload.get("view_orchestration") if isinstance(payload.get("view_orchestration"), dict) else {}
    views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
    result = []
    for raw in views:
        normalized = contract._normalize_view_orchestration_view_type(raw)
        if normalized and normalized not in result:
            result.append(normalized)
    normalized_scope = contract._normalize_view_orchestration_view_type(contract.view_type)
    if normalized_scope and normalized_scope not in result:
        result.append(normalized_scope)
    return result or ["form"]


def _classify(contract):
    validations = [
        contract._runtime_contract_validation(
            contract,
            requested_view_type=view_type,
            action_id=int(contract.action_id.id or 0),
            view_id=int(contract.view_id.id or 0),
            model_name=contract.model,
        )
        for view_type in _contributed_view_types(contract)
    ]
    reasons = sorted({reason for row in validations for reason in row["reason_codes"]})
    fields = sorted({field for row in validations for field in row["fields"]})
    authoritative = {
        row["view_type"]: row["authoritative_fields"]
        for row in validations
        if row["authoritative_fields"]
    }
    return {
        "valid": not reasons,
        "reason_codes": reasons,
        "fields": fields,
        "authoritative_fields": authoritative,
    }


def migrate(cr, installed_version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Contract = env["ui.business.config.contract"].sudo().with_context(active_test=False)
    contracts = Contract.search([("active", "=", True), ("status", "=", "published")])
    before_rows = []
    invalid = Contract.browse()
    for contract in contracts:
        classification = _classify(contract)
        if classification["valid"]:
            continue
        invalid |= contract
        before_rows.append({
            "contract_xmlid": _xmlid(contract),
            "contract_name": contract.name,
            "model": contract.model,
            "view_type": contract.view_type or "multi",
            "action_xmlid": _xmlid(contract.action_id),
            "view_xmlid": _xmlid(contract.view_id),
            "version_no": contract.version_no,
            **classification,
        })

    snapshot = {
        "schema_version": "smart_construction_core.runtime_view_contract_cleanup.v1",
        "installed_version": installed_version,
        "before": {
            "active_published_contracts": len(contracts),
            "invalid_contracts": len(invalid),
            "affected_actions": len({row["action_xmlid"] for row in before_rows if row["action_xmlid"]}),
            "affected_models": len({row["model"] for row in before_rows}),
            "classifications": before_rows,
        },
    }
    if invalid:
        # These rows are retired precisely because their historical payload is
        # invalid under the current contract schema.  Calling ``write`` would
        # revalidate that payload before it can be archived and can therefore
        # make an old-database upgrade impossible.  Limit the SQL mutation to
        # the archive flag of the records classified above.
        cr.execute(
            "UPDATE ui_business_config_contract SET active = FALSE WHERE id = ANY(%s)",
            [invalid.ids],
        )
    env.invalidate_all()

    remaining_invalid = []
    remaining = Contract.search([("active", "=", True), ("status", "=", "published")])
    for contract in remaining:
        classification = _classify(contract)
        if not classification["valid"]:
            remaining_invalid.append({
                "contract_xmlid": _xmlid(contract),
                "contract_name": contract.name,
                "model": contract.model,
                **classification,
            })
    if remaining_invalid:
        raise RuntimeError("runtime view contract cleanup failed closed: %s" % remaining_invalid)

    snapshot["after"] = {
        "active_published_contracts": len(remaining),
        "invalid_contracts": 0,
        "retired_contracts": len(invalid),
    }
    Parameters = env["ir.config_parameter"].sudo()
    previous = Parameters.get_param(SNAPSHOT_KEY)
    if not previous:
        Parameters.set_param(SNAPSHOT_KEY, json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
