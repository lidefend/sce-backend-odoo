#!/usr/bin/env python3
"""Generate and verify the formal form-structure Contract-to-renderer matrix."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/form-structure-contract-projection-matrix-v1.json"

DEFINITIONS = (
    "formStructureContract",
    "formStructureObjectProfile",
    "formStructureNavigation",
    "formStructureSlot",
    "formStructureGroup",
    "formStructureRole",
    "formStructureSourceAuthority",
    "formStructureGovernanceSource",
    "formStructureGovernanceContract",
    "formStructureConfiguredSection",
)

RENDERED = {
    "formStructureContract.presentationMode": ("presentation", "presentContractV2Form.identity.presentationMode"),
    "formStructureContract.columns": ("geometry", "presentNode.columns"),
    "formStructureContract.navigation": ("shell", "presentContractV2Form.shell"),
    "formStructureContract.fieldLabels": ("field-label", "formStructureFieldLabels"),
    "formStructureContract.slots": ("structure", "structureSlot"),
    "formStructureContract.fieldRoles": ("semantic-identity", "fieldSemanticIdentity"),
    "formStructureNavigation.title": ("shell-title", "presentContractV2Form.shell.title"),
    "formStructureSlot.slot": ("semantic-identity", "structureSlot"),
    "formStructureSlot.title": ("section-title", "presentNode.title"),
    "formStructureSlot.role": ("semantic-region", "presentNode.semanticRole"),
    "formStructureSlot.readonly": ("interaction", "fieldFromWidget.readonly"),
    "formStructureSlot.fieldRefs": ("field-membership", "decodeFormStructureContract closure"),
    "formStructureSlot.groups": ("structure", "structureGroup"),
    "formStructureGroup.name": ("semantic-identity", "structureGroup"),
    "formStructureGroup.title": ("section-title", "presentNode.title"),
    "formStructureGroup.role": ("semantic-region", "presentNode.semanticRole"),
    "formStructureGroup.fieldRefs": ("field-membership", "decodeFormStructureContract closure"),
    "formStructureGroup.fieldLabels": ("field-label", "formStructureFieldLabels"),
    "formStructureGroup.columns": ("geometry", "presentNode.columns"),
    "formStructureRole.role": ("semantic-region", "fieldSemanticIdentity"),
    "formStructureRole.slot": ("semantic-identity", "fieldSemanticIdentity"),
    "formStructureRole.group": ("semantic-identity", "fieldSemanticIdentity"),
}

NON_VISUAL = {
    "formStructureContract.source": "runtime carrier identity",
    "formStructureContract.structureVersion": "decoder compatibility boundary",
    "formStructureContract.model": "model identity invariant",
    "formStructureContract.viewType": "view identity invariant",
    "formStructureContract.mode": "legacy producer classification retained for trace compatibility",
    "formStructureContract.layoutPolicy": "producer policy trace; concrete slots/groups/columns carry render facts",
    "formStructureContract.objectProfile": "business fact authority invariant",
    "formStructureContract.sourceSectionTitles": "source trace; slots/groups carry the selected titles",
    "formStructureContract.sourceAuthority": "server authority and provenance proof",
    "formStructureObjectProfile.model": "model identity invariant",
    "formStructureObjectProfile.kind": "object-kind invariant",
    "formStructureObjectProfile.factAuthority": "business fact provenance",
    "formStructureSourceAuthority.kind": "authority invariant",
    "formStructureSourceAuthority.runtime_carrier": "authority invariant",
    "formStructureSourceAuthority.projection_only": "authority boundary invariant",
    "formStructureSourceAuthority.no_business_fact_authority": "authority boundary invariant",
    "formStructureSourceAuthority.governed_form_structure": "authority boundary invariant",
    "formStructureSourceAuthority.governance_source": "server provenance trace",
    "formStructureGovernanceSource.source": "server provenance trace",
    "formStructureGovernanceSource.ownerLayer": "server provenance trace",
    "formStructureGovernanceSource.businessConfigContracts": "server selection trace",
    "formStructureGovernanceSource.legacyFieldPolicyOverlay": "server selection trace",
    "formStructureGovernanceSource.formLayoutOverlay": "server selection trace",
    "formStructureGovernanceSource.formStructureAuthority": "server selection trace",
    "formStructureGovernanceSource.fieldNames": "server projection trace",
    "formStructureGovernanceSource.fieldLabels": "server projection trace; selected fieldLabels carry render facts",
    "formStructureGovernanceSource.fieldSemanticRoles": "server projection trace; fieldRoles carry render facts",
    "formStructureGovernanceSource.sectionSemanticRoles": "server projection trace; slots/groups carry render facts",
    "formStructureGovernanceSource.configuredSections": "server projection trace; slots/groups carry render facts",
    "formStructureGovernanceSource.sectionTitles": "server projection trace; slots/groups carry render facts",
    "formStructureGovernanceSource.fieldGroups": "server projection trace; slots/groups carry render facts",
    "formStructureGovernanceSource.hiddenFieldNames": "server projection trace; layout/status carry visibility facts",
    "formStructureGovernanceSource.formColumns": "server projection trace; selected columns carry render facts",
    "formStructureGovernanceSource.groupColumns": "server projection trace; selected group columns carry render facts",
    "formStructureGovernanceSource.groupVisibility": "server projection trace; status carries visibility facts",
    "formStructureGovernanceSource.categoryId": "server selection trace",
    "formStructureGovernanceSource.categoryCode": "server selection trace",
    "formStructureGovernanceSource.targetModel": "server selection trace",
    "formStructureGovernanceContract.id": "server selection trace",
    "formStructureGovernanceContract.name": "server selection trace",
    "formStructureGovernanceContract.priority": "server selection trace",
    "formStructureGovernanceContract.view_type": "server selection trace",
    "formStructureGovernanceContract.version_no": "server selection trace",
    "formStructureConfiguredSection.identity": "server projection trace",
    "formStructureConfiguredSection.key": "server projection trace",
    "formStructureConfiguredSection.title": "server projection trace; selected group title carries render fact",
    "formStructureConfiguredSection.fields": "server projection trace; selected fieldRefs carry membership",
}


def schema_paths(schema: dict) -> set[str]:
    definitions = schema["$defs"]
    return {
        f"{definition}.{property_name}"
        for definition in DEFINITIONS
        for property_name in definitions[definition].get("properties", {})
    }


def build() -> dict:
    schema = json.loads(SCHEMA.read_text())
    paths = schema_paths(schema)
    declared = set(RENDERED) | set(NON_VISUAL)
    missing = sorted(paths - declared)
    stale = sorted(declared - paths)
    if missing or stale:
        raise SystemExit(f"projection matrix mismatch: missing={missing} stale={stale}")
    rows = []
    for path in sorted(paths):
        if path in RENDERED:
            semantic, consumer = RENDERED[path]
            rows.append({
                "path": path,
                "classification": "rendered_authority",
                "semantic": semantic,
                "consumer": consumer,
            })
        else:
            rows.append({
                "path": path,
                "classification": "validated_non_visual_authority",
                "reason": NON_VISUAL[path],
                "consumer": "decodeFormStructureContract",
            })
    return {
        "schemaVersion": "form-structure-contract-projection-matrix/v1",
        "schemaAuthority": str(SCHEMA.relative_to(ROOT)),
        "scope": list(DEFINITIONS),
        "summary": {
            "schemaFieldCount": len(rows),
            "renderedAuthorityCount": sum(row["classification"] == "rendered_authority" for row in rows),
            "validatedNonVisualAuthorityCount": sum(
                row["classification"] == "validated_non_visual_authority" for row in rows
            ),
            "unclassifiedCount": 0,
        },
        "rows": rows,
    }


def main() -> None:
    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if "--check" in __import__("sys").argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit(f"stale projection matrix: run {Path(__file__).relative_to(ROOT)}")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
    print(
        "[form_structure_contract_projection_matrix] PASS "
        f"fields={payload['summary']['schemaFieldCount']} unclassified=0"
    )


if __name__ == "__main__":
    main()
