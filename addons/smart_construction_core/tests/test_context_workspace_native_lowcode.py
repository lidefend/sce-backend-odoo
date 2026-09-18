# -*- coding: utf-8 -*-
from lxml import etree

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
            self.assertEqual(in_context, {"project_id", "partner_id", "business_date",
                                          "processing_advisory"}, view_key)
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

    def test_the_workspace_models_are_transient_and_carry_no_record_surface(self):
        """These entries are dispatch surfaces: there is no persisted record to read.

        This is a structural property, not a missing sample: the models are
        `TransientModel`, so a record surface cannot exist and the entry is
        therefore never registered as an uncovered record surface.
        """
        Contract = self.env["ui.business.config.contract"].sudo().with_context(active_test=False)
        for action_key, view_key, model_name, _title, _ctx, _note in self.ENTRIES:
            model = self.env[model_name]
            self.assertTrue(model._transient, model_name)
            view = self.ref(view_key)
            self.assertEqual(view.type, "form", view_key)
            self.assertFalse(view.inherit_id, view_key)
            self.assertTrue(view.active, view_key)
            # No model-level structure contract is registered for the model, so
            # the only entry is the action-scoped release asserted above.  The
            # row count is deliberately not asserted: a transient row is a
            # dispatch draft that the product's own vacuum removes, so pinning
            # it would fail on a legal review draft instead of on a structure
            # change.
            self.assertFalse(
                Contract.search([("model", "=", model_name), ("action_id", "=", False)]),
                "%s must not carry a model-level structure contract" % model_name,
            )
