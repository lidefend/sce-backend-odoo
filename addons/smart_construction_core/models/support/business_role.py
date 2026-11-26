"""Enterprise role identity, immutable editions and explicit native authority sources."""
from copy import deepcopy

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.smart_core.security.group_assignment import GroupAuthorityGap, verified_sources
from ...services import capability_registry
from ...services.business_capability_authorization import CapabilityCompositionError

AUTHORITY_BATCH_LIMIT = 50


def _admin(env):
    if not env.su and not env.user.has_group('smart_construction_core.group_sc_cap_business_config_admin'):
        raise AccessError(_('只有业务配置管理员可以管理企业角色。'))


def _reject_context_defaults(record, allowed):
    if any(key.startswith('default_') and key[8:] in record._fields and key[8:] not in allowed
           for key in record.env.context):
        raise AccessError(_('不能通过上下文默认值指定系统维护的授权事实。'))


def _company(env, company):
    company.ensure_one()
    if company.id not in env.user._sc_authorized_company_ids() and not env.su:
        raise AccessError(_('目标公司不在平台许可及当前管理员的授权范围内。'))


def _capability_choices(self):
    return [(row['key'], row['label']) for row in capability_registry.capability_definitions()
            if row['role_composition']['composable']]


class BusinessRole(models.Model):
    _name = 'sc.business.role'
    _description = '企业业务角色'
    _check_company_auto = True
    _order = 'company_id, name, id'

    name = fields.Char('角色名称', required=True)
    code = fields.Char('角色编码', required=True, index=True, copy=False)
    company_id = fields.Many2one('res.company', string='所属公司', required=True, default=lambda self: self.env.company)
    description = fields.Text('业务职责说明')
    state = fields.Selection([('enabled', '启用'), ('disabled', '停用')], default='enabled', required=True, readonly=True, copy=False)
    version_ids = fields.One2many('sc.business.role.version', 'role_id', string='授权依据', readonly=True, copy=False)
    current_version_id = fields.Many2one('sc.business.role.version', string='当前发布方案', readonly=True, copy=False, ondelete='restrict')
    assignment_ids = fields.One2many('sc.user.role.assignment', 'role_id', string='用户分配', readonly=True, copy=False)
    _sql_constraints = [('company_code_unique', 'unique(company_id,code)', '角色编码在公司内必须唯一。')]

    def _lock(self):
        if self.ids:
            self.env.cr.execute('SELECT id FROM sc_business_role WHERE id = ANY(%s) ORDER BY id FOR UPDATE', (self.ids,))
            self.invalidate_recordset()

    def _check_management(self):
        _admin(self.env)
        self.check_access_rights('write')
        self.check_access_rule('write')
        self._lock()
        for role in self:
            _company(self.env, role.company_id)

    @api.model_create_multi
    def create(self, vals_list):
        _reject_context_defaults(self, {'name', 'code', 'company_id', 'description'})
        _admin(self.env)
        for vals in vals_list:
            if set(vals) - {'name', 'code', 'company_id', 'description'}:
                raise AccessError(_('角色版本、状态和分配由受控操作维护。'))
            _company(self.env, self.env['res.company'].browse(vals.get('company_id') or self.env.company.id))
        return super().create(vals_list)

    def write(self, vals):
        self._check_management()
        if set(vals) - {'name', 'description'}:
            raise AccessError(_('角色身份建立后只能修改名称和职责说明。'))
        return super().write(vals)

    def unlink(self):
        self._check_management()
        if any(role.version_ids or role.assignment_ids for role in self):
            raise UserError(_('已有版本或授权历史的角色不可删除。'))
        return super().unlink()

    def action_new_version(self):
        self.ensure_one()
        self._check_management()
        version = self.env['sc.business.role.version'].create({
            'role_id': self.id,
            'capability_line_ids': [(0, 0, {'capability_key': key}) for key in
                                    self.current_version_id.capability_line_ids.mapped('capability_key')],
        })
        return {'type': 'ir.actions.act_window', 'res_model': version._name,
                'res_id': version.id, 'view_mode': 'form', 'target': 'current'}

    def action_disable(self):
        self._check_management()
        if self.assignment_ids.filtered(lambda a: a.state == 'active'):
            raise UserError(_('请先通过分批撤权处理有效分配；停用不能隐式批量修改用户。'))
        super().write({'state': 'disabled'})
        return True

    def action_enable(self):
        self._check_management()
        super().write({'state': 'enabled'})
        return True

    def _event(self, action, version, assignment=None, details=None):
        self.ensure_one()
        return self.env['sc.business.role.event']._append({
            'role_id': self.id, 'company_id': self.company_id.id, 'action': action,
            'assignment_id': assignment.id if assignment else False,
            'actor_id': self.env.uid, 'version_id': version.id,
            'capability_keys': version.capability_line_ids.mapped('capability_key'),
            'details': {'role_name': self.name, 'actor_name': self.env.user.name,
                        'user_name': assignment.user_id.name if assignment else False,
                        'capability_facts': version.sudo().authority_snapshot.get('capability_facts', {}),
                        **(details or {})},
            'summary': '%s\n%s\n%s' % (self.name, assignment.user_id.name if assignment else self.env.user.name,
                                         version.published_capabilities_text or ''),
        })


