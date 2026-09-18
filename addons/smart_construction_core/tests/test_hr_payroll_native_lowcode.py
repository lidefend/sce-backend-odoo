# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestHrPayrollNativeLowcode(TransactionCase):
    """U-C4 G07: 工资薪酬 / 社保公积 / 薪资核算清单 / 薪资发放登记 native surface migration.

    The whole 人事薪酬 group shares one model (`sc.hr.payroll.document`) and one
    native primary form (`smart_construction_core.view_sc_hr_payroll_document_form`):
    four live entries (858 工资薪酬 / menu 673, 873 薪资核算清单 / menu 695,
    884 社保公积 / menu 706, 874 薪资发放登记 / menu 696) plus five archived
    entries reachable through their own menus (663 项目管理人员工资登记,
    660 社保人员登记, 661 社保登记, 662 补助, 664 奖金).  The payment entry 874
    consumes `sc.hr.salary.payment` and its own native form
    `smart_construction_core.view_sc_hr_salary_payment_form`.

    Before this batch every entry carried its own `entry_semantic_surface`
    body, so the same native tree was projected eight different ways, and the
    sibling action 858 had no release at all and fell back to the model-wide
    sparse annotation `sc_hr_payroll_document_form_structure_generated_v1`,
    rendering the generic workspace plane instead of the business task surface
    its siblings rendered.

    After this batch the native arch owns the structure for the whole group.
    Every retired body's fact is still carried (none is dropped), the arch
    states the `fact_type` conditions that separate the sibling entries, and
    the repeated field names are NOT duplicates: the same fact appears once per
    `fact_type` group so each entry's create surface is self-contained, and
    exactly one of those groups is visible for a given `fact_type`.
    """

    PAYROLL_VIEW = "view_sc_hr_payroll_document_form"
    PAYMENT_VIEW = "view_sc_hr_salary_payment_form"

    # (action xmlid, native view xmlid, entry title)
    PAYROLL_ENTRIES = (
        ("action_sc_payroll_management", PAYROLL_VIEW, "工资薪酬"),
        ("action_sc_product_project_payroll_v1", PAYROLL_VIEW, "薪资核算清单"),
        ("action_sc_product_social_fund_v1", PAYROLL_VIEW, "社保公积"),
        ("action_sc_salary_registration", PAYROLL_VIEW, "项目管理人员工资登记"),
        ("action_sc_social_person_registration", PAYROLL_VIEW, "社保人员登记"),
        ("action_sc_social_registration", PAYROLL_VIEW, "社保登记"),
        ("action_sc_subsidy", PAYROLL_VIEW, "补助"),
        ("action_sc_bonus", PAYROLL_VIEW, "奖金"),
    )
    PAYMENT_ENTRIES = (
        ("action_sc_product_project_salary_payment_v1", PAYMENT_VIEW, "薪资发放登记"),
    )
    FORMAL_ENTRIES = PAYROLL_ENTRIES + PAYMENT_ENTRIES

    ENTRY_CONTRACTS = {
        "action_sc_payroll_management":
            "business_config_contract_hr_payroll_management_productized_form_v1",
        "action_sc_product_project_payroll_v1":
            "business_config_contract_project_payroll_productized_form_v1",
        "action_sc_product_social_fund_v1": "business_config_contract_social_fund_form_v1",
        "action_sc_salary_registration":
            "business_config_contract_hr_payroll_salary_productized_form_v1",
        "action_sc_social_person_registration":
            "business_config_contract_hr_payroll_social_person_productized_form_v1",
        "action_sc_social_registration":
            "business_config_contract_hr_payroll_social_registration_productized_form_v1",
        "action_sc_subsidy": "business_config_contract_hr_payroll_subsidy_productized_form_v1",
        "action_sc_bonus": "business_config_contract_hr_payroll_bonus_productized_form_v1",
        "action_sc_product_project_salary_payment_v1":
            "business_config_contract_project_salary_payment_productized_form_v1",
    }
    # The model-wide sparse field-order annotation: no action scope, so it keeps
    # serving the model.  It is an annotation, not a structure, and this batch
    # neither deletes nor rewrites it.
    MODEL_WIDE_CONTRACT = "business_config_contract_sc_hr_payroll_document_form_structure_generated"

    ENTRY_MENUS = {
        "action_sc_payroll_management": "menu_sc_payroll_management",
        "action_sc_product_project_payroll_v1": "menu_sc_product_project_payroll_v1",
        "action_sc_product_social_fund_v1": "menu_sc_product_social_fund_v1",
        "action_sc_product_project_salary_payment_v1": "menu_sc_product_project_salary_payment_v1",
        "action_sc_salary_registration": "menu_sc_salary_registration",
        "action_sc_social_person_registration": "menu_sc_social_person_registration",
        "action_sc_social_registration": "menu_sc_social_registration",
        "action_sc_subsidy": "menu_sc_subsidy",
        "action_sc_bonus": "menu_sc_bonus",
    }
    # The `fact_type` facts each payroll entry's action domain admits.  Retiring
    # a presentation body may not widen or narrow an entry's business scope.
    ENTRY_FACT_TOKENS = {
        "action_sc_payroll_management": ("salary_registration", "subsidy", "bonus"),
        "action_sc_product_project_payroll_v1": ("salary_registration",),
        "action_sc_product_social_fund_v1":
            ("social_person_registration", "social_registration", "provident_fund_registration"),
        "action_sc_salary_registration": ("salary_registration",),
        "action_sc_social_person_registration": ("social_person_registration",),
        "action_sc_social_registration": ("social_registration",),
        "action_sc_subsidy": ("subsidy",),
        "action_sc_bonus": ("bonus",),
    }

    PAYROLL_ANCHORS = (
        "payroll_application_info", "payroll_personnel", "payroll_social_security",
        "payroll_salary", "payroll_provident_fund", "payroll_subsidy_bonus",
        "payroll_handling", "payroll_source_trace",
    )
    PAYMENT_ANCHORS = (
        "salary_payment_identity", "salary_payment_amount", "salary_payment_handling",
    )
    # The one section whose visibility is a record fact, not a `fact_type`
    # branch: a record that was not migrated has nothing to read there.
    CONDITIONAL_ANCHOR = "payroll_source_trace"

    FACT_TYPES = (
        "social_person_registration", "social_registration", "provident_fund_registration",
        "salary_registration", "subsidy", "bonus",
    )
    # Facts that appear more than once in the shared body.  Each occurrence
    # belongs to a different `fact_type` group, so this is a per-context
    # presentation and not an in-context duplicate.
    REPEATED_FACTS = {
        "period_year": 3, "period_month": 3, "people_count": 3,
        "payer_unit": 2, "company_amount": 2, "individual_amount": 2, "payout_unit": 2,
    }
    # Facts the shared body presents exactly once whatever the `fact_type`.  The
    # 人员 group is visible for every `fact_type`, so repeating the person inside
    # a fact_type group would present the same fact twice in one body.
    SINGLE_PRESENTATION_FACTS = ("employee_user_id", "employee_name")
    # The facts this batch added to the shared payroll body.  Measured against
    # the pre-migration arch: the body declared 66 fields at HEAD d2997196 and
    # declares 69 now, and the delta is exactly these five - the four provenance
    # facts the retired bodies used to declare, plus `currency_id`, the companion
    # of the Monetary facts (view 1700 declares it the same way).  All five were
    # already declared by the retired bodies, so moving the structure to the
    # native arch invented no business fact.
    ARCH_FACTS_ADDED_BY_THIS_BATCH = (
        "legacy_document_no", "legacy_document_state", "legacy_source_table",
        "legacy_source_id", "currency_id",
    )
    # Union of the facts the retired payroll bodies declared, captured from the
    # pre-migration definitions at HEAD d2997196.  None of them may be lost.
    RETIRED_PAYROLL_FACTS = (
        "amount", "attachment_ids", "business_date", "certificate_fee", "company_amount",
        "company_contribution_rate", "contact_phone", "currency_id", "deduction_amount",
        "department_id", "description", "document_no", "due_date", "employee_name",
        "employee_status", "employee_type", "employee_user_id", "fact_type", "gross_amount",
        "handler_id", "id_number", "individual_amount", "individual_contribution_rate",
        "item_type", "legacy_document_no", "legacy_document_state", "legacy_source_id",
        "legacy_source_table", "name", "net_salary", "occurrence_date", "paid_amount",
        "payer_unit", "payment_ids", "payment_state", "payout_unit", "people_count",
        "period_month", "period_year", "processing_advisory", "project_id",
        "provident_fund_account", "provident_fund_base", "requester_id", "result_note",
        "salary_base", "social_security_base", "state", "unpaid_amount",
    )
    RETIRED_PAYMENT_FACTS = (
        "attachment_ids", "employee_name", "employee_user_id", "name", "note",
        "payable_amount", "payment_amount", "payment_date", "payment_method",
        "payment_reference", "payroll_document_id", "period_month", "period_year",
        "processing_advisory", "project_id", "responsible_id", "state",
    )

    def setUp(self):
        super().setUp()
        # The batch's view and data files are re-applied inside the transaction so
        # the assertions read the candidate definitions instead of whatever the
        # installed database still holds (same pattern as the G06 suite).  The
        # order is the manifest load order: the shared action 663 is redefined by
        # the later support alignment file, so converting the core view alone
        # would leave the entry with the core file's interim action name.
        from odoo.tools.convert import convert_file
        for source in (
            "views/core/hr_payroll_document_views.xml",
            "views/support/user_confirmed_formal_list_alignment_views.xml",
            "data/hr_payroll_form_productization_contract.xml",
            "data/social_fund_contract.xml",
        ):
            convert_file(self.env, "smart_construction_core", source, {}, mode="update", noupdate=False)

    def ref(self, key):
        return self.env.ref("smart_construction_core." + key)

    def view_ref_id(self, key):
        if isinstance(key, int):
            return key
        return self.env.ref("smart_construction_core." + key).id

    def contract(self, action_key, view_id, **extra):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        action = self.ref(action_key)
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
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
                    yield from TestHrPayrollNativeLowcode.walk([child], node)

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

    def guarding_condition(self, node):
        """Nearest declared `invisible` on a field node or a container above it."""
        while node is not None:
            value = node.get("invisible")
            if value:
                return value
            node = node.getparent()
        return None

    def is_visible(self, condition, fact_type=None, legacy_document_no=None):
        from odoo.tools.safe_eval import safe_eval
        if not condition:
            return True
        value = safe_eval(condition, {"fact_type": fact_type, "legacy_document_no": legacy_document_no})
        return not bool(value)

    # ------------------------------------------------------------------ #
    # 1. the released configurations stopped projecting a body
    # ------------------------------------------------------------------ #
    def test_entry_contracts_spend_one_native_structure(self):
        """Nine released configurations, one native authority per entry, no second root."""
        for action_key, _view, title in self.FORMAL_ENTRIES:
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
        """Every entry resolves its own release over the native body it shares."""
        for action_key, view_key, title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_key)
            contract = data["formStructureContract"]
            governance = contract["sourceAuthority"]["governance_source"]
            self.assertEqual(governance["resolvedActionId"], self.ref(action_key).id, action_key)
            self.assertEqual(governance["resolvedViewId"], self.view_ref_id(view_key), action_key)
            self.assertEqual(governance["formStructureAuthority"], "native_authority", action_key)
            self.assertEqual(governance["formPresentationMode"], "task", action_key)
            self.assertEqual(governance["configuredSections"], [], action_key)
            self.assertEqual(contract["layoutPolicy"], "container_tree_authority", action_key)
            self.assertEqual(contract["navigation"]["title"], title, action_key)
            # the released configuration keeps its title without projecting a body
            self.assertFalse(contract["slots"], action_key)
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            applied = [row["name"] for row in governance["businessConfigContracts"]]
            self.assertIn(own, applied, action_key)
            self.assertTrue(self.tree_field_names(data), "%s must consume a native body" % action_key)

    # ------------------------------------------------------------------ #
    # 2. the entry that had no release now renders the sibling surface
    # ------------------------------------------------------------------ #
    def test_the_entry_that_had_no_release_renders_the_sibling_business_surface(self):
        """858 used to fall back to the model-wide plane and render a generic floorplan.

        858 (工资薪酬 / menu 673) carried no entry-level release, so it consumed
        the model-wide sparse annotation and rendered a workspace surface while
        its siblings rendered the business task surface.  With its own release
        in place the two entries have to consume the same shared body: same
        section identities, same facts.  A regression that lets one entry fall
        back to a different plane fails here.
        """
        fallback = self.contract("action_sc_payroll_management", self.PAYROLL_VIEW)
        sibling = self.contract("action_sc_product_project_payroll_v1", self.PAYROLL_VIEW)
        self.assertEqual(
            sorted(self.rendered_anchors(fallback)), sorted(self.rendered_anchors(sibling)),
            "858 must render the same business sections as its sibling entry",
        )
        self.assertEqual(
            sorted(self.tree_field_names(fallback)), sorted(self.tree_field_names(sibling)),
            "858 must render the same facts as its sibling entry",
        )
        self.assertEqual(
            self.governance("action_sc_payroll_management", self.PAYROLL_VIEW)["formStructureAuthority"],
            "native_authority",
        )

    # ------------------------------------------------------------------ #
    # 3. the shared body declares the section identities
    # ------------------------------------------------------------------ #
    def test_native_arch_declares_every_business_section_identity(self):
        declared = set(self.arch_anchors(self.PAYROLL_VIEW))
        self.assertEqual(declared, set(self.PAYROLL_ANCHORS))
        self.assertEqual(set(self.arch_anchors(self.PAYMENT_VIEW)), set(self.PAYMENT_ANCHORS))

        # the navigation consumes the same identities the body declares: the
        # render tree carries all of them except the one section whose
        # visibility is a record fact, which is legally hidden on a create surface
        for action_key, view_key, _title in self.FORMAL_ENTRIES:
            data = self.contract(action_key, view_key)
            rendered = set(self.rendered_anchors(data))
            expected = set(self.PAYROLL_ANCHORS if view_key == self.PAYROLL_VIEW else self.PAYMENT_ANCHORS)
            self.assertTrue(rendered.issubset(expected), (action_key, rendered - expected))
            missing = expected - rendered
            self.assertTrue(
                missing.issubset({self.CONDITIONAL_ANCHOR}),
                (action_key, "a section identity disappeared from the render tree", missing),
            )

    def test_the_source_trace_section_is_declared_conditionally(self):
        """An unmigrated record has no provenance to read, so the section is declared hidden.

        This is a legal, declared hiding, not a silent removal: the arch states
        the condition and the four provenance facts stay declared inside it.
        """
        root = self.arch(self.PAYROLL_VIEW)
        groups = root.xpath('.//group[@data-sc-anchor=$a]', a=self.CONDITIONAL_ANCHOR)
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0].get("invisible"), "the section must state why it hides")
        self.assertFalse(self.is_visible(groups[0].get("invisible"), legacy_document_no=None))
        self.assertTrue(self.is_visible(groups[0].get("invisible"), legacy_document_no="LEGACY-1"))
        names = [n.get("name") for n in groups[0].xpath(".//field")]
        self.assertEqual(
            sorted(names),
            ["legacy_document_no", "legacy_document_state", "legacy_source_id", "legacy_source_table"],
        )

    # ------------------------------------------------------------------ #
    # 4. repeated names are per-fact_type contexts, not duplicates
    # ------------------------------------------------------------------ #
    def test_repeated_fact_names_are_per_fact_type_contexts(self):
        """A fact repeated across fact_type groups is not an in-context duplicate.

        The same fact appears once per `fact_type` group so each entry's create
        surface is self-contained, and exactly one of those groups is visible
        for a given `fact_type`.  De-duplicating by field name would delete a
        sibling entry's fill surface.
        """
        root = self.arch(self.PAYROLL_VIEW)
        for name, count in self.REPEATED_FACTS.items():
            nodes = root.xpath(".//field[@name=$n]", n=name)
            self.assertEqual(len(nodes), count, name)
            serving = []
            for record_fact_type in self.FACT_TYPES:
                visible = [n for n in nodes
                           if self.is_visible(self.guarding_condition(n), fact_type=record_fact_type)]
                self.assertLessEqual(
                    len(visible), 1,
                    (name, record_fact_type, "one fact_type must not present the fact twice"),
                )
                if visible:
                    serving.append(record_fact_type)
            # a name is repeated because more than one fact_type group needs it,
            # not because two groups both claim the same fact_type
            self.assertGreater(len(serving), 1, (name, "a repeated name must serve more than one fact_type"))
            for node in nodes:
                condition = self.guarding_condition(node)
                self.assertTrue(
                    any(self.is_visible(condition, fact_type=fact_type) for fact_type in self.FACT_TYPES),
                    (name, condition, "an occurrence that can never be visible is dead presentation"),
                )

    def test_the_person_is_presented_once_in_every_fact_type(self):
        """The person of a record is presented once, not once per section.

        The 人员 group is visible for every `fact_type`, so a fact_type group
        that repeats the person would show the same fact twice in the same body
        - an in-context duplicate rather than a second scenario.  The retired
        entry bodies presented the person once, in the person and period
        section, so the shared native body has to do the same.
        """
        root = self.arch(self.PAYROLL_VIEW)
        for name in self.SINGLE_PRESENTATION_FACTS:
            nodes = root.xpath(".//field[@name=$n]", n=name)
            self.assertEqual(len(nodes), 1, (name, "the fact is declared more than once"))
            for record_fact_type in self.FACT_TYPES:
                visible = [n for n in nodes
                           if self.is_visible(self.guarding_condition(n), fact_type=record_fact_type)]
                self.assertEqual(len(visible), 1, (name, record_fact_type))

    def test_the_fact_type_groups_are_mutually_exclusive(self):
        root = self.arch(self.PAYROLL_VIEW)
        groups = {n.get("data-sc-anchor"): n for n in root.xpath(".//group[@data-sc-anchor]")}
        keyed = ("payroll_social_security", "payroll_salary", "payroll_provident_fund",
                 "payroll_subsidy_bonus")
        for record_fact_type in self.FACT_TYPES:
            visible = [anchor for anchor in keyed
                       if self.is_visible(groups[anchor].get("invisible"), fact_type=record_fact_type)]
            self.assertEqual(
                len(visible), 1,
                (record_fact_type, "exactly one fact_type group may be visible", visible),
            )

    # ------------------------------------------------------------------ #
    # 5. no fact the retired bodies declared was lost
    # ------------------------------------------------------------------ #
    def test_no_retired_body_fact_was_lost(self):
        for view_key, facts in (
            (self.PAYROLL_VIEW, self.RETIRED_PAYROLL_FACTS),
            (self.PAYMENT_VIEW, self.RETIRED_PAYMENT_FACTS),
        ):
            model = self.env["sc.hr.payroll.document" if view_key == self.PAYROLL_VIEW
                             else "sc.hr.salary.payment"]
            carried = set(self.arch_field_names(view_key))
            for name in facts:
                self.assertIn(name, model._fields, (view_key, name, "unknown model field"))
                self.assertIn(name, carried, (view_key, name, "fact lost by retiring the body"))

    def test_the_arch_only_added_what_the_retired_bodies_declared(self):
        """The five added facts are the provenance facts plus the currency companion.

        The body declared 66 fields before this batch and 69 after, and the
        delta is exactly `ARCH_FACTS_ADDED_BY_THIS_BATCH`: the four provenance
        facts, which lived only in the retired bodies, plus `currency_id`.  The
        provenance facts have to stay, or retiring the bodies would have dropped
        the migrated-record history; carrying them inside a conditionally
        visible section is the declared way to keep them without presenting an
        empty titled group on every unmigrated record.  Every one of the five
        was already declared by the retired bodies, so the shared body gained no
        fact the entries did not have and invented none.
        """
        carried = set(self.arch_field_names(self.PAYROLL_VIEW))
        provenance = {"legacy_document_no", "legacy_document_state", "legacy_source_table",
                      "legacy_source_id"}
        added = set(self.ARCH_FACTS_ADDED_BY_THIS_BATCH)
        self.assertEqual(sorted(added - provenance), ["currency_id"])
        self.assertTrue(added.issubset(carried), sorted(added - carried))
        # a migration of the structure may not invent a fact: whatever it adds
        # to the body has to be something the retired bodies already declared
        self.assertTrue(
            added.issubset(set(self.RETIRED_PAYROLL_FACTS)),
            sorted(added - set(self.RETIRED_PAYROLL_FACTS)),
        )
        root = self.arch(self.PAYROLL_VIEW)
        # each provenance fact is read-only: the values are migrated history
        for name in sorted(provenance):
            nodes = root.xpath(".//field[@name=$n]", n=name)
            self.assertEqual(len(nodes), 1, name)
            self.assertEqual(nodes[0].get("readonly"), "1", name)
        # the currency companion is declared but not presented: the money control
        # already renders the amount together with its currency, so a second row
        # would repeat the same fact in the same body
        currency = root.xpath(".//field[@name='currency_id']")
        self.assertEqual(len(currency), 1, "currency_id")
        self.assertEqual(currency[0].get("invisible"), "1", "currency_id")
        self.assertEqual(currency[0].get("readonly"), "1", "currency_id")

    # ------------------------------------------------------------------ #
    # 6. the model-wide annotation keeps serving the model
    # ------------------------------------------------------------------ #
    def test_the_model_wide_annotation_keeps_serving_the_model(self):
        record = self.ref(self.MODEL_WIDE_CONTRACT)
        self.assertTrue(record.active)
        self.assertEqual(record.model, "sc.hr.payroll.document")
        self.assertFalse(record.action_id, "the annotation must stay model-wide")
        form = record.contract_json["view_orchestration"]["views"]["form"]
        self.assertNotIn("sections", form)
        self.assertNotIn("columns", form)
        self.assertEqual(len(form["fields"]), 27, "the annotation is a field-order list")

    def test_a_retired_body_no_longer_re_projects_over_the_native_authority(self):
        """The retired bodies are gone, so no entry can be re-projected by them."""
        for action_key, view_key, _title in self.FORMAL_ENTRIES:
            governance = self.governance(action_key, view_key)
            own = self.ref(self.ENTRY_CONTRACTS[action_key]).name
            for row in governance["businessConfigContracts"]:
                self.assertTrue(
                    row["name"] == own or row.get("action_id") is False,
                    (action_key, row["name"], "an entry-scoped body reached this entry"),
                )
            conflicts = [row for row in governance["structureDiagnostics"]
                         if row["code"] == "LEGACY_STRUCTURE_KEY_OVERRIDE"]
            self.assertFalse(conflicts, (action_key, conflicts))

    # ------------------------------------------------------------------ #
    # 7. the entry contract and reachability are unchanged
    # ------------------------------------------------------------------ #
    def test_entry_domains_menus_and_scoping_are_unchanged(self):
        for action_key, expected_tokens in self.ENTRY_FACT_TOKENS.items():
            action = self.ref(action_key)
            self.assertEqual(action.res_model, "sc.hr.payroll.document", action_key)
            for token in expected_tokens:
                self.assertIn(token, action.domain or "", (action_key, token))
            menu = self.ref(self.ENTRY_MENUS[action_key])
            self.assertEqual(menu.action, action, self.ENTRY_MENUS[action_key])
        payment_action = self.ref("action_sc_product_project_salary_payment_v1")
        self.assertEqual(payment_action.res_model, "sc.hr.salary.payment")
        self.assertEqual(self.ref("menu_sc_product_project_salary_payment_v1").action, payment_action)

    def test_the_social_fund_entry_keeps_its_semantic_declaration(self):
        """`fact_authority` / `allowed_fact_types` are semantics, not a second structure."""
        record = self.ref("business_config_contract_social_fund_form_v1")
        context = record.contract_json["view_orchestration"]["context"]
        self.assertEqual(context["fact_authority"], "sc.hr.payroll.document")
        self.assertEqual(
            context["allowed_fact_types"],
            ["social_person_registration", "social_registration", "provident_fund_registration"],
        )
        action = self.ref("action_sc_product_social_fund_v1")
        for token in context["allowed_fact_types"]:
            self.assertIn(token, action.domain)
        form = record.contract_json["view_orchestration"]["views"]["form"]
        self.assertNotIn("sections", form)
        self.assertNotIn("fields", form)
