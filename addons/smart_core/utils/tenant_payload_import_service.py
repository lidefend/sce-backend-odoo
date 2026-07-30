from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from odoo.exceptions import AccessError, UserError

from odoo.addons.smart_core.utils.tenant_payload_v1 import (
    PRODUCT_INTERFACE_VERSION,
    SCHEMA_VERSION,
    TenantPayloadError,
    validate_payload_directory,
    validate_manifest,
)


class TenantPayloadImportError(UserError):
    pass


class TenantPayloadInterrupted(TenantPayloadImportError):
    pass


def _fail(rule: str) -> None:
    raise TenantPayloadImportError(rule)


def _manifest(root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        validate_manifest(payload)
        return payload
    except (OSError, UnicodeError, json.JSONDecodeError, TenantPayloadError) as exc:
        raise TenantPayloadImportError(str(exc) if isinstance(exc, TenantPayloadError) else "TPV1_MANIFEST_READ_FAILED") from exc


def _iter_records(root: Path, relative: str) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with (root / relative).open("r", encoding="utf-8") as handle:
            for line_number, text in enumerate(handle, 1):
                yield line_number, json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TenantPayloadImportError(f"TPV1_RECORD_READ_FAILED:{relative}") from exc


def _resource_name(relative: str) -> str:
    return Path(relative).stem


def _split_reference(reference: str) -> tuple[str, str]:
    try:
        resource, external_key = reference.split("::", 1)
    except ValueError as exc:
        raise TenantPayloadImportError("TPV1_RELATION_REFERENCE_INVALID") from exc
    return resource, external_key


def _scalar_matches(actual: Any, expected: Any) -> bool:
    """Compare JSON scalar values without weakening relational verification."""
    if expected is None:
        return actual in (None, False)
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return abs(Decimal(str(actual)) - Decimal(str(expected))) <= Decimal("0.000001")
        except (InvalidOperation, TypeError, ValueError):
            return False
    return str(actual) == str(expected)


def _validate_adapter(adapter: dict[str, Any], manifest: dict[str, Any]) -> None:
    if not isinstance(adapter, dict):
        _fail("TPV1_CUSTOMER_ADAPTER_INVALID")
    expected = {
        "tenant_key": manifest["tenant_key"],
        "customer_module": manifest["customer_module"],
        "customer_module_version": manifest["customer_module_version"],
        "payload_schema_version": SCHEMA_VERSION,
        "product_interface_version": PRODUCT_INTERFACE_VERSION,
    }
    if any(adapter.get(key) != value for key, value in expected.items()):
        _fail("TPV1_CUSTOMER_ADAPTER_INCOMPATIBLE")
    supported = adapter.get("supported_source_versions")
    if not isinstance(supported, list) or manifest["source_version"] not in supported:
        _fail("TPV1_SOURCE_VERSION_UNSUPPORTED")
    rejected_payloads = adapter.get("rejected_payloads", [])
    if not isinstance(rejected_payloads, list):
        _fail("TPV1_REJECTED_PAYLOAD_POLICY_INVALID")
    for rejected in rejected_payloads:
        if (
            not isinstance(rejected, dict)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",
                str(rejected.get("payload_id") or ""),
            )
            or not re.fullmatch(
                r"[0-9a-f]{64}",
                str(rejected.get("payload_checksum") or ""),
            )
            or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{2,127}",
                str(rejected.get("reason_code") or ""),
            )
        ):
            _fail("TPV1_REJECTED_PAYLOAD_POLICY_INVALID")
        if (
            rejected["payload_id"] == manifest.get("payload_id")
            and rejected["payload_checksum"] == manifest.get("payload_checksum")
        ):
            _fail("TPV1_PAYLOAD_REJECTED_BY_CUSTOMER_SEMANTIC_POLICY")
    resources = adapter.get("resources")
    order = adapter.get("model_import_order")
    if not isinstance(resources, dict) or not isinstance(order, list) or set(order) != set(resources) or len(order) != len(set(order)):
        _fail("TPV1_ADAPTER_RESOURCE_ORDER_INVALID")
    manifest_order = [_resource_name(path) for path in manifest["import_order"]]
    if manifest_order != order:
        _fail("TPV1_PAYLOAD_IMPORT_ORDER_INCOMPATIBLE")
    for resource, spec in resources.items():
        if not isinstance(spec, dict) or not spec.get("model") or not isinstance(spec.get("value_fields"), dict):
            _fail(f"TPV1_ADAPTER_RESOURCE_INVALID:{resource}")
        value_verification = spec.get("value_verification", {})
        if (
            not isinstance(value_verification, dict)
            or set(value_verification) - set(spec["value_fields"])
            or any(policy not in {"exact", "currency_round"} for policy in value_verification.values())
        ):
            _fail(f"TPV1_ADAPTER_VALUE_VERIFICATION_INVALID:{resource}")
        if not isinstance(spec.get("constant_values", {}), dict):
            _fail(f"TPV1_ADAPTER_CONSTANT_VALUES_INVALID:{resource}")
        classifiers = spec.get("error_classifiers", {})
        if not isinstance(classifiers, dict) or any(
            not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", str(code)) or not isinstance(pattern, str) or not pattern
            for code, pattern in classifiers.items()
        ):
            _fail(f"TPV1_ADAPTER_ERROR_CLASSIFIER_INVALID:{resource}")
        system_managed = spec.get("system_managed")
        if system_managed and (system_managed != "res_users_v1" or spec.get("model") != "res.users"):
            _fail(f"TPV1_ADAPTER_SYSTEM_BOUNDARY_INVALID:{resource}")
        relations = spec.get("relationship_fields", {})
        if not isinstance(relations, dict):
            _fail(f"TPV1_ADAPTER_RELATION_INVALID:{resource}")
        for relation in relations.values():
            if (
                not isinstance(relation, dict)
                or (relation.get("write", True) and not relation.get("field"))
                or (relation.get("resource") != "*" and relation.get("resource") not in resources)
            ):
                _fail(f"TPV1_ADAPTER_RELATION_INVALID:{resource}")
            if relation.get("polymorphic") and (relation.get("resource") != "*" or not relation.get("model_field")):
                _fail(f"TPV1_ADAPTER_RELATION_INVALID:{resource}")
            verification = relation.get("verification", "exact")
            if verification not in {"exact", "contains"} or (verification == "contains" and not relation.get("many")):
                _fail(f"TPV1_ADAPTER_RELATION_VERIFICATION_INVALID:{resource}")
            create_visibility = relation.get("create_visibility", {})
            create_visibility_when = relation.get("create_visibility_when", {})
            target_resource = relation.get("resource")
            if create_visibility:
                if (
                    not isinstance(create_visibility, dict)
                    or target_resource == "*"
                    or target_resource not in resources
                    or not relation.get("write", True)
                ):
                    _fail(f"TPV1_ADAPTER_CREATE_VISIBILITY_INVALID:{resource}")
                target_values = resources[target_resource].get("value_fields", {})
                for source_field, policy in create_visibility.items():
                    if (
                        source_field not in target_values
                        or not isinstance(policy, dict)
                        or set(policy) != {"final_value", "temporary_value"}
                        or policy["final_value"] == policy["temporary_value"]
                    ):
                        _fail(f"TPV1_ADAPTER_CREATE_VISIBILITY_INVALID:{resource}")
                if create_visibility_when:
                    if (
                        not isinstance(create_visibility_when, dict)
                        or set(create_visibility_when)
                        != {"relationship", "target_values"}
                        or create_visibility_when["relationship"] not in relations
                        or not isinstance(
                            create_visibility_when["target_values"], dict
                        )
                        or not create_visibility_when["target_values"]
                    ):
                        _fail(
                            f"TPV1_ADAPTER_CREATE_VISIBILITY_CONDITION_INVALID:{resource}"
                        )
                    condition_relation = relations[
                        create_visibility_when["relationship"]
                    ]
                    condition_resource = condition_relation.get("resource")
                    condition_values = resources.get(
                        condition_resource, {}
                    ).get("value_fields", {})
                    if (
                        condition_resource == "*"
                        or condition_resource not in resources
                        or set(create_visibility_when["target_values"])
                        - set(condition_values)
                    ):
                        _fail(
                            f"TPV1_ADAPTER_CREATE_VISIBILITY_CONDITION_INVALID:{resource}"
                        )