class BusinessRoleVersion(models.Model):
    _name = 'sc.business.role.version'
    _description = '企业角色版本'
    _order = 'role_id, number desc'
    _rec_name = 'name'

    name = fields.Char('版本名称', compute='_compute_name', store=True)
    role_id = fields.Many2one('sc.business.role', string='企业角色', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='role_id.company_id', store=True, readonly=True)
    number = fields.Integer('版本号', required=True, readonly=True, copy=False)
    state = fields.Selection([('draft', '草稿'), ('published', '已发布')], default='draft', required=True, readonly=True, copy=False)
    description = fields.Text('变更说明')
    capability_line_ids = fields.One2many('sc.business.role.capability', 'version_id', string='业务能力组合')
    published_role_name = fields.Char('发布时角色名称', readonly=True, copy=False)
    published_capabilities_text = fields.Text('发布时业务职责', readonly=True, copy=False)
    published_at = fields.Datetime('发布时间', readonly=True, copy=False)
    published_by = fields.Many2one('res.users', string='发布人', readonly=True, copy=False)
    authority_snapshot = fields.Json('已验证授权快照', readonly=True, copy=False, groups='base.group_system')
    _sql_constraints = [('role_number_unique', 'unique(role_id,number)', '角色版本号不能重复。')]

    @api.depends('role_id.name', 'description', 'published_at')
    def _compute_name(self):
        for version in self:
            version.name = '%s · %s' % (version.role_id.name, version.description or (str(version.published_at) if version.published_at else _('待发布调整')))

    def _check_edit(self):
        self.check_access_rights('write')
        self.check_access_rule('write')
        self.role_id._check_management()
        self.invalidate_recordset()
        if any(v.state != 'draft' for v in self):
            raise UserError(_('已发布的能力方案不可覆盖，请另建调整草稿。'))

    @api.model_create_multi
    def create(self, vals_list):
        _reject_context_defaults(self, {'role_id', 'description', 'capability_line_ids'})
        _admin(self.env)
        roles = self.env['sc.business.role'].browse(list(dict.fromkeys(v.get('role_id') for v in vals_list))).exists()
        roles._check_management()
        prepared = []
        next_numbers = {}
        for vals in vals_list:
            if set(vals) - {'role_id', 'description', 'capability_line_ids'}:
                raise AccessError(_('版本号、发布状态及授权快照由系统维护。'))
            role = roles.filtered(lambda r: r.id == vals.get('role_id'))
            role.ensure_one()
            if role.state != 'enabled':
                raise UserError(_('停用角色不能创建新版本。'))
            number = next_numbers.get(role.id, max(role.version_ids.mapped('number') or [0])) + 1
            next_numbers[role.id] = number
            prepared.append(dict(vals, number=number))
        return super().create(prepared)

    def write(self, vals):
        self._check_edit()
        if set(vals) - {'description', 'capability_line_ids'}:
            raise AccessError(_('版本身份、发布状态和授权快照不可直接修改。'))
        return super().write(vals)

    def unlink(self):
        self._check_edit()
        return super().unlink()

    def _resolve_authority(self):
        self.ensure_one()
        keys = self.capability_line_ids.mapped('capability_key')
        if not keys:
            raise ValidationError(_('请至少选择一项已验证的业务能力。'))
        try:
            resolved = capability_registry.resolve_role_capabilities(keys)
        except CapabilityCompositionError as error:
            raise ValidationError(_('能力组合不可发布：%s') % error) from error
        definitions = {row['key']: row for row in capability_registry.capability_definitions()}
        mappings = {key: deepcopy(definitions[key]['authorization']) for key in resolved}
        roots = self.env['res.groups'].sudo().browse()
        identity = self.env.ref('base.group_user')
        base_groups = identity | identity.trans_implied_ids
        for mapping in mappings.values():
            capability_roots = self.env['res.groups'].sudo().browse()
            for xmlid in mapping['native_groups']:
                capability_roots |= self.env.ref(xmlid)
            capability_closure = capability_roots | capability_roots.trans_implied_ids
            declared = self.env['res.groups'].sudo().browse()
            for xmlid, edges in mapping['native_group_edges'].items():
                group = self.env.ref(xmlid)
                declared |= group
                if set(group.implied_ids.ids) != {self.env.ref(edge).id for edge in edges}:
                    raise ValidationError(_('能力的原生组继承与平台验证声明不一致。'))
            if capability_closure - base_groups != declared - base_groups:
                raise ValidationError(_('能力包含平台未验证的原生组。'))
            access = self.env['ir.model.access'].sudo().search([
                ('active', '=', True), ('group_id', 'in', (capability_closure - base_groups).ids),
            ])
            actual = {}
            for row in access:
                operations = {op for op in ('read', 'write', 'create', 'unlink') if row['perm_' + op]}
                if operations:
                    actual.setdefault(row.model_id.model, set()).update(operations)
            expected = {model: set(ops) for model, ops in mapping['native_model_access'].items()}
            if actual != expected:
                raise ValidationError(_('能力的模型权限与平台验证声明不一致。'))
            roots |= capability_roots
        closure = roots | roots.trans_implied_ids
        acl = self.env['ir.model.access'].sudo().search([('active', '=', True), ('group_id', 'in', (closure - base_groups).ids)])
        return {'keys': resolved, 'mappings': mappings, 'roots': sorted(roots.ids),
                'capability_facts': {key: {'label': definitions[key]['label'],
                                          'operations': mappings[key]['operations']} for key in resolved},
                'graph': [[g.id, sorted(g.implied_ids.ids)] for g in closure.sorted('id')],
                'acl': [[a.id, a.model_id.model, a.group_id.id, a.perm_read, a.perm_write,
                         a.perm_create, a.perm_unlink] for a in acl.sorted('id')]}

    def _grant_roots(self):
        self.ensure_one()
        if self.state != 'published':
            raise UserError(_('只能授权已发布版本。'))
        current = self._resolve_authority()
        snapshot = self.sudo().authority_snapshot
        if {k: v for k, v in current.items() if k != 'capability_facts'} != {k: v for k, v in snapshot.items() if k != 'capability_facts'}:
            raise UserError(_('能力映射与发布快照不一致，禁止静默改变历史版本授权。'))
        return current['roots']

    def action_publish(self):
        self._check_edit()
        # Atomic even when invoked by another server action which catches errors.
        with self.env.cr.savepoint():
            for version in self:
                role = version.role_id
                if role.state != 'enabled':
                    raise UserError(_('停用角色不能发布版本。'))
                snapshot = version._resolve_authority()
                super(BusinessRoleVersion, version.sudo()).write({
                    'state': 'published', 'authority_snapshot': snapshot,
                    'published_at': fields.Datetime.now(), 'published_by': self.env.uid,
                    'published_role_name': role.name,
                    'published_capabilities_text': '\n'.join(row['label'] for row in snapshot['capability_facts'].values()),
                })
                if version.number > role.current_version_id.number:
                    super(BusinessRole, role).write({'current_version_id': version.id})
                role._event('publish', version)
        return True


