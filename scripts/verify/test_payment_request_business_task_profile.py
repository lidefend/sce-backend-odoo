#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import sys
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

from addons.smart_scene.core.business_task_scene_compiler import compile_business_task_scene_contract  # noqa: E402


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
            "business_available": False,
            "enabled": False,
            "reason_code": "PAYMENT_EXECUTION_ALREADY_EXISTS",
        }
    )
    supply["capabilities"]["payment_execution.open"].update(
        {
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
                "business_available": True,
                "authorization_allowed": True,
                "enabled": False,
                "reason_code": "PAYEE_ACCOUNT_INCOMPLETE",
            }
        )
        repair = supply["capabilities"]["counterparty.maintain_settlement_account"]
        repair.update(
            {
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


if __name__ == "__main__":
    unittest.main()