class TenantPayloadImportService:
    """Generic P4 import mechanism. Customer semantics arrive only through an adapter."""

    def __init__(self, env, payload_root: Path, tenant_key: str, *, approved_payload_checksum: str = ""):
        self.env = env
        public_key_value = str(os.environ.get("SC_TENANT_PAYLOAD_PUBLIC_KEY", "") or "").strip()
        hmac_key = str(os.environ.get("SC_TENANT_PAYLOAD_HMAC_KEY", "") or "").encode("utf-8") or None
        public_key = Path(public_key_value) if public_key_value else None
        try:
            validate_payload_directory(
                payload_root,
                expected_tenant_key=tenant_key,
                hmac_key=hmac_key,
                public_key=public_key,
            )
        except TenantPayloadError as exc:
            raise TenantPayloadImportError(str(exc)) from exc
        self.root = payload_root.resolve(strict=True)
        self.manifest = _manifest(self.root)
        if self.manifest["tenant_key"] != tenant_key:
            _fail("TPV1_TENANT_MISMATCH")
        self.tenant_key = tenant_key
        self.approved_payload_checksum = approved_payload_checksum
        adapter_model = env["sc.tenant.payload.adapter"]
        adapter_model.assert_import_operator()
        self.adapter = adapter_model.get_adapter(tenant_key)
        _validate_adapter(self.adapter, self.manifest)
        self.semantic_validation = adapter_model.validate_payload_semantics(
            tenant_key,
            str(self.root),
            self.manifest,
        )
        if (
            not isinstance(self.semantic_validation, dict)
            or self.semantic_validation.get("status") != "PASS"
        ):
            _fail("TPV1_PAYLOAD_SEMANTIC_VALIDATION_FAILED")
        self.resources = self.adapter["resources"]
        self._assert_adapter_value_targets_writable()
        self.lifecycle_reconstruction = self._build_lifecycle_reconstruction_plan()
        self.Identity = env["sc.tenant.payload.external.identity"]
        self.Batch = env["sc.tenant.payload.import.batch"]
        self._identity_cache: dict[tuple[str, str], int] | None = None
        self._assert_customer_module()

    def _assert_adapter_value_targets_writable(self) -> None:
        """Reject value mappings that ORM will immediately recompute away."""
        for resource, spec in self.resources.items():
            model = self.env[spec["model"]]
            for source_field, target_field in spec["value_fields"].items():
                field = model._fields.get(target_field)
                if not field:
                    _fail(
                        f"TPV1_ADAPTER_TARGET_FIELD_MISSING:{resource}:{source_field}"
                    )
                if field.compute and not field.inverse:
                    _fail(
                        f"TPV1_ADAPTER_TARGET_COMPUTED_WITHOUT_INVERSE:"
                        f"{resource}:{source_field}"
                    )

    def _assert_customer_module(self) -> None:
        module = self.env["ir.module.module"].search([("name", "=", self.manifest["customer_module"])], limit=1)
        if not module or module.state != "installed":
            _fail("TPV1_CUSTOMER_MODULE_NOT_INSTALLED")
        installed_version = str(module.latest_version or module.installed_version or "").strip()
        if installed_version != self.manifest["customer_module_version"]:
            _fail("TPV1_CUSTOMER_MODULE_VERSION_MISMATCH")
        if self.adapter.get("database_tenant_key") != self.tenant_key:
            _fail("TPV1_DATABASE_TENANT_UNAUTHORIZED")

    def _build_lifecycle_reconstruction_plan(self) -> dict[str, Any]:
        """Plan temporary create-visible values without writing payload or ORM state."""
        records_by_resource: dict[str, dict[str, dict[str, Any]]] = {}

        def records(resource: str) -> dict[str, dict[str, Any]]:
            if resource not in records_by_resource:
                relative = next(
                    (
                        item
                        for item in self.manifest["import_order"]
                        if _resource_name(item) == resource
                    ),
                    "",
                )
                if not relative:
                    _fail(f"TPV1_LIFECYCLE_RESOURCE_MISSING:{resource}")
                records_by_resource[resource] = {
                    item["external_key"]: item
                    for _line_number, item in _iter_records(self.root, relative)
                }
            return records_by_resource[resource]

        deferred: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        dependent_records: dict[str, set[str]] = defaultdict(set)
        dependency_edges = 0
        unresolved = 0
        order = {
            _resource_name(relative): index
            for index, relative in enumerate(self.manifest["import_order"])
        }
        invalid_order = 0

        def visibility_condition_matches(
            source_item: dict[str, Any],
            source_spec: dict[str, Any],
            relation_spec: dict[str, Any],
        ) -> bool:
            condition = relation_spec.get("create_visibility_when")
            if not condition:
                return True
            condition_relation = source_spec["relationship_fields"][
                condition["relationship"]
            ]
            reference = source_item.get("relationships", {}).get(
                condition["relationship"]
            )
            if not reference or isinstance(reference, list):
                return False
            target_resource, external_key = _split_reference(reference)
            if target_resource != condition_relation["resource"]:
                return False
            target_item = records(target_resource).get(external_key)
            if not target_item:
                return False
            target_values = target_item.get("values", {})
            return all(
                _scalar_matches(target_values.get(field), expected)
                for field, expected in condition["target_values"].items()
            )

        for source_resource, source_spec in self.resources.items():
            visibility_relations = {
                name: relation
                for name, relation in source_spec.get(
                    "relationship_fields", {}
                ).items()
                if relation.get("create_visibility")
            }
            if not visibility_relations:
                continue
            for source_item in records(source_resource).values():
                for relation_name, relation_spec in visibility_relations.items():
                    if not visibility_condition_matches(
                        source_item, source_spec, relation_spec
                    ):
                        continue
                    reference_value = source_item.get("relationships", {}).get(
                        relation_name
                    )
                    if not reference_value:
                        continue
                    references = (
                        reference_value
                        if isinstance(reference_value, list)
                        else [reference_value]
                    )
                    for reference in references:
                        target_resource, external_key = _split_reference(reference)
                        if target_resource != relation_spec["resource"]:
                            unresolved += 1
                            continue
                        target_item = records(target_resource).get(external_key)
                        if not target_item:
                            unresolved += 1
                            continue
                        if order[target_resource] >= order[source_resource]:
                            invalid_order += 1
                        matched = False
                        for source_field, policy in relation_spec[
                            "create_visibility"
                        ].items():
                            if not _scalar_matches(
                                target_item.get("values", {}).get(source_field),
                                policy["final_value"],
                            ):
                                continue
                            deferred.setdefault(
                                (target_resource, external_key), {}
                            )[source_field] = {
                                "final_value": policy["final_value"],
                                "temporary_value": policy["temporary_value"],
                            }
                            matched = True
                        if matched:
                            dependency_edges += 1
                            dependent_records[source_resource].add(
                                source_item["external_key"]
                            )
        if unresolved:
            _fail("TPV1_LIFECYCLE_DEPENDENCY_UNRESOLVED")
        if invalid_order:
            _fail("TPV1_LIFECYCLE_DEPENDENCY_ORDER_INVALID")
        for (resource, _external_key), fields in deferred.items():
            model = self.env[self.resources[resource]["model"]]
            for source_field in fields:
                target_field = self.resources[resource]["value_fields"][source_field]
                if target_field not in model._fields:
                    _fail("TPV1_LIFECYCLE_FINAL_STATE_NOT_RESTORABLE")
        deferred_resources = sorted({resource for resource, _key in deferred})
        return {
            "schema_version": "tenant_payload_lifecycle_reconstruction.v1",
            "status": "PASS",
            "create_phase_visibility": "PASS",
            "final_state_restorability": "PASS",
            "deferred_state_scope": "PASS",
            "final_state_payload_parity": "PLANNED",
            "deferred_resources": deferred_resources,
            "deferred_records": len(deferred),
            "dependent_records": {
                resource: len(keys)
                for resource, keys in sorted(dependent_records.items())
            },
            "dependency_edges": dependency_edges,
            "unresolved_dependencies": 0,
            "archival_cycles": 0,
            "_deferred": deferred,
        }

    def _public_lifecycle_reconstruction(self, *, parity="PLANNED") -> dict[str, Any]:
        return {
            key: (parity if key == "final_state_payload_parity" else value)
            for key, value in self.lifecycle_reconstruction.items()
            if key != "_deferred"
        }

    def _identity(self, resource: str, external_key: str):
        if self._identity_cache is None:
            identities = self.Identity.search([("tenant_key", "=", self.tenant_key)])
            self._identity_cache = {
                (identity.resource, identity.external_key): identity.id
                for identity in identities
            }
        identity_id = self._identity_cache.get((resource, external_key))
        return self.Identity.browse(identity_id) if identity_id else self.Identity.browse()

    def _create_identity(self, values: dict[str, Any]):
        identity = self.Identity.create(values)
        if self._identity_cache is not None:
            self._identity_cache[(identity.resource, identity.external_key)] = identity.id
        return identity

    def _register_business_company(self, *, resource, external_key, record, batch):
        spec = self.resources[resource]
        if not spec.get("company_identity") or record._name != "res.company":
            return
        Registration = self.env["sc.tenant.company.registration"].with_context(
            sc_tenant_payload_import=True
        )
        registration = Registration.search([("company_id", "=", record.id)], limit=1)
        expected = {
            "tenant_key": self.tenant_key,
            "company_id": record.id,
            "source_module": batch.customer_module,
            "source_external_key": external_key,
        }
        if registration:
            if (
                registration.tenant_key != expected["tenant_key"]
                or registration.company_id.id != expected["company_id"]
                or registration.source_module != expected["source_module"]
                or registration.source_external_key != expected["source_external_key"]
            ):
                _fail("TPV1_COMPANY_REGISTRATION_IDENTITY_CONFLICT")
            if not registration.active:
                registration.write({"active": True})
        else:
            Registration.create(expected)

    def _activate_import_company_scope(self, company) -> None:
        """Authorize the technical importer for the newly registered company.

        Payload business records must never fall back to the platform company.
        The adapter's explicit ``company_identity`` declaration authorizes this
        bootstrap step. Add only that company to the technical operator before
        creating its scoped external identity and registration; the surrounding
        transaction rolls this back if either operation fails. No ordinary
        payload user is changed here.
        """
        if company.is_platform_bootstrap_company:
            _fail("TPV1_PLATFORM_BOOTSTRAP_COMPANY_CANNOT_REGISTER")
        if company not in self.env.user.company_ids:
            self.env.user.sudo().write({"company_ids": [(4, company.id)]})
        allowed_company_ids = list(
            dict.fromkeys(
                [
                    company.id,
                    *(item for item in self.env.companies.ids if item != company.id),
                ]
            )
        )
        self.env = self.env(
            context={
                **self.env.context,
                "allowed_company_ids": allowed_company_ids,
            }
        )
        self.Identity = self.env["sc.tenant.payload.external.identity"]
        self.Batch = self.env["sc.tenant.payload.import.batch"]

    def _payload_external_keys(self) -> dict[str, set[str]]:
        keys: dict[str, set[str]] = defaultdict(set)
        for relative in self.manifest["import_order"]:
            resource = _resource_name(relative)
            for _line_number, item in _iter_records(self.root, relative):
                keys[resource].add(item["external_key"])
        return keys

    def _plan_record(self, resource: str, item: dict[str, Any], payload_keys: dict[str, set[str]]) -> str:
        spec = self.resources[resource]
        if set(item.get("values", {})) - set(spec["value_fields"]):
            _fail(f"TPV1_ADAPTER_VALUE_FIELD_UNMAPPED:{resource}")
        if set(item.get("relationships", {})) - set(spec.get("relationship_fields", {})):
            _fail(f"TPV1_ADAPTER_RELATION_FIELD_UNMAPPED:{resource}")
        for relation_name, reference_value in item.get("relationships", {}).items():
            relation_spec = spec["relationship_fields"][relation_name]
            references = reference_value if isinstance(reference_value, list) else [reference_value]
            if bool(relation_spec.get("many")) != isinstance(reference_value, list):
                _fail(f"TPV1_RELATION_CARDINALITY_MISMATCH:{resource}")
            for reference in references:
                target_resource, external_key = _split_reference(reference)
                if relation_spec["resource"] != "*" and target_resource != relation_spec["resource"]:
                    _fail(f"TPV1_RELATION_RESOURCE_MISMATCH:{resource}")
                if external_key not in payload_keys[target_resource] and not self._identity(target_resource, external_key):
                    _fail(f"TPV1_RELATION_UNRESOLVED:{resource}")
        identity = self._identity(resource, item["external_key"])
        if identity:
            target = self.env[identity.model_name].browse(identity.res_id).exists()
            if not target:
                _fail(f"TPV1_EXTERNAL_IDENTITY_ORPHANED:{resource}")
            return "skip" if identity.content_checksum == item["content_checksum"] else "update"
        bootstrap = spec.get("bootstrap_xmlids", {}).get(item["external_key"])
        if bootstrap:
            record = self.env.ref(bootstrap, raise_if_not_found=False)
            if not record or record._name != spec["model"]:
                _fail(f"TPV1_BOOTSTRAP_IDENTITY_UNRESOLVED:{resource}")
            return "match"
        return "create"

    def plan(self) -> dict[str, Any]:
        payload_keys = self._payload_external_keys()
        resource_report: dict[str, dict[str, int]] = {}
        totals = {key: 0 for key in ("create", "match", "update", "skip", "conflict")}
        for relative in self.manifest["import_order"]:
            resource = _resource_name(relative)
            counts = {key: 0 for key in totals}
            for _line_number, item in _iter_records(self.root, relative):
                decision = self._plan_record(resource, item, payload_keys)
                counts[decision] += 1
                totals[decision] += 1
            resource_report[resource] = counts
        totals["conflict"] = totals["update"] if self.approved_payload_checksum != self.manifest["payload_checksum"] else 0
        for counts in resource_report.values():
            counts["conflict"] = counts["update"] if self.approved_payload_checksum != self.manifest["payload_checksum"] else 0
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "plan",
            "status": "BLOCKER" if totals["conflict"] else "PASS",
            "tenant_key": self.tenant_key,
            "payload_checksum": self.manifest["payload_checksum"],
            "source_snapshot_id": self.manifest["source_snapshot_id"],
            "resources": resource_report,
            "totals": totals,
            "database_write_count": 0,
            "filestore_write_count": 0,
            "semantic_validation": self.semantic_validation,
            "lifecycle_reconstruction": self._public_lifecycle_reconstruction(),
        }

    def _resolve_relationships(self, resource: str, item: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        specs = self.resources[resource].get("relationship_fields", {})
        for relation_name, reference_value in item.get("relationships", {}).items():
            relation_spec = specs[relation_name]
            if relation_spec.get("write", True) is False:
                continue
            references = reference_value if isinstance(reference_value, list) else [reference_value]
            ids = []
            for reference in references:
                target_resource, external_key = _split_reference(reference)
                identity = self._identity(target_resource, external_key)
                if not identity:
                    _fail(f"TPV1_RELATION_NOT_IMPORTED:{resource}")
                target = self._import_model(identity.model_name).browse(
                    identity.res_id
                ).exists()
                if not target:
                    _fail(f"TPV1_EXTERNAL_IDENTITY_ORPHANED:{resource}")
                ids.append(target.id)
            values[relation_spec["field"]] = [(6, 0, ids)] if relation_spec.get("many") else ids[0]
            if relation_spec.get("polymorphic"):
                if len(references) != 1:
                    _fail(f"TPV1_RELATION_CARDINALITY_MISMATCH:{resource}")
                values[relation_spec["model_field"]] = self._identity(*_split_reference(references[0])).model_name
        return values

    def _import_model(self, model_name: str):
        """Return the narrow privileged ORM boundary for a validated import."""
        self.env["sc.tenant.payload.adapter"].assert_import_operator()
        return self.env[model_name].with_context(
            sc_tenant_payload_import=True,
            sc_tenant_payload_checksum=self.manifest["payload_checksum"],
        ).sudo()

    def _mapped_values(self, resource: str, item: dict[str, Any]) -> dict[str, Any]:
        spec = self.resources[resource]
        values = {}
        mappings = spec.get("value_mappings", {})
        for source, value in item.get("values", {}).items():
            target = spec["value_fields"].get(source)
            if not target:
                _fail(f"TPV1_ADAPTER_VALUE_FIELD_UNMAPPED:{resource}")
            mapping = mappings.get(source)
            if mapping is not None:
                if str(value) not in mapping:
                    _fail(f"TPV1_ADAPTER_VALUE_UNMAPPED:{resource}:{source}")
                value = mapping[str(value)]
            values[target] = value
        overlap = set(values) & set(spec.get("constant_values", {}))
        if overlap:
            _fail(f"TPV1_ADAPTER_CONSTANT_VALUE_COLLISION:{resource}")
        values.update(spec.get("constant_values", {}))
        values.update(self._resolve_relationships(resource, item))
        deferred = self.lifecycle_reconstruction["_deferred"].get(
            (resource, item["external_key"]), {}
        )
        for source_field, policy in deferred.items():
            values[spec["value_fields"][source_field]] = policy["temporary_value"]
        return values

    def _restore_deferred_final_states(
        self, *, interrupt_after: str = ""
    ) -> int:
        restored = 0
        for (resource, external_key), fields in sorted(
            self.lifecycle_reconstruction["_deferred"].items()
        ):
            identity = self._identity(resource, external_key)
            if not identity:
                _fail(f"TPV1_LIFECYCLE_IDENTITY_MISSING:{resource}")
            record = self._import_model(identity.model_name).browse(
                identity.res_id
            ).exists()
            if not record:
                _fail(f"TPV1_LIFECYCLE_RECORD_MISSING:{resource}")
            spec = self.resources[resource]
            values = {
                spec["value_fields"][source_field]: policy["final_value"]
                for source_field, policy in fields.items()
            }
            record.write(values)
            for target_field, expected in values.items():
                if not _scalar_matches(record[target_field], expected):
                    _fail(
                        f"TPV1_LIFECYCLE_FINAL_STATE_MISMATCH:{resource}"
                    )
            restored += 1
            if interrupt_after == f"lifecycle_restore:{restored}":
                raise TenantPayloadInterrupted(
                    "TPV1_INJECTED_LIFECYCLE_RESTORE_INTERRUPTION"
                )
        return restored

    def _company_for(self, resource: str, item: dict[str, Any], record):
        spec = self.resources[resource]
        if spec.get("global_identity"):
            company = self.env.company
        elif spec.get("company_identity"):
            company = record
            # A company-identity resource is the explicit tenant bootstrap
            # boundary.  The imported company cannot already belong to
            # ``env.companies`` because its registration and operator scope are
            # established only after this record receives its stable payload
            # identity.  Do not weaken the check for any other resource.
            if (
                not company
                or company._name != "res.company"
                or company.is_platform_bootstrap_company
            ):
                _fail(f"TPV1_COMPANY_SCOPE_UNAUTHORIZED:{resource}")
            return company
        elif spec.get("company_via_relationship"):
            relation_name = spec["company_via_relationship"]
            reference = item.get("relationships", {}).get(relation_name)
            if not reference or isinstance(reference, list):
                _fail(f"TPV1_COMPANY_SCOPE_MISSING:{resource}")
            identity = self._identity(*_split_reference(reference))
            company = identity.company_id if identity else False
        else:
            relation_name = spec.get("company_relationship")
            reference = item.get("relationships", {}).get(relation_name) if relation_name else None
            if not reference or isinstance(reference, list):
                _fail(f"TPV1_COMPANY_SCOPE_MISSING:{resource}")
            target_resource, external_key = _split_reference(reference)
            identity = self._identity(target_resource, external_key)
            company = self.env[identity.model_name].browse(identity.res_id).exists() if identity else False
        if not company or company._name != "res.company" or company not in self.env.companies:
            _fail(f"TPV1_COMPANY_SCOPE_UNAUTHORIZED:{resource}")
        return company

    def _apply_record(self, batch, resource: str, item: dict[str, Any]) -> str:
        spec = self.resources[resource]
        identity = self._identity(resource, item["external_key"])
        if identity and identity.content_checksum == item["content_checksum"]:
            return "skip"
        if identity and self.approved_payload_checksum != self.manifest["payload_checksum"]:
            _fail(f"TPV1_UPDATE_NOT_APPROVED:{resource}")
        values = self._mapped_values(resource, item)
        target_model = self._import_model(spec["model"])
        if "migration_batch_id" in target_model._fields and "migration_batch_id" not in values:
            values["migration_batch_id"] = batch.id
        attachment_store_name = ""
        try:
            if spec.get("kind") == "attachment":
                file_meta = item.get("file") or {}
                path = self.root / str(file_meta.get("path") or "")
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != file_meta.get("sha256") or len(raw) != file_meta.get("bytes"):
                    _fail("TPV1_ATTACHMENT_INTEGRITY_MISMATCH")
                values["raw"] = raw
            if identity:
                record = self._import_model(identity.model_name).browse(
                    identity.res_id
                ).exists()
                if not record:
                    _fail(f"TPV1_EXTERNAL_IDENTITY_ORPHANED:{resource}")
                if spec.get("system_managed") == "res_users_v1":
                    record = self._apply_system_user(values, record=record)
                else:
                    record.write(values)
                self._register_business_company(
                    resource=resource,
                    external_key=item["external_key"],
                    record=record,
                    batch=batch,
                )
                attachment_store_name = str(getattr(record, "store_fname", "") or "") if spec.get("kind") == "attachment" else ""
                identity.write({"content_checksum": item["content_checksum"], "batch_id": batch.id})
                return "update"
            bootstrap = spec.get("bootstrap_xmlids", {}).get(item["external_key"])
            if bootstrap:
                record = self.env.ref(bootstrap, raise_if_not_found=False)
                if not record or record._name != spec["model"]:
                    _fail(f"TPV1_BOOTSTRAP_IDENTITY_UNRESOLVED:{resource}")
                decision = "match"
            else:
                if spec.get("system_managed") == "res_users_v1":
                    record = self._apply_system_user(values)
                else:
                    record = self._import_model(spec["model"]).create(values)
                attachment_store_name = str(getattr(record, "store_fname", "") or "")
                decision = "create"
            company = self._company_for(resource, item, record)
            if spec.get("company_identity"):
                self._activate_import_company_scope(company)
            self._create_identity(
                {
                    "tenant_key": self.tenant_key,
                    "resource": resource,
                    "external_key": item["external_key"],
                    "model_name": record._name,
                    "res_id": record.id,
                    "content_checksum": item["content_checksum"],
                    "company_id": company.id,
                    "batch_id": batch.id,
                }
            )
            self._register_business_company(
                resource=resource,
                external_key=item["external_key"],
                record=record,
                batch=batch,
            )
            return decision
        except TenantPayloadImportError:
            if attachment_store_name:
                self.env["ir.attachment"]._file_delete(attachment_store_name)
            raise
        except Exception as exc:
            if attachment_store_name:
                self.env["ir.attachment"]._file_delete(attachment_store_name)
            exception_type = type(exc).__name__
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,63}", exception_type):
                exception_type = "UnknownError"
            safe_code = ""
            message = str(exc)
            mapped_type = values.get("type")
            if mapped_type in {"pay", "receive"}:
                safe_code = f":MAPPED_TYPE_{mapped_type.upper()}"
            for code, pattern in spec.get("error_classifiers", {}).items():
                if pattern in message:
                    safe_code += f":{code}"
                    break
            if not any(f":{code}" in safe_code for code in spec.get("error_classifiers", {})):
                product_frames = [
                    frame
                    for frame in traceback.extract_tb(exc.__traceback__)
                    if "/smart_" in frame.filename
                ]
                constraint_frames = [
                    frame
                    for frame in product_frames
                    if frame.name.startswith(("_check_", "_constrain"))
                ]
                for frame in reversed(constraint_frames or product_frames):
                    function_name = re.sub(
                        r"[^A-Za-z0-9_]",
                        "_",
                        frame.name,
                    ).upper().lstrip("_")
                    if re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", function_name):
                        safe_code += f":SOURCE_{function_name}"
                        break
            safe_code += f":MESSAGE_{hashlib.sha256(message.encode('utf-8')).hexdigest()[:12].upper()}"
            raise TenantPayloadImportError(f"TPV1_RECORD_APPLY_FAILED:{resource}:{exception_type}{safe_code}") from None

    def _apply_system_user(self, values: dict[str, Any], *, record=None):
        """Narrow system boundary for Odoo's internally protected user fields."""
        allowed = {"name", "login", "email", "active", "company_id", "company_ids", "partner_id", "groups_id"}
        if set(values) - allowed or any(key in values for key in {"password", "totp_secret"}):
            _fail("TPV1_SYSTEM_USER_FIELD_FORBIDDEN")
        self.env["sc.tenant.payload.adapter"].assert_import_operator()
        Users = self.env["res.users"].with_context(no_reset_password=True, active_test=False).sudo()
        desired_active = bool(values.pop("active", True))
        try:
            if record:
                system_record = Users.browse(record.id).exists()
                if not system_record:
                    _fail("TPV1_SYSTEM_USER_MISSING")
                system_record.write(values)
            else:
                system_record = Users.create({**values, "active": True})
            if system_record.active != desired_active:
                system_record.write({"active": desired_active})
        except TenantPayloadImportError:
            raise
        except Exception:
            raise TenantPayloadImportError("TPV1_SYSTEM_USER_WRITE_FAILED") from None
        return self.env["res.users"].browse(system_record.id)

    def import_payload(self, *, chunk_size: int = 100, interrupt_after: str = "", resume_failed: bool = False) -> dict[str, Any]:
        plan = self.plan()
        if plan["totals"]["conflict"]:
            _fail("TPV1_PLAN_HAS_UNAPPROVED_CONFLICTS")
        batch = self.Batch.search(
            [("tenant_key", "=", self.tenant_key), ("payload_hash", "=", self.manifest["payload_checksum"])],
            limit=1,
        )
        if batch and batch.state == "completed":
            report = self.verify(batch=batch)
            report.update(
                {
                    "mode": "import",
                    "idempotent_noop": True,
                    "restored_final_states": 0,
                    "lifecycle_reconstruction": (
                        self._public_lifecycle_reconstruction(parity="PASS")
                    ),
                }
            )
            return report
        if not batch:
            batch = self.Batch.create({"tenant_key": self.tenant_key, "manifest_json": self.manifest})
        if batch.state == "validated":
            batch.action_plan(plan)
        if batch.state in {"planned", "interrupted", "failed"}:
            batch.action_start(allow_failed=resume_failed)
        if batch.state != "importing":
            _fail("TPV1_BATCH_NOT_RESUMABLE")
        checkpoint = batch.checkpoint or {}
        start_resource = int(checkpoint.get("resource_index", 0))
        start_row = int(checkpoint.get("row_offset", 0))
        counters = {
            "created_count": batch.created_count,
            "updated_count": batch.updated_count,
            "skipped_count": batch.skipped_count,
            "conflict_count": batch.conflict_count,
            "warning_count": batch.warning_count,
            "filestore_count": batch.filestore_count,
        }
        attachment_paths_seen: set[str] = set()
        if start_resource < len(self.manifest["import_order"]):
            resumed_relative = self.manifest["import_order"][start_resource]
            if _resource_name(resumed_relative) == "attachments" and start_row:
                for line_number, item in _iter_records(self.root, resumed_relative):
                    if line_number > start_row:
                        break
                    file_path = str((item.get("file") or {}).get("path") or "")
                    if file_path:
                        attachment_paths_seen.add(file_path)
        for resource_index, relative in enumerate(self.manifest["import_order"]):
            if resource_index < start_resource:
                continue
            resource = _resource_name(relative)
            row_offset = start_row if resource_index == start_resource else 0
            for line_number, item in _iter_records(self.root, relative):
                if line_number <= row_offset:
                    continue
                decision = self._apply_record(batch, resource, item)
                counter_key = {"create": "created_count", "update": "updated_count", "skip": "skipped_count", "match": "skipped_count"}[decision]
                counters[counter_key] += 1
                if resource == "attachments":
                    file_path = str((item.get("file") or {}).get("path") or "")
                    if file_path:
                        attachment_paths_seen.add(file_path)
                        counters["filestore_count"] = len(attachment_paths_seen)
                if line_number % chunk_size == 0 or line_number == self.manifest["record_counts"][resource]:
                    batch.update_checkpoint(
                        checkpoint={"resource_index": resource_index, "resource": resource, "row_offset": line_number},
                        counters=counters,
                    )
                    self.env.cr.commit()
                    batch = self.Batch.browse(batch.id)
                    marker = f"{resource}:{line_number}"
                    if interrupt_after == marker:
                        batch.action_interrupt("TPV1_INJECTED_INTERRUPTION")
                        self.env.cr.commit()
                        raise TenantPayloadInterrupted("TPV1_INJECTED_INTERRUPTION")
            batch.update_checkpoint(
                checkpoint={"resource_index": resource_index + 1, "resource": resource, "row_offset": 0},
                counters=counters,
            )
            self.env.cr.commit()
            batch = self.Batch.browse(batch.id)
        restored_final_states = self._restore_deferred_final_states(
            interrupt_after=interrupt_after
        )
        self.env.cr.commit()
        batch = self.Batch.browse(batch.id)
        batch.action_verify()
        self.env.cr.commit()
        if interrupt_after == "final_verification":
            batch = self.Batch.browse(batch.id)
            batch.action_interrupt("TPV1_INJECTED_VERIFICATION_INTERRUPTION")
            self.env.cr.commit()
            raise TenantPayloadInterrupted("TPV1_INJECTED_VERIFICATION_INTERRUPTION")
        report = self.verify(batch=batch)
        batch = self.Batch.browse(batch.id)
        if batch.state == "verifying":
            batch.action_complete(report)
            self.env.cr.commit()
            report["batch_state"] = "completed"
        report.update({"mode": "import", "idempotent_noop": False})
        report["restored_final_states"] = restored_final_states
        report["lifecycle_reconstruction"] = (
            self._public_lifecycle_reconstruction(parity="PASS")
        )
        return report

    def verify(self, *, batch=None, finalize_failed=False) -> dict[str, Any]:
        batch = batch or self.Batch.search(
            [("tenant_key", "=", self.tenant_key), ("payload_hash", "=", self.manifest["payload_checksum"])],
            limit=1,
        )
        if not batch:
            _fail("TPV1_BATCH_NOT_FOUND")
        verified = 0
        attachment_records = 0
        attachment_files: set[str] = set()
        amount_totals: dict[str, Decimal] = defaultdict(Decimal)
        normalized_expected_amount_totals: dict[str, Decimal] = defaultdict(Decimal)
        relationship_totals: dict[str, int] = defaultdict(int)
        for relative in self.manifest["import_order"]:
            resource = _resource_name(relative)
            spec = self.resources[resource]
            for _line_number, item in _iter_records(self.root, relative):
                identity = self._identity(resource, item["external_key"])
                if not identity or identity.content_checksum != item["content_checksum"]:
                    _fail(f"TPV1_VERIFY_IDENTITY_MISMATCH:{resource}")
                record = self._import_model(identity.model_name).browse(
                    identity.res_id
                ).exists()
                if not record or record._name != spec["model"]:
                    _fail(f"TPV1_VERIFY_RECORD_MISSING:{resource}")
                if identity.company_id not in self.env.companies:
                    _fail(f"TPV1_VERIFY_COMPANY_SCOPE:{resource}")
                for source_field, expected_value in item.get("values", {}).items():
                    target_field = spec["value_fields"][source_field]
                    mapping = spec.get("value_mappings", {}).get(source_field)
                    if mapping is not None:
                        expected_value = mapping[str(expected_value)]
                    verification = spec.get("value_verification", {}).get(source_field, "exact")
                    normalized_expected = expected_value
                    if verification == "currency_round":
                        field = record._fields[target_field]
                        currency = record[getattr(field, "currency_field", None) or "currency_id"]
                        if not currency:
                            _fail(f"TPV1_VERIFY_CURRENCY_MISSING:{resource}:{source_field}")
                        normalized_expected = currency.round(float(expected_value))
                    if not _scalar_matches(record[target_field], normalized_expected):
                        _fail(f"TPV1_VERIFY_VALUE_MISMATCH:{resource}:{source_field}")
                    amount_key = f"{resource}.{source_field}"
                    if amount_key in self.manifest.get("amount_summaries", {}):
                        try:
                            amount_totals[amount_key] += Decimal(str(record[target_field]))
                            normalized_expected_amount_totals[amount_key] += Decimal(str(normalized_expected))
                        except (InvalidOperation, TypeError, ValueError):
                            _fail(f"TPV1_VERIFY_AMOUNT_INVALID:{resource}:{source_field}")
                for target_field, expected_value in spec.get("constant_values", {}).items():
                    if not _scalar_matches(record[target_field], expected_value):
                        _fail(f"TPV1_VERIFY_CONSTANT_MISMATCH:{resource}:{target_field}")
                for relation_name, reference_value in item.get("relationships", {}).items():
                    relation_spec = spec.get("relationship_fields", {})[relation_name]
                    references = reference_value if isinstance(reference_value, list) else [reference_value]
                    target_identities = [self._identity(*_split_reference(reference)) for reference in references]
                    if any(not target for target in target_identities):
                        _fail(f"TPV1_VERIFY_RELATION_IDENTITY_MISSING:{resource}")
                    expected_ids = {target.res_id for target in target_identities}
                    actual = record[relation_spec["field"]]
                    if relation_spec.get("polymorphic"):
                        # Generic references such as ir.attachment.res_id store
                        # the target id as an integer alongside a model field.
                        actual_ids = {actual} if actual else set()
                    else:
                        actual_ids = set(actual.ids) if relation_spec.get("many") else ({actual.id} if actual else set())
                    verification = relation_spec.get("verification", "exact")
                    relation_matches = (
                        expected_ids.issubset(actual_ids)
                        if verification == "contains"
                        else actual_ids == expected_ids
                    )
                    if not relation_matches:
                        _fail(f"TPV1_VERIFY_RELATION_MISMATCH:{resource}:{relation_name}")
                    if relation_spec.get("polymorphic"):
                        expected_model = target_identities[0].model_name
                        if record[relation_spec["model_field"]] != expected_model:
                            _fail(f"TPV1_VERIFY_RELATION_MODEL_MISMATCH:{resource}:{relation_name}")
                    relationship_totals[f"{resource}.{relation_name}"] += len(references)
                if spec.get("kind") == "attachment":
                    file_meta = item.get("file") or {}
                    raw = record.raw or b""
                    if hashlib.sha256(raw).hexdigest() != file_meta.get("sha256") or len(raw) != file_meta.get("bytes"):
                        _fail("TPV1_VERIFY_ATTACHMENT_MISMATCH")
                    attachment_records += 1
                    attachment_files.add(str(file_meta.get("path") or ""))
                verified += 1
        pending = self.env["ir.module.module"].search_count([("state", "in", ["to install", "to upgrade", "to remove"])])
        if pending:
            _fail("TPV1_VERIFY_PENDING_MODULES")
        amount_summary_report = {}
        verification_warnings = []
        for key, source_expected in self.manifest.get("amount_summaries", {}).items():
            target_total = amount_totals[key].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            normalized_expected = normalized_expected_amount_totals[key].quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            source_total = Decimal(str(source_expected)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if target_total != normalized_expected:
                _fail(f"TPV1_VERIFY_AMOUNT_SUMMARY_MISMATCH:{key}")
            delta = target_total - source_total
            amount_summary_report[key] = {
                "source": str(source_total),
                "target": str(target_total),
                "delta": str(delta),
            }
            if delta:
                verification_warnings.append(f"TPV1_AMOUNT_NORMALIZED:{key}")
        if dict(sorted(relationship_totals.items())) != dict(sorted(self.manifest.get("relationship_summaries", {}).items())):
            _fail("TPV1_VERIFY_RELATIONSHIP_SUMMARY_MISMATCH")
        report = {
            "schema_version": SCHEMA_VERSION,
            "mode": "verify",
            "status": "WARN" if verification_warnings else "PASS",
            "tenant_key": self.tenant_key,
            "payload_checksum": self.manifest["payload_checksum"],
            "source_snapshot_id": self.manifest["source_snapshot_id"],
            "verified_record_count": verified,
            "verified_attachment_record_count": attachment_records,
            "verified_filestore_count": len(attachment_files),
            "pending_modules": pending,
            "batch_state": batch.state,
            "amount_summaries": amount_summary_report,
            "verification_warning_count": len(verification_warnings),
            "verification_warnings": verification_warnings,
            "counters": {
                "created": batch.created_count,
                "updated": batch.updated_count,
                "skipped": batch.skipped_count,
                "conflicts": batch.conflict_count,
                "warnings": batch.warning_count,
            },
        }
        if finalize_failed and batch.state == "failed":
            batch.action_complete_after_reverify(report)
            self.env.cr.commit()
            report["batch_state"] = "completed"
            report["recovered_after_reverify"] = True
            report["counters"]["warnings"] = max(batch.warning_count, len(verification_warnings))
        return report

    def reconcile_filestore(self, *, confirmed=False) -> dict[str, Any]:
        if not confirmed:
            _fail("TPV1_FILESTORE_RECONCILE_CONFIRMATION_REQUIRED")
        batch = self.Batch.search(
            [("tenant_key", "=", self.tenant_key), ("payload_hash", "=", self.manifest["payload_checksum"])],
            limit=1,
        )
        if not batch or batch.state != "completed":
            _fail("TPV1_FILESTORE_RECONCILE_BATCH_INVALID")
        repaired_records = 0
        repaired_files: set[str] = set()
        new_store_names: set[str] = set()
        try:
            for relative in self.manifest["import_order"]:
                resource = _resource_name(relative)
                spec = self.resources[resource]
                if spec.get("kind") != "attachment":
                    continue
                for _line_number, item in _iter_records(self.root, relative):
                    identity = self._identity(resource, item["external_key"])
                    if not identity or identity.content_checksum != item["content_checksum"]:
                        _fail("TPV1_FILESTORE_RECONCILE_IDENTITY_MISMATCH")
                    record = self.env[identity.model_name].browse(identity.res_id).exists()
                    if not record or record._name != "ir.attachment" or identity.company_id not in self.env.companies:
                        _fail("TPV1_FILESTORE_RECONCILE_SCOPE_MISMATCH")
                    file_meta = item.get("file") or {}
                    expected = (self.root / str(file_meta.get("path") or "")).read_bytes()
                    if hashlib.sha256(expected).hexdigest() != file_meta.get("sha256") or len(expected) != file_meta.get("bytes"):
                        _fail("TPV1_ATTACHMENT_INTEGRITY_MISMATCH")
                    actual = record.raw or b""
                    if hashlib.sha256(actual).hexdigest() == file_meta.get("sha256") and len(actual) == file_meta.get("bytes"):
                        continue
                    record.write({"raw": expected})
                    if record.store_fname:
                        new_store_names.add(record.store_fname)
                    repaired_records += 1
                    repaired_files.add(str(file_meta.get("path") or ""))
            report = self.verify(batch=batch)
            reconciliation = {
                "status": "PASS",
                "payload_checksum": self.manifest["payload_checksum"],
                "repaired_attachment_record_count": repaired_records,
                "repaired_distinct_file_count": len(repaired_files),
            }
            batch.record_filestore_reconciliation(reconciliation)
            self.env.cr.commit()
            report.update({"mode": "filestore_reconcile", **reconciliation})
            return report
        except Exception:
            self.env.cr.rollback()
            for store_name in new_store_names:
                self.env["ir.attachment"]._file_delete(store_name)
            raise