class BusinessRoleCapability(models.Model):
    _name = 'sc.business.role.capability'
    _description = '企业角色版本能力'
    _rec_name = 'capability_key'

    version_id = fields.Many2one('sc.business.role.version', required=True, ondelete='cascade', string='授权依据')
    company_id = fields.Many2one(related='version_id.company_id', store=True, readonly=True)
    capability_key = fields.Selection(_capability_choices, required=True, string='场景业务能力')
    _sql_constraints = [('version_capability_unique', 'unique(version_id,capability_key)', '同一业务能力无需重复添加。')]

    @api.model_create_multi
    def create(self, vals_list):
        _reject_context_defaults(self, {'version_id', 'capability_key'})
        if any(set(vals) - {'version_id', 'capability_key'} for vals in vals_list):
            raise AccessError(_('只能维护版本及业务能力。'))
        versions = self.env['sc.business.role.version'].browse([v.get('version_id') for v in vals_list]).exists()
        versions._check_edit()
        return super().create(vals_list)

    def write(self, vals):
        self.version_id._check_edit()
        if set(vals) - {'capability_key'}:
            raise AccessError(_('能力行不能转移到其他版本或公司。'))
        return super().write(vals)

    def unlink(self):
        self.version_id._check_edit()
        return super().unlink()


