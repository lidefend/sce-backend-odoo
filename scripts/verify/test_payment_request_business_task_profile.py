#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PROFILE_PATH = (
    ROOT
    / "addons"
    / "smart_construction_scene"
    / "profiles"
    / "payment_request_business_task_profile.py"
)
SPEC = importlib.util.spec_from_file_location("payment_request_business_task_profile", PROFILE_PATH)
PROFILE_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PROFILE_MODULE)

from addons.smart_scene.core.business_task_scene_compiler import (  # noqa: E402
    compile_business_task_scene_contract,
    verify_business_task_scene_contract_seal,
)
SERVICES_PACKAGE = "addons.smart_construction_scene.services"
services_package = types.ModuleType(SERVICES_PACKAGE)
services_package.__path__ = [str(ROOT / "addons" / "smart_construction_scene" / "services")]
sys.modules[SERVICES_PACKAGE] = services_package
PROJECTION_PATH = services_package.__path__[0] + "/payment_request_business_task_projection.py"
PROJECTION_SPEC = importlib.util.spec_from_file_location(
    f"{SERVICES_PACKAGE}.payment_request_business_task_projection",
    PROJECTION_PATH,
)
PROJECTION_MODULE = importlib.util.module_from_spec(PROJECTION_SPEC)
assert PROJECTION_SPEC and PROJECTION_SPEC.loader
sys.modules[PROJECTION_SPEC.name] = PROJECTION_MODULE
PROJECTION_SPEC.loader.exec_module(PROJECTION_MODULE)
attach_payment_request_business_task_scene = PROJECTION_MODULE.attach_payment_request_business_task_scene


def _source(key: str) -> str:
    return f"smart_construction_core.payment_request.{key}"


def approved_ready_supply() -> dict:
    facts = {
        "request_identity": ("FE-PAY-001", "always"),
        "handling_subject": ("付款申请", "always"),
        "lifecycle_state": ("已批准", "always"),
        "project": ("FE Project A", "always"),
        "payee": ("FE 往来单位", "always"),
        "payment_basis": ("合同付款", "contract_basis"),
        "requested_amount": ("¥80.00", "always"),
        "payable_balance": ("¥80.00", "always"),
        "account_readiness": ("完整", "payment_request"),
        "account_source": ("往来单位默认结算账户", "payment_request"),
        "execution_status": ("尚未生成", "always"),
        "blocking_summary": ("无业务阻断", "always"),
        "legal_next_step": ("生成付款登记", "always"),
    }
    disabled = {
        "payment_request.submit": "STATE_NOT_SUBMITTABLE",
        "payment_request.approve": "STATE_ALREADY_APPROVED",
        "payment_request.reject": "STATE_ALREADY_APPROVED",
        "payment_execution.open": "PAYMENT_EXECUTION_NOT_CREATED",
    }
    capabilities = {}
    for key in (
        "payment_request.submit",
        "payment_request.approve",
        "payment_request.reject",
        "payment_execution.create",
        "payment_execution.open",
        "payment_request.cancel",
        "counterparty.resolve_eligibility",
        "payment_request.complete_basis",
        "counterparty.maintain_settlement_account",
    ):
        enabled = key in {"payment_execution.create", "payment_request.cancel"}
        disabled.setdefault(key, "REPAIR_NOT_REQUIRED")
        capabilities[key] = {
            "visible": enabled,
            "business_available": enabled,
            "authorization_allowed": True,
            "enabled": enabled,
            "reason_code": "" if enabled else disabled[key],
            "reason": "" if enabled else "当前状态不可执行该办理能力",
            "source_authority": _source("available_actions"),
        }
    return {
        "task": {"mode": "readonly", "stage": "payment_ready", "state": "approved"},
        "facts": {
            key: {
                "value": value,
                "value_state": "known",
                "source_authority": _source(key),
                "applicability": applicability,
            }
            for key, (value, applicability) in facts.items()
        },
        "inputs": {
            "application_note": {
                "value": "按合同约定付款",
                "visible": True,
                "readonly": True,
                "required": False,
                "source_authority": _source("note_policy"),
                "applicability": "always",
            }
        },
        "blockers": {
            key: {
                "active": False,
                "reason_code": "",
                "message": "",
                "missing_items": [],
                "source_authority": _source(key),
            }
            for key in (
                "counterparty_eligibility",
                "payment_basis_readiness",
                "payee_account_readiness",
            )
        },
        "capabilities": capabilities,
        "evidence": {
            "attachments": {
                "state": "ready",
                "count": 1,
                "required": False,
                "source_authority": _source("attachments"),
            },
            "approval_audit": {
                "state": "approved",
                "count": 2,
                "required": True,
                "source_authority": _source("approval_audit"),
            },
        },
        "relations": {
            key: {
                "state": "linked" if key != "payment_execution_relation" else "empty",
                "count": 0 if key == "payment_execution_relation" else 1,
                "summary": key.replace("_", " "),
                "source_authority": _source(key),
            }
            for key in (
                "project_anchor",
                "payee_anchor",
                "contract_anchor",
                "settlement_anchor",
                "payment_execution_relation",
            )
        },
        "completion": {
            "complete": False,
            "next_capability_key": "payment_execution.create",
            "outcome_code": "PAYMENT_EXECUTION_REQUIRED",
        },
    }


