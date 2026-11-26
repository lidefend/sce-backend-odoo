import os
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.delivery.runtime_route_authority import (
    menu_publication_decision, published_route_authority,
)


from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService

from ..tools.frontend_productization_fixture import (
    FIXTURE_SCOPE_ENV,
    ensure_fixture,
)


def publish_scenarios(env):
    params = env["ir.config_parameter"].sudo()
    params.set_param("smart_core.platform_release_db", env.cr.dbname)
    params.set_param("smart_core.release_operator.catalog_source_db", env.cr.dbname)
    # The catalog reads both editions. Isolate historical carrier releases
    # inside the caller's rollback transaction, then produce a real snapshot.
    Snapshot = env["sc.edition.release.snapshot"].sudo()
    Snapshot.search([
        ("product_key", "in", ["construction.standard", "construction.preview"]),
        ("is_active", "=", True),
    ]).write({"is_active": False})
    result = EditionReleaseSnapshotService(env).freeze_release_surface(
        product_key="construction.standard",
        version="acceptance-maintained-scenarios",
        replace_active=True,
    )
    snapshot = Snapshot.browse(result["id"])
    assert snapshot.is_active and snapshot.state == "released", "test publication must be active and released"
    assert not Snapshot.search_count([
        ("product_key", "=", "construction.preview"), ("is_active", "=", True),
    ]), "historical preview must not enter this standard-edition fixture"
    return result


def ensure_acceptance_fixture_for_local_test(env):
    if env.ref(
        "smart_construction_acceptance_fixture.fe_user_finance",
        raise_if_not_found=False,
    ):
        return
    expected_database = os.environ.get("SC_TEST_DB_NAME", "")
    if not expected_database or env.cr.dbname != expected_database:
        raise RuntimeError(
            "local fixture seeding is restricted to the current isolated test attempt"
        )
    snapshot = env["sc.edition.release.snapshot"].sudo().search([
        ("product_key", "=", "construction.standard"),
        ("state", "=", "released"),
        ("is_active", "=", True),
        ("active", "=", True),
    ], limit=1)
    if not snapshot:
        publish_scenarios(env)
    with patch.dict(os.environ, {
        FIXTURE_SCOPE_ENV: "local_test",
        "SC_ENVIRONMENT": "dev",
        "SC_ALLOW_DEMO_DATA": "1",
        "SC_ACCEPTANCE_FIXTURE_PASSWORD": "local-test-fixture-password",
    }):
        ensure_fixture(env)


