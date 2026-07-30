# -*- coding: utf-8 -*-
"""Tenant-scoped extension definitions and typed values.

Extensions are deliberately not ``ir.model.fields``.  They are projected into
an explicit contract slot and therefore cannot change the public model
registry or the physical schema of a business table.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from decimal import Decimal, InvalidOperation

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError


EXTENSION_TYPES = (
    ("char", "单行文本"),
    ("text", "多行文本"),
    ("boolean", "是/否"),
    ("integer", "整数"),
    ("float", "小数"),
    ("monetary", "金额"),
    ("date", "日期"),
    ("datetime", "日期时间"),
    ("selection", "选项"),
    ("many2one", "关联对象"),
)
EXTENSION_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
HASH_IDENTITY_RE = re.compile(r"(?:^|_)[0-9a-f]{12}(?:_|$)")
FORBIDDEN_KEY_PREFIXES = ("x_", "p1_", "uc_", "legacy_", "accepted_", "user_acceptance_")


def _database_scope(env) -> str:
    value = env["ir.config_parameter"].sudo().get_param("database.uuid")
    return str(value or env.cr.dbname or "").strip()


class UITenantExtensionField(models.Model):
    _name = "ui.tenant.extension.field"
    _description = "Tenant Extension Field Definition"
    _order = "company_id, model_name, sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    database_scope = fields.Char(required=True, readonly=True, index=True)
    tenant_registration_id = fields.Many2one(
        "sc.tenant.company.registration",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="tenant_registration_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="业务模型",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(
        related="model_id.model",
        string="模型技术名",
        store=True,
        readonly=True,
        index=True,
    )
    extension_key = fields.Char(required=True, index=True)
    display_name = fields.Char(required=True)
    data_type = fields.Selection(EXTENSION_TYPES, required=True, default="char", index=True)
    required = fields.Boolean()
    readonly = fields.Boolean()
    active = fields.Boolean(default=True, index=True)
    sequence = fields.Integer(default=100)
    slot_key = fields.Char(required=True, default="business_extensions")
    slot_label = fields.Char(default="业务扩展")
    action_id = fields.Many2one("ir.actions.act_window", ondelete="cascade", index=True)
    view_id = fields.Many2one("ir.ui.view", ondelete="cascade", index=True)
    role_group_ids = fields.Many2many(
        "res.groups",
        "ui_tenant_extension_field_group_rel",
        "extension_field_id",
        "group_id",
    )
    selection_definition = fields.Json(default=list)
    relation_model_id = fields.Many2one(
        "ir.model",
        ondelete="set null",
        domain=[("transient", "=", False)],
    )
    precision = fields.Integer(default=16)
    scale = fields.Integer(default=2)
    currency_strategy = fields.Selection(
        (
            ("company", "Company currency"),
            ("record_field", "Currency from record field"),
            ("explicit", "Explicit currency"),
        ),
        default="company",
    )
    currency_field_name = fields.Char()
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    default_semantics = fields.Json(default=dict)
    validation_rule = fields.Json(default=dict)
    index_policy = fields.Selection(
        (("none", "No dedicated index"), ("shared", "Shared typed-value index")),
        default="none",
        required=True,
    )
    searchable = fields.Boolean()
    sortable = fields.Boolean()
    filterable = fields.Boolean()
    groupable = fields.Boolean()
    aggregatable = fields.Boolean()
    exportable = fields.Boolean(default=True)
    effective_version = fields.Integer(default=1, required=True)
    schema_version = fields.Integer(default=1, required=True, index=True)
    created_source = fields.Selection(
        (
            ("business_config", "Business configuration"),
            ("private_migration", "Private migration package"),
            ("test_fixture", "Isolated test fixture"),
        ),
        default="business_config",
        required=True,
    )
    migration_source = fields.Char()
    lifecycle_state = fields.Selection(
        (("draft", "Draft"), ("active", "Active"), ("retired", "Retired")),
        default="draft",
        required=True,
        index=True,
    )

    _sql_constraints = [
        (
            "extension_field_identity_uniq",
            "unique(database_scope, company_id, model_id, extension_key)",
            "The extension key must be unique for this company and model.",
        ),
    ]

    @api.depends("model_name", "extension_key", "display_name")
    def _compute_name(self):
        for record in self:
            record.name = "%s · %s" % (
                record.model_name or "-",
                record.display_name or record.extension_key or "-",
            )

    @api.model_create_multi
    def create(self, vals_list):
        scope = _database_scope(self.env)
        normalized = []
        for raw in vals_list:
            vals = dict(raw or {})
            vals["database_scope"] = scope
            vals["extension_key"] = str(vals.get("extension_key") or "").strip().lower()
            normalized.append(vals)
        records = super().create(normalized)
        records._clear_contract_cache()
        return records

    def write(self, vals):
        vals = dict(vals or {})
        if "database_scope" in vals and vals["database_scope"] != _database_scope(self.env):
            raise ValidationError("Database scope is immutable.")
        if "extension_key" in vals:
            vals["extension_key"] = str(vals.get("extension_key") or "").strip().lower()
        result = super().write(vals)
        self._clear_contract_cache()
        return result

    def unlink(self):
        if any(record.lifecycle_state != "draft" for record in self):
            raise ValidationError("Active or retired extension definitions must be retained for value audit.")
        result = super().unlink()
        self._clear_contract_cache()
        return result

    @api.model
    def retire_company_extensions(self, company):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError("Only platform administrators can retire all company extensions.")
        definitions = self.sudo().with_context(active_test=False).search(
            [("company_id", "=", company.id)]
        )
        definitions.write({"active": False, "lifecycle_state": "retired"})
        return {"company_id": int(company.id), "retired_definition_count": len(definitions)}

    @api.model
    def purge_retired_company_extensions(self, company, *, dry_run=True):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError("Only platform administrators can purge retired company extensions.")
        definitions = self.sudo().with_context(active_test=False).search(
            [("company_id", "=", company.id)]
        )
        if definitions.filtered(lambda row: row.lifecycle_state != "retired"):
            raise ValidationError("Every company extension must be retired before purge.")
        values = self.env["ui.tenant.extension.value"].sudo().search(
            [("field_definition_id", "in", definitions.ids)]
        )
        report = {
            "dry_run": bool(dry_run),
            "company_id": int(company.id),
            "definition_count": len(definitions),
            "value_count": len(values),
        }
        if dry_run:
            return report
        if not self.env.context.get("tenant_extension_company_purge"):
            raise AccessError("Company extension purge requires an explicit lifecycle context.")
        values.unlink()
        super(UITenantExtensionField, definitions).unlink()
        self._clear_contract_cache()
        return report

    @api.constrains(
        "database_scope",
        "tenant_registration_id",
        "company_id",
        "model_id",
        "extension_key",
        "data_type",
        "selection_definition",
        "relation_model_id",
        "precision",
        "scale",
        "currency_strategy",
        "currency_field_name",
        "currency_id",
        "action_id",
        "view_id",
        "slot_key",
        "slot_label",
        "aggregatable",
    )
    def _check_definition(self):
        for record in self:
            if record.database_scope != _database_scope(record.env):
                raise ValidationError("Extension definition belongs to another database scope.")
            if (
                not record.tenant_registration_id.active
                or record.company_id.is_platform_bootstrap_company
            ):
                raise ValidationError("Extension definitions require an active registered business company.")
            key = str(record.extension_key or "")
            if (
                not EXTENSION_KEY_RE.fullmatch(key)
                or key.startswith(FORBIDDEN_KEY_PREFIXES)
                or HASH_IDENTITY_RE.search(key)
            ):
                raise ValidationError("Extension key must be a stable tenant-neutral business key.")
            if record.model_id.transient:
                raise ValidationError("Transient models cannot own tenant extension values.")
            if key in record.env[record.model_name]._fields:
                raise ValidationError("Extension definitions cannot override product fields.")
            if not record.action_id and not record.view_id:
                raise ValidationError("An explicit action or view extension slot is required.")
            if record.action_id and record.action_id.res_model != record.model_name:
                raise ValidationError("Extension action does not belong to the target model.")
            if record.view_id and record.view_id.model != record.model_name:
                raise ValidationError("Extension view does not belong to the target model.")
            if not str(record.slot_key or "").strip():
                raise ValidationError("Extension slot key is required.")
            if not EXTENSION_KEY_RE.fullmatch(str(record.slot_key or "").strip()):
                raise ValidationError("Extension slot key must be a stable lowercase key.")
            if record.data_type == "selection":
                options = record._selection_options()
                if not options:
                    raise ValidationError("Selection extensions require at least one stable option.")
            elif record.selection_definition:
                raise ValidationError("Selection options are only valid for selection extensions.")
            if record.data_type == "many2one":
                if not record.relation_model_id or record.relation_model_id.transient:
                    raise ValidationError("Many2one extensions require a non-transient relation model.")
            elif record.relation_model_id:
                raise ValidationError("Relation model is only valid for many2one extensions.")
            if record.data_type in {"float", "monetary"}:
                if record.precision < 1 or record.precision > 38:
                    raise ValidationError("Precision must be between 1 and 38.")
                if record.scale < 0 or record.scale > record.precision:
                    raise ValidationError("Scale must be between zero and precision.")
            if record.data_type == "monetary":
                if record.currency_strategy == "record_field":
                    field_name = str(record.currency_field_name or "").strip()
                    model_fields = record.env[record.model_name]._fields
                    field = model_fields.get(field_name)
                    if not field or field.type != "many2one" or field.comodel_name != "res.currency":
                        raise ValidationError("Currency field must be a res.currency many2one.")
                if record.currency_strategy == "explicit" and not record.currency_id:
                    raise ValidationError("Explicit monetary extensions require a currency.")
            elif record.aggregatable and record.data_type not in {"integer", "float", "monetary"}:
                raise ValidationError("Only numeric extension types can be aggregated.")

    def _selection_options(self) -> dict[str, str]:
        self.ensure_one()
        raw = self.selection_definition if isinstance(self.selection_definition, list) else []
        options = {}
        for item in raw:
            if isinstance(item, dict):
                key = str(item.get("key") or "").strip()
                label = str(item.get("label") or "").strip()
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                key, label = str(item[0]).strip(), str(item[1]).strip()
            else:
                continue
            if key and label and key not in options:
                options[key] = label
        return options

    def _clear_contract_cache(self):
        # Odoo 17 owns ormcache instances at registry level. Mutations are rare,
        # while reads are hot, so invalidate once per definition change rather
        # than disabling or bypassing the scoped contract cache.
        self.env.registry.clear_cache()

    @api.model
    def contract_for(
        self,
        *,
        model_name,
        view_type,
        action_id=0,
        view_id=0,
        product_contract_version="v2",
    ):
        company = self.env.company
        if company not in self.env.user.company_ids:
            raise AccessError("Current company is not allowed for this user.")
        try:
            registration = self.env[
                "sc.tenant.company.registration"
            ].resolve_registered_company(company.id, require_active=True)
        except UserError:
            return []
        group_ids = tuple(sorted(self.env.user.groups_id.ids))
        group_fingerprint = hashlib.sha256(
            ",".join(str(value) for value in group_ids).encode("utf-8")
        ).hexdigest()[:16]
        domain = [
            ("database_scope", "=", _database_scope(self.env)),
            ("company_id", "=", company.id),
            ("tenant_registration_id", "=", registration.id),
            ("model_name", "=", str(model_name or "").strip()),
            ("active", "=", True),
            ("lifecycle_state", "=", "active"),
        ]
        schema_version = max(self.sudo().search(domain).mapped("schema_version") or [0])
        return self._cached_contract(
            _database_scope(self.env),
            company.id,
            registration.id,
            self.env.uid,
            group_fingerprint,
            str(model_name or "").strip(),
            str(view_type or "").strip(),
            int(action_id or 0),
            int(view_id or 0),
            int(schema_version),
            str(product_contract_version or "v2"),
        )

    @api.model
    @tools.ormcache(
        "database_scope",
        "company_id",
        "registration_id",
        "user_id",
        "group_fingerprint",
        "model_name",
        "view_type",
        "action_id",
        "view_id",
        "schema_version",
        "product_contract_version",
    )
    def _cached_contract(
        self,
        database_scope,
        company_id,
        registration_id,
        user_id,
        group_fingerprint,
        model_name,
        view_type,
        action_id,
        view_id,
        schema_version,
        product_contract_version,
    ):
        del group_fingerprint
        if view_type not in {"form", "tree", "list"}:
            return []
        user = self.env["res.users"].browse(user_id).exists()
        if not user or company_id not in user.company_ids.ids:
            return []
        records = self.sudo().search(
            [
                ("database_scope", "=", database_scope),
                ("company_id", "=", company_id),
                ("tenant_registration_id", "=", registration_id),
                ("model_name", "=", model_name),
                ("active", "=", True),
                ("lifecycle_state", "=", "active"),
            ],
            order="sequence, id",
        )
        user_groups = set(user.groups_id.ids)
        output = []
        for record in records:
            if record.action_id and record.action_id.id != action_id:
                continue
            if record.view_id and record.view_id.id != view_id:
                continue
            if record.role_group_ids and not (set(record.role_group_ids.ids) & user_groups):
                continue
            output.append(record._contract_descriptor(product_contract_version))
        return output

    def _contract_descriptor(self, product_contract_version):
        self.ensure_one()
        return {
            "extension_id": int(self.id),
            "extension_key": self.extension_key,
            "label": self.display_name,
            "data_type": self.data_type,
            "required": bool(self.required),
            "readonly": bool(self.readonly),
            "sequence": int(self.sequence or 0),
            "slot_key": self.slot_key,
            "slot_label": self.slot_label or "",
            "selection": [
                {"key": key, "label": label}
                for key, label in self._selection_options().items()
            ],
            "relation_model": self.relation_model_id.model if self.relation_model_id else "",
            "precision": int(self.precision or 0),
            "scale": int(self.scale or 0),
            "currency_strategy": self.currency_strategy if self.data_type == "monetary" else "",
            "currency_field": self.currency_field_name if self.currency_strategy == "record_field" else "",
            "currency_id": int(self.currency_id.id or 0) if self.currency_strategy == "explicit" else 0,
            "searchable": bool(self.searchable),
            "sortable": bool(self.sortable),
            "filterable": bool(self.filterable),
            "groupable": bool(self.groupable),
            "aggregatable": bool(self.aggregatable),
            "exportable": bool(self.exportable),
            "schema_version": int(self.schema_version or 1),
            "product_contract_version": product_contract_version,
            "source": "tenant_extension",
        }


class UITenantExtensionValue(models.Model):
    _name = "ui.tenant.extension.value"
    _description = "Tenant Extension Typed Value"
    _order = "field_definition_id, record_id, id"

    field_definition_id = fields.Many2one(
        "ui.tenant.extension.field",
        required=True,
        index=True,
        ondelete="restrict",
    )
    database_scope = fields.Char(related="field_definition_id.database_scope", store=True, index=True)
    company_id = fields.Many2one(
        related="field_definition_id.company_id",
        store=True,
        index=True,
    )
    model_name = fields.Char(related="field_definition_id.model_name", store=True, index=True)
    record_id = fields.Integer(required=True, index=True)
    active = fields.Boolean(default=True, index=True)
    value_schema_version = fields.Integer(default=1, required=True)
    char_value = fields.Char(index=True)
    text_value = fields.Text()
    boolean_is_set = fields.Boolean()
    boolean_value = fields.Boolean()
    integer_value = fields.Integer(index=True)
    float_value = fields.Float(index=True)
    monetary_value = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    date_value = fields.Date(index=True)
    datetime_value = fields.Datetime(index=True)
    selection_value = fields.Char(index=True)
    relation_model = fields.Char(index=True)
    relation_record_id = fields.Integer(index=True)
    archived_reason = fields.Char()

    _sql_constraints = [
        (
            "extension_value_identity_uniq",
            "unique(field_definition_id, record_id)",
            "Only one value is allowed per extension definition and business record.",
        ),
    ]

    @api.model
    def set_typed_value(self, definition, record_id, value, *, currency_id=0):
        definition = definition.exists()
        if not definition or definition.lifecycle_state != "active" or not definition.active:
            raise ValidationError("Extension definition is not active.")
        target = self._checked_target(definition, int(record_id), "write")
        vals = self._typed_values(definition, value, currency_id=currency_id, target=target)
        current = self.sudo().search(
            [
                ("field_definition_id", "=", definition.id),
                ("record_id", "=", target.id),
            ],
            limit=1,
        )
        vals.update(
            {
                "field_definition_id": definition.id,
                "record_id": target.id,
                "value_schema_version": definition.schema_version,
                "active": True,
            }
        )
        if current:
            current.write(vals)
            return current
        return self.sudo().create(vals)

    @api.model
    def read_for_record(self, definition, record_id):
        definition = definition.exists()
        if not definition or not definition.active:
            return None
        target = self._checked_target(definition, int(record_id), "read")
        value = self.sudo().search(
            [
                ("field_definition_id", "=", definition.id),
                ("record_id", "=", target.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        return value._export_typed_value(definition) if value else None

    @api.model
    def export_for_records(self, definitions, record_ids):
        output = []
        for definition in definitions:
            if not definition.exportable:
                continue
            for record_id in record_ids:
                value = self.read_for_record(definition, record_id)
                if value is not None:
                    output.append(
                        {
                            "extension_id": int(definition.id),
                            "extension_key": definition.extension_key,
                            "record_id": int(record_id),
                            "value": value,
                        }
                    )
        return output

    @api.model
    def _checked_target(self, definition, record_id, operation):
        if definition.database_scope != _database_scope(self.env):
            raise AccessError("Extension definition belongs to another database.")
        if definition.company_id != self.env.company:
            raise AccessError("Extension definition is outside the active company context.")
        if definition.company_id not in self.env.user.company_ids:
            raise AccessError("Extension definition belongs to another company.")
        registration = self.env[
            "sc.tenant.company.registration"
        ].resolve_registered_company(definition.company_id.id, require_active=True)
        if registration != definition.tenant_registration_id:
            raise AccessError("Extension definition registration is no longer authoritative.")
        model = self.env[definition.model_name]
        model.check_access_rights(operation)
        target = model.browse(record_id).exists()
        if not target:
            raise AccessError("Business record is unavailable.")
        target.check_access_rule(operation)
        if "company_id" in target._fields:
            target_company = target.company_id
            if target_company and target_company != definition.company_id:
                raise AccessError("Business record and extension definition company do not match.")
        return target

    @api.model
    def _typed_values(self, definition, value, *, currency_id=0, target=None):
        vals = {
            "char_value": False,
            "text_value": False,
            "boolean_is_set": False,
            "boolean_value": False,
            "integer_value": 0,
            "float_value": 0.0,
            "monetary_value": 0.0,
            "currency_id": False,
            "date_value": False,
            "datetime_value": False,
            "selection_value": False,
            "relation_model": False,
            "relation_record_id": 0,
        }
        if value is None:
            return vals
        kind = definition.data_type
        if kind == "char":
            vals["char_value"] = str(value)
        elif kind == "text":
            vals["text_value"] = str(value)
        elif kind == "boolean":
            if not isinstance(value, bool):
                raise ValidationError("Boolean extension values must be true or false.")
            vals["boolean_is_set"] = True
            vals["boolean_value"] = value
        elif kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError("Integer extension values must be integers.")
            vals["integer_value"] = value
        elif kind in {"float", "monetary"}:
            if isinstance(value, bool):
                raise ValidationError("Numeric extension values must be numbers.")
            try:
                decimal_value = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValidationError("Numeric extension value is invalid.") from None
            if not decimal_value.is_finite():
                raise ValidationError("Numeric extension value must be finite.")
            fractional = max(0, -decimal_value.as_tuple().exponent)
            if fractional > definition.scale:
                raise ValidationError("Numeric extension value exceeds configured scale.")
            total_digits = max(
                len(decimal_value.as_tuple().digits),
                decimal_value.adjusted() + 1,
            )
            if total_digits > definition.precision:
                raise ValidationError("Numeric extension value exceeds configured precision.")
            if kind == "float":
                vals["float_value"] = float(decimal_value)
            else:
                vals["monetary_value"] = float(decimal_value)
                vals["currency_id"] = self._currency_for(definition, currency_id, target=target).id
        elif kind == "date":
            vals["date_value"] = fields.Date.to_date(value)
        elif kind == "datetime":
            vals["datetime_value"] = fields.Datetime.to_datetime(value)
        elif kind == "selection":
            key = str(value)
            if key not in definition._selection_options():
                raise ValidationError("Selection extension value is not allowed.")
            vals["selection_value"] = key
        elif kind == "many2one":
            relation_id = int(value or 0)
            relation_model = definition.relation_model_id.model
            relation = self.env[relation_model].browse(relation_id).exists()
            if not relation:
                raise ValidationError("Related extension record does not exist.")
            relation.check_access_rights("read")
            relation.check_access_rule("read")
            if "company_id" in relation._fields and relation.company_id and relation.company_id != definition.company_id:
                raise AccessError("Related extension record belongs to another company.")
            vals["relation_model"] = relation_model
            vals["relation_record_id"] = relation.id
        else:
            raise ValidationError("Unsupported extension value type.")
        return vals

    @api.model
    def _currency_for(self, definition, explicit_currency_id, *, target=None):
        if definition.currency_strategy == "company":
            return definition.company_id.currency_id
        if definition.currency_strategy == "explicit":
            return definition.currency_id
        if definition.currency_strategy == "record_field":
            if not target:
                raise ValidationError("A business record is required to resolve currency.")
            currency = target[definition.currency_field_name]
            if not currency:
                raise ValidationError("The business record has no currency.")
            return currency
        currency = self.env["res.currency"].browse(int(explicit_currency_id or 0)).exists()
        if not currency:
            raise ValidationError("A valid currency is required.")
        return currency

    def _export_typed_value(self, definition):
        self.ensure_one()
        kind = definition.data_type
        if kind == "char":
            return self.char_value
        if kind == "text":
            return self.text_value
        if kind == "boolean":
            return self.boolean_value if self.boolean_is_set else None
        if kind == "integer":
            return self.integer_value
        if kind == "float":
            return self.float_value
        if kind == "monetary":
            return {
                "amount": self.monetary_value,
                "currency_id": int(self.currency_id.id or 0),
            }
        if kind == "date":
            return fields.Date.to_string(self.date_value) if self.date_value else None
        if kind == "datetime":
            return fields.Datetime.to_string(self.datetime_value) if self.datetime_value else None
        if kind == "selection":
            return self.selection_value
        if kind == "many2one":
            return {
                "model": self.relation_model,
                "id": int(self.relation_record_id or 0),
            }
        return None


class UITenantExtensionMigrationService(models.AbstractModel):
    """Generic, customer-neutral migration boundary.

    Private user-data packages resolve old columns and ownership.  The public
    product only validates typed rows and writes through the same isolated
    value service used at runtime.
    """

    _name = "ui.tenant.extension.migration.service"
    _description = "Tenant Extension Migration Service"

    @api.model
    def migrate_rows(self, definition, rows, *, dry_run=True):
        definition = definition.exists()
        if not definition or definition.company_id != self.env.company:
            raise AccessError("Migration definition must belong to the active company.")
        if not isinstance(rows, list):
            raise ValidationError("Migration rows must be a list.")
        if not dry_run and not self.env.context.get("tenant_extension_isolated_migration"):
            raise AccessError("Migration execution is restricted to an explicit isolated context.")

        Value = self.env["ui.tenant.extension.value"]
        digest_rows = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValidationError("Each migration row must be an object.")
            record_id = int(row.get("record_id") or 0)
            if record_id <= 0:
                raise ValidationError("Migration rows require a positive record_id.")
            target = Value._checked_target(definition, record_id, "write")
            typed = Value._typed_values(
                definition,
                row.get("value"),
                currency_id=int(row.get("currency_id") or 0),
                target=target,
            )
            digest_rows.append(
                {
                    "record_id": record_id,
                    "typed": {
                        key: value
                        for key, value in sorted(typed.items())
                        if value not in (False, None, "")
                    },
                }
            )
            if not dry_run:
                Value.set_typed_value(
                    definition,
                    record_id,
                    row.get("value"),
                    currency_id=int(row.get("currency_id") or 0),
                )
        checksum = hashlib.sha256(
            json.dumps(
                digest_rows,
                sort_keys=True,
                ensure_ascii=True,
                default=str,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "dry_run": bool(dry_run),
            "definition_id": int(definition.id),
            "company_id": int(definition.company_id.id),
            "model": definition.model_name,
            "row_count": len(rows),
            "typed_validation": "PASS",
            "checksum_algorithm": "sha256",
            "checksum": checksum,
            "old_columns_deleted": 0,
            "formal_fields_modified": 0,
        }


class UIUnresolvedExtensionAuditValue(models.Model):
    """Restricted carrier for an extension value whose owner is unresolved.

    This model is intentionally absent from product page contracts and tenant
    extension discovery.  It preserves bytes and provenance without assigning
    a company or inventing a business meaning.
    """

    _name = "ui.unresolved.extension.audit.value"
    _description = "Unresolved Extension Audit Value"
    _order = "id"

    database_scope = fields.Char(required=True, readonly=True, index=True)
    source_model = fields.Char(required=True, readonly=True)
    source_table = fields.Char(required=True, readonly=True)
    source_column = fields.Char(required=True, readonly=True)
    record_locator_hash = fields.Char(required=True, readonly=True, index=True)
    value_type = fields.Selection(
        (
            ("char", "Character"),
            ("text", "Text"),
            ("boolean", "Boolean"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("date", "Date"),
            ("datetime", "Datetime"),
            ("binary", "Binary"),
        ),
        required=True,
        readonly=True,
    )
    payload = fields.Binary(required=True, readonly=True, attachment=False)
    checksum_salt = fields.Char(required=True, readonly=True)
    payload_checksum = fields.Char(required=True, readonly=True, index=True)
    source_state = fields.Selection(
        (
            ("unresolved", "Unresolved"),
            ("owner_confirmed", "Owner confirmed"),
            ("migrated", "Migrated"),
        ),
        default="unresolved",
        required=True,
        readonly=True,
    )
    unresolved_reason = fields.Char(required=True, readonly=True)
    archive_schema_version = fields.Integer(default=1, required=True, readonly=True)
    archived_at = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    archived_by = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        ondelete="restrict",
    )

    _sql_constraints = [
        (
            "unresolved_archive_identity_uniq",
            "unique(database_scope, source_model, source_table, source_column, record_locator_hash)",
            "This unresolved source value is already archived.",
        ),
    ]

    @api.model
    def archive_unresolved(
        self,
        *,
        source_model,
        source_table,
        source_column,
        source_record_locator,
        value_type,
        raw_value,
        unresolved_reason,
    ):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError("Only platform administrators can archive unresolved extension values.")
        if not self.env.context.get("unresolved_extension_audit_archive"):
            raise AccessError("Unresolved archive writes require an explicit governance context.")
        if value_type not in dict(self._fields["value_type"].selection):
            raise ValidationError("Unsupported unresolved archive value type.")
        payload = self._payload_bytes(raw_value)
        salt = secrets.token_hex(16)
        checksum = hashlib.sha256(salt.encode("ascii") + b":" + payload).hexdigest()
        locator_secret = (
            self.env["ir.config_parameter"].sudo().get_param("database.secret")
            or _database_scope(self.env)
        )
        locator = hashlib.sha256(
            (
                str(locator_secret)
                + "\x00"
                + str(source_model)
                + "\x00"
                + str(source_table)
                + "\x00"
                + str(source_column)
                + "\x00"
                + str(source_record_locator)
            ).encode("utf-8")
        ).hexdigest()
        return self.sudo().create(
            {
                "database_scope": _database_scope(self.env),
                "source_model": str(source_model),
                "source_table": str(source_table),
                "source_column": str(source_column),
                "record_locator_hash": locator,
                "value_type": value_type,
                "payload": payload,
                "checksum_salt": salt,
                "payload_checksum": checksum,
                "unresolved_reason": str(unresolved_reason),
            }
        )

    def verify_integrity(self):
        self.ensure_one()
        payload = bytes(self.payload or b"")
        checksum = hashlib.sha256(
            str(self.checksum_salt).encode("ascii") + b":" + payload
        ).hexdigest()
        return secrets.compare_digest(checksum, str(self.payload_checksum or ""))

    @api.model
    def _payload_bytes(self, raw_value):
        if isinstance(raw_value, bytes):
            return raw_value
        if isinstance(raw_value, str):
            return raw_value.encode("utf-8")
        return json.dumps(
            raw_value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("unresolved_extension_audit_archive"):
            raise AccessError("Unresolved audit values can only be created by the archive service.")
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError("Unresolved audit values are immutable.")

    def unlink(self):
        raise AccessError("Unresolved audit values cannot be deleted through the product runtime.")