def _disable_all_capabilities(supply: dict, reason_code: str) -> None:
    for row in supply["capabilities"].values():
        row.update(
            {
                "visible": False,
                "business_available": False,
                "authorization_allowed": True,
                "enabled": False,
                "reason_code": reason_code,
            }
        )


def draft_supply() -> dict:
    supply = copy.deepcopy(approved_ready_supply())
    supply["task"].update({"mode": "edit", "stage": "preparation", "state": "draft"})
    supply["facts"]["lifecycle_state"]["value"] = "草稿"
    supply["facts"]["legal_next_step"]["value"] = "提交审批"
    _disable_all_capabilities(supply, "STATE_NOT_APPLICABLE")
    for key in ("payment_request.submit", "payment_request.cancel"):
        supply["capabilities"][key].update(
            {
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "reason_code": "",
            }
        )
    supply["inputs"]["application_note"].update({"readonly": False})
    supply["completion"].update(
        {
            "next_capability_key": "payment_request.submit",
            "outcome_code": "SUBMISSION_REQUIRED",
        }
    )
    return supply


def approval_supply() -> dict:
    supply = copy.deepcopy(approved_ready_supply())
    supply["task"].update({"mode": "readonly", "stage": "approval", "state": "submitted"})
    supply["facts"]["lifecycle_state"]["value"] = "待审批"
    supply["facts"]["legal_next_step"]["value"] = "审批处理"
    _disable_all_capabilities(supply, "STATE_NOT_APPLICABLE")
    for key in ("payment_request.approve", "payment_request.reject"):
        supply["capabilities"][key].update(
            {
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "reason_code": "",
            }
        )
    supply["completion"].update(
        {
            "next_capability_key": "payment_request.approve",
            "outcome_code": "APPROVAL_REQUIRED",
        }
    )
    return supply


def execution_created_supply() -> dict:
    supply = copy.deepcopy(approved_ready_supply())
    supply["task"].update({"mode": "readonly", "stage": "payment_execution", "state": "approved"})
    supply["facts"]["execution_status"]["value"] = "已生成：草稿"
    supply["facts"]["legal_next_step"]["value"] = "查看付款登记"
    supply["capabilities"]["payment_execution.create"].update(
        {
            "visible": False,
            "business_available": False,
            "enabled": False,
            "reason_code": "PAYMENT_EXECUTION_ALREADY_EXISTS",
        }
    )
    supply["capabilities"]["payment_execution.open"].update(
        {
            "visible": True,
            "business_available": True,
            "authorization_allowed": True,
            "enabled": True,
            "reason_code": "",
        }
    )
    supply["relations"]["payment_execution_relation"].update(
        {"state": "linked", "count": 1, "summary": "付款登记已生成"}
    )
    supply["completion"].update(
        {
            "next_capability_key": "payment_execution.open",
            "outcome_code": "PAYMENT_EXECUTION_IN_PROGRESS",
        }
    )
    return supply


