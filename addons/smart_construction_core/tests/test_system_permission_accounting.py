"""Actual journal operations under SC accounting roles, in rollback-only fixtures."""
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'system_permission_accounting')
class TestSystemPermissionAccounting(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.journal = cls.env['account.journal'].create({
            'name': 'Synthetic AUTH01 journal', 'code': 'AUT01',
            'type': 'general', 'company_id': cls.env.company.id,
        })

    def _subject(self, suffix):
        role = self.env.ref('smart_construction_core.group_sc_role_' + suffix)
        self.assertTrue(role.sc_assignable_user_permission)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic accounting ' + suffix,
            'login': 'auth01_accounting_' + suffix,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, (self.env.ref('base.group_user') | role).ids)],
        })

    def _readonly_configuration(self, suffix):
        user = self._subject(suffix)
        journal = self.journal.with_user(user)
        self.assertFalse(journal.env.su)
        self.assertEqual(journal.read(['name'])[0]['name'], self.journal.name)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            journal.write({'name': 'Forbidden journal configuration'})
        self.assertEqual(self.journal.name, 'Synthetic AUTH01 journal')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.journal'].with_user(user).create({
                'name': 'Forbidden AUTH01 journal', 'code': 'AUT02',
                'type': 'general', 'company_id': self.env.company.id,
            })
        self.assertFalse(self.env['account.journal'].search([
            ('code', '=', 'AUT02'), ('company_id', '=', self.env.company.id)]))

    def test_accounting_read_cannot_configure_journal(self):
        self._readonly_configuration('accounting_read')

    def test_accounting_user_cannot_configure_journal(self):
        self._readonly_configuration('accounting_user')

    def test_accounting_manager_write_then_revoke(self):
        user = self._subject('accounting_manager')
        journal = self.env['account.journal'].with_user(user)
        self.assertFalse(journal.env.su)
        created = journal.create({
            'name': 'Synthetic AUTH01 manager journal', 'code': 'AUT03',
            'type': 'general', 'company_id': self.env.company.id,
        })
        created.write({'name': 'Synthetic AUTH01 manager changed'})
        self.assertEqual(created.with_env(self.env).name, 'Synthetic AUTH01 manager changed')
        user.with_context(sc_runtime_user_management=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.env.registry.clear_cache()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            created.with_user(user).write({'name': 'Forbidden after revoke'})
        self.assertEqual(created.with_env(self.env).name, 'Synthetic AUTH01 manager changed')

    def test_accounting_user_posts_entry_reader_and_revoked_user_cannot_create(self):
        user = self._subject('accounting_user')
        reader = self._subject('accounting_read')
        debit = self.env['account.account'].create({
            'name': 'Synthetic AUTH01 debit', 'code': 'AUTH0101',
            'account_type': 'asset_current', 'company_id': self.env.company.id,
        })
        credit = self.env['account.account'].create({
            'name': 'Synthetic AUTH01 credit', 'code': 'AUTH0102',
            'account_type': 'liability_current', 'company_id': self.env.company.id,
        })
        values = {
            'ref': 'Synthetic AUTH01 journal entry',
            'journal_id': self.journal.id, 'company_id': self.env.company.id,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {'name': 'Synthetic AUTH01 debit line', 'account_id': debit.id, 'debit': 100}),
                (0, 0, {'name': 'Synthetic AUTH01 credit line', 'account_id': credit.id, 'credit': 100}),
            ],
        }
        model = self.env['account.move'].with_user(user)
        self.assertFalse(model.env.su)
        move = model.create(values)
        self.assertEqual(move.state, 'draft')
        move.action_post()
        self.assertEqual(move.with_env(self.env).state, 'posted')
        self.assertEqual(sum(move.with_env(self.env).line_ids.mapped('balance')), 0)
        self.assertEqual(move.with_user(reader).read(['state'])[0]['state'], 'posted')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.move'].with_user(reader).create(values)
        user.with_context(sc_runtime_user_management=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.env.registry.clear_cache()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.move'].with_user(user).create(values)
        self.assertEqual(self.env['account.move'].search_count([
            ('ref', '=', values['ref']), ('company_id', '=', self.env.company.id)]), 1)
        self.assertEqual(move.with_env(self.env).state, 'posted')

    def test_native_onchange_handler_uses_authorized_view(self):
        from odoo.addons.smart_core.handlers.api_onchange import ApiOnchangeHandler
        user = self._subject('accounting_user')
        model = self.env['res.partner'].with_user(user)
        state = self.env['res.country.state'].search([('country_id', '=', self.env.ref('base.us').id)], limit=1)
        self.assertTrue(state)
        view = self.env.ref('base.view_partner_form')
        result = ApiOnchangeHandler(model.env, payload={'params': {
            'model': 'res.partner', 'view_id': view.id,
            'values': {'name': 'Synthetic native onchange', 'country_id': self.env.ref('base.fr').id,
                       'state_id': state.id}, 'changed_fields': ['country_id'],
        }}).handle()
        self.assertFalse(model.env.su)
        self.assertTrue(result.get('ok'), result)
        self.assertIn('state_id', result['data']['patch'])
        self.assertFalse(result['data']['patch']['state_id'])
        self.assertEqual(result['data']['applied_fields'], ['country_id'])
        selected = ApiOnchangeHandler(model.env, payload={'params': {
            'model': 'res.partner', 'view_id': view.id,
            'values': {'name': 'Synthetic native onchange', 'country_id': self.env.ref('base.fr').id,
                       'state_id': state.id}, 'changed_fields': ['state_id'],
        }}).handle()
        self.assertTrue(selected.get('ok'), selected)
        self.assertEqual(selected['data']['patch']['country_id'][0], state.country_id.id)
        self.assertIsInstance(selected['data']['patch']['country_id'][1], str)
        origin = self.env['res.partner'].create({
            'name': 'Synthetic onchange origin', 'country_id': state.country_id.id, 'state_id': state.id,
        })
        existing = ApiOnchangeHandler(model.env, payload={'params': {
            'model': 'res.partner', 'view_id': view.id, 'res_id': origin.id,
            'values': {'country_id': self.env.ref('base.fr').id, 'state_id': state.id},
            'changed_fields': ['country_id'],
        }}).handle()
        self.assertTrue(existing.get('ok'), existing)
        self.assertFalse(existing['data']['patch']['state_id'])
        self.assertEqual(origin.with_user(user).state_id, state)
        self.assertEqual(origin.country_id, state.country_id)

    def test_native_relation_link_snapshot_contains_row_data(self):
        from odoo.addons.web.models.models import RecordSnapshot
        from odoo.addons.smart_core.core.native_onchange_spec import normalize_native_onchange_values
        user = self._subject('accounting_user')
        model = self.env['res.partner'].with_user(user)
        child = self.env['res.partner'].create({'name': 'Synthetic linked contact'})
        draft = model.new({'name': 'Synthetic parent draft', 'child_ids': []})
        specification = {'child_ids': {'fields': {'name': {}}}}
        before = RecordSnapshot(draft, specification)
        draft.update({'child_ids': [(4, child.id)]})
        patch = normalize_native_onchange_values(model, RecordSnapshot(draft, specification).diff(before))
        self.assertFalse(model.env.su)
        self.assertEqual(len(patch['child_ids']), 1)
        command = patch['child_ids'][0]
        self.assertEqual((int(command[0]), command[1]), (4, child.id))
        self.assertEqual(command[2], {'id': child.id, 'name': 'Synthetic linked contact'})
        self.assertFalse(child.with_user(user).parent_id)

    def test_native_virtual_relation_snapshot_roundtrip(self):
        from odoo.addons.web.models.models import RecordSnapshot
        user = self._subject('accounting_user')
        model = self.env['account.move'].with_user(user)
        model.check_access_rights('read')
        model.check_access_rights('create')
        draft = model.new({'move_type': 'out_invoice', 'invoice_line_ids': [
            (0, 'sce_virtual_a', {'name': 'Synthetic same label', 'quantity': 1}),
            (0, 'sce_virtual_b', {'name': 'Synthetic same label', 'quantity': 1}),
        ]})
        specification = {'invoice_line_ids': {'fields': {'name': {}, 'quantity': {}}}}
        before = RecordSnapshot(draft, specification)
        target = draft.invoice_line_ids.filtered(lambda line: line.id.ref == 'sce_virtual_b')
        self.assertEqual(len(target), 1)
        target.quantity = 8
        patch = RecordSnapshot(draft, specification).diff(before)
        commands = patch['invoice_line_ids']
        self.assertTrue(commands)
        self.assertEqual([(int(command[0]), command[1]) for command in commands], [(1, 'sce_virtual_b')])
        self.assertEqual(commands[0][2]['quantity'], 8)
        self.assertEqual(draft.invoice_line_ids._origin.ids, [])

    def test_native_create_relation_modifier_snapshot(self):
        from odoo.addons.smart_core.core.unified_page_contract_v2_modifier_dependencies import hydrate_final_modifier_dependencies
        from odoo.addons.smart_core.core.native_modifier_context import native_modifier_values
        from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import _evaluate_action_modifier
        user = self._subject('accounting_user')
        model = self.env['account.move'].with_user(user)
        commands = [(0, 0, {'name': 'Synthetic unsaved line', 'quantity': 1})]
        context = {'default_invoice_line_ids': commands, 'default_move_type': 'out_invoice'}
        defaults = model.with_context(**context).default_get(['invoice_line_ids'])
        source = defaults['invoice_line_ids']
        condition = {'kind': 'field_truthy', 'field': 'invoice_line_ids'}
        contract = {
            'statusContract': {'globalStatus': {'effectiveRenderProfile': 'create', 'effectiveRecordCapabilities': {'create': True}}},
            'layoutContract': {'containerTree': [{'modifiers': {'readonly': condition}}]},
            'dataContract': {'mainData': {'invoice_line_ids': source}, 'dataMeta': {'sourceContext': {'context': context}}},
        }
        hydrate_final_modifier_dependencies(model.env, contract, model='account.move', record_id='new', view_type='form')
        self.assertTrue(source, 'must exercise nonempty native create commands')
        snapshots = contract['dataContract']['dataMeta']['nativeModifierRelationSnapshots']
        self.assertEqual(snapshots['invoice_line_ids']['persistedIds'], [])
        self.assertEqual(contract['dataContract']['mainData']['invoice_line_ids'], source)
        from odoo.addons.smart_core.core.native_modifier_context import _snapshot_json, _same_snapshot
        from odoo.addons.smart_core.core.native_modifier_comparison import _json_value
        normalized_source = _snapshot_json(source)
        self.assertTrue(_json_value(normalized_source), repr(normalized_source))
        self.assertTrue(_same_snapshot(normalized_source, snapshots['invoice_line_ids']['sourceValue']), repr(snapshots))
        self.assertIs(_evaluate_action_modifier(condition, native_modifier_values(contract), strict=True), False)

    def test_native_journal_notice_parser_preserves_inline_contract(self):
        from lxml import etree
        user = self._subject('accounting_user')
        model = self.env['account.move'].with_user(user).with_context(lang='zh_CN')
        native = model.get_view(view_id=self.env.ref('account.view_move_form').id, view_type='form')
        root = etree.fromstring(native['arch'].encode())
        parser = self.env['app.view.parser'].with_user(user).with_context(lang='zh_CN')
        result = parser.parse_odoo_view('account.move', 'form', view_data=native)
        def walk(nodes):
            for node in nodes:
                yield node
                for key in ('children', 'tabs'):
                    yield from walk(node.get(key, []))
        nodes = list(walk(result['layout']))
        # Real inherited journal conditions retain the explicit Python comparison
        # semantics all the way from native XML to the backend consumer.
        from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import _evaluate_action_modifier
        comparisons = [value for node in nodes for value in node.get('modifiers', {}).values()]
        state_conditions = [value for value in comparisons if isinstance(value, dict)
                            and value.get('raw') == "state != 'draft'"]
        self.assertTrue(state_conditions, 'real journal must expose native draft-state conditions')
        for condition in state_conditions:
            self.assertEqual(condition.get('semantics'), 'python')
            self.assertIs(_evaluate_action_modifier(condition, {'state': 'draft'}, strict=True), False)
            self.assertIs(_evaluate_action_modifier(condition, {'state': 'posted'}, strict=True), True)
        from odoo.addons.smart_core.core.native_modifier_context import native_modifier_values
        context_expression = "context.get('default_journal_id') and context.get('move_type', 'entry') != 'entry'"
        context_conditions = [value for value in comparisons if isinstance(value, dict)
                              and value.get('raw') == context_expression]
        self.assertTrue(context_conditions, 'real journal must carry its native context condition')
        for condition in context_conditions:
            self.assertEqual(condition['kind'], 'all')
            for context, expected in (({'default_journal_id': 7, 'move_type': 'out_invoice'}, True),
                                      ({'default_journal_id': 7, 'move_type': 'entry'}, False),
                                      ({'default_journal_id': 0, 'move_type': 'out_invoice'}, False), ({}, False)):
                contract = {'dataContract': {'mainData': {}, 'dataMeta': {'sourceContext': {'context': context}}}}
                self.assertIs(_evaluate_action_modifier(condition, native_modifier_values(contract), strict=True), expected)
            self.assertIsNone(_evaluate_action_modifier(condition, {}, strict=True))
        spans = root.xpath('.//span[@invisible="not auto_post_until"]')
        self.assertEqual(len(spans), 1)
        span = spans[0]
        locator = root.getroottree().getpath(span)
        # The parser uses explicit ordinal [1] for every element.
        identity = parser._native_element_identity(span)
        projected = [n for n in nodes if n.get('native_locator') == identity['native_locator']]
        self.assertEqual(len(projected), 1, locator)
        self.assertEqual(projected[0]['modifiers']['invisible']['expr']['field'], 'auto_post_until')
        self.assertEqual(projected[0]['text'], ' '.join((span.text or '').split()))
        self.assertTrue(any(n.get('name') == 'auto_post_until' for n in projected[0]['children']))
        links = root.xpath('.//a[@href="#outstanding"]')
        self.assertEqual(len(links), 4)
        for link in links:
            identity = parser._native_element_identity(link)
            rows = [n for n in nodes if n.get('native_locator') == identity['native_locator']]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['type'], 'text')
            self.assertEqual(rows[0]['attributes'], {})
            self.assertNotIn('action', rows[0])
            self.assertEqual(rows[0]['text'], ' '.join((link.text or '').split()))
        buttons = root.xpath('.//button[@name="action_activate_currency"]')
        self.assertEqual(len(buttons), 2)
        for button in buttons:
            identity = parser._native_element_identity(button)
            row = next(n for n in nodes if n.get('native_locator') == identity['native_locator'])
            expected = ' '.join(''.join(button.itertext()).split())
            self.assertTrue(expected)
            self.assertEqual(row['label'], expected)
            self.assertEqual(row['action']['label'], expected)
            self.assertEqual(row['action']['name'], 'action_activate_currency')

    def test_native_child_initialization_uses_parent_draft(self):
        from odoo.addons.smart_core.core.native_onchange_spec import (
            build_native_onchange_spec, normalize_native_onchange_values,
        )
        from odoo.addons.smart_core.handlers.api_onchange import ApiOnchangeHandler
        user = self._subject('accounting_user')
        parent = self.env['account.move'].with_user(user)
        child = parent.env['account.move.line']
        self.assertFalse(child.env.su)
        currency = self.env.ref('base.EUR')
        if currency == self.env.company.currency_id:
            currency = self.env.ref('base.USD')
        currency.active = True
        self.assertNotEqual(currency, self.env.company.currency_id)
        self.journal.currency_id = currency
        specification = build_native_onchange_spec(parent)['line_ids']['fields']
        before = parent.search_count([])
        # Native journal entries use company currency unless the line supplies
        # one; invoices inherit the move currency. Neither rule belongs in JS.
        for move_type, expected in [('entry', self.env.company.currency_id), ('out_invoice', currency)]:
            values = {'move_id': {'move_type': move_type, 'journal_id': self.journal.id,
                                 'company_id': self.env.company.id, 'currency_id': currency.id}}
            result = child.onchange(values, [], specification)
            patch = normalize_native_onchange_values(child, result['value'])
            self.assertEqual(patch['currency_id'][0], expected.id, patch)
            self.assertEqual(patch['company_id'][0], self.env.company.id, patch)
            response = ApiOnchangeHandler(parent.env, payload={'params': {
                'model': 'account.move', 'values': values['move_id'], 'changed_fields': [],
                'child_initialization': {'field': 'line_ids', 'fields': ['currency_id', 'company_id'], 'values': {}},
            }}).handle()
            self.assertTrue(response.get('ok'), response)
            self.assertEqual(response['data']['patch']['currency_id'][0], expected.id, response)
            self.assertEqual(response['data']['patch']['company_id'][0], self.env.company.id, response)

        self.assertEqual(parent.search_count([]), before)
        existing = parent.create({'ref': 'Synthetic child-init origin', 'journal_id': self.journal.id})
        persisted_currency = existing.currency_id.id
        result = ApiOnchangeHandler(parent.env, payload={'params': {
            'model': 'account.move', 'res_id': existing.id,
            'values': {'ref': 'Unsaved parent edit', 'move_type': 'entry', 'journal_id': self.journal.id,
                       'company_id': self.env.company.id, 'currency_id': currency.id}, 'changed_fields': [],
            'child_initialization': {'field': 'line_ids', 'fields': ['currency_id', 'company_id'], 'values': {}},
        }}).handle()
        self.assertTrue(result.get('ok'), result)
        self.assertEqual(result['data']['patch']['company_id'][0], self.env.company.id)
        existing.invalidate_recordset()
        self.assertEqual(existing.ref, 'Synthetic child-init origin')
        self.assertEqual(existing.currency_id.id, persisted_currency)
        self.assertFalse(existing.line_ids)


    def test_native_child_amount_onchange_preserves_saved_amounts(self):
        from odoo.addons.smart_core.core.native_onchange_spec import (
            build_native_onchange_spec, normalize_native_onchange_values,
        )
        user = self._subject('accounting_user')
        parent = self.env['account.move'].with_user(user)
        child = parent.env['account.move.line']
        self.assertFalse(child.env.su)
        account = self.env['account.account'].create({
            'name': 'Synthetic child amount', 'code': 'AUTH0191',
            'account_type': 'asset_current', 'company_id': self.env.company.id,
        })
        parent_values = {'move_type': 'entry', 'journal_id': self.journal.id,
                         'company_id': self.env.company.id, 'currency_id': self.env.company.currency_id.id}
        spec = build_native_onchange_spec(parent)['line_ids']['fields']
        commands = []
        for changed, sign in [('debit', 1), ('credit', -1)]:
            values = {'account_id': account.id, 'currency_id': self.env.company.currency_id.id,
                      'debit': 0.0, 'credit': 0.0, 'balance': 0.0, 'amount_currency': 0.0}
            values[changed] = 100.0
            result = child.onchange({**values, 'move_id': parent_values}, [changed], spec)
            patch = normalize_native_onchange_values(child, result['value'])
            self.assertEqual(patch.get('balance'), sign * 100, result)
            self.assertEqual(patch.get('amount_currency'), sign * 100, result)
            from odoo.addons.smart_core.handlers.api_onchange import ApiOnchangeHandler
            response = ApiOnchangeHandler(parent.env, payload={'params': {
                'model': 'account.move', 'values': parent_values, 'changed_fields': [],
                'child_onchange': {'field': 'line_ids', 'fields': list(values), 'values': values,
                                   'changed_fields': [changed], 'record_id': 0},
            }}).handle()
            self.assertTrue(response.get('ok'), response)
            self.assertEqual(response['data']['patch']['balance'], sign * 100, response)
            self.assertEqual(response['data']['patch']['amount_currency'], sign * 100, response)
            commands.append((0, 0, {**values, 'balance': patch['balance'], 'amount_currency': patch['amount_currency']}))
        record = parent.create({**parent_values, 'ref': 'Synthetic child amount roundtrip', 'line_ids': commands})
        self.assertEqual(sum(record.line_ids.mapped('debit')), 100)
        self.assertEqual(sum(record.line_ids.mapped('credit')), 100)
        self.assertEqual(sorted(record.line_ids.mapped('balance')), [-100, 100])

        line = record.line_ids[0]
        from odoo.addons.smart_core.handlers.api_onchange import ApiOnchangeHandler
        persisted = {'account_id': account.id, 'currency_id': self.env.company.currency_id.id,
                     'debit': 120.0, 'credit': 0.0, 'balance': 100.0, 'amount_currency': 100.0}
        request = {'model': 'account.move', 'res_id': record.id, 'values': parent_values, 'changed_fields': [],
                   'child_onchange': {'field': 'line_ids', 'fields': list(persisted), 'values': persisted,
                                      'changed_fields': ['debit'], 'record_id': line.id}}
        response = ApiOnchangeHandler(parent.env, payload={'params': request}).handle()
        self.assertTrue(response.get('ok'), response)
        self.assertEqual(response['data']['patch']['balance'], 120, response)
        line.invalidate_recordset()
        self.assertEqual(line.balance, 100, 'onchange must not persist child edits')
        other = parent.create({**parent_values, 'ref': 'Synthetic unrelated parent'})
        request['res_id'] = other.id
        denied = ApiOnchangeHandler(parent.env, payload={'params': request}).handle()
        self.assertEqual(denied['error']['reason_code'], 'ONCHANGE_SPEC_INVALID', denied)


    def test_native_saved_journal_feedback_contract(self):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        user = self._subject('accounting_user')
        record = self.env['account.move'].with_user(user).create({'journal_id': self.journal.id, 'ref': 'Synthetic saved contract'})
        self.assertFalse(record.env.su)
        result = UiContractV2Handler(record.env, su_env=self.env).handle({
            'op': 'model', 'model': 'account.move', 'view_id': self.env.ref('account.view_move_form').id,
            'view_type': 'form', 'render_profile': 'edit', 'record_id': record.id,
            'client_contract_capabilities': ['form.feedback.message.v1', 'form.navigation.anchor.v1', 'form.feedback.draft.v1'],
        })
        result = result.to_legacy_dict() if hasattr(result, 'to_legacy_dict') else result
        self.assertTrue(result.get('ok', True), result)

    def test_native_saved_journal_reader_contract_and_write_denials(self):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        record = self.env['account.move'].create({'journal_id': self.journal.id, 'ref': 'Synthetic reader boundary'})
        for role in ('accounting_read', 'finance_manager'):
            user = self._subject(role)
            actor_record = record.with_user(user)
            self.assertFalse(actor_record.env.su)
            result = UiContractV2Handler(actor_record.env, su_env=self.env).handle({
                'op': 'model', 'model': 'account.move', 'view_id': self.env.ref('account.view_move_form').id,
                'view_type': 'form', 'render_profile': 'edit', 'record_id': record.id,
                'client_contract_capabilities': ['form.feedback.message.v1', 'form.navigation.anchor.v1', 'form.feedback.draft.v1'],
            })
            result = result.to_legacy_dict() if hasattr(result, 'to_legacy_dict') else result
            self.assertTrue(result.get('ok', True), result)
            caps = result['data']['statusContract']['globalStatus']['effectiveRecordCapabilities']
            self.assertFalse(caps['create'])
            self.assertFalse(caps['write'])
            self.assertEqual(actor_record.read(['ref'])[0]['ref'], record.ref)
            for operation in (lambda: actor_record.write({'ref':'Forbidden reader edit'}),
                              lambda: actor_record.unlink(), lambda: actor_record.action_post(),
                              lambda: actor_record.create({'journal_id':self.journal.id, 'ref':'Forbidden reader create'})):
                with self.assertRaises(AccessError), self.env.cr.savepoint():
                    operation()
            self.assertTrue(record.exists())
            self.assertEqual(record.ref, 'Synthetic reader boundary')
            self.assertEqual(record.state, 'draft')

    def test_native_saved_journal_cross_company_feedback_denied(self):
        from odoo.addons.smart_core.core.node_component_validation import read_native_facts
        from odoo.addons.smart_core.core.form_configuration_compiler import FormConfigurationError
        other_company = self.env['res.company'].create({'name':'Synthetic foreign journal company'})
        self.register_business_company(other_company)
        foreign_journal = self.env['account.journal'].create({
            'name':'Synthetic foreign journal', 'code':'AUTHX', 'type':'general', 'company_id':other_company.id})
        foreign = self.env['account.move'].with_context(allowed_company_ids=other_company.ids).create({
            'journal_id':foreign_journal.id, 'company_id':other_company.id, 'ref':'Synthetic foreign journal'})
        user = self._subject('accounting_user')
        actor = foreign.with_user(user).with_context(allowed_company_ids=self.env.company.ids)
        self.assertFalse(actor.env.su)
        self.assertFalse(actor.search([('id','=',foreign.id)]))
        with self.assertRaises(FormConfigurationError) as caught:
            read_native_facts(actor, {'state', 'payment_state'}, 'layoutContract.feedback')
        self.assertEqual(caught.exception.code, 'FEEDBACK_SOURCE_FORBIDDEN')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            actor.write({'ref':'Forbidden foreign edit'})
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            read_native_facts(actor.with_context(allowed_company_ids=other_company.ids), {'state'}, 'layoutContract.feedback')
        self.assertEqual(foreign.ref, 'Synthetic foreign journal')
        self.assertEqual(foreign.state, 'draft')

    def test_finance_and_project_reader_journal_route_not_published(self):
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        finance = self._subject('finance_manager')
        reader = self.env['res.users'].with_context(no_reset_password=True).create({
            'name':'Synthetic project finance reader', 'login':'auth01_project_finance_reader',
            'company_id':self.env.company.id, 'company_ids':[(6,0,self.env.company.ids)],
            'groups_id':[(6,0,[self.env.ref(name).id for name in (
                'base.group_user','smart_construction_core.group_sc_cap_project_read',
                'smart_construction_core.group_sc_cap_finance_read')])],
        })
        action = self.env.ref('account.action_move_journal_line')
        menu = self.env.ref('account.menu_action_move_journal_line_form')
        for user in (finance, reader):
            actor_env = self.env['account.move'].with_user(user).env
            self.assertTrue(actor_env['account.move'].check_access_rights('read', raise_exception=False))
            authority = build_runtime_route_authority(actor_env)
            published = [row for row in authority.get('primary_actions', [])
                         if row.get('action_id') and row.get('menu_id')
                         and not (row.get('context_requirements') or {}).get('required_query')]
            self.assertTrue(published, (user.login, authority))
            positive = RouteAuthorityValidateHandler(actor_env, su_env=self.env).handle({
                'action_id':published[0]['action_id'], 'menu_id':published[0]['menu_id']}).to_legacy_dict()
            self.assertTrue(positive['ok'], positive)
            self.assertTrue(positive['data']['allowed'])
            for bucket in ('primary_actions','role_home_actions','contextual_actions','admin_actions'):
                self.assertFalse(any(row.get('action_id') == action.id for row in authority.get(bucket, [])))
            result = RouteAuthorityValidateHandler(actor_env, su_env=self.env).handle({
                'action_id':action.id,'menu_id':menu.id}).to_legacy_dict()
            self.assertFalse(result['ok'])
            self.assertEqual(result['error']['reason_code'],'ROUTE_ACTION_NOT_AUTHORIZED')

    def test_explicit_accounting_roles_publish_journal_entry(self):
        from odoo.addons.smart_construction_core.services.role_catalog_contract import load_role_catalog_contract
        catalog = load_role_catalog_contract()
        self.assertEqual(catalog['status'], 'ok', catalog)
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        action = self.env.ref('account.action_move_journal_line')
        menu = self.env.ref('account.menu_action_move_journal_line_form')
        for role in ('accounting_read', 'accounting_user', 'accounting_manager'):
            user = self._subject(role)
            actor_env = self.env['account.move'].with_user(user).env
            self.assertTrue(actor_env['account.move'].check_access_rights('read', raise_exception=False))
            authority = build_runtime_route_authority(actor_env)
            entries = [row for row in authority.get('primary_actions', [])
                       if row.get('action_id') == action.id and row.get('menu_id') == menu.id]
            self.assertEqual(len(entries), 1, (role, authority))
            result = RouteAuthorityValidateHandler(actor_env, su_env=self.env).handle({
                'action_id':action.id,'menu_id':menu.id}).to_legacy_dict()
            self.assertTrue(result['ok'], result)
            self.assertTrue(result['data']['allowed'])
            self.assertEqual(actor_env['account.move'].check_access_rights('write', raise_exception=False), role != 'accounting_read')

    def test_explicit_accounting_roles_publish_all_six_entries(self):
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        menu_xmlids = (
            'account.menu_action_move_journal_line_form',
            'account.menu_action_account_moves_all',
            'account.menu_action_account_form',
            'smart_construction_core.menu_sc_account_journal_foundation',
            'smart_construction_core.menu_sc_analytic_account_foundation',
            'smart_construction_core.menu_sc_analytic_distribution_foundation',
        )
        menus = [self.env.ref(xmlid) for xmlid in menu_xmlids]
        expected = {(menu.id, menu.action.id) for menu in menus}
        self.assertEqual(len(expected), 6)
        for role in ('accounting_read', 'accounting_user', 'accounting_manager'):
            user = self._subject(role)
            actor_env = self.env['account.move'].with_user(user).env
            self.assertFalse(actor_env.su)
            authority = build_runtime_route_authority(actor_env)
            actual = {(row.get('menu_id'), row.get('action_id'))
                      for row in authority.get('primary_actions', [])}
            self.assertEqual(actual, expected, (role, authority))
            for menu in menus:
                with self.subTest(role=role, menu=menu.get_external_id()[menu.id]):
                    self.assertTrue(actor_env[menu.action.res_model].check_access_rights('read', raise_exception=False))
                    result = RouteAuthorityValidateHandler(actor_env, su_env=self.env).handle({
                        'action_id': menu.action.id, 'menu_id': menu.id}).to_legacy_dict()
                    self.assertTrue(result['ok'], result)
                    self.assertTrue(result['data']['allowed'])

    def test_accounting_mixed_identity_and_revocation(self):
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        user = self._subject('finance_manager')
        role = self.env.ref('smart_construction_core.group_sc_role_accounting_read')
        user.with_context(sc_runtime_user_management=True).write({'sc_user_role_group_ids': [(4, role.id)]})
        self.env.registry.clear_cache()
        actor_env = self.env['account.move'].with_user(user).env
        resolver = IdentityResolver(actor_env)
        codes, evidence = resolver.resolve_role_codes_with_evidence(resolver.user_group_xmlids(user))
        self.assertIn('finance', codes)
        self.assertIn('accounting', codes)
        marker = {'smart_construction_core.group_sc_role_experience',
                  'smart_construction_core.group_sc_role_accounting_read'}
        self.assertEqual(resolver.resolve_role_code(marker), 'experience')
        self.assertEqual(resolver.resolve_role_code(marker | {'smart_core.group_smart_core_admin'}), 'system_admin')
        menu = self.env.ref('account.menu_action_move_journal_line_form')
        authority = build_runtime_route_authority(actor_env)
        self.assertTrue(any(row.get('menu_id') == menu.id for row in authority['primary_actions']))
        self.assertFalse(actor_env['account.move'].check_access_rights('write', raise_exception=False))
        user.with_context(sc_runtime_user_management=True).write({'sc_user_role_group_ids': [(3, role.id)]})
        self.env.registry.clear_cache()
        actor_env = self.env['account.move'].with_user(user).env
        result = RouteAuthorityValidateHandler(actor_env, su_env=self.env).handle({
            'action_id': menu.action.id, 'menu_id': menu.id}).to_legacy_dict()
        self.assertFalse(result['ok'])
        self.assertEqual(result['error']['reason_code'], 'ROUTE_ACTION_NOT_AUTHORIZED')
        self.assertTrue(actor_env['account.move'].check_access_rights('read', raise_exception=False))
