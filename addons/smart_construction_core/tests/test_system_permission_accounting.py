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
            self.assertEqual(rows[0]['attributes']['href'], '#outstanding')
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