def terminal_supply(*, state: str, state_label: str, outcome_code: str) -> dict:
    supply = copy.deepcopy(approved_ready_supply())
    supply["task"].update({"mode": "readonly", "stage": "complete", "state": state})
    supply["facts"]["lifecycle_state"]["value"] = state_label
    supply["facts"]["legal_next_step"]["value"] = state_label
    supply["facts"]["payable_balance"]["value"] = "¥0.00" if state == "done" else "¥80.00"
    _disable_all_capabilities(supply, "TASK_ALREADY_COMPLETE")
    supply["completion"].update(
        {
            "complete": True,
            "next_capability_key": "",
            "outcome_code": outcome_code,
        }
    )
    return supply


def normalized_payment_contract(*, authorization_allowed: bool | None = True) -> dict:
    main_data = {
        "name": "FE-PAY-001",
        "payment_flow_label": "付款申请",
        "state": "approved",
        "project_id": [7, "FE Project A"],
        "partner_id": [8, "FE 往来单位"],
        "contract_id": [9, "FE 合同"],
        "settlement_id": False,
        "material_settlement_id": False,
        "payment_basis_type": "合同付款",
        "amount": 80,
        "unpaid_amount": 80,
        "payee_account_completeness": "complete",
        "payee_account_source_display": "往来单位默认结算账户",
        "payment_execution_status_display": "尚未生成",
        "payment_blocking_reason_display": "无业务阻断",
        "legal_next_action_display": "生成付款登记",
        "partner_transaction_eligibility": "eligible",
        "partner_transaction_eligibility_reason": "",
        "has_active_payment_execution": False,
        "note": "按合同约定付款",
        "attachment_ids": [3],
        "review_ids": [4, 5],
    }
    trace = {
        "sourceChannel": "runtime_business_action",
        "businessAvailable": True,
        "entitlementEvaluated": authorization_allowed is not None,
    }
    if authorization_allowed is not None:
        trace["authorizationAllowed"] = authorization_allowed
    rule = {
        "actionId": "action.payment_execution",
        "actionKey": "payment_execution",
        "backendIdentity": "button:object:action_create_payment_execution",
        "button": {"name": "action_create_payment_execution", "type": "object"},
        "visible": True,
        "enabled": bool(authorization_allowed),
        "disabled": authorization_allowed is not True,
        "presentation": {"tier": "primary"},
        "sourceTrace": [trace],
    }
    return {
        "pageInfo": {"model": "payment.request", "viewType": "form", "renderProfile": "readonly"},
        "dataContract": {"mainData": main_data},
        "actionContract": {"actionRuleList": [rule]},
        "statusContract": {
            "buttonStatus": [
                {
                    "btnId": "btn.payment_execution",
                    "visible": True,
                    "disabled": authorization_allowed is not True,
                    **({"reasonCode": "ROLE_HANDOFF_REQUIRED"} if authorization_allowed is False else {}),
                }
            ]
        },
        "runtimeContract": {
            "businessTaskSemantics": {
                "version": "v1",
                "source_authority": "payment_request_model_capability_projection",
                "blockers": {
                    key: {
                        "active": False,
                        "reason_code": "",
                        "message": "",
                        "missing_items": [],
                        "source_authority": f"payment_request.{key}",
                    }
                    for key in (
                        "counterparty_eligibility",
                        "payment_basis_readiness",
                        "payee_account_readiness",
                    )
                },
            }
        },
    }


