# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from lxml import etree as ET

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.smart_core.utils.backend_contract_boundaries import (
    classify_view_orchestration_contract,
    view_orchestration_apply_order_key,
)
from odoo.addons.smart_core.utils.business_config_mutation_audit import record_business_config_mutation
from odoo.addons.smart_core.core.view_contract_presence import (
    contract_contributes_view,
    normalize_contract_view_type,
)

TEST_PLACEHOLDER_TOKENS = ("CODEX_", "codex_view_orch_surface")
STALE_TRANSITION_FIELD_PREFIXES = (
    "_".join(("p1", "visible", "")),
    "_".join(("uc", "formal", "")),
    "accepted_visible_",
    "user_acceptance_",
)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ViewOrchestrationContractProjection:
    """Typed runtime projection shared by published and preview contracts.

    Runtime consumers must not depend on ORM relation objects: preview rows do
    not exist in the database and therefore expose relation identifiers as
    primitive integers.
    """

    id: int
    name: str
    contract_json: dict[str, Any]
    view_type: str
    action_id: int
    view_id: int
    role_key: str
    priority: int
    version_no: int
    status: str
    source_kind: str

    @classmethod
    def from_record(cls, record):
        return cls(
            id=int(record.id or 0),
            name=str(record.name or ""),
            contract_json=record.contract_json if isinstance(record.contract_json, dict) else {},
            view_type=str(record.view_type or ""),
            action_id=int(record.action_id.id or 0),
            view_id=int(record.view_id.id or 0),
            role_key=str(record.role_key or ""),
            priority=int(record.priority or 100),
            version_no=int(record.version_no or 1),
            status=str(record.status or ""),
            source_kind="published",
        )

    @classmethod
    def from_preview_item(cls, item):
        return cls(
            id=0,
            name="preview:%s" % item.target_key,
            contract_json=item.draft_payload if isinstance(item.draft_payload, dict) else {},
            view_type=str(item.view_type or ""),
            action_id=int(item.action_id or 0),
            view_id=int(item.view_id or 0),
            role_key=str(item.role_key or ""),
            priority=1_000_000,
            version_no=int(item.base_version_no or 0) + 1,
            status="preview",
            source_kind="change_set_preview",
        )


