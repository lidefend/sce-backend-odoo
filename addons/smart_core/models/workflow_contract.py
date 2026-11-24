# -*- coding: utf-8 -*-
"""Platform workflow and approval contract producer.

Business modules declare workflow profiles and business evidence.  This model
owns the canonical contract shape, approval-phase projection, action
availability and fail-closed reconciliation.  Odoo model methods and
``tier.validation`` remain the runtime authorities.
"""

from __future__ import annotations

from odoo import api, models

from odoo.addons.smart_core.utils.contract_governance import (
    workflow_contract_profiles,
)
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first


class SmartCoreWorkflowContract(models.AbstractModel):
    _name = "smart_core.workflow.contract"
    _description = "Platform workflow and approval contract producer"

    SOURCE_KIND = "sc_backend_workflow_contract"
    SOURCE_AUTHORITIES = (
        "odoo_model_state",
        "base_tier_validation",
        "workflow_contract_profiles",
        "business_model_methods",
    )

    ACTIONS = {
        "return_rental": {"label": "确认退还", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "confirm_settlement": {"label": "确认结算", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "accept_result": {"label": "验收通过", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reject_result": {"label": "验收不通过", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "pause": {"label": "暂停执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "pause_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "resume": {"label": "恢复执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "start_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "advance_closing": {"label": "推进阶段", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "advance_phase", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "advance_warranty": {"label": "推进阶段", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "advance_phase", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "close": {"label": "关闭记录", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "close_record", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "save_draft": {"label": "保存草稿", "intent": "data.write", "method": None, "kind": "save"},
        "submit": {"label": "提交审批", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "submit", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "approve": {"label": "审批通过", "intent": "server.object", "kind": "approval", "action_semantics": {"kind": "business", "purpose": "approve", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reject": {"label": "审批驳回", "intent": "server.object", "kind": "approval", "action_semantics": {"kind": "business", "purpose": "reject", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "activate": {"label": "开始执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "start_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "complete": {"label": "完成", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "done": {"label": "完成", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "cancel": {"label": "取消", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "cancel_record", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reverse_payment": {"label": "撤销付款", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "cancel_record", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reopen": {"label": "重置为草稿", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "reopen", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reactivate": {"label": "重新打开", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "reopen", "executor": "contract.action", "origin": "workflow.contract.service"}},
    }

    TERMINAL_PHASES = {"done", "cancelled", "legacy_confirmed"}

    @api.model
    def source_authority_contract(self):
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "runtime_carrier": self._name,
        }

    @api.model
    def profile_by_model(self):
        profiles = workflow_contract_profiles()
        payload = call_extension_hook_first(
            self.env, "smart_core_workflow_contract_profiles", self.env
        )
        if isinstance(payload, dict):
            for model_name, profile in payload.items():
                if isinstance(profile, dict):
                    profiles[str(model_name)] = dict(profile)
        return profiles

    @api.model
    def supported_model_names(self):
        return sorted(self.profile_by_model())

    @api.model
    def is_model_supported(self, model_name):
        return str(model_name or "").strip() in self.profile_by_model()

    @api.model
    def describe_model_actions(self, model_name):
        profile = self.profile_by_model().get(model_name)
        if not profile:
            return {}
        contract = {
            "model": model_name,
            "source": {"kind": "sc_backend_workflow_action_catalog", "projection_only": True},
            "availabilityScope": "declaration_only",
            "actions": self._declared_actions(profile),
            "submissionRequirements": list(profile.get("submission_requirements") or []),
        }
        self._assert_workflow_contract_consistency(contract)
        return contract

    @api.model
    def describe_record(self, record):
        if not record or len(record) != 1:
            return {}
        record = record.with_user(self.env.user)
        profile = self.profile_by_model().get(record._name)
        if not profile:
            return {}
        raw_state = str(getattr(record, profile["state_field"], "") or "").strip()
        business_phase = profile["state_phase"].get(raw_state, raw_state or "unknown")
        approval_phase = self._approval_phase(record, raw_state=raw_state, business_phase=business_phase)
        evidence_gate = self._evidence_gate(record)
        actions = self._available_actions(
            record, profile, raw_state, business_phase, approval_phase, evidence_gate
        )
        current_action_keys = {action["key"] for action in actions}
        contract = {
            "source": self.source_authority_contract(),
            "model": record._name,
            "record_id": record.id,
            "availabilityScope": "record",
            "stateField": profile["state_field"],
            "rawState": raw_state,
            "businessPhase": business_phase,
            "approvalPhase": approval_phase,
            "editability": self._editability(profile, business_phase, approval_phase),
            "statusbar": self._statusbar_projection(record, profile["state_field"], raw_state),
            "evidenceGate": [
                gate for gate in evidence_gate
                if not gate.get("actionKeys") or current_action_keys.intersection(gate["actionKeys"])
            ],
            "submissionRequirements": list(profile.get("submission_requirements") or []),
            "actions": self._declared_actions(profile),
            "availableActions": actions,
        }
        self._assert_workflow_contract_consistency(contract)
        return contract

    @api.model
    def _declared_actions(self, profile):
        actions = []
        ordered_keys = list((profile.get("method_by_action") or {}).keys())
        for state_keys in (profile.get("state_actions") or {}).values():
            for key in state_keys:
                if key not in ordered_keys:
                    ordered_keys.append(key)
        for key in ordered_keys:
            spec = dict(self.ACTIONS.get(key) or {})
            action = {
                "key": key,
                "method": (profile.get("method_by_action") or {}).get(key, spec.get("method")),
                "intent": spec.get("intent") or "server.object",
                "kind": spec.get("kind") or "transition",
            }
            if spec.get("action_semantics"):
                action["action_semantics"] = dict(spec["action_semantics"])
            action.update(self._action_input_contract(profile, key))
            actions.append(action)
        return actions

    @api.model
    def _approval_phase(self, record, *, raw_state, business_phase):
        status = str(getattr(record, "validation_status", "") or "").strip()
        if status in ("waiting", "pending"):
            return status
        if status in ("validated", "approved"):
            return "approved"
        if status == "rejected":
            return "rejected"
        if business_phase == "under_review" and raw_state in ("submit", "approve"):
            return "pending"
        if business_phase in ("approved", "done", "legacy_confirmed"):
            return "approved"
        return "none"

    @api.model
    def _editability(self, profile, business_phase, approval_phase):
        if approval_phase in ("waiting", "pending"):
            return "readonly"
        field_editable = {
            str(value or "").strip()
            for value in (profile.get("field_editable_phases") or [])
            if str(value or "").strip()
        }
        if business_phase in field_editable:
            return "editable"
        if business_phase in self.TERMINAL_PHASES:
            return "locked"
        editable = {
            str(value or "").strip()
            for value in (profile.get("editable_phases") or ["draft"])
            if str(value or "").strip()
        }
        if business_phase in editable and approval_phase not in ("waiting", "pending", "approved"):
            return "editable"
        if business_phase in ("under_review", "approved", "rejected") or approval_phase in ("waiting", "pending", "approved"):
            return "readonly"
        return "editable"

    @api.model
    def _handles_without_approval(self, record, approval_phase):
        if approval_phase in ("waiting", "pending"):
            return False
        payload = call_extension_hook_first(
            self.env, "smart_core_workflow_approval_required", self.env, record
        )
        return payload is False

    @api.model
    def _available_actions(self, record, profile, raw_state, business_phase, approval_phase, evidence_gate):
        del business_phase
        keys = list(profile.get("state_actions", {}).get(raw_state, []))
        direct_handling = (profile.get("direct_handling") or {}).get(raw_state)
        if direct_handling and self._handles_without_approval(record, approval_phase):
            keys = [key for key in direct_handling if key not in keys] + [
                key for key in keys if key != "submit"
            ]
        if approval_phase in ("waiting", "pending"):
            for key in profile.get("approval_actions", []):
                if key not in keys:
                    keys.append(key)
            if not bool(getattr(record, "can_review", False)):
                keys = [key for key in keys if key not in {"approve", "reject"}]
        method_by_action = profile.get("method_by_action", {})
        actions = []
        seen = set()
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            action_authorizer = getattr(record, "_workflow_action_is_authorized", None)
            if action_authorizer and not action_authorizer(key):
                continue
            domain = (profile.get("action_domains") or {}).get(key)
            blockers = []
            if domain:
                if not bool(record.filtered_domain(domain)):
                    denial = (profile.get("action_domain_denials") or {}).get(key)
                    if not denial:
                        continue
                    blockers.append(self._gate(
                        denial["reasonCode"], denial["message"], action_keys=[key]
                    ))
            spec = dict(self.ACTIONS.get(key) or {})
            if not spec:
                continue
            blockers += [
                row for row in evidence_gate
                if row.get("blocking") and key in (row.get("actionKeys") or [])
            ]
            advisories = [
                row for row in evidence_gate
                if row.get("blocking") is False
                and key in (row.get("actionKeys") or [])
                and row.get("message")
            ]
            method = method_by_action.get(key, spec.get("method"))
            input_contract = self._action_input_contract(profile, key)
            presentation = dict(input_contract.pop("presentation", {}) or {})
            if advisories:
                presentation.update({
                    "requires_confirmation": True,
                    "warning_message": "\n".join(row["message"] for row in advisories),
                })
            actions.append({
                "key": key,
                "label": profile.get("label_by_action", {}).get(key) or spec.get("label") or key,
                "intent": spec.get("intent") or "server.object",
                "kind": spec.get("kind") or "transition",
                **({"action_semantics": dict(spec["action_semantics"])} if spec.get("action_semantics") else {}),
                "method": method,
                "enabled": not blockers,
                **input_contract,
                **({"presentation": presentation} if presentation else {}),
                "reason_code": blockers[0].get("reasonCode") if blockers else "OK",
                "blocked_message": blockers[0].get("message") if blockers else "",
                "target": {"model": record._name, "id": record.id, "method": method},
            })
        return actions

    @api.model
    def _evidence_gate(self, record):
        payload = call_extension_hook_first(
            self.env, "smart_core_workflow_contract_evidence", self.env, record
        )
        return [dict(row) for row in payload or [] if isinstance(row, dict)]

    @staticmethod
    def _gate(reason_code, message, *, action_keys, severity="block"):
        return {
            "reasonCode": str(reason_code or "").strip(),
            "message": str(message or "").strip(),
            "severity": severity,
            "blocking": severity == "block",
            "actionKeys": list(action_keys or []),
        }

    @api.model
    def _action_input_contract(self, profile, key):
        raw = (profile.get("action_inputs") or {}).get(key) or {}
        required_params = [
            str(item or "").strip()
            for item in (raw.get("required_params") or [])
            if str(item or "").strip()
        ]
        presentation = dict(raw.get("presentation") or {})
        requires_reason = raw.get("requires_reason") is True or presentation.get("requires_reason") is True
        if requires_reason and "reason" not in required_params:
            required_params.append("reason")
            presentation["requires_reason"] = True
        contract = {}
        if required_params:
            contract["required_params"] = required_params
        if requires_reason:
            contract["requires_reason"] = True
        if presentation:
            contract["presentation"] = presentation
        return contract

    @api.model
    def _statusbar_projection(self, record, state_field, raw_state):
        current = str(raw_state or "").strip()
        field_info = record.fields_get([state_field]).get(state_field) or {}
        states = [
            {"value": str(value), "label": str(label)}
            for value, label in field_info.get("selection") or []
            if value not in (None, False, "")
        ]
        if current and current not in {row["value"] for row in states}:
            states.append({"value": current, "label": current})
        if not current and states:
            current = states[0]["value"]
        if not current:
            current = "unknown"
            states.append({"value": "unknown", "label": "未知"})
        return {
            "field": state_field,
            "current": current,
            "states": states,
            "readonly": True,
            "source": "workflowContract",
        }

    @api.model
    def _assert_workflow_contract_consistency(self, contract):
        scope = str(contract.get("availabilityScope") or "")
        declared_by_key = {}
        for action in contract.get("actions") or []:
            key = str(action.get("key") or "").strip()
            if not key or key in declared_by_key:
                raise ValueError("WORKFLOW_ACTION_CATALOG_IDENTITY_INVALID")
            kind = str(action.get("kind") or "").strip()
            if kind == "save":
                if action.get("intent") != "data.write" or action.get("method") is not None:
                    raise ValueError("WORKFLOW_SAVE_ACTION_TARGET_INVALID")
            elif not str(action.get("method") or "").strip():
                raise ValueError("WORKFLOW_OBJECT_ACTION_METHOD_MISSING")
            declared_by_key[key] = action
        if scope == "declaration_only":
            if "record_id" in contract or "availableActions" in contract:
                raise ValueError("WORKFLOW_CREATE_CATALOG_SCOPE_LEAK")
            return
        if scope != "record":
            raise ValueError("WORKFLOW_AVAILABILITY_SCOPE_INVALID")
        model = str(contract.get("model") or "").strip()
        record_id = contract.get("record_id")
        if not model or type(record_id) is not int or record_id <= 0:
            raise ValueError("WORKFLOW_RECORD_IDENTITY_INVALID")
        state_field = str(contract.get("stateField") or "").strip()
        raw_state = str(contract.get("rawState") or "").strip()
        statusbar = contract.get("statusbar") or {}
        if not state_field or statusbar.get("field") != state_field or statusbar.get("current") != raw_state:
            raise ValueError("WORKFLOW_STATUS_FIELD_INCONSISTENT")
        statusbar_values = []
        for state in statusbar.get("states") or []:
            value = str(state.get("value") or "").strip()
            label = str(state.get("label") or "").strip()
            if not value or not label or value in statusbar_values:
                raise ValueError("WORKFLOW_STATUS_STATES_INVALID")
            statusbar_values.append(value)
        if raw_state and raw_state not in statusbar_values:
            raise ValueError("WORKFLOW_STATUS_CURRENT_NOT_LISTED")
        available_by_key = {}
        for action in contract.get("availableActions") or []:
            key = str(action.get("key") or "").strip()
            if not key or key in available_by_key or key not in declared_by_key:
                raise ValueError("WORKFLOW_RECORD_ACTION_REFERENCE_INVALID")
            declaration = declared_by_key[key]
            for field_name in ("method", "intent", "kind", "action_semantics"):
                if action.get(field_name) != declaration.get(field_name):
                    raise ValueError("WORKFLOW_RECORD_ACTION_DECLARATION_MISMATCH")
            target = action.get("target") or {}
            if target.get("model") != model or target.get("id") != record_id or target.get("method") != action.get("method"):
                raise ValueError("WORKFLOW_ACTION_TARGET_INVALID")
            if type(action.get("enabled")) is not bool:
                raise ValueError("WORKFLOW_ACTION_ENABLED_INVALID")
            if action["enabled"] is True and (action.get("reason_code") != "OK" or action.get("blocked_message")):
                raise ValueError("WORKFLOW_ENABLED_REASON_INVALID")
            if action["enabled"] is False and (not action.get("reason_code") or not action.get("blocked_message")):
                raise ValueError("WORKFLOW_DISABLED_REASON_MISSING")
            available_by_key[key] = action
        for gate in contract.get("evidenceGate") or []:
            action_keys = gate.get("actionKeys") or []
            if any(key not in declared_by_key for key in action_keys):
                raise ValueError("WORKFLOW_GATE_ACTION_REFERENCE_INVALID")
            if action_keys and not available_by_key.keys() & set(action_keys):
                raise ValueError("WORKFLOW_GATE_ACTION_SCOPE_INVALID")
            if gate.get("severity") not in {"block", "warn", "info"}:
                raise ValueError("WORKFLOW_GATE_SEVERITY_INVALID")
            if gate.get("blocking") is True and gate.get("severity") != "block":
                raise ValueError("WORKFLOW_GATE_BLOCKING_SEVERITY_INVALID")