class PaymentRequestBusinessTaskProfileTest(unittest.TestCase):
    def test_fact_and_input_bindings_are_declared_by_field_matrix(self):
        matrix = json.loads(
            (ROOT / "config" / "p1_payment_request_field_completeness_v1.json").read_text(encoding="utf-8")
        )
        field_rules = {
            row["field"]: row
            for row in matrix["field_rules"]
            if row.get("model") == "payment.request"
        }
        profile = PROFILE_MODULE.payment_request_task_profile_v1()
        for section in ("facts", "inputs"):
            for row in profile[section]:
                field = ((row.get("source_binding") or {}).get("field"))
                self.assertIn(field, field_rules, f"{section}.{row['key']} binding drift")
                self.assertIn("readonly", field_rules[field]["surfaces"], f"{section}.{row['key']} readonly drift")

    def test_approved_ready_readonly_task_has_one_direct_business_primary(self):
        contract = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=approved_ready_supply(),
        )
        enabled_primary = [
            row
            for row in contract["capabilities"]
            if row["enabled"] and row.get("presentation") == "primary"
        ]
        self.assertEqual([row["key"] for row in enabled_primary], ["payment_execution.create"])
        self.assertEqual(contract["completion"]["next_capability_key"], "payment_execution.create")
        self.assertEqual(contract["task"]["stage"], "payment_ready")

    def test_readonly_first_screen_has_complete_business_context(self):
        contract = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=approved_ready_supply(),
        )
        facts = {row["key"]: row for row in contract["facts"]}
        required = {
            "request_identity",
            "handling_subject",
            "lifecycle_state",
            "project",
            "payee",
            "payment_basis",
            "requested_amount",
            "payable_balance",
            "account_readiness",
            "account_source",
            "execution_status",
            "blocking_summary",
            "legal_next_step",
        }
        self.assertEqual(set(facts), required)
        self.assertTrue(all(row.get("source_authority") for row in facts.values()))

    def test_terminal_payment_profile_has_no_native_renderer_vocabulary(self):
        contract = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=approved_ready_supply(),
        )
        serialized = str(contract).lower()
        for term in ("payment.request", "view_type", "xml_id", "notebook", "modifiers", "server_action_id"):
            self.assertNotIn(term, serialized)

    def test_account_blocker_exposes_authoritative_repair_capability(self):
        supply = approved_ready_supply()
        supply["facts"]["account_readiness"]["value"] = "不完整"
        supply["facts"]["blocking_summary"]["value"] = "缺少户名、开户行、账号"
        supply["facts"]["legal_next_step"]["value"] = "维护结算账户"
        supply["blockers"]["payee_account_readiness"].update(
            {
                "active": True,
                "reason_code": "PAYEE_ACCOUNT_INCOMPLETE",
                "message": "缺少户名、开户行、账号",
                "missing_items": ["account_name", "bank_name", "account_number"],
            }
        )
        create = supply["capabilities"]["payment_execution.create"]
        create.update(
            {
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": False,
                "reason_code": "PAYEE_ACCOUNT_INCOMPLETE",
            }
        )
        repair = supply["capabilities"]["counterparty.maintain_settlement_account"]
        repair.update(
            {
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "reason_code": "",
            }
        )
        supply["completion"]["next_capability_key"] = "counterparty.maintain_settlement_account"
        supply["completion"]["outcome_code"] = "PAYEE_ACCOUNT_REPAIR_REQUIRED"
        contract = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=supply,
        )
        blockers = {row["key"]: row for row in contract["blockers"]}
        capabilities = {row["key"]: row for row in contract["capabilities"]}
        self.assertTrue(blockers["payee_account_readiness"]["active"])
        self.assertFalse(capabilities["payment_execution.create"]["enabled"])
        self.assertTrue(capabilities["counterparty.maintain_settlement_account"]["enabled"])

    def test_state_matrix_promotes_only_the_current_business_capability(self):
        cases = (
            (draft_supply(), "payment_request.submit"),
            (approval_supply(), "payment_request.approve"),
            (approved_ready_supply(), "payment_execution.create"),
            (execution_created_supply(), "payment_execution.open"),
        )
        for supply, expected_primary in cases:
            with self.subTest(stage=supply["task"]["stage"]):
                contract = compile_business_task_scene_contract(
                    profile=PROFILE_MODULE.payment_request_task_profile_v1(),
                    semantic_supply=supply,
                )
                enabled_primary = [
                    row["key"]
                    for row in contract["capabilities"]
                    if row["enabled"] and row.get("presentation") == "primary"
                ]
                self.assertEqual(enabled_primary, [expected_primary])
                self.assertEqual(contract["completion"]["next_capability_key"], expected_primary)

    def test_terminal_states_have_no_next_capability(self):
        cases = (
            terminal_supply(state="done", state_label="已办结", outcome_code="PAYMENT_REQUEST_COMPLETED"),
            terminal_supply(state="cancel", state_label="已取消", outcome_code="PAYMENT_REQUEST_CANCELLED"),
        )
        for supply in cases:
            with self.subTest(state=supply["task"]["state"]):
                contract = compile_business_task_scene_contract(
                    profile=PROFILE_MODULE.payment_request_task_profile_v1(),
                    semantic_supply=supply,
                )
                self.assertTrue(contract["completion"]["complete"])
                self.assertEqual(contract["completion"]["next_capability_key"], "")
                self.assertFalse(any(row["enabled"] for row in contract["capabilities"]))

    def test_business_available_without_authorization_is_visible_but_not_executable(self):
        supply = draft_supply()
        submit = supply["capabilities"]["payment_request.submit"]
        submit.update(
            {
                "visible": True,
                "business_available": True,
                "authorization_allowed": False,
                "enabled": False,
                "reason_code": "ROLE_HANDOFF_REQUIRED",
            }
        )
        supply["facts"]["legal_next_step"]["value"] = "等待有提交能力的人员办理"
        contract = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=supply,
        )
        compiled_submit = next(row for row in contract["capabilities"] if row["key"] == "payment_request.submit")
        self.assertTrue(compiled_submit["business_available"])
        self.assertFalse(compiled_submit["authorization_allowed"])
        self.assertFalse(compiled_submit["enabled"])
        self.assertEqual(compiled_submit["reason_code"], "ROLE_HANDOFF_REQUIRED")

    def test_role_handoff_changes_only_authoritative_capability_verdict(self):
        authorized_supply = draft_supply()
        handoff_supply = copy.deepcopy(authorized_supply)
        handoff_supply["capabilities"]["payment_request.submit"].update(
            {
                "visible": True,
                "authorization_allowed": False,
                "enabled": False,
                "reason_code": "ROLE_HANDOFF_REQUIRED",
                "reason": "请交接给具备提交能力的人员",
            }
        )
        authorized = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=authorized_supply,
        )
        handoff = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=handoff_supply,
        )
        self.assertEqual(authorized["facts"], handoff["facts"])
        self.assertEqual(authorized["relations"], handoff["relations"])
        authorized_submit = next(
            row for row in authorized["capabilities"] if row["key"] == "payment_request.submit"
        )
        handoff_submit = next(
            row for row in handoff["capabilities"] if row["key"] == "payment_request.submit"
        )
        self.assertTrue(authorized_submit["enabled"])
        self.assertFalse(handoff_submit["enabled"])

    def test_same_authority_snapshot_is_retry_stable(self):
        supply = execution_created_supply()
        first = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=supply,
        )
        second = compile_business_task_scene_contract(
            profile=PROFILE_MODULE.payment_request_task_profile_v1(),
            semantic_supply=copy.deepcopy(supply),
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first["trace"]["sealed_contract_sha256"],
            second["trace"]["sealed_contract_sha256"],
        )

    def test_state_transition_preserves_relationship_anchor_identity(self):
        stages = (draft_supply(), approval_supply(), approved_ready_supply(), execution_created_supply())
        relation_keys = None
        for supply in stages:
            contract = compile_business_task_scene_contract(
                profile=PROFILE_MODULE.payment_request_task_profile_v1(),
                semantic_supply=supply,
            )
            current_keys = [row["key"] for row in contract["relations"]]
            if relation_keys is None:
                relation_keys = current_keys
            self.assertEqual(current_keys, relation_keys)
            self.assertTrue(all(row["source_authority"] for row in contract["relations"]))

    def test_production_projection_attaches_sealed_terminal_scene_after_canonical_actions(self):
        projected = attach_payment_request_business_task_scene(normalized_payment_contract())
        self.assertIsNotNone(projected)
        runtime = projected["runtimeContract"]
        terminal = runtime["businessTaskContract"]
        self.assertTrue(verify_business_task_scene_contract_seal(terminal))
        self.assertEqual(
            terminal["completion"]["next_capability_key"],
            "payment_execution.create",
        )
        create = next(
            row for row in terminal["capabilities"] if row["key"] == "payment_execution.create"
        )
        self.assertTrue(create["enabled"])
        self.assertEqual(
            runtime["businessTaskSceneContract"]["business_task"],
            terminal,
        )

    def test_production_projection_does_not_infer_missing_authorization(self):
        projected = attach_payment_request_business_task_scene(
            normalized_payment_contract(authorization_allowed=None)
        )
        create = next(
            row
            for row in projected["runtimeContract"]["businessTaskContract"]["capabilities"]
            if row["key"] == "payment_execution.create"
        )
        self.assertFalse(create["authorization_allowed"])
        self.assertFalse(create["enabled"])
        self.assertEqual(create["reason_code"], "ACTION_PERMISSION_UNRESOLVED")
        self.assertEqual(
            projected["runtimeContract"]["businessTaskContract"]["completion"]["next_capability_key"],
            "payment_execution.create",
        )

    def test_production_projection_preserves_handoff_action_as_next_capability(self):
        projected = attach_payment_request_business_task_scene(
            normalized_payment_contract(authorization_allowed=False)
        )
        terminal = projected["runtimeContract"]["businessTaskContract"]
        create = next(
            row for row in terminal["capabilities"] if row["key"] == "payment_execution.create"
        )
        self.assertTrue(create["visible"])
        self.assertTrue(create["business_available"])
        self.assertFalse(create["authorization_allowed"])
        self.assertFalse(create["enabled"])
        self.assertEqual(create["reason_code"], "ROLE_HANDOFF_REQUIRED")
        self.assertEqual(terminal["completion"]["next_capability_key"], "payment_execution.create")

    def test_production_projection_requires_domain_blocker_authority(self):
        contract = normalized_payment_contract()
        del contract["runtimeContract"]["businessTaskSemantics"]
        self.assertIsNone(attach_payment_request_business_task_scene(contract))

    def test_account_blocker_uses_domain_verdict_and_selects_repair_handoff(self):
        contract = normalized_payment_contract()
        account = contract["runtimeContract"]["businessTaskSemantics"]["blockers"]["payee_account_readiness"]
        account.update({
            "active": True,
            "reason_code": "PAYEE_ACCOUNT_INCOMPLETE",
            "message": "缺少收款账号。",
            "missing_items": ["账号"],
        })
        rule = contract["actionContract"]["actionRuleList"][0]
        rule["enabled"] = False
        rule["disabled"] = True
        rule["sourceTrace"][0]["businessAvailable"] = False
        status = contract["statusContract"]["buttonStatus"][0]
        status.update({"disabled": True, "reasonCode": "PAYEE_ACCOUNT_INCOMPLETE"})
        projected = attach_payment_request_business_task_scene(contract)
        terminal = projected["runtimeContract"]["businessTaskContract"]
        blocker = next(row for row in terminal["blockers"] if row["key"] == "payee_account_readiness")
        self.assertTrue(blocker["active"])
        self.assertEqual(blocker["missing_items"], ["账号"])
        self.assertEqual(
            terminal["completion"]["next_capability_key"],
            "counterparty.maintain_settlement_account",
        )

    def test_production_projection_ignores_non_payment_forms(self):
        contract = normalized_payment_contract()
        contract["pageInfo"]["model"] = "x.document"
        self.assertIsNone(attach_payment_request_business_task_scene(contract))

if __name__ == "__main__":
    unittest.main()