class UIBusinessConfigContract(models.Model):
    _name = "ui.business.config.contract"
    _description = "UI Business Config Contract"
    _order = "write_date desc, id desc"

    name = fields.Char(required=True)
    model = fields.Char(required=True, index=True)
    view_type = fields.Selection([
        ("form", "Form"),
        ("tree", "Tree/List"),
        ("list", "List"),
        ("kanban", "Kanban"),
        ("search", "Search"),
        ("pivot", "Pivot"),
        ("graph", "Graph"),
        ("calendar", "Calendar"),
        ("gantt", "Gantt"),
        ("activity", "Activity"),
        ("dashboard", "Dashboard"),
    ], index=True)
    action_id = fields.Many2one("ir.actions.act_window", string="Action", ondelete="cascade", index=True)
    view_id = fields.Many2one("ir.ui.view", string="View", ondelete="cascade", index=True)
    role_key = fields.Char(index=True)
    priority = fields.Integer(default=100, index=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    status = fields.Selection([("draft", "Draft"), ("published", "Published")], default="draft", required=True)
    version_no = fields.Integer(default=1, required=True)
    contract_json = fields.Json(required=True, default=dict)
    created_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    published_at = fields.Datetime()

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)", "同公司下业务配置名称必须唯一。"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        record_business_config_mutation(records, "create", vals_list)
        return records

    def write(self, vals):
        result = super().write(vals)
        record_business_config_mutation(self, "write", vals)
        return result

    def unlink(self):
        record_business_config_mutation(self, "unlink")
        return super().unlink()

    def _normalize_view_orchestration_view_type(self, view_type: str | None) -> str:
        return normalize_contract_view_type(view_type)

    @api.model
    def contract_contributes_view(self, contract, requested_view_type: str | None) -> bool:
        return contract_contributes_view(contract, requested_view_type)

    @staticmethod
    def _contains_test_placeholder(value) -> bool:
        text = str(value or "")
        return any(token in text for token in TEST_PLACEHOLDER_TOKENS)

    @api.constrains("name", "contract_json", "action_id", "active", "status")
    def _check_formal_surface_no_test_placeholders(self):
        for rec in self:
            if not rec.active or rec.status != "published":
                continue
            if rec._contains_test_placeholder(rec.name) or rec._contains_test_placeholder(rec.contract_json):
                raise ValidationError(
                    "正式产品列表配置不能发布测试占位内容：%s" % (rec.action_id.display_name or rec.name)
                )

    @staticmethod
    def _simple_view_orchestration_field_name(value) -> str:
        if not isinstance(value, str):
            return ""
        candidate = value.strip()
        if not candidate:
            return ""
        if "." in candidate or "(" in candidate or ")" in candidate or " " in candidate:
            return ""
        if not candidate.replace("_", "").isalnum():
            return ""
        return candidate

    @classmethod
    def _unknown_view_orchestration_fields(cls, payload: dict, model_fields) -> list[str]:
        if not isinstance(payload, dict):
            return []
        orchestration = payload.get("view_orchestration")
        if not isinstance(orchestration, dict):
            return []
        views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
        known_fields = set(model_fields or [])
        unknown: list[str] = []

        def add_ref(view_type: str, key: str, value) -> None:
            field_name = cls._simple_view_orchestration_field_name(value)
            if field_name and field_name not in known_fields:
                unknown.append("%s.%s:%s" % (view_type, key, field_name))

        def add_row_ref(view_type: str, key: str, row) -> None:
            if isinstance(row, str):
                add_ref(view_type, key, row)
                return
            if not isinstance(row, dict):
                return
            for ref_key in ("field", "name", "field_name"):
                if row.get(ref_key):
                    add_ref(view_type, key, row.get(ref_key))
                    return

        def add_slot_refs(view_type: str, key: str, value) -> None:
            if not isinstance(value, dict):
                return
            for slot_key, slot_value in value.items():
                if isinstance(slot_value, str):
                    add_ref(view_type, "%s.%s" % (key, slot_key), slot_value)
                elif isinstance(slot_value, list):
                    for item in slot_value:
                        if isinstance(item, str):
                            add_ref(view_type, "%s.%s" % (key, slot_key), item)
                        elif isinstance(item, dict):
                            for nested_key in ("field", "name", "field_name"):
                                if item.get(nested_key):
                                    add_ref(view_type, "%s.%s" % (key, slot_key), item.get(nested_key))
                                    break

        def add_layout_refs(view_type: str, rows, path: str = "layout") -> None:
            if not isinstance(rows, list):
                return
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                if str(row.get("type") or "").strip().lower() == "field":
                    add_row_ref(view_type, "%s[%s]" % (path, idx), row)
                for child_key in ("children", "pages", "tabs", "nodes", "items"):
                    children = row.get(child_key)
                    if isinstance(children, list):
                        add_layout_refs(view_type, children, "%s[%s].%s" % (path, idx, child_key))

        for view_type, spec in views.items():
            if not isinstance(spec, dict):
                continue
            for key in ("fields", "columns", "measures", "dimensions"):
                rows = spec.get(key) if isinstance(spec.get(key), list) else []
                for row in rows:
                    add_row_ref(view_type, key, row)
            for key in ("filters", "group_by", "groupBys"):
                rows = spec.get(key) if isinstance(spec.get(key), list) else []
                for row in rows:
                    if isinstance(row, str):
                        add_ref(view_type, key, row)
                    elif isinstance(row, dict) and row.get("field"):
                        add_ref(view_type, key, row.get("field"))
            for key in (
                "slots",
                "date_slots",
                "resource_slots",
                "color_slots",
                "dependency_slots",
                "activity_type_slots",
                "deadline_slots",
                "assignee_slots",
                "metric_slots",
                "chart_slots",
            ):
                add_slot_refs(view_type, key, spec.get(key))
            add_layout_refs(view_type, spec.get("layout"))
            for key in ("default_group_by", "order", "default_order"):
                add_ref(view_type, key, spec.get(key))
        return sorted(set(unknown))

    @classmethod
    def _view_orchestration_rows(cls, payload: dict, requested_view_type: str) -> list[dict[str, str]]:
        orchestration = payload.get("view_orchestration") if isinstance(payload, dict) else {}
        views = orchestration.get("views") if isinstance(orchestration, dict) and isinstance(orchestration.get("views"), dict) else {}
        normalized = normalize_contract_view_type(requested_view_type)
        spec = views.get(normalized) if isinstance(views.get(normalized), dict) else {}
        if normalized == "tree" and not spec:
            spec = views.get("list") if isinstance(views.get("list"), dict) else {}
        rows = spec.get("columns") if normalized == "tree" and isinstance(spec.get("columns"), list) else spec.get("fields")
        if not isinstance(rows, list):
            return []
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            if isinstance(row, str):
                name = cls._simple_view_orchestration_field_name(row)
                label = ""
            elif isinstance(row, dict):
                name = cls._simple_view_orchestration_field_name(
                    row.get("name") or row.get("field") or row.get("field_name")
                )
                label = str(row.get("label") or row.get("string") or row.get("display_label") or "").strip()
            else:
                continue
            if name:
                normalized_rows.append({"name": name, "label": label})
        return normalized_rows

    @api.model
    def _authoritative_action_view_columns(
        self,
        model_name: str,
        *,
        action_id: int = 0,
        view_id: int = 0,
    ) -> list[dict[str, str]]:
        if not model_name or model_name not in self.env:
            return []
        resolved_view_id = int(view_id or 0)
        if not resolved_view_id and action_id and "ir.actions.act_window" in self.env:
            action = self.env["ir.actions.act_window"].sudo().browse(int(action_id))
            if action.exists():
                action_views = action.view_ids.filtered(lambda row: row.view_mode in ("tree", "list")).sorted("sequence")
                candidate = action_views[:1].view_id if action_views else action.view_id
                if candidate and candidate.type in ("tree", "list"):
                    resolved_view_id = int(candidate.id or 0)
        try:
            Model = self.env[model_name].sudo().with_context(
                contract_projection_readonly=True,
                contract_action_id=int(action_id or 0),
                contract_view_id=resolved_view_id,
            )
            if hasattr(Model, "get_view"):
                view_def = Model.get_view(view_id=resolved_view_id or None, view_type="tree")
            else:
                view_def = Model.fields_view_get(view_id=resolved_view_id or None, view_type="tree", toolbar=False)
            root = ET.fromstring(str((view_def or {}).get("arch") or ""))
        except Exception:
            _logger.exception(
                "RUNTIME_VIEW_CONTRACT_DIAGNOSTIC reason_code=authoritative_view_unavailable model=%s action_id=%s view_id=%s",
                model_name,
                int(action_id or 0),
                resolved_view_id,
            )
            return []
        columns: list[dict[str, str]] = []
        for node in root.iter("field"):
            name = self._simple_view_orchestration_field_name(node.get("name"))
            if not name or any(row["name"] == name for row in columns):
                continue
            field = self.env[model_name]._fields.get(name)
            label = str(node.get("string") or getattr(field, "string", "") or "").strip()
            columns.append({"name": name, "label": label})
        return columns

    @api.model
    def _runtime_contract_validation(
        self,
        contract,
        *,
        requested_view_type: str,
        action_id: int = 0,
        view_id: int = 0,
        model_name: str = "",
    ) -> dict[str, Any]:
        model_name = str(model_name or (contract.model if hasattr(contract, "model") else "")).strip()
        payload = contract.contract_json if isinstance(getattr(contract, "contract_json", None), dict) else {}
        normalized = self._normalize_view_orchestration_view_type(requested_view_type)
        rows = self._view_orchestration_rows(payload, normalized)
        reasons: list[dict[str, Any]] = []
        if model_name not in self.env:
            reasons.append({"reason_code": "runtime_model_unavailable", "model": model_name})
            model_fields = {}
        else:
            model_fields = self.env[model_name]._fields
        names = [row["name"] for row in rows]
        referenced_values: list[str] = []

        def collect_references(value) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect_references(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_references(nested)
            elif isinstance(value, str):
                candidate = self._simple_view_orchestration_field_name(value)
                if candidate:
                    referenced_values.append(candidate)

        collect_references(payload.get("view_orchestration"))
        stale = sorted({name for name in referenced_values if name.startswith(STALE_TRANSITION_FIELD_PREFIXES)})
        if stale:
            reasons.append({"reason_code": "historical_stale_alias", "fields": stale})
        unknown_paths = self._unknown_view_orchestration_fields(payload, model_fields)
        unknown = sorted({path.rsplit(":", 1)[-1] for path in unknown_paths})
        if unknown:
            reasons.append({"reason_code": "runtime_unknown_columns", "fields": unknown})
        unlabeled = []
        for row in rows:
            field = model_fields.get(row["name"]) if model_fields else None
            label = str(row["label"] or getattr(field, "string", "") or "").strip()
            if not label or label == row["name"] or label.startswith(STALE_TRANSITION_FIELD_PREFIXES):
                unlabeled.append(row["name"])
        if unlabeled:
            reasons.append({"reason_code": "runtime_unlabeled_columns", "fields": unlabeled})
        authoritative: list[dict[str, str]] = []
        effective_action_id = int(action_id or getattr(getattr(contract, "action_id", None), "id", 0) or 0)
        effective_view_id = int(view_id or getattr(getattr(contract, "view_id", None), "id", 0) or 0)
        if normalized == "tree" and (effective_action_id or effective_view_id):
            authoritative = self._authoritative_action_view_columns(
                model_name,
                action_id=effective_action_id,
                view_id=effective_view_id,
            )
            authoritative_names = [row["name"] for row in authoritative]
            if not authoritative_names:
                reasons.append({"reason_code": "authoritative_view_unavailable"})
            else:
                positions = [authoritative_names.index(name) for name in names if name in authoritative_names]
                nonmembers = [name for name in names if name not in authoritative_names]
                if nonmembers:
                    reasons.append({"reason_code": "runtime_columns_not_in_authoritative_view", "fields": nonmembers})
                if positions != sorted(positions):
                    reasons.append({"reason_code": "runtime_columns_order_drift"})
        return {
            "valid": not reasons,
            "reason_codes": [row["reason_code"] for row in reasons],
            "reasons": reasons,
            "fields": names,
            "authoritative_fields": [row["name"] for row in authoritative],
            "view_type": normalized,
            "model": model_name,
            "action_id": effective_action_id,
            "view_id": effective_view_id,
        }

    @api.constrains("contract_json", "model")
    def _check_contract_json(self):
        for rec in self:
            payload = rec.contract_json if isinstance(rec.contract_json, dict) else {}
            rec._check_view_orchestration_payload(payload)
            if rec.model and rec.model in self.env:
                unknown_fields = rec._unknown_view_orchestration_fields(payload, self.env[rec.model]._fields)
                if unknown_fields:
                    raise ValidationError("view_orchestration 引用了不存在字段：%s" % ", ".join(unknown_fields))
            objects = payload.get("objects") if isinstance(payload.get("objects"), list) else []
            object_fields_map: dict[str, set[str]] = {}
            for obj in objects:
                if not isinstance(obj, dict):
                    raise ValidationError("objects 节点必须是对象数组。")
                obj_name = str(obj.get("name") or "").strip()
                if not obj_name:
                    raise ValidationError("业务对象 name 不能为空。")
                fields_rows = obj.get("fields") if isinstance(obj.get("fields"), list) else []
                object_fields_map.setdefault(obj_name, set())
                for row in fields_rows:
                    if not isinstance(row, dict):
                        raise ValidationError("fields 节点必须是对象数组。")
                    field_name = str(row.get("name") or "").strip()
                    field_type = str(row.get("type") or "").strip()
                    if not field_name:
                        raise ValidationError("字段 name 不能为空。")
                    if field_type not in {"string", "float", "date", "selection", "integer", "boolean", "text"}:
                        raise ValidationError("字段类型不支持：%s" % field_type)
                    if field_name and not field_name.replace("_", "").isalnum():
                        raise ValidationError("字段名不合法：%s" % field_name)
                    object_fields_map[obj_name].add(field_name)
                    default_value = row.get("default")
                    if default_value is not None and field_type in {"float", "integer"} and not isinstance(default_value, (int, float)):
                        raise ValidationError("字段默认值类型不匹配：%s 需要数字" % field_name)
                    if default_value is not None and field_type == "boolean" and not isinstance(default_value, bool):
                        raise ValidationError("字段默认值类型不匹配：%s 需要布尔值" % field_name)
                    if field_type == "selection":
                        options = row.get("options") if isinstance(row.get("options"), list) else []
                        if not options:
                            raise ValidationError("selection 字段必须提供 options：%s" % field_name)
                        for option in options:
                            if not isinstance(option, dict):
                                raise ValidationError("selection 字段 options 必须是对象数组：%s" % field_name)
                            value = str(option.get("value") or "").strip()
                            label = str(option.get("label") or "").strip()
                            if not value or not label:
                                raise ValidationError("selection 字段 option 必须包含 value/label：%s" % field_name)

            layout = payload.get("layout") if isinstance(payload.get("layout"), dict) else {}
            for section in ("form", "list", "kanban"):
                nodes = layout.get(section) if isinstance(layout.get(section), list) else []
                for node in nodes:
                    if not isinstance(node, dict):
                        raise ValidationError("layout.%s 节点必须是对象数组。" % section)
                    target_obj = str(node.get("object") or "").strip()
                    target_field = str(node.get("field") or "").strip()
                    if target_obj and target_field and target_obj in object_fields_map and target_field not in object_fields_map[target_obj]:
                        raise ValidationError("layout 引用了不存在字段：%s.%s" % (target_obj, target_field))

            rules = payload.get("rules") if isinstance(payload.get("rules"), list) else []
            for rule in rules:
                if not isinstance(rule, dict):
                    raise ValidationError("rules 节点必须是对象数组。")
                trigger = str(rule.get("trigger") or "").strip()
                if trigger not in {"on_create", "on_update", "scheduled"}:
                    raise ValidationError("规则触发器不支持：%s" % trigger)
                action = rule.get("action") if isinstance(rule.get("action"), dict) else {}
                target_obj = str(action.get("object") or "").strip()
                target_field = str(action.get("field") or "").strip()
                if target_obj and target_field and target_obj in object_fields_map and target_field not in object_fields_map[target_obj]:
                    raise ValidationError("规则动作引用不存在字段：%s.%s" % (target_obj, target_field))

    @api.constrains("contract_json", "model", "view_type", "action_id", "view_id", "active", "status")
    def _check_published_runtime_contract(self):
        for rec in self:
            if not rec.active or rec.status != "published":
                continue
            payload = rec.contract_json if isinstance(rec.contract_json, dict) else {}
            orchestration = payload.get("view_orchestration") if isinstance(payload.get("view_orchestration"), dict) else {}
            views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
            requested_types = list(views) or [rec.view_type or "form"]
            failures = []
            for requested_type in requested_types:
                validation = rec._runtime_contract_validation(
                    rec,
                    requested_view_type=requested_type,
                    action_id=int(rec.action_id.id or 0),
                    view_id=int(rec.view_id.id or 0),
                    model_name=rec.model,
                )
                if not validation["valid"]:
                    failures.extend(validation["reason_codes"])
            if failures:
                raise ValidationError(
                    "发布配置未通过正式视图合同校验：%s" % ", ".join(sorted(set(failures)))
                )

    @api.constrains("model", "action_id", "view_id")
    def _check_view_scope(self):
        for rec in self:
            if rec.model and rec.model not in self.env:
                raise ValidationError("模型不存在：%s" % rec.model)
            if rec.action_id and rec.action_id.res_model != rec.model:
                raise ValidationError("动作不属于当前模型：%s" % rec.action_id.display_name)
            if rec.view_id and rec.view_id.model != rec.model:
                raise ValidationError("视图不属于当前模型：%s" % rec.view_id.display_name)
            if (
                rec.view_id
                and rec.view_type
                and self._normalize_view_orchestration_view_type(rec.view_id.type)
                != self._normalize_view_orchestration_view_type(rec.view_type)
            ):
                raise ValidationError("视图类型与配置范围不一致：%s" % rec.view_id.display_name)

    def _check_view_orchestration_payload(self, payload: dict) -> None:
        orchestration = payload.get("view_orchestration")
        if orchestration is None:
            return
        if not isinstance(orchestration, dict):
            raise ValidationError("view_orchestration 必须是对象。")
        views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
        allowed = {"form", "tree", "list", "kanban", "search", "pivot", "graph", "calendar", "gantt", "activity", "dashboard"}
        list_keys = {
            "fields",
            "columns",
            "filters",
            "group_by",
            "groupBys",
            "measures",
            "dimensions",
            "actions",
            "quick_actions",
            "row_classes",
            "cards",
            "kpis",
            "sections",
            "layout",
        }
        dict_keys = {
            "defaults",
            "slots",
            "action_slots",
            "context",
            "domain",
            "chart_policy",
            "date_slots",
            "resource_slots",
            "color_slots",
            "dependency_slots",
            "activity_type_slots",
            "deadline_slots",
            "assignee_slots",
            "metric_slots",
            "chart_slots",
            "navigation_slots",
        }
        for view_type, spec in views.items():
            if view_type not in allowed:
                raise ValidationError("view_orchestration.views 不支持视图类型：%s" % view_type)
            if not isinstance(spec, dict):
                raise ValidationError("view_orchestration.views.%s 必须是对象。" % view_type)
            for key in list_keys:
                rows = spec.get(key)
                if rows is None:
                    continue
                if key == "columns" and view_type == "form":
                    if isinstance(rows, int) and rows in {1, 2, 3}:
                        continue
                    raise ValidationError("view_orchestration.views.form.columns 必须是 1、2 或 3。")
                if not isinstance(rows, list):
                    raise ValidationError("view_orchestration.views.%s.%s 必须是数组。" % (view_type, key))
                if key in {"measures", "dimensions"}:
                    invalid = [row for row in rows if not isinstance(row, (str, dict))]
                    if invalid:
                        raise ValidationError("view_orchestration.views.%s.%s 必须是字符串或对象数组。" % (view_type, key))
                    continue
                for row in rows:
                    if key == "row_classes" and isinstance(row, str):
                        continue
                    if not isinstance(row, dict):
                        raise ValidationError("view_orchestration.views.%s.%s 必须是对象数组。" % (view_type, key))
            for key in dict_keys:
                value = spec.get(key)
                if value is not None and not isinstance(value, dict):
                    raise ValidationError("view_orchestration.views.%s.%s 必须是对象。" % (view_type, key))

    @api.model
    def _effective_view_orchestration_contracts(
        self,
        model_name: str,
        *,
        view_type: str | None = None,
        action_id: int | None = None,
        view_id: int | None = None,
        role_key: str | None = None,
    ):
        if not model_name:
            return []
        normalized_view_type = self._normalize_view_orchestration_view_type(view_type)
        domain = [
            ("active", "=", True),
            ("status", "=", "published"),
            ("model", "=", model_name),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.env.company.id),
        ]
        records = self.sudo().search(domain, order="priority, version_no, id")
        role_key = str(role_key or "").strip()

        def applies(contract) -> bool:
            if normalized_view_type and not self.contract_contributes_view(contract, normalized_view_type):
                return False
            contract_action = int(contract.action_id.id or 0)
            contract_view = int(contract.view_id.id or 0)
            contract_role = str(contract.role_key or "").strip()
            if contract_action and contract_action != int(action_id or 0):
                return False
            if contract_view and contract_view != int(view_id or 0):
                return False
            if contract_role and contract_role != role_key:
                return False
            return True

        effective = []
        for contract in records:
            if not applies(contract):
                continue
            validation = self._runtime_contract_validation(
                contract,
                requested_view_type=normalized_view_type or contract.view_type or "form",
                action_id=int(action_id or 0),
                view_id=int(view_id or 0),
                model_name=model_name,
            )
            if not validation["valid"]:
                _logger.warning(
                    "RUNTIME_VIEW_CONTRACT_DIAGNOSTIC reason_code=contract_rejected contract_id=%s contract_name=%s model=%s action_id=%s view_id=%s view_type=%s reason_codes=%s",
                    int(contract.id or 0),
                    contract.name,
                    model_name,
                    validation["action_id"],
                    validation["view_id"],
                    validation["view_type"],
                    ",".join(validation["reason_codes"]),
                )
                continue
            effective.append(ViewOrchestrationContractProjection.from_record(contract))

        preview_token = str(self.env.context.get("business_config_preview_token") or "").strip()
        preview_user_id = int(self.env.context.get("business_config_preview_user_id") or 0)
        if preview_token and preview_user_id and "ui.business.config.change.set" in self.env:
            change_set = self.env["ui.business.config.change.set"].sudo().search([
                ("preview_token", "=", preview_token),
                ("user_id", "=", preview_user_id),
                ("company_id", "=", self.env.company.id),
                ("database_name", "=", self.env.cr.dbname),
                ("state", "=", "ready"),
                ("preview_expires_at", ">", fields.Datetime.now()),
            ], limit=1)
            if change_set:
                requested_role = str(self.env.context.get("business_config_preview_role_key") or "").strip()
                if requested_role == str(change_set.role_key or "").strip():
                    for item in change_set.item_ids.filtered(lambda row: row.config_type != "menu"):
                        preview_projection = ViewOrchestrationContractProjection.from_preview_item(item)
                        if item.model != model_name or (
                            normalized_view_type and not self.contract_contributes_view(preview_projection, normalized_view_type)
                        ):
                            continue
                        if item.action_id and int(item.action_id) != int(action_id or 0):
                            continue
                        if item.view_id and int(item.view_id) != int(view_id or 0):
                            continue
                        if item.role_key and str(item.role_key or "").strip() != requested_role:
                            continue
                        validation = self._runtime_contract_validation(
                            preview_projection,
                            requested_view_type=normalized_view_type or item.view_type or "form",
                            action_id=int(action_id or 0),
                            view_id=int(view_id or 0),
                            model_name=model_name,
                        )
                        if not validation["valid"]:
                            _logger.warning(
                                "RUNTIME_VIEW_CONTRACT_DIAGNOSTIC reason_code=preview_contract_rejected model=%s action_id=%s view_id=%s view_type=%s reason_codes=%s",
                                model_name,
                                validation["action_id"],
                                validation["view_id"],
                                validation["view_type"],
                                ",".join(validation["reason_codes"]),
                            )
                            continue
                        effective = [contract for contract in effective if contract.id != item.target_contract_id.id]
                        effective.append(preview_projection)

        effective = sorted(effective, key=view_orchestration_apply_order_key)
        return effective

    @api.model
    def source_authority_contract(self) -> dict:
        return {
            "kind": "ui_business_config_contract_orchestration_config",
            "authorities": ["ui.business.config.contract", "ui.business.config.contract.version"],
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": True,
            "runtime_carrier": "ui.business.config.contract",
            "boundary_classifier": "smart_core.utils.backend_contract_boundaries",
        }

    def boundary_contract(self) -> dict:
        self.ensure_one()
        return classify_view_orchestration_contract(self.name, self.contract_json or {})

    def action_publish(self):
        for rec in self:
            rec.status = "published"
            rec.published_at = fields.Datetime.now()
            rec.version_no = int(rec.version_no or 1) + 1
            self.env["ui.business.config.contract.version"].create({
                "contract_id": rec.id,
                "version_no": rec.version_no,
                "snapshot_json": rec.contract_json or {},
                "status": rec.status,
                "created_by": self.env.user.id,
            })


class UIBusinessConfigContractVersion(models.Model):
    _name = "ui.business.config.contract.version"
    _description = "UI Business Config Contract Version"
    _order = "id desc"

    contract_id = fields.Many2one("ui.business.config.contract", required=True, ondelete="cascade", index=True)
    version_no = fields.Integer(required=True)
    status = fields.Selection([("draft", "Draft"), ("published", "Published")], default="draft", required=True)
    snapshot_json = fields.Json(required=True, default=dict)
    created_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        record_business_config_mutation(records, "create", vals_list)
        return records

    def unlink(self):
        record_business_config_mutation(self, "unlink")
        return super().unlink()
