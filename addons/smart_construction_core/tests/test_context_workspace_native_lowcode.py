# -*- coding: utf-8 -*-
import ast
import copy
import unittest

from lxml import etree

from odoo.exceptions import AccessError, UserError

from odoo.addons.smart_core.utils.contract_governance import (
    apply_contract_governance,
    apply_native_authority_domain_overrides,
)
from odoo.addons.smart_construction_core.services import contract_governance_overrides  # noqa: F401
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestContextWorkspaceNativeLowcode(TransactionCase):
    """U-C4 G08: 上下文办理工作台整组原生结构迁移.

    Three live entries share one configuration shape on three distinct models:

      875 班组借/扣款登记 / menu 697 -> sc.team.loan.deduction.workspace  / view 1932
      877 往来款登记     / menu 699 -> sc.current.account.workspace       / view 1933
      878 公司&项目退款  / menu 700 -> sc.company.project.refund.workspace / view 1934

    All three models are dispatch-only transient workspaces: they hold no
    business record of their own and every header button opens the real
    document (loan, expense claim, fund transfer, refund) that carries the
    money.  Before this batch each entry carried its own
    `entry_semantic_surface` body (办理上下文 + 办理说明) that duplicated the
    groups its own native form already declared.

    After this batch the native arch owns the structure for each entry.  The
    retired bodies declared no fact the native form does not already present,
    the section identities are addressable on the native arch, and each entry
    keeps its semantic declaration (`fact_authority`, and for the two finance
    entries `fact_models` / `projection_authority`) in
    `view_orchestration.context`.  Because the three entries sit on three
    different models and three different views, retiring a body here cannot
    reach a sibling entry — the isolation assertions below pin that down.
    """

    # (action xmlid, native view xmlid, model, entry title, context anchor, note anchor)
    ENTRIES = (
        (
            "action_sc_product_team_loan_deduction_v1",
            "view_sc_team_loan_deduction_workspace_form",
            "sc.team.loan.deduction.workspace",
            "班组借/扣款登记",
            "team_loan_processing_context",
            "team_loan_processing_note",
        ),
        (
            "action_sc_product_current_account_v1",
            "view_sc_current_account_workspace_form",
            "sc.current.account.workspace",
            "往来款登记",
            "current_account_processing_context",
            "current_account_processing_note",
        ),
        (
            "action_sc_product_company_project_refund_v1",
            "view_sc_company_project_refund_workspace_form",
            "sc.company.project.refund.workspace",
            "公司&项目退款",
            "company_project_refund_processing_context",
            "company_project_refund_processing_note",
        ),
    )
    ENTRY_CONTRACTS = {
        "action_sc_product_team_loan_deduction_v1":
            "business_config_contract_team_loan_deduction_workspace_form_v1",
        "action_sc_product_current_account_v1":
            "business_config_contract_current_account_workspace_form_v1",
        "action_sc_product_company_project_refund_v1":
            "business_config_contract_company_project_refund_workspace_form_v1",
    }
    ENTRY_MENUS = {
        "action_sc_product_team_loan_deduction_v1": "menu_sc_product_team_loan_deduction_v1",
        "action_sc_product_current_account_v1": "menu_sc_product_current_account_v1",
        "action_sc_product_company_project_refund_v1":
            "menu_sc_product_company_project_refund_v1",
    }
    ENTRY_SCREEN = {
        "action_sc_product_team_loan_deduction_v1": "班组借/扣款登记",
        "action_sc_product_current_account_v1": "往来款登记",
        "action_sc_product_company_project_refund_v1": "公司&项目退款",
    }
    # The action carriers are business facts of the workspace: retiring a
    # presentation body may not drop a way to reach the real document.
    ENTRY_CARRIERS = {
        "action_sc_product_team_loan_deduction_v1": (
            "action_register_loan", "action_register_deduction", "action_view_account",
        ),
        "action_sc_product_current_account_v1": (
            "action_project_borrow_company", "action_project_repay_company",
            "action_contractor_borrow_project", "action_contractor_repay_project",
            "action_account_transfer", "action_view_current_account",
        ),
        "action_sc_product_company_project_refund_v1": (
            "action_deduction_refund", "action_bid_deposit_return",
            "action_contract_deposit_return", "action_self_funding_refund",
            "action_view_refund_account",
        ),
    }
    # The 办理提示 stays auxiliary feedback.  Round 1 moved the computed hint out
    # of 办理上下文; round 3 of the product review found that fix had promoted it
    # to a business section of its own (its own group, its own navigation item).
    # It is now carried by the feedback surface the native renderer already owns
    # (`div.alert[role=status]` -> `native-form-feedback`), so it never becomes a
    # section, never enters the section navigation, and still disappears whenever
    # the compute has nothing the operator must handle.
    PROMPT_FEEDBACK = {
        "view_sc_team_loan_deduction_workspace_form": "team_loan",
        "view_sc_current_account_workspace_form": "current_account",
        "view_sc_company_project_refund_workspace_form": "company_project_refund",
    }
    # The workbench usage note each entry shows: how the entry is used, and where
    # the communication, remarks and attachments of the dispatch are recorded.
    # The usage note names the two steps in the order the page actually offers
    # them (the only action above it is 记录办理上下文) and says where the amounts,
    # accounts and detail lines are filled in.  Round 3 of the product review
    # found the previous wording ("填写上下文后选择上方的办理按钮") described a
    # button the page does not have.
    USAGE_NOTE_MARKERS = (
        "先记录办理上下文，再选择办理事项",
        "金额、账户和明细在打开的正式单据中填写",
        "沟通、备注与附件也在正式单据中登记",
    )
    # The advisory a fully recorded context produces (the compute's else-branch).
    COMPLETE_ADVISORY = {
        "action_sc_product_team_loan_deduction_v1": "办理上下文已完善",
        "action_sc_product_current_account_v1": "往来办理上下文已完善",
        "action_sc_product_company_project_refund_v1": "退款办理上下文已完善",
    }
    # `docs/architecture/backend_business_model_ownership_specs_v1.json` declares
    # the fact owners each entry may dispatch to (never a fact of its own).
    ENTRY_FACT_MODELS = {
        "action_sc_product_team_loan_deduction_v1": (
            "sc.financing.loan", "sc.expense.claim",
        ),
        "action_sc_product_current_account_v1": (
            "sc.financing.loan", "sc.expense.claim", "sc.fund.account.operation",
        ),
        "action_sc_product_company_project_refund_v1": (
            "sc.expense.claim", "sc.self.funding.registration",
        ),
    }
    # header carrier -> (target model, "fact" | "projection").  Every carrier
    # must open exactly one canonical owner and must open it UNSAVED.
    ENTRY_DISPATCH = {
        "action_sc_product_team_loan_deduction_v1": {
            "action_register_loan": ("sc.financing.loan", "fact"),
            "action_register_deduction": ("sc.expense.claim", "fact"),
            "action_view_account": (
                "sc.finance.project.counterparty.position", "projection",
            ),
        },
        "action_sc_product_current_account_v1": {
            "action_project_borrow_company": ("sc.financing.loan", "fact"),
            "action_project_repay_company": ("sc.expense.claim", "fact"),
            "action_contractor_borrow_project": ("sc.financing.loan", "fact"),
            "action_contractor_repay_project": ("sc.expense.claim", "fact"),
            "action_account_transfer": ("sc.fund.account.operation", "fact"),
            "action_view_current_account": (
                "sc.finance.project.counterparty.position", "projection",
            ),
        },
        "action_sc_product_company_project_refund_v1": {
            "action_deduction_refund": ("sc.expense.claim", "fact"),
            "action_bid_deposit_return": ("sc.expense.claim", "fact"),
            "action_contract_deposit_return": ("sc.expense.claim", "fact"),
            "action_self_funding_refund": ("sc.self.funding.registration", "fact"),
            "action_view_refund_account": (
                "sc.finance.project.counterparty.position", "projection",
            ),
        },
    }
    PROJECTION_MODEL = "sc.finance.project.counterparty.position"
    # Which carriers need only the project, and which also need the
    # counterparty.  This mirrors the model guard `_check_project_operator` /
    # `require_partner`: a carrier that moves a counterparty balance cannot run
    # without the counterparty, so its button must declare the same condition.
    # Round 1 of the product review found the three workspaces rendered only
    # 保存草稿 because every header button was stripped by the assembler
    # (no declared visibility -> the entitlement gate cannot prove it).  A
    # declared, context-bound `invisible` is what keeps the carrier visible to
    # the governance pipeline *and* honest about what it needs.
    PROJECT_ONLY_CARRIERS = (
        "action_project_borrow_company",
        "action_project_repay_company",
        "action_account_transfer",
        "action_view_current_account",
        "action_deduction_refund",
        "action_bid_deposit_return",
        "action_contract_deposit_return",
        "action_view_refund_account",
    )

    # Semantic declarations that must survive verbatim: they are the entry's
    # fact scope, not a second structure (same rule as G06's 177 and G07's 884).
    ENTRY_SEMANTICS = {
        "action_sc_product_team_loan_deduction_v1": {"fact_authority": "dispatch_only"},
        "action_sc_product_current_account_v1": {
            "fact_authority": "dispatch_only",
            "fact_models": [
                "sc.financing.loan", "sc.expense.claim", "sc.fund.account.operation",
            ],
            "projection_authority": "sc.finance.project.counterparty.position",
        },
        "action_sc_product_company_project_refund_v1": {
            "fact_authority": "dispatch_only",
            "fact_models": ["sc.expense.claim", "sc.self.funding.registration"],
            "projection_authority": "sc.finance.project.counterparty.position",
        },
    }
    # The business center each workspace belongs to.  The ACL that lets a
    # principal record the context follows the center, so the dispatch path can
    # only be exercised by an operator of that center.
    WORKSPACE_OPERATOR_GROUP = {
        "action_sc_product_team_loan_deduction_v1":
            "smart_construction_core.group_sc_cap_project_user",
        "action_sc_product_current_account_v1":
            "smart_construction_core.group_sc_cap_finance_user",
        "action_sc_product_company_project_refund_v1":
            "smart_construction_core.group_sc_cap_finance_user",
    }
    # Entries whose dispatch targets the operator's own role surface contains.
    # Probe evidence (this round, per role): the finance role surface carries
    # every 877/878 target menu (552-584, 372); no project-center role surface
    # carries the 875 targets, so a 875 operator - the only principal the 875
    # ACL admits - always fails closed.  That mismatch is the open gap the
    # batch record registers; it is asserted, not hidden.
    ENTRY_DISPATCH_CLOSED = (
        "action_sc_product_current_account_v1",
        "action_sc_product_company_project_refund_v1",
    )
    # What the retired bodies declared. The native arch may carry nothing more.
    RETIRED_BODY_FIELDS = ("project_id", "partner_id", "business_date",
                           "processing_advisory", "note")
    RETIRED_BODY_SECTIONS = (("办理上下文", 2), ("办理说明", 1))
    # The only field the retired bodies declared read-only.
    READONLY_FACTS = ("processing_advisory",)

    def setUp(self):
        super().setUp()
        # Re-apply the candidate view and data files inside the transaction so
        # the assertions read the candidate definitions rather than whatever the
        # installed database still holds (same pattern as the G06/G07 suites).
        from odoo.tools.convert import convert_file
        for source in (
            "views/support/team_loan_deduction_workspace_views.xml",
            "views/support/current_account_workspace_views.xml",
            "views/support/company_project_refund_workspace_views.xml",
            "data/team_loan_deduction_workspace_contract.xml",
            "data/current_account_workspace_contract.xml",
            "data/company_project_refund_workspace_contract.xml",
        ):
            convert_file(self.env, "smart_construction_core", source, {}, mode="update",
                         noupdate=False)

    def operator_env(self, action_key, project_name, group_xmlid=None):
        """Return ``(user, env, project)`` for a principal that may operate the entry.

        The dispatch authority is the principal's route authority, so a carrier
        can only resolve for a principal the role surface grants the target.  The
        fixture therefore builds a real operator: the capability group the
        workspace ACL requires plus the project the operator owns.
        """
        login = "g08_" + action_key.replace("action_sc_product_", "").replace("_v1", "")
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": "%s@invalid.local" % login,
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref(group_xmlid or self.WORKSPACE_OPERATOR_GROUP[action_key]).id,
            ])],
        })
        project = self.env["project.project"].create({
            "name": project_name,
            "company_id": self.env.company.id,
            "operation_strategy": "direct",
            "user_id": user.id,
        })
        return user, self.env(user=user), project

    def ref(self, key):
        return self.env.ref("smart_construction_core." + key)

    def view_ref_id(self, key):
        if isinstance(key, int):
            return key
        return self.env.ref("smart_construction_core." + key).id

    def contract(self, action_key, view_id, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle({
            "op": "model", "model": action.res_model, "action_id": action.id,
            "view_id": self.view_ref_id(view_id),
            "view_type": "form", "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error"))
        return result["data"]

    def governance(self, action_key, view_id):
        data = self.contract(action_key, view_id)
        return data["formStructureContract"]["sourceAuthority"]["governance_source"]

    @staticmethod
    def walk(rows, parent=None):
        for node in rows if isinstance(rows, list) else []:
            if isinstance(node, dict):
                yield node, parent
                for child in node.get("children", []) or []:
                    yield from TestContextWorkspaceNativeLowcode.walk([child], node)

    def tree_nodes(self, data):
        return [n for n, _parent in self.walk(data["layoutContract"]["containerTree"])]

    def tree_field_names(self, data):
        return [n.get("name") for n in self.tree_nodes(data) if n.get("type") == "field"]

    def rendered_anchors(self, data):
        return [n.get("containerId") for n in self.tree_nodes(data)
                if (n.get("attributes") or {}).get("data-sc-anchor")]

    def arch(self, view_key):
        return etree.fromstring(self.ref(view_key).arch_db.encode())

    def arch_field_names(self, view_key):
        return [n.get("name") for n in self.arch(view_key).xpath(".//field")]

    def arch_anchors(self, view_key):
        return [n.get("data-sc-anchor") for n in self.arch(view_key).xpath(".//group[@data-sc-anchor]")]

    # ------------------------------------------------------------------ #
    # 1. the released configurations stopped projecting a body
    # ------------------------------------------------------------------ #
    def test_entry_contracts_spend_one_native_structure(self):
        """Three released configurations, one native authority per entry, no second root."""
        for action_key, _view, _model, title, _ctx, _note in self.ENTRIES:
            record = self.ref(self.ENTRY_CONTRACTS[action_key])
            self.assertTrue(record.active, action_key)
            context = record.contract_json["view_orchestration"]["context"]
            self.assertEqual(context["source_status"], "product_release", action_key)
            form = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(form["composition_mode"], "native_semantic_surface", action_key)
            self.assertEqual(form["title"], title, action_key)
            for key in ("sections", "fields", "columns", "field_slots", "layout"):
                self.assertNotIn(key, form, (action_key, key))

    def test_entries_consume_their_own_release_on_the_native_authority(self):
        """Every entry resolves its own release over its own native body."""
        for action_key, view_key, _model, title, _ctx, _note in self.ENTRIES:
            data = self.contract(action_key, view_key)
            contract = data["formStructureContract"]
            governance = contract["sourceAuthority"]["governance_source"]
            self.assertEqual(governance["resolvedActionId"], self.ref(action_key).id, action_key)
            self.assertEqual(governance["resolvedViewId"], self.view_ref_id(view_key), action_key)
            self.assertEqual(governance["formStructureAuthority"], "native_authority", action_key)
            self.assertEqual(governance["configuredSections"], [], action_key)
            self.assertEqual(contract["layoutPolicy"], "container_tree_authority", action_key)
            self.assertEqual(contract["navigation"]["title"], title, action_key)
            self.assertFalse(contract["slots"], action_key)
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            applied = [row["name"] for row in governance["businessConfigContracts"]]
            self.assertIn(own, applied, action_key)
            self.assertTrue(self.tree_field_names(data), "%s must consume a native body" % action_key)

    # ------------------------------------------------------------------ #
    # 2. the native arch declares the section identities
    # ------------------------------------------------------------------ #
    def test_native_arch_declares_every_business_section_identity(self):
        """Two sections per entry: the context and the handling note.

        The advisory is auxiliary feedback, so it is deliberately not a section
        identity any more (see `test_the_prompt_is_feedback_not_a_section`).
        """
        for _action_key, view_key, _model, _title, ctx_anchor, note_anchor in self.ENTRIES:
            declared = set(self.arch_anchors(view_key))
            self.assertEqual(declared, {ctx_anchor, note_anchor}, view_key)
            data = self.contract(_action_key, view_key)
            rendered = set(self.rendered_anchors(data))
            self.assertEqual(rendered, declared,
                             (view_key, "every declared section identity must be rendered"))

    def test_the_native_groups_keep_the_declared_section_titles_and_columns(self):
        """The retired body declared 办理上下文 (2 cols) + 办理说明 (1 col)."""
        for _action_key, view_key, _model, _title, ctx_anchor, note_anchor in self.ENTRIES:
            root = self.arch(view_key)
            by_anchor = {
                node.get("data-sc-anchor"): node
                for node in root.xpath(".//group[@data-sc-anchor]")
            }
            self.assertEqual(by_anchor[ctx_anchor].get("string"), "办理上下文", view_key)
            self.assertEqual(by_anchor[ctx_anchor].get("col"), "2", view_key)
            self.assertEqual(by_anchor[note_anchor].get("string"), "办理说明", view_key)
            self.assertEqual(by_anchor[note_anchor].get("col"), "1", view_key)

    # ------------------------------------------------------------------ #
    # 3. no retired fact was lost, and none was invented
    # ------------------------------------------------------------------ #
    def test_no_retired_body_fact_was_lost(self):
        for _action_key, view_key, model_name, _title, ctx_anchor, note_anchor in self.ENTRIES:
            model = self.env[model_name]
            carried = set(self.arch_field_names(view_key))
            for name in self.RETIRED_BODY_FIELDS:
                self.assertIn(name, model._fields, (view_key, name, "unknown model field"))
                self.assertIn(name, carried, (view_key, name, "fact lost by retiring the body"))
            root = self.arch(view_key)
            in_context = {
                n.get("name") for n in root.xpath(".//group[@data-sc-anchor=$a]//field", a=ctx_anchor)
            }
            in_note = {
                n.get("name") for n in root.xpath(".//group[@data-sc-anchor=$a]//field", a=note_anchor)
            }
            self.assertEqual(in_context, {"project_id", "partner_id", "business_date"}, view_key)
            self.assertEqual(in_note, {"note"}, view_key)

    def test_the_arch_only_added_what_the_retired_bodies_declared(self):
        """Migrating the structure may not invent a fact on the create surface."""
        for _action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            carried = set(self.arch_field_names(view_key))
            self.assertTrue(carried.issubset(set(self.RETIRED_BODY_FIELDS)),
                            (view_key, sorted(carried - set(self.RETIRED_BODY_FIELDS))))
            self.assertEqual(carried, set(self.RETIRED_BODY_FIELDS), view_key)

    def test_the_advisory_fact_stays_readonly(self):
        """`processing_advisory` is a computed hint: it must not become editable."""
        for _action_key, view_key, model_name, _title, _ctx, _note in self.ENTRIES:
            for name in self.READONLY_FACTS:
                nodes = self.arch(view_key).xpath(".//field[@name=$n]", n=name)
                self.assertEqual(len(nodes), 1, (view_key, name))
                self.assertEqual(nodes[0].get("readonly"), "1", (view_key, name))
                field = self.env[model_name]._fields[name]
                self.assertTrue(field.compute, (model_name, name, "the hint must stay computed"))

    # ------------------------------------------------------------------ #
    # 4. the action carriers and the entry semantics survive
    # ------------------------------------------------------------------ #
    def test_the_action_carriers_are_preserved(self):
        for action_key, view_key, model_name, _title, _ctx, _note in self.ENTRIES:
            declared = {
                n.get("name") for n in self.arch(view_key).xpath(".//header/button")
            }
            self.assertEqual(declared, set(self.ENTRY_CARRIERS[action_key]), action_key)
            model = self.env[model_name]
            for name in self.ENTRY_CARRIERS[action_key]:
                self.assertTrue(hasattr(model, name), (model_name, name))

    def test_the_dispatch_semantics_are_preserved(self):
        for action_key, _view, _model, _title, _ctx, _note in self.ENTRIES:
            record = self.ref(self.ENTRY_CONTRACTS[action_key])
            context = record.contract_json["view_orchestration"]["context"]
            for key, value in self.ENTRY_SEMANTICS[action_key].items():
                self.assertEqual(context[key], value, (action_key, key))
            form = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertNotIn("sections", form, action_key)
            self.assertNotIn("fields", form, action_key)

    def test_a_retired_body_no_longer_re_projects_over_the_native_authority(self):
        for action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            governance = self.governance(action_key, view_key)
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            for row in governance["businessConfigContracts"]:
                self.assertEqual(row["name"], own,
                                 (action_key, row["name"], "another entry's body reached this entry"))
            conflicts = [row for row in governance["structureDiagnostics"]
                         if row["code"] == "LEGACY_STRUCTURE_KEY_OVERRIDE"]
            self.assertFalse(conflicts, (action_key, conflicts))

    # ------------------------------------------------------------------ #
    # 5. cross-entry isolation: three models, three views, no sharing
    # ------------------------------------------------------------------ #
    def test_each_entry_keeps_its_own_native_authority(self):
        """The three entries share a configuration shape, not a model or a view."""
        models = set()
        views = set()
        for action_key, view_key, model_name, _title, _ctx, _note in self.ENTRIES:
            action = self.ref(action_key)
            self.assertEqual(action.res_model, model_name, action_key)
            self.assertEqual(action.view_id, self.ref(view_key), action_key)
            self.assertEqual(action.view_mode, "form", action_key)
            models.add(model_name)
            views.add(self.ref(view_key).id)
            # a sibling entry's body must not appear on this entry
            governance = self.governance(action_key, view_key)
            applied = {row["name"] for row in governance["businessConfigContracts"]}
            for other_key, other_contract in self.ENTRY_CONTRACTS.items():
                if other_key == action_key:
                    continue
                self.assertNotIn(self.ref(other_contract).name, applied,
                                 (action_key, other_key, "cross-entry projection"))
        self.assertEqual(len(models), 3, "each entry owns a distinct model")
        self.assertEqual(len(views), 3, "each entry owns a distinct native view")

    def test_entry_menus_actions_and_scoping_are_unchanged(self):
        for action_key, _view, _model, _title, _ctx, _note in self.ENTRIES:
            action = self.ref(action_key)
            menu = self.ref(self.ENTRY_MENUS[action_key])
            self.assertEqual(menu.action, action, self.ENTRY_MENUS[action_key])
            self.assertTrue(menu.active, self.ENTRY_MENUS[action_key])
            self.assertFalse(action.domain, action_key)
            self.assertEqual(action.target, "current", action_key)
            self.assertTrue(action.groups_id, "%s must keep its group surface" % action_key)

    def test_the_workspace_models_are_transient_and_carry_no_model_level_contract(self):
        """These entries are dispatch surfaces, but `transient` is NOT "no record".

        The first review round found the earlier wording claiming that a record
        surface "cannot exist" because the model is a `TransientModel`.  That
        reasoning is wrong and is corrected here: a `TransientModel` holds
        ordinary rows while it lives, and the product's own vacuum removes them
        later.  The workspace therefore *does* have a legal edit state, which is
        exactly why the dispatch carriers are reachable after the context is
        recorded (asserted in `test_saving_the_context_reaches_every_dispatch_carrier`).

        What stays true is the narrower, structural statement: no *model-level*
        structure contract is registered, so the only release is the
        action-scoped one asserted above, and the row count is deliberately not
        pinned (a legal review draft would break it without any structure change).
        """
        Contract = self.env["ui.business.config.contract"].sudo().with_context(active_test=False)
        for action_key, view_key, model_name, _title, _ctx, _note in self.ENTRIES:
            model = self.env[model_name]
            self.assertTrue(model._transient, model_name)
            view = self.ref(view_key)
            self.assertEqual(view.type, "form", view_key)
            self.assertFalse(view.inherit_id, view_key)
            self.assertTrue(view.active, view_key)
            self.assertFalse(
                Contract.search([("model", "=", model_name), ("action_id", "=", False)]),
                "%s must not carry a model-level structure contract" % model_name,
            )

    # ------------------------------------------------------------------ #
    # 6. the handling path the entry exists to sell (review round 1)
    # ------------------------------------------------------------------ #
    def test_the_prompt_is_feedback_not_a_section(self):
        """`processing_advisory` is auxiliary feedback, never a business section.

        Three delivery rounds agree on one convention: the computed hint is not a
        fact.  Round 3 of the product review found the round-1 fix had given it
        its own group, which the native section renderer then promoted to a
        section with its own navigation item.  It is now carried by the feedback
        surface the renderer already owns (`div.alert[role=status]`), which is
        not a group, so it can never become a section or a navigation entry, and
        it still hides itself while the compute has nothing to act on.
        """
        for action_key, view_key, _model, _title, ctx_anchor, note_anchor in self.ENTRIES:
            root = self.arch(view_key)
            groups = root.xpath(".//group[field[@name='processing_advisory']]")
            self.assertFalse(groups, (view_key, "the hint must not own a group"))
            hosts = root.xpath(".//div[field[@name='processing_advisory']]")
            self.assertEqual(len(hosts), 1, view_key)
            host = hosts[0]
            classes = set((host.get("class") or "").split())
            self.assertIn("alert", classes, (view_key, "reuse the delivered feedback surface"))
            self.assertIn("alert-info", classes, view_key)
            self.assertEqual(host.get("role"), "status", view_key)
            self.assertFalse(host.get("data-sc-anchor"), (view_key, "a hint is not an anchor"))
            node = host.xpath("./field[@name='processing_advisory']")[0]
            self.assertEqual(node.get("nolabel"), "1", view_key)
            self.assertEqual(node.get("readonly"), "1", view_key)
            # An empty hint must not occupy a normal fact position: the feedback
            # surface disappears until the computed hint has something to say.
            self.assertEqual(host.get("invisible"), "not processing_advisory", view_key)
            # The two remaining anchors own the facts, and the advisory is not
            # one of them.
            self.assertEqual(set(self.arch_anchors(view_key)), {ctx_anchor, note_anchor}, view_key)
            data = self.contract(action_key, view_key)
            sections = [node for node in self.rendered_anchors(data)]
            self.assertNotIn(self.PROMPT_FEEDBACK[view_key] + "_processing_advisory", sections, view_key)
            names = [
                (node.get("attributes") or {}).get("data-sc-anchor")
                for node in self.tree_nodes(data)
                if (node.get("attributes") or {}).get("data-sc-anchor")
            ]
            self.assertEqual(sorted(name for name in names if name), sorted([ctx_anchor, note_anchor]), view_key)

    def test_the_recorded_context_is_a_real_transient_row(self):
        """Recording the context creates a row, and it is a legal edit state."""
        project = self.env["project.project"].search([], limit=1)
        partner = self.env["res.partner"].search([], limit=1)
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            workspace = self.env[model_name].create({
                "project_id": project.id,
                "partner_id": partner.id,
                "note": "G08 transient lifecycle",
            })
            self.assertTrue(workspace.exists(), model_name)
            self.assertEqual(workspace.processing_advisory,
                             self.COMPLETE_ADVISORY[action_key], model_name)
            workspace.unlink()
            self.assertFalse(workspace.exists(), model_name)

    def test_saving_the_context_reaches_every_dispatch_carrier(self):
        """One intent -> exactly one canonical owner, on an UNSAVED target form.

        `docs/architecture/backend_business_model_ownership_specs_v1.json`
        declares all three entries `transient_dispatch_only` with an explicit
        `fact_models` list plus a read-only `projection_model`, and
        `frontend_policy: contract_renderer_only`.  The entry collects the
        context and hands it over; the fact is only created inside the target
        document by the authority that owns it.  This test stops at that
        unsaved target - it never creates a loan, claim, transfer or refund.

        Each entry is exercised by an operator of its own business center, and
        the carrier only resolves when that operator's route authority carries
        the target (see `ENTRY_DISPATCH_CLOSED`).  For the 875 operator it does
        not, so those carriers must fail closed with the governed business
        message - never a navigation denial, and never a silent success.
        """
        closed = 0
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            _user, uenv, project = self.operator_env(action_key, "G08 办理路径 %s" % action_key)
            partner = self.env["res.partner"].create({"name": "G08 办理对象 %s" % action_key})
            workspace = uenv[model_name].create({
                "project_id": project.id,
                "partner_id": partner.id,
                "note": "G08 dispatch target",
            })
            declared_facts = set(self.ENTRY_FACT_MODELS[action_key])
            resolved = 0
            for method, (target_model, kind) in self.ENTRY_DISPATCH[action_key].items():
                self.assertTrue(hasattr(uenv[model_name], method), (model_name, method))
                try:
                    result = getattr(workspace, method)()
                except UserError as exc:
                    # The carrier resolves the menu the operator may open. When
                    # the route authority has no entry for the target the
                    # carrier fails closed with a business message instead of
                    # sending the operator into a navigation denial; the entry
                    # stays a declared fact owner of the workspace either way.
                    self.assertIn("正式入口", str(exc), (action_key, method))
                    self.assertIn(target_model, declared_facts | {self.PROJECTION_MODEL},
                                  (action_key, method))
                    continue
                resolved += 1
                self.assertEqual(result["res_model"], target_model, (action_key, method))
                self.assertFalse(result.get("res_id"),
                                 (action_key, method, "the target must open unsaved"))
                self.assertTrue(int(result.get("menu_id") or 0),
                                (action_key, method, "the route menu must be pinned"))
                if kind == "fact":
                    self.assertIn(target_model, declared_facts,
                                  (action_key, method, "not a declared fact owner"))
                    self.assertEqual(list(result["views"]), [(False, "form")], (action_key, method))
                    self.assertEqual(result["context"]["default_project_id"], project.id,
                                     (action_key, method))
                    self.assertEqual(result["context"]["default_partner_id"], partner.id,
                                     (action_key, method))
                else:
                    self.assertEqual(kind, "projection", (action_key, method))
                    self.assertEqual(target_model, self.PROJECTION_MODEL, (action_key, method))
                    modes = [mode for _view_id, mode in result["views"]]
                    self.assertIn("tree", modes, (action_key, method))
                    self.assertNotIn("form", modes[:1],
                                     (action_key, method, "the projection must not open a write form"))
            if action_key in self.ENTRY_DISPATCH_CLOSED:
                self.assertEqual(resolved, len(self.ENTRY_DISPATCH[action_key]),
                                 (action_key, "every carrier of a closed entry must dispatch"))
                closed += resolved
            else:
                self.assertEqual(resolved, 0, (action_key,
                                 "this entry's role surface declares no dispatch route"))
            workspace.unlink()
        self.assertEqual(closed, 11, "the closed entries carry eleven dispatch carriers")

    def test_the_entry_declares_its_own_primary_action_label(self):
        """A dispatch workspace must not promise a long-lived draft.

        The create-profile default is the generic 保存草稿.  For an entry whose
        own architecture says it must not persist business state, that label
        promises persistence the entry cannot make, so the entry declares its
        own governed label through the shared `form_governance` seam.
        """
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            declared = apply_contract_governance(
                {"head": {"model": model_name, "view_type": "form", "render_profile": "create"},
                 "model": model_name, "render_profile": "create",
                 "views": {"form": {"layout": [{"type": "sheet"}]}}, "fields": {}},
                "user",
            )
            governance = declared.get("form_governance") or {}
            self.assertEqual(governance.get("surface"), "context_workspace", action_key)
            self.assertNotEqual(governance.get("primary_action_label"), "保存草稿", action_key)
            self.assertTrue(governance.get("primary_action_label"), action_key)
            # A transient model can carry rows and be recycled; that is not the
            # same as being a long-lived record.  The context stays a dispatch
            # context after it is written, so the record surface keeps the same
            # declared semantics instead of falling back to a draft wording.
            edited = apply_contract_governance(
                {"head": {"model": model_name, "view_type": "form", "render_profile": "edit"},
                 "model": model_name, "render_profile": "edit", "record_id": 1,
                 "views": {"form": {"layout": [{"type": "sheet"}]}}, "fields": {}},
                "user",
            )
            edited_governance = edited.get("form_governance") or {}
            self.assertEqual(edited_governance.get("create_flow_mode"), "transient_dispatch", action_key)
            self.assertEqual(edited_governance.get("primary_action_label"),
                             governance.get("primary_action_label"), action_key)
            # The entry owns no collaboration of its own, so it must not declare
            # a collaboration promise either; where the communication is
            # recorded is stated by the workbench usage note instead.
            self.assertNotIn("collaboration_unavailable_message", governance, action_key)

    def test_the_native_authority_path_keeps_the_declared_governance(self):
        """A declaration must survive the native-authority skip.

        These three entries were moved onto `native_semantic_surface`, so the
        generic governance pass is skipped to keep one structure owner.  The
        overrides that only declare semantics must still run, otherwise moving
        an entry onto the native authority silently drops its declared
        create-flow governance.  The structural override stays out of that path.
        """
        from odoo.addons.smart_core.utils.contract_governance_domain_overrides import (
            DOMAIN_OVERRIDE_REGISTRY,
        )

        safe_names = {
            row.get("name") for row in DOMAIN_OVERRIDE_REGISTRY
            if row.get("native_authority_safe")
        }
        self.assertIn("smart_construction_core.context_workspace_form", safe_names)
        self.assertNotIn(
            "smart_construction_core.project_form", safe_names,
            "an override that rewrites structure must not run under a native view",
        )
        project_form = {
            "head": {"model": "project.project", "view_type": "form", "render_profile": "create"},
            "model": "project.project", "render_profile": "create",
            "views": {"form": {"layout": [{"type": "sheet"}]}}, "fields": {},
        }
        before = apply_native_authority_domain_overrides(project_form, "user")
        self.assertEqual(before, [], "the structural override must not be reached")
        self.assertFalse(project_form.get("form_governance"))
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            data = {
                "head": {"model": model_name, "view_type": "form", "render_profile": "create"},
                "model": model_name, "render_profile": "create",
                "views": {"form": {"layout": [{"type": "sheet"}]}}, "fields": {},
            }
            failures = apply_native_authority_domain_overrides(data, "user")
            self.assertEqual(failures, [], action_key)
            governance = data.get("form_governance") or {}
            self.assertEqual(governance.get("create_flow_mode"), "transient_dispatch", action_key)
            self.assertEqual(governance.get("primary_action_label"), "记录办理上下文", action_key)

    def test_each_carrier_declares_the_context_it_needs(self):
        """A carrier button must declare the context that unlocks it.

        The three workspaces unlock their header carriers by recording the
        project/counterparty context first.  A carrier therefore has to declare
        the same condition the model enforces, otherwise either the button
        shows while the action cannot run, or — as the product review found —
        the governance pipeline cannot prove the button is safe and drops it
        entirely, leaving the page with nothing but 保存草稿.
        """
        for action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            buttons = self.arch(view_key).xpath(".//header/button")
            self.assertTrue(buttons, (action_key, "the header must keep its carriers"))
            for button in buttons:
                name = button.get("name")
                expression = button.get("invisible") or ""
                self.assertIn("project_id", expression, (action_key, name))
                if name not in self.PROJECT_ONLY_CARRIERS:
                    self.assertIn("partner_id", expression, (action_key, name))

    def test_the_dispatch_context_survives_the_literal_transport(self):
        """The handed-over context must round-trip as a Python literal.

        A carrier returns a window action and the gateway transports its
        `context` with `repr()` (`execute_button._query_literal`).  A `date`
        object reprs as `datetime.date(2026, 9, 19)`, which neither the route
        parser nor the list gateway accepts, so the whole context would be
        rejected ("context_raw 无效") and the target document would open
        without the project and counterparty the operator just recorded.
        """
        checked = 0
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            _user, uenv, project = self.operator_env(action_key, "G08 字面量 %s" % action_key)
            partner = self.env["res.partner"].create({"name": "G08 字面量对象 %s" % action_key})
            workspace = uenv[model_name].create({
                "project_id": project.id, "partner_id": partner.id,
                "note": "G08 literal transport",
            })
            for method in self.ENTRY_DISPATCH[action_key]:
                try:
                    result = getattr(workspace, method)()
                except UserError as exc:
                    self.assertIn("正式入口", str(exc), (action_key, method))
                    continue
                checked += 1
                raw = repr(result["context"])
                self.assertNotIn("datetime.", raw, (action_key, method, raw[:120]))
                parsed = ast.literal_eval(raw)
                self.assertIsInstance(parsed, dict, (action_key, method))
                if result["res_model"] == self.PROJECTION_MODEL:
                    # A projection scopes by domain and needs no default context.
                    self.assertIn(("project_id", "=", project.id), result["domain"],
                                  (action_key, method))
                    continue
                self.assertEqual(parsed.get("default_project_id"), project.id,
                                 (action_key, method))
                self.assertEqual(parsed.get("current_project_id"), project.id,
                                 (action_key, method))
                self.assertEqual(parsed.get("default_partner_id"), partner.id,
                                 (action_key, method))
            workspace.unlink()
        self.assertEqual(checked, 11, "every closed carrier must travel as a literal")

    def test_every_returned_carrier_is_pinned_to_the_operators_route_menu(self):
        """A returned action must carry the menu the operator's route owns.

        The client only routes an action the principal's navigation pairs with
        a menu (`routeAuthority` requires action_id *and* menu_id).  A carrier
        therefore pins that menu before handing the action back; an action
        without that pairing would land the operator on a denial page.
        """
        _user, uenv, project = self.operator_env(
            "action_sc_product_current_account_v1", "G08 路由菜单")
        partner = self.env["res.partner"].create({"name": "G08 路由菜单对象"})
        workspace = uenv["sc.current.account.workspace"].create({
            "project_id": project.id, "partner_id": partner.id, "note": "G08 entry authority",
        })
        routes = {
            int(entry.get("action_id") or 0): int(entry.get("menu_id") or 0)
            for entry in uenv["sc.context.workspace.entry.authority"]._sc_route_authority()
        }
        self.assertTrue(routes, "the operator's route authority must declare entries")
        checked = 0
        for method in self.ENTRY_DISPATCH["action_sc_product_current_account_v1"]:
            try:
                result = getattr(workspace, method)()
            except UserError as exc:
                self.assertIn("正式入口", str(exc), method)
                continue
            menu_id = int(result.get("menu_id") or 0)
            self.assertEqual(menu_id, routes.get(int(result["id"]) or 0),
                             (method, "the pinned menu must be the route authority menu"))
            menu = uenv["ir.ui.menu"].browse(menu_id)
            self.assertTrue(menu.exists(), (method, menu_id))
            self.assertEqual(menu.action.id, int(result["id"]),
                             (method, "the pinned menu owns another action"))
            checked += 1
        self.assertEqual(checked, 6, "every 877 carrier must be pinned to its route menu")

    def test_a_principal_outside_the_role_surface_is_refused(self):
        """A principal outside the entry's boundary is refused, not denied.

        Probe evidence this round: the released workbench entries are visible to
        every principal, while the dispatch targets are finance-role entries and
        875's own ACL admits the project center.  A project-center principal that
        does not natively hold the target document menus therefore reaches the
        875 workbench (recording the context is allowed) and every carrier
        answers with the governed role message instead of
        `NAVIGATION_AUTHORITY_DENIED`; on 877/878 the same principal is kept out
        one step earlier, by the workspace ACL.

        This is the boundary that must survive the round-2 route alignment: the
        project surface now declares the entry and the three target routes, but a
        route is only generated for a menu the principal natively sees, so a
        principal without the finance/initiator groups keeps failing closed with
        the actionable message rather than being handed a button that would end
        in a navigation denial.  The membership boundary is asserted too, so the
        alignment cannot be read as "anyone may now register a loan".
        """
        _user, uenv, project = self.operator_env(
            "action_sc_product_team_loan_deduction_v1", "G08 角色边界 875",
            group_xmlid="smart_construction_core.group_sc_cap_project_user")
        partner = self.env["res.partner"].create({"name": "G08 角色边界对象 875"})
        workspace = uenv["sc.team.loan.deduction.workspace"].create({
            "project_id": project.id, "partner_id": partner.id, "note": "G08 role boundary",
        })
        for method in ("action_register_loan", "action_register_deduction", "action_view_account"):
            with self.assertRaises(UserError) as caught:
                getattr(workspace, method)()
            message = str(caught.exception)
            self.assertIn("正式入口", message, method)
            self.assertIn("角色", message, method)

        for action_key, model_name in (
            ("action_sc_product_current_account_v1", "sc.current.account.workspace"),
            ("action_sc_product_company_project_refund_v1",
             "sc.company.project.refund.workspace"),
        ):
            _other, other_env, other_project = self.operator_env(
                action_key, "G08 角色边界 %s" % action_key,
                group_xmlid="smart_construction_core.group_sc_cap_project_user")
            with self.assertRaises(AccessError, msg=(action_key, "ACL")):
                other_env[model_name].create({
                    "project_id": other_project.id,
                    "partner_id": partner.id,
                    "note": "G08 role boundary",
                })

    # ------------------------------------------------------------------ #
    # 7. what the reviewer asked for: the operator path and the page config
    # ------------------------------------------------------------------ #
    def test_the_native_authority_contract_carries_the_declared_governance(self):
        """The declaration must reach the page contract, not just the registry.

        Product review round 2 found the three pages showing only 保存草稿 and no
        handling entry.  The declarations existed, but the entries had been moved
        onto the native authority, whose pass skips the generic governance, so
        the page never received them.  This asserts the delivered contract:
        the runtime governance carries the declaration, and the standard create
        action is labelled by it instead of the generic draft wording.
        """
        for action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            data = self.contract(action_key, view_key)
            governance = ((data.get("runtimeContract") or {}).get("governance") or {})
            governance = governance.get("form_governance") or {}
            self.assertEqual(governance.get("surface"), "context_workspace", action_key)
            self.assertEqual(governance.get("create_flow_mode"), "transient_dispatch", action_key)
            self.assertEqual(governance.get("primary_action_label"), "记录办理上下文", action_key)
            rules = ((data.get("actionContract") or {}).get("actionRuleList")) or []
            save_rules = [row for row in rules if row.get("actionId") == "form.save"]
            self.assertEqual(len(save_rules), 1, (action_key, "one create action per page"))
            self.assertEqual(save_rules[0].get("label"), "记录办理上下文", action_key)
            self.assertNotEqual(save_rules[0].get("label"), "保存草稿", action_key)

    def test_the_finance_role_surface_grants_the_two_finance_workbenches(self):
        """The dispatch path needs the workbench entry *and* the carriers.

        Probe evidence (this round, per role): the finance role surface carried
        the eleven dispatch targets but none of the workbench menus, so a finance
        operator could dispatch yet could not open the workbench; no
        project-center surface carried the targets, so the 875 operator could
        open its workbench yet could never dispatch.  The two finance entries are
        aligned here through the existing authorization path (role nav surface +
        the menu's own declared groups); 875 stays out of the finance surface
        because its menu groups and its model ACL both declare the project
        center, and that mismatch is registered as the open deviation rather
        than papered over.
        """
        from odoo.addons.smart_construction_core.core_extension_policy_maps import (
            ROLE_GROUPS_CAPABILITY_FALLBACK,
            ROLE_GROUPS_EXPLICIT,
            ROLE_PRECEDENCE,
            ROLE_SURFACE_OVERRIDES,
        )
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

        finance_primary = ROLE_SURFACE_OVERRIDES["finance"]["primary_menu_xmlids"]
        for menu in ("menu_sc_product_current_account_v1",
                     "menu_sc_product_company_project_refund_v1"):
            self.assertIn("smart_construction_core." + menu, finance_primary, menu)
        self.assertNotIn("smart_construction_core.menu_sc_product_team_loan_deduction_v1",
                         finance_primary, "875 belongs to the project center, not finance")

        login = "g08_finance_route_surface"
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": "%s@invalid.local" % login,
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_role_finance_user").id,
            ])],
        })
        resolver = IdentityResolver(self.env(user=user))
        resolver._role_groups_explicit = ROLE_GROUPS_EXPLICIT
        resolver._role_groups_capability_fallback = ROLE_GROUPS_CAPABILITY_FALLBACK
        resolver._role_precedence = ROLE_PRECEDENCE
        resolver._role_surface_map = {**resolver._role_surface_map, **ROLE_SURFACE_OVERRIDES}
        surface = resolver.build_role_surface(
            resolver.user_group_xmlids(user), [], {"workspace.home"})
        self.assertEqual(surface.get("role_code"), "finance")
        authority = MenuService(self.env(user=user)).build_route_authority(surface)
        routes = {}
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions",
                       "admin_actions", "menu_containers"):
            for row in authority.get(bucket) or []:
                if isinstance(row, dict):
                    routes.setdefault(int(row.get("action_id") or 0),
                                      int(row.get("menu_id") or 0))
        self.assertEqual(routes.get(877), 699, "the finance surface must reach 往来款登记")
        self.assertEqual(routes.get(878), 700, "the finance surface must reach 公司&项目退款")
        self.assertNotIn(875, routes, "875 is not a finance-center entry")
        for action_id in self.FINANCE_CARRIER_ACTIONS:
            self.assertIn(action_id, routes, "the finance surface must keep carrier %s" % action_id)

    def test_the_project_role_surface_grants_the_team_loan_workbench(self):
        """875 must route for the project surface that legitimately operates it.

        Probe evidence (this round, per role): the 875 entry menu declares the
        project capability groups and the three dispatch documents
        (承包人借项目款 / 扣款单 / 项目往来台账) already grant the project
        capability create rights in their ACL, but neither the entry nor the
        target menus were declared on any role navigation surface, so a project
        operator - the principal the entry and the ACL both name - could not have
        the carrier button paired with the menu the client requires.  The
        alignment below uses the existing authorization path only: the role nav
        surface plus the menu's own declared groups, with the target menus
        declared as contextual routes so project navigation does not gain the
        finance center.

        The route is visibility gated: the project *read* principal below sees
        neither the entry nor a created route, because the declaration never
        invents visibility the principal does not natively have.
        """
        from odoo.addons.smart_construction_core.core_extension_policy_maps import (
            ROLE_GROUPS_CAPABILITY_FALLBACK,
            ROLE_GROUPS_EXPLICIT,
            ROLE_PRECEDENCE,
            ROLE_SURFACE_OVERRIDES,
        )
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

        project_surface = ROLE_SURFACE_OVERRIDES["project_member"]
        self.assertIn(
            "smart_construction_core.menu_sc_product_team_loan_deduction_v1",
            project_surface["primary_menu_xmlids"],
            "the 875 entry declares the project capability groups",
        )
        for menu in ("menu_sc_contractor_project_borrow",
                     "menu_sc_deduction_bill",
                     "menu_sc_finance_project_counterparty_position"):
            self.assertIn("smart_construction_core." + menu,
                          project_surface["contextual_menu_xmlids"], menu)

        def build_routes(login, group_xmlids):
            user = self.env["res.users"].with_context(no_reset_password=True).create({
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id] + [
                    self.env.ref(xmlid).id for xmlid in group_xmlids
                ])],
            })
            resolver = IdentityResolver(self.env(user=user))
            resolver._role_groups_explicit = ROLE_GROUPS_EXPLICIT
            resolver._role_groups_capability_fallback = ROLE_GROUPS_CAPABILITY_FALLBACK
            resolver._role_precedence = ROLE_PRECEDENCE
            resolver._role_surface_map = {**resolver._role_surface_map, **ROLE_SURFACE_OVERRIDES}
            surface = resolver.build_role_surface(
                resolver.user_group_xmlids(user), [], {"workspace.home"})
            authority = MenuService(self.env(user=user)).build_route_authority(surface)
            routes = {}
            for bucket in ("primary_actions", "role_home_actions", "contextual_actions",
                           "admin_actions", "menu_containers"):
                for row in authority.get(bucket) or []:
                    if isinstance(row, dict):
                        routes.setdefault(int(row.get("action_id") or 0),
                                          int(row.get("menu_id") or 0))
            return surface, routes

        surface, routes = build_routes("g08_project_route_surface", [
            "smart_construction_core.group_sc_cap_project_user",
            "smart_construction_core.group_sc_cap_business_initiator",
            "smart_construction_core.group_sc_cap_finance_read",
        ])
        self.assertEqual(surface.get("role_code"), "project_member")
        self.assertEqual(routes.get(875), 697, "the project surface must reach 班组借/扣款登记")
        self.assertEqual(routes.get(804), 553, "承包人借项目款 route")
        self.assertEqual(routes.get(798), 563, "扣款单 route")
        self.assertEqual(routes.get(714), 372, "项目往来台账 route")

        _read_surface, read_routes = build_routes("g08_project_read_surface", [
            "smart_construction_core.group_sc_cap_project_read",
        ])
        self.assertNotIn(875, read_routes,
                         "a read-only project principal must not be handed the entry")

    # ------------------------------------------------------------------ #
    # 8. review round 3: auxiliary feedback, readable identity, boundaries
    # ------------------------------------------------------------------ #
    def test_the_workbench_usage_note_owns_the_collaboration_note(self):
        """The dispatch note belongs to the workbench usage note, not a chapter.

        Round 3 of the product review found the 协作记录 navigation item pointing
        at a note that only told the operator to collaborate in the formal
        document - a titled chapter with no collaboration behind it.  The note is
        stated by the workbench usage note on the same native view (P1), and the
        entry declares no collaboration surface of its own; the formal documents
        keep their own collaboration, which their own entries own.
        """
        for action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            root = self.arch(view_key)
            notes = root.xpath(".//div[@role='status'][not(field)]")
            self.assertEqual(len(notes), 1, (view_key, "one usage note per entry"))
            note = notes[0]
            body = " ".join(" ".join(note.itertext()).split())
            for marker in self.USAGE_NOTE_MARKERS:
                self.assertIn(marker, body, (view_key, marker))
            self.assertFalse(note.get("data-sc-anchor"),
                             (view_key, "the usage note is not a section"))
            self.assertFalse(
                root.xpath(".//chatter | .//*[@name='message_ids'] | .//*[@name='activity_ids']"),
                (view_key, "the entry declares no collaboration surface"),
            )
            governance = (((self.contract(action_key, view_key).get("runtimeContract") or {})
                           .get("governance") or {}).get("form_governance") or {})
            self.assertEqual(governance.get("create_flow_mode"), "transient_dispatch", action_key)

    def test_the_record_surface_reads_a_readable_name(self):
        """P1 supplies the record name; the client never concatenates the model.

        Round 3 of the product review found the record tab and subtitle showing
        ``sc.company.project.refund.workspace,103``, the default ``display_name``
        of a model without ``_rec_name``.  Each entry now states its own readable
        name through Odoo's standard display-name mechanism (a `name` field the
        standard ``_rec_name`` resolves to), and the client keeps reading
        ``display_name``/``name`` with no model special case.
        """
        project = self.env["project.project"].search([], limit=1)
        partner = self.env["res.partner"].search([], limit=1)
        for _action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            workspace = self.env[model_name].create({
                "project_id": project.id, "partner_id": partner.id,
            })
            self.assertEqual(self.env[model_name]._rec_name, "name", model_name)
            self.assertTrue(workspace.name, (model_name, "the record carries a readable name"))
            display = workspace.display_name
            self.assertNotIn(model_name, display, model_name)
            self.assertNotIn(",%s" % workspace.id, display, model_name)
            self.assertIn(project.display_name, display, model_name)
            self.assertIn(partner.display_name, display, model_name)
            self.assertEqual(workspace.name_get(), [(workspace.id, display)], model_name)
            workspace.unlink()

    def test_the_native_authority_pass_runs_only_declared_semantic_overrides(self):
        """``native_authority_safe`` may declare semantics, never structure.

        Round 3 asked whether the new flag could restore a second structure
        authority or relax a constraint.  The registry is the whole surface: an
        override runs under a native view only when it declares itself
        native-authority safe, and every such override must leave the structural
        declarations of the contract byte-identical.
        """
        from odoo.addons.smart_core.utils.contract_governance_domain_overrides import (
            DOMAIN_OVERRIDE_REGISTRY,
        )

        safe_names = sorted({
            row.get("name") for row in DOMAIN_OVERRIDE_REGISTRY
            if row.get("native_authority_safe")
        })
        self.assertEqual(safe_names, ["smart_construction_core.context_workspace_form"])
        structural_keys = (
            "sections", "fields", "columns", "field_slots", "layout",
            "header_buttons", "actions", "button_box", "view_orchestration",
            "containerTree", "nodes",
        )
        for action_key, _view, model_name, _title, _ctx, _note in self.ENTRIES:
            data = {
                "head": {"model": model_name, "view_type": "form", "render_profile": "create"},
                "model": model_name, "render_profile": "create",
                "views": {"form": {"layout": [{"type": "sheet", "children": []}]}},
                "fields": {"project_id": {"type": "many2one", "required": True}},
            }
            before = copy.deepcopy(data)
            failures = apply_native_authority_domain_overrides(data, "user")
            self.assertEqual(failures, [], action_key)
            self.assertEqual(
                sorted(set(data) - set(before)), ["form_governance"],
                (action_key, "the safe pass may only add its declaration"),
            )
            for key in structural_keys:
                self.assertEqual(data.get(key), before.get(key), (action_key, key))
            # The declaration may not weaken a constraint the native form owns.
            self.assertEqual(data["fields"], before["fields"], action_key)
            self.assertEqual(data["views"], before["views"], action_key)

    def test_a_carrier_fails_closed_when_the_authority_offers_several_routes(self):
        """Several candidate routes must not be resolved by picking one.

        A carrier pins the menu the client pairs with its target action.  When the
        principal's authority offers more than one candidate, the product has not
        chosen an entry, so the dispatch fails closed with a business message
        instead of sending the operator into a route nobody selected.  Missing and
        query-scoped routes stay non-dispatchable, and exactly one candidate is
        still pinned.
        """
        from unittest.mock import patch

        model_name = "sc.team.loan.deduction.workspace"
        _user, uenv, project = self.operator_env(
            "action_sc_product_team_loan_deduction_v1", "G08 多候选 875",
        )
        partner = self.env["res.partner"].create({"name": "G08 多候选对象 875"})
        workspace = uenv[model_name].create({
            "project_id": project.id, "partner_id": partner.id, "note": "G08 ambiguity",
        })
        target_action = self.ref("action_sc_financing_loan_contractor_project_borrow").id
        exact = {"action_id": target_action, "model": "sc.financing.loan", "menu_id": 553}
        other = {"action_id": target_action, "model": "sc.financing.loan", "menu_id": 554}
        queried = {
            "action_id": target_action, "model": "sc.financing.loan", "menu_id": 555,
            "context_requirements": {"required_query": ["project_id"]},
        }
        model_class = type(workspace)
        with patch.object(model_class, "_sc_route_authority", lambda self: [exact, other]):
            with self.assertRaises(UserError) as caught:
                workspace._sc_entry_menu_id(target_action, "sc.financing.loan", label="借款登记")
            self.assertIn("多个可打开入口", str(caught.exception))
        with patch.object(model_class, "_sc_route_authority", lambda self: [exact]):
            self.assertEqual(
                workspace._sc_entry_menu_id(target_action, "sc.financing.loan"), 553,
            )
        with patch.object(model_class, "_sc_route_authority", lambda self: [exact, queried]):
            self.assertEqual(
                workspace._sc_entry_menu_id(target_action, "sc.financing.loan"), 553,
                "a query-scoped route is not a dispatch candidate",
            )
        with patch.object(model_class, "_sc_route_authority", lambda self: [queried]):
            self.assertEqual(
                workspace._sc_entry_menu_id(target_action, "sc.financing.loan"), 0,
                "a query-scoped route alone leaves the carrier undispatchable",
            )
        with patch.object(model_class, "_sc_route_authority", lambda self: []):
            self.assertEqual(
                workspace._sc_entry_menu_id(target_action, "sc.financing.loan"), 0,
            )
        # No candidate at all: the carrier fails closed with the governed
        # business message instead of navigating the operator into a denial.
        with patch.object(model_class, "_sc_route_authority", lambda self: []):
            with self.assertRaises(UserError) as missing:
                workspace.action_register_loan()
            self.assertIn("正式入口", str(missing.exception))
            self.assertIn("角色", str(missing.exception))
        workspace.unlink()

    def test_every_dispatch_carrier_is_covered_by_its_target_type(self):
        """All fourteen carriers, grouped by target type and covered by type.

        Round 3 asked for coverage of every carrier, because the browser walk
        only exercised three representative ones.  This is the contract:
        fourteen carriers, eleven targeting a fact owner and three targeting the
        read-only projection, so a per-button browser journey is not required -
        the type-level checks (unsaved form / domain-scoped projection) and the
        pinned route are what each carrier must satisfy.
        """
        table = {}
        for action_key, _view, _model, _title, _ctx, _note in self.ENTRIES:
            for method, (target_model, kind) in self.ENTRY_DISPATCH[action_key].items():
                table[(action_key, method)] = (target_model, kind)
        self.assertEqual(len(table), 14, "the three entries carry fourteen carriers")
        facts = 0
        projections = 0
        by_target = {}
        for (action_key, method), (target_model, kind) in table.items():
            self.assertIn(kind, ("fact", "projection"), (action_key, method))
            self.assertIn(target_model, self.env, (action_key, method))
            self.assertFalse(self.env[target_model]._transient,
                             (action_key, method, "a dispatch target is not a transient entry"))
            by_target.setdefault(target_model, set()).add(kind)
            if kind == "fact":
                facts += 1
                self.assertIn(target_model, self.ENTRY_FACT_MODELS[action_key],
                              (action_key, method, "not a declared fact owner"))
            else:
                projections += 1
                self.assertEqual(target_model, self.PROJECTION_MODEL, (action_key, method))
        self.assertEqual((facts, projections), (11, 3),
                         "eleven fact carriers and three projection carriers")
        # The representative browser walk covered one carrier per entry plus the
        # projection: 登记借款 (875), 项目借公司款 (877), 扣款实缴退回 (878).
        walked = {
            ("action_sc_product_team_loan_deduction_v1", "action_register_loan"),
            ("action_sc_product_current_account_v1", "action_project_borrow_company"),
            ("action_sc_product_company_project_refund_v1", "action_deduction_refund"),
        }
        self.assertTrue(walked.issubset(set(table)), sorted(walked - set(table)))
        walked_targets = {table[key][0] for key in walked}
        self.assertTrue(walked_targets.issubset(set(by_target)), sorted(walked_targets))

    FINANCE_CARRIER_ACTIONS = (798, 804, 805, 796, 797, 812, 800, 817, 819, 644, 714)

    # ------------------------------------------------------------------ #
    # 9. review round 3: the authorized form configuration path
    # ------------------------------------------------------------------ #
    CONFIG_ADMIN_GROUP = "smart_core.group_smart_core_business_config_admin"
    CONFIG_ENTRY = (
        "action_sc_product_company_project_refund_v1",
        "view_sc_company_project_refund_workspace_form",
        "sc.company.project.refund.workspace",
    )
    CONFIG_NEIGHBOURS = (
        ("action_sc_product_team_loan_deduction_v1",
         "view_sc_team_loan_deduction_workspace_form", "sc.team.loan.deduction.workspace"),
        ("action_sc_product_current_account_v1",
         "view_sc_current_account_workspace_form", "sc.current.account.workspace"),
    )

    def config_admin_env(self, action_key=None):
        """Return the principal the shipped configuration path authorizes.

        Form configuration is authorized through the existing business
        configuration administrator group and scoped to a company, a surface and
        a draft.  The surface scope is real, not decorative: a workbench view can
        only be resolved, and its preview can only run, under an authenticated
        role that the entry itself admits.  The principal below therefore carries
        the product's base internal user group (which is what grants the action's
        native view family) plus, when an entry is named, that entry's own
        capability group.  No new mechanism is introduced and no system settings
        entry is opened.
        """
        groups = [
            "base.group_user",
            "smart_construction_core.group_sc_internal_user",
            self.CONFIG_ADMIN_GROUP,
            "smart_construction_core.group_sc_cap_business_config_admin",
        ]
        suffix = "base"
        if action_key:
            groups.append(self.WORKSPACE_OPERATOR_GROUP[action_key])
            suffix = action_key.replace("action_sc_product_", "").replace("_v1", "")
        login = "g08_config_admin_%s" % suffix
        user = self.env["res.users"].with_context(no_reset_password=True).search(
            [("login", "=", login)], limit=1)
        if not user:
            user = self.env["res.users"].with_context(no_reset_password=True).create({
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [(6, 0, [self.env.ref(xmlid).id for xmlid in groups])],
            })
        return user, self.env(user=user, context={
            **self.env.context, "allowed_company_ids": [self.env.company.id]})

    def entry_contract(self, env, action_key, view_key, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(env, su_env=env["ir.model"].sudo().env).handle({
            "op": "model", "model": action.res_model, "action_id": action.id,
            "view_id": self.view_ref_id(view_key), "view_type": "form",
            "render_profile": "create", **extra,
        })
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error") or result)
        return result["data"]

    def contract_identity(self, data):
        """The three contracts the delivered page is actually rendered from."""
        from odoo.addons.smart_core.model.ui_business_config_change_set import stable_payload_hash
        return stable_payload_hash({key: data.get(key) for key in (
            "layoutContract", "statusContract", "actionContract")})

    def layout_nodes(self, data):
        return [node for node, _parent in self.walk(data["layoutContract"]["containerTree"])]

    @staticmethod
    def named_node(nodes, name):
        found = [node for node in nodes if node.get("name") == name]
        if len(found) != 1:
            raise AssertionError("expected exactly one node named %s, got %s" % (name, len(found)))
        return found[0]

    @staticmethod
    def node_label(node):
        return node.get("label") or node.get("string") or ""

    @staticmethod
    def node_binding(node, extra):
        """Bind a patch to the node identity the compiler indexes.

        The delivered contract exposes the locator in its client spelling while
        the compiler indexes the source spelling; both are the same value, so the
        binding reads whichever one the carrier owns instead of guessing.
        """
        return {
            "target": node.get("native_locator") or node.get("nativeLocator"),
            "expected": {
                "type": node.get("type"),
                "name": node.get("name") or None,
                "occurrence_index": node.get("occurrence_index")
                if "occurrence_index" in node else node.get("occurrenceIndex"),
            },
            **extra,
        }

    @staticmethod
    def node_hidden(node):
        if node.get("visible") is False:
            return True
        invisible = node.get("invisible")
        if invisible is True:
            return True
        if isinstance(invisible, dict):
            return bool(invisible.get("value"))
        return False

    def stage_form_configuration(self, env, action_key, view_key, patches, *, diff_summary):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetOpenHandler,
            BusinessConfigChangeSetStageHandler,
        )
        action = self.ref(action_key)
        opened = BusinessConfigChangeSetOpenHandler(env).handle(
            payload={"params": {"fresh": True, "name": "G08 C 包受管表单配置"}})
        self.assertTrue(opened["ok"], opened)
        change_set = opened["data"]
        result = BusinessConfigChangeSetStageHandler(env).handle(payload={"params": {
            "change_set_token": change_set["token"],
            "config_type": "form",
            "target_key": "view_orchestration:%s:form:action:%s:view:%s" % (
                action.res_model, action.id, self.view_ref_id(view_key)),
            "model": action.res_model,
            "view_type": "form",
            "action_id": action.id,
            "view_id": self.view_ref_id(view_key),
            "draft_payload": {"view_orchestration": {"views": {"form": {"node_patches": patches}}}},
            "diff_summary": {"summary": diff_summary},
        }})
        self.assertTrue(result["ok"], result)
        return change_set

    def preview_form_configuration(self, env, change_set, *, expect_ok=True):
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetValidateHandler,
            BusinessConfigChangeSetPreviewHandler,
        )
        validated = BusinessConfigChangeSetValidateHandler(env).handle(
            payload={"params": {"change_set_token": change_set["token"]}})
        self.assertTrue(validated["ok"], validated)
        previewed = BusinessConfigChangeSetPreviewHandler(env).handle(
            payload={"params": {"change_set_token": change_set["token"]}})
        if not expect_ok:
            return validated, previewed
        self.assertTrue(previewed["ok"], previewed)
        return validated, previewed

    def test_one_workbench_closes_the_authorized_form_configuration_loop(self):
        """878 closes stage -> preview -> publish -> runtime -> rollback.

        Round 3 rejected the previous C answer: route and menu authorization says
        which principal may open an entry, not how a legal form configuration
        (label, visibility, order) reaches the page.  This drives the shipped
        change-set path for the 公司&项目退款 workbench and reads the delivered
        page contract - the one the native renderer consumes - at every step,
        with the two neighbouring workbenches read alongside it so the scope of
        the configuration is measured instead of assumed.
        """
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetPublishHandler,
            BusinessConfigChangeSetRollbackHandler,
        )
        action_key, view_key, model_name = self.CONFIG_ENTRY
        _user, env = self.config_admin_env(action_key)
        baseline = self.entry_contract(self.env, action_key, view_key)
        baseline_identity = self.contract_identity(baseline)
        neighbour_identity = {
            key: self.contract_identity(self.entry_contract(self.env, key[0], key[1]))
            for key in self.CONFIG_NEIGHBOURS
        }
        baseline_rules = sorted(
            row.get("actionId") for row in
            (baseline["actionContract"].get("actionRuleList") or []))

        nodes = self.layout_nodes(baseline)
        note = self.named_node(nodes, "note")
        business_date = self.named_node(nodes, "business_date")
        context_group = self.named_node(nodes, "company_project_refund_processing_context")
        project = self.named_node(nodes, "project_id")
        children = [child for child in (context_group.get("children") or []) if isinstance(child, dict)]
        self.assertEqual(len(children), 3, [child.get("name") for child in children])
        self.assertTrue(
            all(child.get("native_locator") or child.get("nativeLocator") for child in children),
            children)
        configured_label = "办理说明（受管表单配置）"
        patches = [
            self.node_binding(note, {"set": {"label": configured_label}}),
            self.node_binding(business_date, {"set": {"visible": False}}),
            self.node_binding(context_group, {
                "order": [
                    child.get("native_locator") or child.get("nativeLocator")
                    for child in reversed(children)
                ],
            }),
        ]

        change_set = self.stage_form_configuration(
            env, action_key, view_key, patches,
            diff_summary="标签、显隐与顺序按受管配置生效")
        _validated, previewed = self.preview_form_configuration(env, change_set)
        token = previewed["data"]["preview"]["token"]
        self.assertTrue(token)
        preview_nodes = self.layout_nodes(self.entry_contract(
            env, action_key, view_key, preview_token=token, preview_role_key=""))
        self.assertEqual(self.node_label(self.named_node(preview_nodes, "note")), configured_label)
        self.assertTrue(self.node_hidden(self.named_node(preview_nodes, "business_date")),
                        "a legal configuration must be able to hide an optional context fact")
        self.assertEqual(
            [child.get("name") for child in
             (self.named_node(preview_nodes, "company_project_refund_processing_context").get("children") or [])],
            ["business_date", "partner_id", "project_id"],
            "an explicit order permutation must be honoured",
        )
        # The preview is still the same page: the required context fact and every
        # dispatch carrier survive the configuration untouched.
        self.assertTrue(self.named_node(preview_nodes, "project_id").get("required"),
                        "a configuration may not relax the required context fact")
        self.assertEqual(
            sorted(row.get("actionId") for row in
                   (self.entry_contract(env, action_key, view_key,
                                        preview_token=token, preview_role_key="")["actionContract"]
                    .get("actionRuleList") or [])),
            baseline_rules,
            "a configuration may not add or drop an action carrier",
        )

        published = BusinessConfigChangeSetPublishHandler(env).handle(payload={"params": {
            "change_set_token": change_set["token"],
            "request_id": "g08-c-closure-%s" % change_set["id"],
        }})
        self.assertTrue(published["ok"], published)
        publish_result = published["data"]["publish_result"]
        self.assertTrue(publish_result["published_content_verified"], publish_result)
        self.assertTrue(publish_result["runtime_verified"], publish_result)

        runtime_nodes = self.layout_nodes(self.entry_contract(self.env, action_key, view_key))
        self.assertEqual(self.node_label(self.named_node(runtime_nodes, "note")), configured_label,
                         "the published configuration must reach the delivered page contract")
        self.assertTrue(self.node_hidden(self.named_node(runtime_nodes, "business_date")))
        for key in self.CONFIG_NEIGHBOURS:
            self.assertEqual(
                self.contract_identity(self.entry_contract(self.env, key[0], key[1])),
                neighbour_identity[key],
                "%s must not inherit %s's configuration" % (key[2], model_name),
            )

        rolled_back = BusinessConfigChangeSetRollbackHandler(env).handle(payload={"params": {
            "change_set_token": change_set["token"],
            "request_id": "g08-c-rollback-%s" % change_set["id"],
        }})
        self.assertTrue(rolled_back["ok"], rolled_back)
        self.assertEqual(self.contract_identity(self.entry_contract(self.env, action_key, view_key)),
                         baseline_identity, "rollback must restore the delivered baseline")
        for key in self.CONFIG_NEIGHBOURS:
            self.assertEqual(self.contract_identity(self.entry_contract(self.env, key[0], key[1])),
                             neighbour_identity[key])

    def test_the_configuration_path_refuses_to_relax_a_workbench_constraint(self):
        """The workbench keeps the product's business constraints under configuration.

        The same authorized path that publishes a label, a hidden optional fact
        and an order permutation must not be usable to hide the required context
        fact or to relax a readonly constraint.  Without this the closure above
        would only show that configuration is accepted, not that it stays inside
        the business rules.
        """
        from odoo.addons.smart_core.handlers.business_config_change_set import (
            BusinessConfigChangeSetDiscardHandler,
        )
        action_key, view_key, _model = self.CONFIG_ENTRY
        _user, env = self.config_admin_env(action_key)
        nodes = self.layout_nodes(self.entry_contract(self.env, action_key, view_key))
        project = self.named_node(nodes, "project_id")
        advisory = self.named_node(nodes, "processing_advisory")
        for name, patch, reason in (
            ("required", self.node_binding(project, {"set": {"visible": False}}),
             "CONFIG_REQUIRED_FIELD_HIDDEN"),
            ("readonly", self.node_binding(advisory, {"set": {"readonly": False}}),
             "CONFIG_BUSINESS_CONSTRAINT_RELAXED"),
            ("stale", {**self.node_binding(project, {"set": {"label": "失效目标"}}),
                       "target": "/removed/node"}, "CONFIG_TARGET_STALE"),
        ):
            change_set = self.stage_form_configuration(
                env, action_key, view_key, [patch], diff_summary="越界配置应被拒绝")
            _validated, previewed = self.preview_form_configuration(env, change_set, expect_ok=False)
            self.assertFalse(previewed["ok"], (name, previewed))
            self.assertIn(reason, str(previewed), name)
            discard = BusinessConfigChangeSetDiscardHandler(env).handle(
                payload={"params": {"change_set_token": change_set["token"]}})
            self.assertTrue(discard["ok"], discard)

    def test_a_transient_workbench_stays_out_of_the_per_form_field_policy_editor(self):
        """The other form-configuration entry is closed for these models by design.

        A capability limitation must be registered, not renamed.  Two different
        capabilities are called "form configuration" in this product: the tenant
        low-code change set, which owns the page contract and closes on these
        three entries (see the loop test above), and the per-form field policy
        editor, whose 表单设置 entry is injected into a page and which refuses a
        transient model at its entry, its write handler and its order handler.
        This pins the refusal so a later change cannot widen the entry silently,
        and so the remaining gap is a named, owned limitation instead of a
        renamed pass.
        """
        from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import (
            PageAssembler,
        )
        from odoo.addons.smart_core.handlers.form_field_configuration import (
            FormCustomFieldCreateHandler,
            FormFieldPolicySetHandler,
        )
        _user, env = self.config_admin_env(self.CONFIG_ENTRY[0])
        for action_key, view_key, model_name in (self.CONFIG_ENTRY,) + tuple(
                (key[0], key[1], key[2]) for key in self.CONFIG_NEIGHBOURS):
            action = self.ref(action_key)
            data = {"render_profile": "create"}
            PageAssembler(env, su_env=env["ir.model"].sudo().env)._inject_current_form_settings_action(
                data, model_name=model_name, action_id=action.id,
                view_id=self.view_ref_id(view_key), render_profile="create")
            carriers = list(data.get("buttons") or []) + list(
                (data.get("toolbar") or {}).get("header") or [])
            injected = [row for row in carriers
                        if row.get("key") == "current_form_field_settings"]
            self.assertEqual(
                injected, [],
                (model_name, "the per-form field policy entry is not offered for a transient workbench"))
            policy = FormFieldPolicySetHandler(env, payload={"params": {
                "model": model_name, "field_name": "note", "label": "越界标签"}}).run()
            self.assertFalse(policy.get("ok"), (model_name, policy))
            self.assertIn("临时模型", str(policy))
            custom = FormCustomFieldCreateHandler(env, payload={"params": {
                "model": model_name, "field_name": "g08_extra", "field_type": "char"}}).run()
            self.assertFalse(custom.get("ok"), (model_name, custom))

    def test_the_design_authority_is_bounded_by_the_entry_surface(self):
        """The configuration entry is a conjunction of authority and surface.

        Probe (this round): the change-set authority alone cannot design one of
        these workbenches.  Resolving an entry's native view family needs the
        product's base internal user group, and the preview path additionally
        binds the draft to the authenticated role surface.  The product's
        business configuration administrator capability in turn already carries
        the capability groups of the entries it is expected to design, so a
        scoped designer reaches 878's page and its preview legitimately - and a
        principal without that surface does not reach it at all.
        """
        action_key, view_key, model_name = self.CONFIG_ENTRY
        login = "g08_config_admin_without_surface"
        user = self.env["res.users"].with_context(no_reset_password=True).search(
            [("login", "=", login)], limit=1)
        if not user:
            user = self.env["res.users"].with_context(no_reset_password=True).create({
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [(6, 0, [
                    self.env.ref("base.group_user").id,
                    self.env.ref(self.CONFIG_ADMIN_GROUP).id,
                ])],
            })
        restricted = self.env(user=user, context={
            **self.env.context, "allowed_company_ids": [self.env.company.id]})
        with self.assertRaises(Exception) as caught:
            self.entry_contract(restricted, action_key, view_key)
        self.assertIn("unavailable", str(caught.exception),
                      "the entry surface must be resolved for the principal, never assumed")

        admin, scoped = self.config_admin_env(action_key)
        self.assertTrue(admin.has_group(
            "smart_construction_core.group_sc_cap_business_config_admin"))
        self.assertTrue(scoped.user.has_group(self.WORKSPACE_OPERATOR_GROUP[action_key]),
                        "the shipped design capability carries the entry's capability group")
        self.assertTrue(self.entry_contract(scoped, action_key, view_key))

    def test_the_runtime_governance_merge_keeps_one_structure_owner(self):
        """The projected runtime may add governance, never a second structure owner.

        The native-authority merge exists so a projected page keeps the entry's
        declared create-flow semantics.  Merging must therefore stay additive on
        semantics: the delivered contract carries both the projected
        ``view_orchestration`` governance and the declared ``form_governance``,
        while the structure authority still names exactly one owner and the
        structural contracts are the ones the single compiler produced.
        """
        for action_key, view_key, _model, _title, _ctx, _note in self.ENTRIES:
            data = self.contract(action_key, view_key)
            runtime_governance = ((data.get("runtimeContract") or {}).get("governance") or {})
            self.assertTrue(runtime_governance.get("view_orchestration"),
                            (action_key, "the projected governance must survive"))
            declared = runtime_governance.get("form_governance") or {}
            self.assertEqual(declared.get("create_flow_mode"), "transient_dispatch",
                             (action_key, "the declared semantics must survive the merge"))
            authority = ((data.get("formStructureContract") or {}).get("sourceAuthority") or {})
            self.assertEqual(authority.get("kind"), "unified_page_contract_v2", action_key)
            self.assertTrue(authority.get("governed_form_structure"), action_key)
            governance_source = authority.get("governance_source") or {}
            self.assertEqual(governance_source.get("formStructureAuthority"), "native_authority",
                             (action_key, "the native view stays the single structure owner"))
            self.assertEqual(governance_source.get("structureDiagnostics"), [],
                             (action_key, "no competing structural declaration is reported"))