@tagged("post_install", "-at_install", "acceptance_business_scene_lifecycle")
class TestBusinessSceneLifecycle(TransactionCase):
    """Native company/permission behavior; TransactionCase rolls back all toggles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_acceptance_fixture_for_local_test(cls.env)

    def setUp(self):
        super().setUp()
        self.finance = self.env.ref('smart_construction_acceptance_fixture.fe_user_finance')
        self.company_a = self.env.ref('smart_construction_acceptance_fixture.fe_company_a')
        self.company_b = self.env.ref('smart_construction_acceptance_fixture.fe_company_b')
        self.menu = self.env.ref('smart_construction_core.menu_sc_user_payment_apply')
        self.states = self.env['sc.scene.company.enablement'].sudo()
        # These cases verify company revocation against a released policy.
        # Build that prerequisite inside TransactionCase, independently of
        # maintained policy rows or an existing product release snapshot.
        policy = self.env['sc.product.policy'].sudo()
        policy.search([('product_key', 'in', [
            'construction.standard', 'construction.preview',
        ])]).unlink()
        policy.sync_construction_menu_product_policies()
        publish_scenarios(self.env)

    def _state(self, company):
        row = self.states.search([('company_id', '=', company.id),
                                  ('scene_key', '=', 'business.v1:finance.payment_approval')])
        self.assertEqual(len(row), 1, 'run the governed fixture before lifecycle acceptance')
        return row

    def _actor(self, company):
        return self.env(user=self.finance.id, context=dict(
            self.env.context, allowed_company_ids=[company.id]))

    def _allowed(self, company):
        authority = published_route_authority(self._actor(company))
        self.assertTrue(authority, 'authority construction must succeed')
        return menu_publication_decision(authority, self.menu.id, self.menu.action.id)

    def test_company_scene_selection_narrows_role_navigation_authority(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        a.set_enabled(True)
        b.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(False)
        self.assertFalse(self._allowed(self.company_a))
        self.assertTrue(self._allowed(self.company_b))
        a.set_enabled(True)
        self.assertTrue(self._allowed(self.company_a))

    def test_project_kanban_fixture_binding_is_released_for_all_business_roles(self):
        menu = self.env.ref("smart_construction_core.menu_sc_project_kanban")
        entry = self.env["sc.product.scenario.entry"].sudo().search(
            [("menu_id", "=", menu.id)],
            limit=1,
        )
        self.assertTrue(entry, "project Kanban must have an acceptance scenario binding")
        self.assertEqual(entry.scenario_id.code, "reporting.project_portfolio")

        for login in (
            "fixture_role_config_admin",
            "fixture_role_pm",
            "fixture_role_project_a_member",
        ):
            user = self.env["res.users"].sudo().search([("login", "=", login)], limit=1)
            self.assertTrue(user, login)
            actor = self.env(
                user=user.id,
                context=dict(
                    self.env.context,
                    allowed_company_ids=[self.company_a.id],
                    company_id=self.company_a.id,
                ),
            )
            authority = published_route_authority(actor)
            self.assertTrue(
                menu_publication_decision(authority, menu.id, menu.action.id),
                "%s must receive the released project Kanban route" % login,
            )
            self.assertTrue(
                actor["project.project"].check_access_rights("read", raise_exception=False),
                "%s must retain project read ACL" % login,
            )
            self.assertGreater(
                actor["project.project"].search_count([
                    ("company_id", "=", self.company_a.id),
                ]),
                0,
                "%s must receive the fixture company's project data" % login,
            )

    def test_payment_approval_fixture_assigns_a_real_current_reviewer(self):
        request = self.env.ref(
            "smart_construction_acceptance_fixture.fe_journey_payment_request_approval_a"
        )
        reviewer = self.env.ref(
            "smart_construction_acceptance_fixture.fe_user_finance_reviewer"
        )
        pending = request.review_ids.filtered(
            lambda review: review.status in ("waiting", "pending")
        )
        self.assertTrue(pending, "the approval fixture must contain a live review instance")
        self.assertIn(reviewer, pending.mapped("reviewer_ids"))
        self.assertTrue(
            request.with_user(reviewer).with_context(
                allowed_company_ids=[self.company_a.id],
                company_id=self.company_a.id,
            ).can_review,
            "the assigned finance reviewer must own the current approval step",
        )
        member = self.env.ref(
            "smart_construction_acceptance_fixture.fe_user_project_a_member"
        )
        self.assertFalse(request.with_user(member).can_review)

    def test_missing_business_scene_selection_denies_existing_native_route(self):
        self._state(self.company_a).unlink()
        self.assertFalse(self._allowed(self.company_a))
        self.states.create({'company_id': self.company_a.id,
                            'scene_key': 'finance.payment_requests', 'enabled': True})
        self.assertFalse(self._allowed(self.company_a))
        self.states.create({
            'company_id': self.company_a.id,
            'scene_key': 'business.v1:finance.payment_approval',
            'enabled': True,
        })
        self.assertTrue(self._allowed(self.company_a))

    def test_finance_cannot_enable_scenes_or_read_another_active_company(self):
        a, b = self._state(self.company_a), self._state(self.company_b)
        actor = self._actor(self.company_a)
        with self.assertRaises(AccessError), self.cr.savepoint():
            a.with_env(actor).set_enabled(not a.enabled)
        self.assertFalse(actor['sc.scene.company.enablement'].search([('id', '=', b.id)]))

    def test_fixture_scenario_choices_match_current_product_identity(self):
        from odoo.addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (
            FIXTURE_BUSINESS_SCENARIOS,
        )
        current = set(self.env["sc.product.scenario"].sudo().with_context(
            active_test=False
        ).search([]).mapped("code"))
        self.assertEqual(set(FIXTURE_BUSINESS_SCENARIOS), current)

    def test_maintained_membership_drives_scenario_catalog_without_seed_file(self):
        from unittest.mock import patch
        from odoo.addons.smart_construction_core.services import scenario_surface_projection
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import write_tenant_enablement
        from odoo.addons.smart_construction_scene.handlers.scenario_activation import _catalog
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        self.assertEqual(len(entry), 1)
        replacement = self.env['sc.product.scenario'].sudo().create({
            'code': 'test.maintained.payment', 'name': 'Maintained payment',
        })
        entry.scenario_id = replacement
        publish_scenarios(self.env)
        with patch.object(scenario_surface_projection, 'load_surface', side_effect=AssertionError('runtime read seed')):
            write_tenant_enablement(self.env, self.company_a.id, 'business.v1:test.maintained.payment', True)
            self.assertTrue(self._allowed(self.company_a))
            self.assertFalse(self._allowed(self.company_b))
            write_tenant_enablement(self.env, self.company_b.id, 'business.v1:test.maintained.payment', True)
            self.assertTrue(self._allowed(self.company_b))
            replacement.name = 'Renamed payment'
            publish_scenarios(self.env)
            rows = _catalog(self.env, self.company_a.id)['business_scenarios']
            row = next(row for row in rows if row['scene_key'] == replacement.code)
            self.assertEqual(row['name'], 'Renamed payment')
            self.assertTrue(row['tenant_enabled'])
            replacement.active = False
            with self.assertRaisesRegex(
                ValueError,
                "RELEASE_PREFLIGHT_BLOCKED:business_scene_composition"
                "\\[BUSINESS_SCENE_PAGE_UNASSIGNED",
            ):
                publish_scenarios(self.env)
            replacement.active = True
            publish_scenarios(self.env)
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == replacement.code)
            self.assertTrue(row['tenant_enabled'])
            entry.unlink()
            with self.assertRaisesRegex(
                ValueError,
                "RELEASE_PREFLIGHT_BLOCKED:business_scene_composition"
                "\\[BUSINESS_SCENE_PAGE_UNASSIGNED",
            ):
                publish_scenarios(self.env)
        self.menu.sc_scenario_exempt = True

    def test_binding_clears_old_exemption_and_identity_cannot_be_renamed(self):
        from odoo.exceptions import ValidationError
        for code in (' test.ambiguous ', '   '):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.env['sc.product.scenario'].sudo().create({'code': code, 'name': 'Invalid identity'})
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        scenario = entry.scenario_id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            scenario.code = 'test.reassigned.identity'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.menu.sc_scenario_exempt = True
        entry.unlink()
        self.menu.sc_scenario_exempt = True
        rebound = self.env['sc.product.scenario.entry'].sudo().create({
            'menu_id': self.menu.id, 'scenario_id': scenario.id,
        })
        self.assertFalse(self.menu.sc_scenario_exempt)
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            write_tenant_enablement,
        )
        write_tenant_enablement(
            self.env,
            self.company_a.id,
            'business.v1:' + scenario.code,
            True,
        )
        self.assertTrue(self._allowed(self.company_a))
        rebound.unlink()
        with self.assertRaisesRegex(
            ValueError,
            "RELEASE_PREFLIGHT_BLOCKED:business_scene_composition"
                "\\[BUSINESS_SCENE_PAGE_UNASSIGNED",
        ):
            publish_scenarios(self.env)
            self.menu.sc_scenario_exempt = True

    def test_exemption_migration_does_not_revive_deleted_business_binding(self):
        scenario = self.env['sc.product.scenario'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        marker = 'smart_construction_core.scenario_entry_scope.v1'
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        entry.unlink()
        direct = self.env['ir.ui.menu'].sudo().create({
            'name': 'Explicit direct test entry', 'sc_scenario_exempt': True, 'action': 'ir.actions.act_window,%s' % self.menu.action.id,
        })
        params.set_param(marker, False)
        scenario.initialize_direct_entry_exemptions()
        self.assertTrue(direct.sc_scenario_exempt)
        self.assertFalse(self.menu.sc_scenario_exempt)
        direct.sc_scenario_exempt = False
        scenario.initialize_direct_entry_exemptions()
        self.assertFalse(direct.sc_scenario_exempt)

    def test_custom_binding_deleted_before_upgrade_stays_unconfigured(self):
        Scenario = self.env['sc.product.scenario'].sudo()
        Entry = self.env['sc.product.scenario.entry'].sudo()
        Menu = self.env['ir.ui.menu'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        marker = 'smart_construction_core.scenario_entry_scope.v1'
        custom = Scenario.create({'code': 'test.custom.deleted', 'name': 'Custom'})
        action = 'ir.actions.act_window,%s' % self.menu.action.id
        for vals in ({'name': 'Custom action', 'action': action},
                     {'name': 'Custom actionless leaf'}):
            menu = Menu.create(vals)
            # Previously explicit direct entries also lose their exemption
            # when bound. Deletion must not resurrect the prior declaration.
            menu.sc_scenario_exempt = True
            entry = Entry.create({'scenario_id': custom.id, 'menu_id': menu.id})
            self.assertFalse(menu.sc_scenario_exempt)
            entry.unlink()
            publish_scenarios(self.env)
            params.set_param(marker, False)
            Scenario.initialize_direct_entry_exemptions()
            self.assertFalse(menu.sc_scenario_exempt)
            self.assertTrue(params.get_param(marker))
            Scenario.initialize_direct_entry_exemptions()
            self.assertFalse(menu.sc_scenario_exempt)
        unknown = Menu.create({'name': 'Unknown history', 'action': action})
        params.set_param(marker, False)
        Scenario.initialize_direct_entry_exemptions()
        self.assertFalse(unknown.sc_scenario_exempt)
        # Missing history can only be resolved by an explicit maintenance act.
        unknown.sc_scenario_exempt = True
        Scenario.initialize_direct_entry_exemptions()
        self.assertTrue(unknown.sc_scenario_exempt)

    def test_business_diagnosis_consumes_same_catalog_without_composition_record(self):
        from odoo.addons.smart_construction_scene.handlers.scenario_activation import _catalog
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        entry = self.env['sc.product.scenario.entry'].sudo().search([('menu_id', '=', self.menu.id)])
        scenario = entry.scenario_id
        for active in (True, False):
            scenario.active = active
            if active:
                publish_scenarios(self.env)
            else:
                with self.assertRaisesRegex(
                    ValueError,
                    "RELEASE_PREFLIGHT_BLOCKED:business_scene_composition"
                    "\\[BUSINESS_SCENE_PAGE_UNASSIGNED\\]",
                ):
                    publish_scenarios(self.env)
                scenario.active = True
                publish_scenarios(self.env)
            row = next(row for row in _catalog(self.env, self.company_a.id)['business_scenarios']
                       if row['scene_key'] == scenario.code)
            diagnosis = diagnose_scenario_dependencies(self.env,
                scene_key='business.v1:' + scenario.code, company_id=self.company_a.id)
            self.assertEqual(diagnosis['enable_allowed'], row['product_released'])
            self.assertFalse(diagnosis['publication']['scene_composition']['applicable'])

    def test_native_entry_does_not_require_composition_release(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'enterprise.setup')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'enterprise.setup', 'name': 'Native entry diagnosis test'})
        scene.state = 'draft'
        diagnosis = diagnose_scenario_dependencies(self.env, scene_key='enterprise.setup', company_id=self.company_a.id)
        self.assertEqual(diagnosis['dependencies'][0]['evidence']['readiness_kind'], 'native_action', diagnosis)
        self.assertTrue(diagnosis['dependencies'][0]['evidence']['structure_ready'])
        self.assertEqual(diagnosis['enable_allowed'], diagnosis['publication']['native_capability']['entry_qualified'])
        self.assertFalse(diagnosis['publication']['scene_composition']['applicable'])
        menu = self.env.ref('smart_construction_core.menu_sc_enterprise_initialization')
        menu.action = False
        invalid = diagnose_scenario_dependencies(self.env, scene_key='enterprise.setup', company_id=self.company_a.id)
        self.assertFalse(invalid['dependencies'][0]['evidence']['structure_ready'])
        self.assertFalse(invalid['enable_allowed'])

    def test_composition_has_its_own_version_and_edition_release(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'projects.detail')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'projects.detail', 'name': 'Composition diagnosis test'})
        version = self.env['sc.scene.version'].sudo().create({
            'scene_id': scene.id, 'version': 'test-diagnosis', 'payload_json': {'scene_key': scene.code},
            'product_release_state': 'PREVIEW', 'product_edition': 'construction.standard',
        })
        scene.write({'state': 'published', 'active_version_id': version.id})
        def diagnose():
            return diagnose_scenario_dependencies(self.env, scene_key=scene.code, company_id=self.company_a.id)
        result = diagnose()
        self.assertTrue(result['publication']['native_capability']['entry_qualified'])
        self.assertTrue(result['publication']['scene_composition']['snapshot_published'])
        self.assertFalse(result['enable_allowed'])
        version.product_release_state = 'STANDARD_RELEASE'
        self.assertTrue(diagnose()['enable_allowed'])
        version.product_edition = 'construction.preview'
        self.assertFalse(diagnose()['enable_allowed'])
        version.product_edition = 'construction.standard'
        other = Scene.create({'code': 'test.other.composition', 'name': 'Other composition'})
        version.scene_id = other
        self.assertFalse(diagnose()['enable_allowed'])

    def test_direct_handoff_does_not_erase_published_composition_content(self):
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import diagnose_scenario_dependencies
        Scene = self.env['sc.scene'].sudo()
        scene = Scene.search([('code', '=', 'projects.list')], limit=1)
        if not scene:
            scene = Scene.create({'code': 'projects.list', 'name': 'Composed list test'})
        version = self.env['sc.scene.version'].sudo().create({
            'scene_id': scene.id, 'version': 'test-hidden-composition',
            'payload_json': {'tiles': [{'key': 'restricted', 'groups_xmlids': ['base.group_system']}]},
            'product_release_state': 'PREVIEW',
        })
        scene.write({'state': 'published', 'active_version_id': version.id})
        result = diagnose_scenario_dependencies(self._actor(self.company_a),
            scene_key='projects.list', company_id=self.company_a.id)
        self.assertEqual(result['dependencies'][0]['evidence']['readiness_kind'], 'orchestration')
        self.assertTrue(result['publication']['scene_composition']['applicable'])
        self.assertFalse(result['enable_allowed'])


@tagged("post_install", "-at_install", "acceptance_business_scene_lifecycle")
class TestFixtureCompanyWorkProjection(TransactionCase):
    """The browser's B-company work item must exist under the real fixture ACLs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_acceptance_fixture_for_local_test(cls.env)

    def test_finance_initiated_item_survives_company_selection(self):
        from odoo.addons.smart_construction_core.services.review_work_item_service import CurrentWorkItemService
        finance = self.env.ref('smart_construction_acceptance_fixture.fe_user_finance')
        company_a = self.env.ref('smart_construction_acceptance_fixture.fe_company_a')
        company_b = self.env.ref('smart_construction_acceptance_fixture.fe_company_b')
        request_b = self.env.ref('smart_construction_acceptance_fixture.fe_request_c_001')
        self.assertEqual(request_b.create_uid, finance)
        self.assertEqual(request_b.company_id, company_b)
        for allowed in ([company_a.id, company_b.id], [company_b.id]):
            with self.subTest(allowed=allowed):
                context = {'allowed_company_ids': allowed, 'company_id': company_b.id}
                caller = self.env(user=finance, context=context, su=False)
                workspace = CurrentWorkItemService(caller, params={'product_workspace': True}, context=context).build()
                initiated = next(row for row in workspace['sections'] if row['key'] == 'initiated')
                self.assertIn(request_b.id, [row['target']['record_id'] for row in initiated['items']], workspace)
                self.assertEqual(workspace['query_scope']['company_ids'], [company_b.id])

    def test_license_does_not_add_native_company_membership_and_can_be_revoked(self):
        finance = self.env.ref('smart_construction_acceptance_fixture.fe_user_finance')
        member = self.env.ref('smart_construction_acceptance_fixture.fe_user_project_a_member')
        company_a = self.env.ref('smart_construction_acceptance_fixture.fe_company_a')
        company_b = self.env.ref('smart_construction_acceptance_fixture.fe_company_b')
        self.assertEqual(set(finance._sc_authorized_company_ids()), {company_a.id, company_b.id})
        self.assertEqual(member._sc_authorized_company_ids(), [company_a.id])
        plan = self.env.ref('smart_construction_acceptance_fixture.fe_multi_company_plan')
        plan.multi_company_enabled = False
        self.assertEqual(finance._sc_authorized_company_ids(), [company_a.id])
        caller = self.env(user=finance, context={'allowed_company_ids': [company_b.id]}, su=False)
        with self.assertRaisesRegex(AccessError, 'PLATFORM_COMPANY_NOT_AUTHORIZED'):
            caller['payment.request'].search([])

    def test_work_projection_reuses_totals_without_changing_actions(self):
        from odoo.addons.smart_construction_core.models.support import operating_metrics as metrics
        from odoo.addons.smart_construction_core.services.review_work_item_service import CurrentWorkItemService
        finance = self.env.ref('smart_construction_acceptance_fixture.fe_user_finance')
        company = self.env.ref('smart_construction_acceptance_fixture.fe_company_a')
        context = {'allowed_company_ids': [company.id], 'company_id': company.id}
        actor = self.env(user=finance.id, context=context, su=False)
        def build():
            return CurrentWorkItemService(actor, params={'product_workspace': True}, context=context).build()
        original = metrics.compute_payment_payable_excluding_self
        # Reference execution re-reads totals for every native check.
        with patch.object(metrics, 'compute_payment_payable_excluding_self',
                          side_effect=lambda record, **kwargs: original(record)):
            with patch.object(metrics, 'settlement_reserved_amount_map', wraps=metrics.settlement_reserved_amount_map) as queries:
                expected = build()
                uncached_calls = queries.call_count
        with patch.object(metrics, 'settlement_reserved_amount_map', wraps=metrics.settlement_reserved_amount_map) as queries:
            actual = build()
            cached_calls = queries.call_count
        self.assertEqual(actual, expected)
        self.assertGreater(cached_calls, 0)
        self.assertGreater(uncached_calls, cached_calls * 2)
        # A new projection must read totals again, rather than retaining a
        # handler/session/global permission or business-data cache.
        with patch.object(metrics, 'settlement_reserved_amount_map', wraps=metrics.settlement_reserved_amount_map) as queries:
            self.assertEqual(build(), expected)
            self.assertEqual(queries.call_count, cached_calls)

    def test_snapshot_projection_reads_json_once_and_keeps_detached_values(self):
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
        snapshot = self.env['sc.edition.release.snapshot'].sudo().search([
            ('state', '=', 'released'), ('is_active', '=', True),
            ('product_key', '=', 'construction.standard'),
        ], limit=1)
        self.assertTrue(snapshot)
        field_type = type(snapshot._fields['snapshot_json'])
        original = field_type.convert_to_record
        counts = {}
        def convert(field, value, record):
            if record._name == snapshot._name and record.id == snapshot.id:
                counts[field.name] = counts.get(field.name, 0) + 1
            return original(field, value, record)
        with patch.object(field_type, 'convert_to_record', convert):
            runtime = snapshot.to_runtime_dict()
        self.assertEqual(counts.get('snapshot_json'), 1)
        self.assertEqual(counts.get('meta_json'), 1)
        counts.clear()
        with patch.object(field_type, 'convert_to_record', convert):
            lineage = EditionReleaseSnapshotService(self.env)._lineage_meta(snapshot)
        self.assertEqual(counts.get('snapshot_json'), 1)
        self.assertEqual(lineage['snapshot_id'], snapshot.id)
        before = snapshot.snapshot_json
        runtime['snapshot_json']['diagnostic_mutation'] = True
        self.assertEqual(snapshot.snapshot_json, before)

    def test_native_settlement_execution_checks_do_not_reuse_projection_totals(self):
        from odoo.addons.smart_construction_core.models.support import operating_metrics as metrics
        from odoo.exceptions import UserError
        request = self.env['payment.request'].sudo().search([
            ('type', '=', 'pay'), ('settlement_id', '!=', False), ('amount', '>', 0),
        ], limit=1)
        self.assertTrue(request)
        settlement = request.settlement_id
        # A completed read projection cannot make a later native execution
        # check reuse its previously favorable total.
        with patch.object(metrics, 'settlement_reserved_amount_map', return_value={settlement.id: 0.0}):
            metrics.compute_payment_payable_excluding_self(request, evaluation_cache={})
        with patch.object(metrics, 'settlement_reserved_amount_map', return_value={settlement.id: 10**12}) as queries:
            with self.assertRaises(UserError):
                request._check_settlement_remaining_amount()
            with self.assertRaises(UserError):
                request._check_not_overpay_settlement()
            self.assertEqual(queries.call_count, 2)