class UserRoleAssignment(models.Model):
    _name = 'sc.user.role.assignment'
    _description = '用户企业角色分配'
    _rec_name = 'role_id'

    role_id = fields.Many2one('sc.business.role', string='企业角色', required=True, ondelete='restrict')
    version_id = fields.Many2one('sc.business.role.version', string='授权依据', required=True, ondelete='restrict')
    user_id = fields.Many2one('res.users', string='用户', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='role_id.company_id', store=True, readonly=True, string='所属公司')
    state = fields.Selection([('draft', '待生效'), ('active', '已生效'), ('revoked', '已撤销')], default='draft', readonly=True, required=True, copy=False)
    note = fields.Text('授权说明')
    _sql_constraints = [('role_user_unique', 'unique(role_id,user_id)', '该用户已有此角色的分配记录。')]

    @api.onchange('role_id')
    def _onchange_role_id(self):
        for assignment in self:
            if not assignment._origin.id:
                assignment.version_id = assignment.role_id.current_version_id

    def _check_management(self):
        _admin(self.env)
        self.check_access_rights('write')
        self.check_access_rule('write')
        self.role_id._check_management()
        if self.ids:
            self.env.cr.execute('SELECT id FROM sc_user_role_assignment WHERE id = ANY(%s) ORDER BY id FOR UPDATE', (self.ids,))
            self.invalidate_recordset()

    @api.model_create_multi
    def create(self, vals_list):
        _reject_context_defaults(self, {'role_id', 'version_id', 'user_id', 'note'})
        _admin(self.env)
        roles = self.env['sc.business.role'].browse(list(dict.fromkeys(v.get('role_id') for v in vals_list))).exists()
        roles._check_management()
        prepared = []
        for vals in vals_list:
            if set(vals) - {'role_id', 'version_id', 'user_id', 'note'}:
                raise AccessError(_('导入只能指定角色、版本、用户和说明；生效必须通过授权操作。'))
            role = roles.filtered(lambda r: r.id == vals.get('role_id'))
            role.ensure_one()
            version = self.env['sc.business.role.version'].browse(vals.get('version_id') or role.current_version_id.id).exists()
            if not version or version.role_id != role or version.state != 'published':
                raise ValidationError(_('请选择本角色的已发布版本。'))
            version.check_access_rights('read')
            version.check_access_rule('read')
            self.env['res.users'].browse(vals.get('user_id'))._sc_check_runtime_user_management_targets()
            prepared.append(dict(vals, version_id=version.id))
        return super().create(prepared)

    def write(self, vals):
        self._check_management()
        if set(vals) - {'note'}:
            raise AccessError(_('版本和用户不能直接修改，请使用受控迁移或撤销操作。'))
        return super().write(vals)

    def unlink(self):
        self._check_management()
        if any(a.state != 'draft' for a in self):
            raise UserError(_('授权历史必须保留审计记录。'))
        return super().unlink()

    def _source(self):
        self.ensure_one()
        return 'business_role_assignment:%s:version:%s' % (self.id, self.version_id.id)

    def _check_target(self):
        self.ensure_one()
        self.user_id._sc_check_runtime_user_management_targets()
        if self.role_id.state != 'enabled':
            raise UserError(_('停用角色不能授权。'))
        if self.company_id.id not in self.user_id._sc_authorized_company_ids():
            raise AccessError(_('用户没有该公司的平台许可及原生成员授权。'))

    def action_prepare_adjustment(self):
        return self._prepare_change_batches('migrate')

    def _prepare_change_batches(self, operation):
        self._check_management()
        if not self or len(self.role_id) != 1:
            raise UserError(_('请选择同一角色下需要调整的用户。'))
        ordered = self.sorted('id')
        batches = self.env['sc.business.role.change'].create([
            {'name': _('%s：用户授权调整（第 %s 批）') % (self.role_id.name, offset // AUTHORITY_BATCH_LIMIT + 1),
             'role_id': self.role_id.id, 'operation': operation,
             'assignment_ids': [(6, 0, ordered[offset:offset + AUTHORITY_BATCH_LIMIT].ids)]}
            for offset in range(0, len(ordered), AUTHORITY_BATCH_LIMIT)
        ])
        return {'type': 'ir.actions.act_window', 'res_model': batches._name,
                'res_id': batches.id if len(batches) == 1 else False,
                'domain': [('id', 'in', batches.ids)],
                'view_mode': 'form' if len(batches) == 1 else 'tree,form', 'target': 'current'}

    def _route_authority_change(self, operation):
        self._check_management()
        if len(self.role_id) != 1:
            raise UserError(_('请选择同一角色下需要调整的用户。'))
        pending = self.filtered(lambda a: a.state != 'active' if operation == 'grant' else a.state == 'active')
        if not pending:
            return True
        if len(pending) > AUTHORITY_BATCH_LIMIT:
            return pending._prepare_change_batches(operation)
        existing = self.env['sc.business.role.change'].search([
            ('role_id', '=', self.role_id.id), ('operation', '=', operation),
            ('state', '=', 'preview'), ('preview_by', '=', self.env.uid),
        ]).filtered(lambda batch: set(batch.assignment_ids.ids) == set(pending.ids))[:1]
        if existing:
            return {'type': 'ir.actions.act_window', 'res_model': existing._name,
                    'res_id': existing.id, 'view_mode': 'form', 'target': 'current'}
        batch = self.env['sc.business.role.change'].create({
            'name': _('%s：用户授权办理') % self.role_id.name,
            'role_id': self.role_id.id, 'operation': operation,
            'assignment_ids': [(6, 0, pending.ids)],
        })
        batch.action_preview()
        batch.action_execute()
        return {'type': 'ir.actions.act_window', 'res_model': batch._name,
                'res_id': batch.id, 'view_mode': 'form', 'target': 'current'}

    def action_activate(self):
        return self._route_authority_change('grant')

    def action_revoke(self):
        return self._route_authority_change('revoke')

    def _apply_activation(self):
        if len(self) > AUTHORITY_BATCH_LIMIT:
            raise UserError(_("每次最多处理 %s 人，请分批办理。") % AUTHORITY_BATCH_LIMIT)
        self._check_management()
        self.user_id._sc_lock_group_authority()
        with self.env.cr.savepoint():
            for assignment in self:
                if assignment.state == 'active':
                    continue
                assignment._check_target()
                assignment.user_id._sc_replace_group_authority_source(assignment._source(), assignment.version_id._grant_roots())
                assignment.user_id._sc_explicit_group_roots()
                super(UserRoleAssignment, assignment).write({'state': 'active'})
                assignment.role_id._event('activate', assignment.version_id, assignment)
        self.env.registry.clear_cache()
        return True

    def _apply_revocation(self):
        if len(self) > AUTHORITY_BATCH_LIMIT:
            raise UserError(_("每次最多处理 %s 人，请分批办理。") % AUTHORITY_BATCH_LIMIT)
        self._check_management()
        self.user_id._sc_lock_group_authority()
        with self.env.cr.savepoint():
            for assignment in self:
                if assignment.state != 'active':
                    continue
                try:
                    user = assignment.user_id
                    user._sc_explicit_group_roots()
                    if assignment._source() not in verified_sources(user.sudo().sc_group_authority_state):
                        raise GroupAuthorityGap('GROUP_AUTHORITY_ASSIGNMENT_SOURCE_MISSING')
                except GroupAuthorityGap as error:
                    raise UserError(_('授权来源不一致，撤销未执行：%s') % error) from error
                user._sc_replace_group_authority_source(assignment._source(), [])
                user._sc_explicit_group_roots()
                super(UserRoleAssignment, assignment).write({'state': 'revoked'})
                assignment.role_id._event('revoke', assignment.version_id, assignment)
        self.env.registry.clear_cache()
        return True


class BusinessRoleEvent(models.Model):
    _name = 'sc.business.role.event'
    _description = '企业角色授权审计'
    _order = 'id desc'

    role_id = fields.Many2one('sc.business.role', ondelete='restrict', string='企业角色')
    version_id = fields.Many2one('sc.business.role.version', ondelete='restrict', string='授权依据')
    assignment_id = fields.Many2one('sc.user.role.assignment', ondelete='restrict', string='分配记录')
    company_id = fields.Many2one('res.company', required=True)
    actor_id = fields.Many2one('res.users', required=True, string='操作人')
    action = fields.Selection([('publish', '发布'), ('activate', '授权生效'), ('revoke', '移除角色职责'), ('migrate', '调整角色职责')], required=True, string='操作')
    capability_keys = fields.Json('能力快照')
    details = fields.Json('变更详情', readonly=True)
    summary = fields.Text('当时授权事实', readonly=True)

    @api.model
    def _append(self, vals):
        return super(BusinessRoleEvent, self.sudo()).create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_('审计记录由授权操作生成。'))

    def write(self, vals):
        raise AccessError(_('审计记录不可修改。'))

    def unlink(self):
        raise AccessError(_('审计记录不可删除。'))
