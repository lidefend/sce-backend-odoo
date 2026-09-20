# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.form_structure_authority import (
    diagnose_structure_ownership,
    resolve_form_structure_governance,
    structural_form_declarations,
)


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class TestEngineeringProcessNativeLowcode(TransactionCase):
    """U-C4 G10: 工程过程与资料整组原生结构迁移.

    Five P1 native forms carry this group and nothing else:

      682 安全检查 / menu 526 / action `action_sc_safety_issue`
        -> `sc.safety.issue` / `view_sc_safety_issue_form`
      867 质量验收 / menu 686 / action `action_sc_product_quality_acceptance_v1`
        -> `sc.quality.acceptance` / `view_sc_quality_acceptance_form`
      729 施工日志 / menu 426 / action `action_sc_construction_diary`
        -> `sc.construction.diary` / `view_sc_construction_diary_form`
      597 工程资料 / menu 412 / action `action_sc_project_document`
        -> `sc.project.document` / `view_sc_project_document_form`
      527 进度计量 / menu 520 / action `action_project_progress_entry`
        -> `project.progress.entry` / `view_project_progress_entry_form`

    The group reaches the compatibility floorplan two different ways, and the
    batch closes both:

      * 682 / 867 / 729 carried an entry-level `entry_semantic_surface` body
        (sections + fields + columns) that duplicated the groups and notebook
        pages their own native forms already declare.  Those bodies are retired:
        each entry keeps only `title` + `composition_mode:
        native_semantic_surface`, and the native arch owns the structure.
      * 597 / 527 had NO entry release at all.  They consumed only the
        model-wide generated mirror (104 at priority 142, 45 at priority 76), so
        `form_structure_authority` stayed `""` and `ui_contract_v2` ran the
        generic governance projection.  This batch publishes the same native
        shape on those two actions at priority 800.

    In both cases the entry declaration becomes the LAST structure writer for
    its own action, so `form_structure_authority` resolves to
    `native_authority` and `layoutPolicy` resolves to
    `container_tree_authority`: the compatibility regrouping path stops
    applying.

    The regression rule this batch must not break: a model-wide carrier may only
    be retired when it is not the last remaining structure writer for any OTHER
    action on the same model.  Measured A/B (read-only, `sc_dev_demo`) rejected
    the first plan of retiring the diary mirror 61: 730/731/732
    (日报表/周报表/月报表) render the same diary form but keep consuming mirrors
    61 / 148, and retiring 61 shrank their rendered facts from 23 to 14.  Mirrors
    45 / 61 / 104 / 115 and policies 25 / 148 therefore stay active, and this
    batch retires only its own entries' bodies.

    The batch is presentation-neutral: the native arch is the ground truth and
    `RENDERED_FIELDS` pins it, so a retired declaration cannot silently drop a
    fact.
    """

    # entry contract xmlid -> (action xmlid, model, view xmlid, title, kind)
    # kind: "body_retired" keeps the release and drops its structural body;
    #       "release_added" publishes a release where the entry had none.
    ENTRIES = {
        "business_config_contract_sc_safety_issue_handling_form_v1": (
            "action_sc_safety_issue", "sc.safety.issue",
            "view_sc_safety_issue_form", "安全问题办理", "body_retired"),
        "business_config_contract_sc_quality_acceptance_handling_form_v1": (
            "action_sc_product_quality_acceptance_v1", "sc.quality.acceptance",
            "view_sc_quality_acceptance_form", "质量验收办理", "body_retired"),
        "business_config_contract_construction_diary_productized_form_v1": (
            "action_sc_construction_diary", "sc.construction.diary",
            "view_sc_construction_diary_form", "施工日志", "body_retired"),
        "business_config_contract_sc_project_document_productized_form_v1": (
            "action_sc_project_document", "sc.project.document",
            "view_sc_project_document_form", "工程资料", "release_added"),
        "business_config_contract_project_progress_entry_productized_form_v1": (
            "action_project_progress_entry", "project.progress.entry",
            "view_project_progress_entry_form", "进度计量", "release_added"),
    }

    # Deliberate release priorities.  Every entry release must outrank the
    # model-wide carriers still active on its own model; the highest of those is
    # the safety mirror 115 at 154.
    ENTRY_PRIORITIES = {
        "sc_safety_issue_handling_form_v1": 900,
        "sc_quality_acceptance_handling_form_v1": 900,
        "construction_diary_productized_form_v1": 800,
        "sc_project_document_productized_form_v1": 800,
        "project_progress_entry_productized_form_v1": 800,
    }

    # Model-wide carriers retained on purpose.  Each one is still the structure
    # plane of actions that this batch must not touch, so retiring it belongs to
    # another group (see 8.36 G10 A/B in the iteration record).
    # xmlid -> (model, the sibling actions that keep depending on it)
    RETAINED_MODEL_WIDE_CARRIERS = {
        "business_config_contract_sc_safety_issue_form_structure_generated": (
            "sc.safety.issue", ()),
        "business_config_contract_sc_project_document_form_structure_generated": (
            "sc.project.document", (
                "action_sc_project_document_safety",
                "action_sc_project_document_quality",
                "action_sc_project_document_self_inspection",
                "action_sc_project_document_archive",
            )),
        "business_config_contract_sc_construction_diary_form_structure_generated": (
            "sc.construction.diary", (
                "action_sc_construction_daily_report",
                "action_sc_construction_weekly_report",
                "action_sc_construction_monthly_report",
            )),
        "business_config_contract_project_progress_entry_form_structure_generated": (
            "project.progress.entry", ("action_project_progress_quick",)),
    }

    # The diary shape is split across a sparse field mirror and a policy carrier;
    # both stay active for the same reason and neither is an entry release.
    RETAINED_DIARY_AUXILIARY_CARRIERS = {
        "business_config_contract_sc_construction_diary_form_p1_fields_v1": "sc.construction.diary",
        "business_config_contract_sc_construction_diary_p1_form_business_facts_v1": "sc.construction.diary",
    }

    # Facts declared by the retired entry bodies.  No name may be missing from
    # the model, and every fact must still be reachable from the native arch -
    # which is exactly what makes the retirement presentation-neutral.
    RETIRED_ENTRY_FACTS = {
        "sc.safety.issue": (
            "state", "name", "project_id", "issue_category", "issue_level", "issue_date",
            "location", "coordinate", "responsible_party_id", "owner_id", "rechecker_id",
            "cc_user_ids", "rectification_deadline", "reminder_before_days", "closed_date",
            "overdue_days", "is_overdue", "description", "voice_text", "attachment_ids",
            "photo_batch_ids", "hazard_source_id",
        ),
        "sc.quality.acceptance": (
            "state", "project_id", "name", "acceptance_type", "acceptance_date", "location",
            "responsible_id", "participant_ids", "result", "rectification_deadline",
            "standard", "conclusion", "issue_ids", "attachment_ids", "processing_advisory",
        ),
        "sc.construction.diary": (
            "state", "source_origin", "name", "project_id", "date_diary", "title",
            "diary_type", "category", "report_period_start", "report_period_end",
            "document_no", "handler_name", "construction_unit", "project_manager",
            "weather", "manpower_count", "attendance_equipment", "quality_name",
            "description", "material_inspection_note", "design_change_note",
            "test_block_note", "safety_note", "hidden_acceptance_note", "next_plan",
            "header_description", "note", "attachment_ids", "active",
        ),
    }

    # Retired facts the native arch deliberately does not render.  The diary
    # entry body carried the provenance marker `source_origin`
    # (`default="manual"`, string 来源) which records whether a row came from the
    # legacy migration; it is never user-entered, and no native form shows it
    # (same class as G09 dropping `legacy_fact_*` off the labor-usage surface).
    NOT_RENDERED_PROVENANCE_FACTS = {
        "sc.construction.diary": ("source_origin",),
    }

    # Business field set the native arch renders for each form, in document
    # order.  Pinned so the batch is provably presentation-neutral.
    RENDERED_FIELDS = {
        "view_sc_safety_issue_form": (
            "state", "name", "project_id", "issue_category", "source_channel",
            "issue_level", "issue_date", "location", "coordinate",
            "responsible_party_id", "owner_id", "rechecker_id", "cc_user_ids",
            "rectification_deadline", "reminder_before_days", "closed_date",
            "overdue_days", "is_overdue", "description", "voice_text",
            "attachment_ids", "photo_batch_ids", "hazard_source_id",
        ),
        "view_sc_quality_acceptance_form": (
            "state", "project_id", "name", "acceptance_type", "acceptance_date",
            "location", "responsible_id", "participant_ids", "result",
            "rectification_deadline", "standard", "conclusion", "issue_ids",
            "attachment_ids", "processing_advisory",
        ),
        "view_sc_construction_diary_form": (
            "state", "name", "date_diary", "report_period_start", "report_period_end",
            "document_no", "title", "project_id", "diary_type", "category",
            "handler_name", "construction_unit", "project_manager", "weather",
            "manpower_count", "attendance_equipment", "quality_name", "description",
            "material_inspection_note", "design_change_note", "test_block_note",
            "safety_note", "hidden_acceptance_note", "next_plan",
            "header_description", "note", "attachment_ids", "active",
        ),
        "view_sc_project_document_form": (
            "state", "name", "document_kind", "project_id", "wbs_id", "task_id",
            "contract_id", "doc_type_id", "doc_subtype_id", "is_mandatory",
            "date_doc", "version", "responsible_id", "attachment_count",
            "company_id", "note", "attachment_ids",
        ),
        "view_project_progress_entry_form": (
            "state", "project_id", "wbs_id", "date", "qty_done", "qty_cum",
            "progress_rate", "note", "attachment_ids",
        ),
    }

    # The anchored native business sections this batch declares.  Notebook
    # descendants are excluded by the helper, and the trailing 依据类事实 group
    # (备注/附件) plus the computed 办理提示/录入口径 groups deliberately carry
    # no anchor because they are not editable business sections.
    NATIVE_SECTIONS = {
        "view_sc_safety_issue_form": (
            ("safety_issue_identification", "问题识别"),
            ("safety_issue_location_responsibility", "位置与责任"),
        ),
        "view_sc_quality_acceptance_form": (
            ("quality_acceptance_object", "验收对象"),
            ("quality_acceptance_responsibility_result", "责任与结果"),
            ("quality_acceptance_basis_opinion", "验收依据与意见"),
            ("quality_acceptance_issue_attachment", "问题与资料"),
        ),
        "view_sc_construction_diary_form": (
            ("construction_diary_log_main", "日志主信息"),
            ("construction_diary_period_handler", "期间与经办"),
            ("construction_diary_site_information", "现场信息"),
            ("construction_diary_log_content", "日志内容"),
        ),
        "view_sc_project_document_form": (
            ("project_document_main", "资料主信息"),
            ("project_document_classification", "业务分类"),
            ("project_document_responsibility", "责任与归档"),
        ),
        "view_project_progress_entry_form": (
            ("project_progress_entry_object", "计量对象"),
            ("project_progress_entry_measure", "计量数据"),
            ("project_progress_entry_note_attachment", "备注与附件"),
        ),
    }

    # -- helpers -------------------------------------------------------------

    def _contract(self, xmlid):
        return self.env["ui.business.config.contract"].sudo().browse(
            self.ref("smart_construction_core.%s" % xmlid)
        )

    def _entry_contracts(self, model, action_xmlid, view_xmlid):
        """Resolve the contracts the runtime would use for this exact entry.

        Two of the G10 entries are view-scoped, so the form view must be part of
        the request: resolving with `view_id=0` would drop them and answer with
        an empty plane instead of the entry's own release.
        """
        return self.env["ui.business.config.contract"].sudo()._effective_view_orchestration_contracts(
            model,
            view_type="form",
            action_id=self.ref("smart_construction_core.%s" % action_xmlid),
            view_id=self.env.ref("smart_construction_core.%s" % view_xmlid).id,
            role_key="",
        )

    def _form_spec(self, record):
        return (
            ((record.contract_json or {}).get("view_orchestration") or {})
            .get("views", {})
            .get("form", {})
        )

    def _arch(self, view_xmlid):
        view = self.env.ref("smart_construction_core.%s" % view_xmlid)
        return etree.fromstring(view.arch.encode("utf-8"))

    def _arch_fields(self, view_xmlid):
        arch = self._arch(view_xmlid)
        seen, ordered = set(), []
        for node in arch.iter("field"):
            name = node.get("name")
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def _arch_sections(self, view_xmlid):
        """Anchored native business groups, excluding notebook descendants."""
        arch = self._arch(view_xmlid)
        sections = []
        for notebook in arch.iter("notebook"):
            notebook.getparent().remove(notebook)
        for group in arch.iter("group"):
            anchor = group.get("data-sc-anchor")
            if anchor:
                sections.append((anchor, group.get("string")))
        return tuple(sections)

    def _arch_field_owners(self, nodes, model, out):
        """Resolve every `<field>` against the model that actually owns it."""
        for node in nodes:
            if node.tag == "field":
                name = node.get("name")
                if name:
                    out.append((model, name))
                containers = [child for child in node if child.tag in ("tree", "form", "kanban")]
                if containers:
                    field = self.env[model]._fields.get(name) if model in self.env else None
                    relation = getattr(field, "relation", None)
                    if relation:
                        for container in containers:
                            self._arch_field_owners(list(container), relation, out)
            else:
                self._arch_field_owners(list(node), model, out)
        return out

    # -- declaration surface -------------------------------------------------

    def test_every_entry_declares_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, _view, title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertEqual(record.model, model)
                self.assertEqual(
                    record.action_id.id,
                    self.ref("smart_construction_core.%s" % action_xmlid),
                )
                spec = self._form_spec(record)
                self.assertEqual(spec.get("composition_mode"), "native_semantic_surface")
                self.assertEqual(spec.get("title"), title)
                # A native declaration may not carry a competing structure.
                self.assertEqual(structural_form_declarations(spec), {})
                self.assertEqual(record.priority, self.ENTRY_PRIORITIES[record.name])

    def test_the_entry_semantics_are_preserved_verbatim(self):
        """The release context stays the entry's semantic declaration."""
        for contract_xmlid in self.ENTRIES:
            with self.subTest(contract=contract_xmlid):
                context = (
                    (self._contract(contract_xmlid).contract_json or {})
                    .get("view_orchestration", {})
                    .get("context", {})
                )
                self.assertEqual(context.get("source"), "smart_construction_core.product_release")
                self.assertEqual(context.get("source_status"), "product_release")

    def test_the_retired_bodies_are_the_only_structural_bodies_removed(self):
        """`body_retired` keeps no structure; `release_added` never had one."""
        for contract_xmlid, (_action, _model, _view, _title, kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                self.assertIn(kind, {"body_retired", "release_added"})
                spec = self._form_spec(self._contract(contract_xmlid))
                for key in ("sections", "fields", "columns", "layout"):
                    self.assertNotIn(key, spec)

    # -- resolution surface --------------------------------------------------

    def test_every_entry_resolves_the_native_semantic_surface(self):
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                native = [
                    config for config in configs
                    if (self._form_spec(config) or {}).get("composition_mode")
                    in {"native_semantic_surface", "semantic_native_surface"}
                ]
                self.assertEqual(
                    [config.name for config in native],
                    [self._contract(contract_xmlid).name],
                )

    def test_every_entry_resolves_native_authority(self):
        """The entry declaration must be the last structure writer for its action.

        This is the assertion that closes the compatibility path: while a
        model-wide carrier still declares `entry_semantic_surface`, a native
        declaration that sorted before it would leave the resolved authority
        pointing back at the legacy plane and `layoutPolicy` back at the
        compatibility floorplan.
        """
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                resolved = resolve_form_structure_governance({}, configs, view_type="form")
                self.assertEqual(resolved.get("form_structure_authority"), "native_authority")
                self.assertEqual(resolved.get("form_presentation_mode"), "task")

    def test_the_entry_release_outranks_every_model_wide_carrier(self):
        """The entry priority is the whole mechanism, so it is pinned."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                entry = self._contract(contract_xmlid)
                others = [
                    config for config in self._entry_contracts(model, action_xmlid, view_xmlid)
                    if config.name != entry.name
                ]
                self.assertGreater(
                    entry.priority,
                    max((config.priority for config in others), default=0),
                    "the entry release must sort after every carrier it competes with",
                )

    def test_the_retained_carriers_are_reported_as_suppressed_not_rejected(self):
        """An unscoped legacy declaration degrades; it never blocks the native owner."""
        for contract_xmlid, (action_xmlid, model, view_xmlid, _title, _kind) in self.ENTRIES.items():
            with self.subTest(contract=contract_xmlid):
                configs = self._entry_contracts(model, action_xmlid, view_xmlid)
                diagnostics = diagnose_structure_ownership(
                    configs,
                    model=model,
                    action_id=self.ref("smart_construction_core.%s" % action_xmlid),
                )
                codes = {row["code"] for row in diagnostics}
                self.assertNotIn("NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT", codes)
                for row in diagnostics:
                    self.assertFalse(
                        row["explicit_structure_scope"],
                        "a scoped competing declaration must never survive the native owner",
                    )

    def test_a_scoped_competing_declaration_is_refused(self):
        """Negative control: the mechanism still fails closed on a scoped conflict."""
        model = "sc.construction.diary"

        class _Config:
            def __init__(self, name, contract_json, action_id, view_id=0):
                self.id = 0
                self.name = name
                self.priority = 50
                self.view_type = "form"
                self.contract_json = contract_json
                self.action_id = action_id
                self.view_id = view_id

        native = _Config("native", {"view_orchestration": {"views": {"form": {
            "title": "施工日志", "composition_mode": "native_semantic_surface"}}}}, 999)
        competitor = _Config("competitor", {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "sections": [{"title": "旧章节"}]}}}}, 999)
        with self.assertRaises(ValueError):
            diagnose_structure_ownership([native, competitor], model=model, action_id=999)

    # -- retention surface ---------------------------------------------------

    def test_the_model_wide_carriers_stay_active_for_their_sibling_actions(self):
        """The regression rule: a shared mirror is never retired by this group.

        Each retained carrier is the last structure writer for at least one
        action that renders the same native form without being a counted entry
        (730/731/732, 598-601, 586).  Retiring them here would shrink those
        sibling surfaces, so they stay active and stay unscoped.
        """
        for contract_xmlid, (model, sibling_actions) in self.RETAINED_MODEL_WIDE_CARRIERS.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertFalse(record.action_id)
                self.assertFalse(record.view_id)
                self.assertEqual(record.model, model)
                for action_xmlid in sibling_actions:
                    action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                    self.assertEqual(action.res_model, model)

    def test_the_diary_auxiliary_carriers_are_retained(self):
        for contract_xmlid, model in self.RETAINED_DIARY_AUXILIARY_CARRIERS.items():
            with self.subTest(contract=contract_xmlid):
                record = self._contract(contract_xmlid)
                self.assertTrue(record.active)
                self.assertFalse(record.action_id)
                self.assertFalse(record.view_id)
                self.assertEqual(record.model, model)

    def test_the_sibling_actions_still_exist_and_reach_their_own_form(self):
        for _contract_xmlid, (model, sibling_actions) in self.RETAINED_MODEL_WIDE_CARRIERS.items():
            for action_xmlid in sibling_actions:
                with self.subTest(action=action_xmlid):
                    action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                    self.assertEqual(action.res_model, model)
                    self.assertIn("form", action.view_mode or "")

    # -- native arch ---------------------------------------------------------

    def test_the_native_arch_declares_every_business_section_identity(self):
        for view_xmlid, expected in self.NATIVE_SECTIONS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_sections(view_xmlid), expected)

    def test_the_native_arch_is_presentation_neutral(self):
        """The batch retires declarations; it must not add or drop a rendered fact."""
        for view_xmlid, expected in self.RENDERED_FIELDS.items():
            with self.subTest(view=view_xmlid):
                self.assertEqual(self._arch_fields(view_xmlid), expected)

    def test_every_retired_fact_is_still_reachable_from_the_native_arch(self):
        """Every retired business fact stays on the surface, one way or the other.

        A fact a retired body declared must either be rendered by the native arch
        that now owns the structure, or be registered below as a provenance
        marker the native surface never showed.  Nothing may vanish silently.
        """
        view_by_model = {
            model: view_xmlid
            for _contract_xmlid, (_action, model, view_xmlid, _title, kind) in self.ENTRIES.items()
            if kind == "body_retired"
        }
        for model, names in self.RETIRED_ENTRY_FACTS.items():
            with self.subTest(model=model):
                rendered = set(self._arch_fields(view_by_model[model]))
                accounted = rendered | set(self.NOT_RENDERED_PROVENANCE_FACTS.get(model, ()))
                self.assertEqual(
                    sorted(name for name in names if name not in accounted),
                    [],
                    "a retired declaration may not hold a fact nobody accounts for",
                )
                self.assertEqual(
                    sorted(rendered & set(self.NOT_RENDERED_PROVENANCE_FACTS.get(model, ()))),
                    [],
                    "a registered provenance marker must really be off the surface",
                )

    def test_no_retired_declaration_referenced_a_missing_fact(self):
        for model, names in self.RETIRED_ENTRY_FACTS.items():
            fields = set(self.env[model]._fields)
            with self.subTest(model=model):
                self.assertEqual(sorted(set(names) - fields), [])

    def test_every_rendered_fact_belongs_to_its_own_model(self):
        mapping = {
            view_xmlid: model
            for _contract_xmlid, (_action, model, view_xmlid, _title, _kind) in self.ENTRIES.items()
        }
        for view_xmlid, model in mapping.items():
            owners = self._arch_field_owners(list(self._arch(view_xmlid)), model, [])
            unknown = sorted({
                "%s.%s" % (owner, name)
                for owner, name in owners
                if owner not in self.env or name not in self.env[owner]._fields
            })
            with self.subTest(view=view_xmlid):
                self.assertEqual(unknown, [])

    def test_the_native_arch_keeps_no_empty_business_page(self):
        """Same rule as G09: an empty 来源追溯 page holds no fact, so it goes."""
        for view_xmlid in {entry[2] for entry in self.ENTRIES.values()}:
            arch = self._arch(view_xmlid)
            empty = []
            for page in arch.iter("page"):
                if not page.xpath(".//field"):
                    empty.append(page.get("string"))
            with self.subTest(view=view_xmlid):
                self.assertEqual(empty, [])
