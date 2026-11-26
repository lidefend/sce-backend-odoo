"""Explicit, bounded authorization changes over native group source projections."""
from copy import deepcopy

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.smart_core.security.group_assignment import (
    GroupAuthorityGap, verified_sources, replace_source, source_union,
)
from .business_role import _admin, UserRoleAssignment, AUTHORITY_BATCH_LIMIT, _reject_context_defaults

# Product execution bound: a confirmed request is one independently atomic batch.
CHANGE_BATCH_LIMIT = AUTHORITY_BATCH_LIMIT


class BusinessRoleChange(models.Model):
    _name = 'sc.business.role.change'
    _description = '企业角色授权调整批次'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tier.validation']
    _state_from = ['preview']
    _state_to = ['done']
    _cancel_state = 'cancelled'

    name = fields.Char('调整说明', required=True)
    role_id = fields.Many2one('sc.business.role', string='企业角色', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='role_id.company_id', store=True, readonly=True)
    operation = fields.Selection([('grant', '授予角色职责'), ('migrate', '采用当前角色职责'), ('revoke', '移除角色职责')], required=True, default='migrate', string='办理事项')
    assignment_ids = fields.Many2many('sc.user.role.assignment', string='本批涉及的用户授权')
    target_version_id = fields.Many2one('sc.business.role.version', string='目标授权依据', readonly=True, copy=False, ondelete='restrict')
    state = fields.Selection([('draft', '待预览'), ('preview', '待确认'), ('done', '已完成'), ('failed', '未执行成功'), ('cancelled', '已取消，未生效')], default='draft', required=True, readonly=True, copy=False)
    preview_by = fields.Many2one('res.users', string='预览人', readonly=True, copy=False)
    confirmed_by = fields.Many2one('res.users', string='确认人', readonly=True, copy=False)
    preview_at = fields.Datetime('预览时间', readonly=True, copy=False)
    completed_at = fields.Datetime('处理时间', readonly=True, copy=False)
    affected_count = fields.Integer('本批用户数', readonly=True, copy=False)
    retained_count = fields.Integer('保持原授权用户数', readonly=True, copy=False)
    executed_count = fields.Integer('已执行数', readonly=True, copy=False)
    failed_count = fields.Integer('失败数', readonly=True, copy=False)
    batch_limit = fields.Integer('每批上限', compute='_compute_batch_limit')
    impact_text = fields.Text('有效权限变化预览', readonly=True, copy=False)
    result_text = fields.Text('执行及回读结果', readonly=True, copy=False)
    preview_snapshot = fields.Json('受控预览依据', readonly=True, copy=False, groups='base.group_system')
    completed_review_snapshot = fields.Json('生效时审批依据', readonly=True, copy=False, groups='base.group_system')
    completed_review_text = fields.Text('生效时审批事实', readonly=True, copy=False)
    cancelled_by = fields.Many2one('res.users', string='取消人', readonly=True, copy=False)
    cancelled_at = fields.Datetime('取消时间', readonly=True, copy=False)
    cancelled_review_text = fields.Text('取消前审批事实', readonly=True, copy=False)
    cancelled_review_snapshot = fields.Json('取消前审批依据', readonly=True, copy=False, groups='base.group_system')
    readback_snapshot = fields.Json('执行回读依据', readonly=True, copy=False, groups='base.group_system')
    scheduled_job_id = fields.Many2one('ir.cron', readonly=True, copy=False, ondelete='restrict', groups='base.group_system')
    scheduled_by = fields.Many2one('res.users', string='批量提交人', readonly=True, copy=False)
    scheduled_at = fields.Datetime('批量提交时间', readonly=True, copy=False)
    queue_state = fields.Selection([('none', '未提交后台'), ('queued', '等待办理'), ('dispatched', '已办理或进入审批'),
                                    ('failed', '办理失败'), ('cancelled', '已取消')],
                                   string='后台办理状态', default='none', required=True, readonly=True, copy=False)

    def _compute_batch_limit(self):
        for batch in self:
            batch.batch_limit = CHANGE_BATCH_LIMIT

    def _check_management(self):
        _admin(self.env)
        self.check_access_rights('write')
        self.check_access_rule('write')
        if self.ids:
            self.env.cr.execute('SELECT id FROM sc_business_role_change WHERE id = ANY(%s) ORDER BY id FOR UPDATE', (self.ids,))
            self.invalidate_recordset()
        self.role_id._check_management()

    @api.model_create_multi
    def create(self, vals_list):
        _reject_context_defaults(self, {'name', 'role_id', 'operation', 'assignment_ids'})
        _admin(self.env)
        for vals in vals_list:
            if set(vals) - {'name', 'role_id', 'operation', 'assignment_ids'}:
                raise AccessError(_('预览、确认及执行结果不能由导入或客户端指定。'))
            role = self.env['sc.business.role'].browse(vals.get('role_id')).exists()
            role.ensure_one()
            role._check_management()
        result = super().create(vals_list)
        result._validate_selection()
        return result

    def write(self, vals):
        self._check_management()
        if any(batch.state != 'draft' for batch in self) or set(vals) - {'name', 'assignment_ids'}:
            raise AccessError(_('已预览的调整依据不可修改；请新建调整批次。'))
        result = super().write(vals)
        self._validate_selection()
        return result

    def unlink(self):
        self._check_management()
        if any(batch.state != 'draft' for batch in self):
            raise AccessError(_('已预览或执行的调整记录必须保留。'))
        return super().unlink()

    def _validate_selection(self):
        for batch in self:
            assignments = batch.assignment_ids
            assignments.check_access_rights('read')
            assignments.check_access_rule('read')
            if len(assignments) > CHANGE_BATCH_LIMIT:
                raise UserError(_('每批最多处理 %s 人，请分批办理。') % CHANGE_BATCH_LIMIT)
            if any(a.role_id != batch.role_id for a in assignments):
                raise ValidationError(_('本批用户授权必须属于同一个企业角色。'))

    def _closure(self, roots):
        groups = self.env['res.groups'].sudo().browse(sorted(roots)).exists()
        if set(groups.ids) != set(roots):
            raise UserError(_('授权引用的原生能力已变化，请重新核对。'))
        return set((groups | groups.trans_implied_ids).ids)

    def _model_permissions(self, groups):
        rows = self.env['ir.model.access'].sudo().search([
            ('active', '=', True), '|', ('group_id', '=', False), ('group_id', 'in', sorted(groups)),
        ])
        result = {}
        for row in rows:
            ops = result.setdefault(row.model_id.model, set())
            for name in ('read', 'create', 'write', 'unlink'):
                if row['perm_' + name]:
                    ops.add(name)
        return {key: sorted(ops) for key, ops in sorted(result.items()) if ops}

    def _plan(self):
        self.ensure_one()
        self._validate_selection()
        assignments = self.assignment_ids.sorted('user_id')
        if not assignments:
            raise UserError(_('请明确选择本批需要调整的用户授权。'))
        assignments._check_management()
        assignments.user_id._sc_lock_group_authority()
        target = self.role_id.current_version_id if self.operation == 'migrate' else self.env['sc.business.role.version']
        target_roots = target._grant_roots() if target else []
        if self.operation == 'migrate' and not target:
            raise UserError(_('角色尚未发布可用的能力方案。'))
        result = []
        for assignment in assignments:
            if self.operation == 'grant':
                if assignment.state == 'active':
                    raise UserError(_('该用户已获得此角色授权。'))
                assignment._check_target()
                target = assignment.version_id
                target_roots = target._grant_roots()
            elif assignment.state != 'active':
                raise UserError(_('预览只接受当前有效的用户授权。'))
            user = assignment.user_id
            if self.operation == 'migrate':
                assignment._check_target()
                if assignment.version_id == target:
                    raise UserError(_('所选用户已采用当前角色职责，无需重复调整。'))
            try:
                roots = user._sc_explicit_group_roots()
                sources = verified_sources(user.sudo().sc_group_authority_state)
                present = assignment._source() in sources
                if present == (self.operation == 'grant'):
                    raise GroupAuthorityGap('GROUP_AUTHORITY_ASSIGNMENT_SOURCE_MISMATCH')
            except GroupAuthorityGap as error:
                raise UserError(_('授权来源未确认，不能预览或执行：%s') % error) from error
            new_sources = replace_source(sources, assignment._source(), [])
            if target:
                new_key = 'business_role_assignment:%s:version:%s' % (assignment.id, target.id)
                new_sources = replace_source(new_sources, new_key, target_roots)
            before = self._model_permissions(self._closure(roots))
            after = self._model_permissions(self._closure(source_union(new_sources)))
            delta = []
            for model in sorted(set(before) | set(after)):
                added = sorted(set(after.get(model, [])) - set(before.get(model, [])))
                removed = sorted(set(before.get(model, [])) - set(after.get(model, [])))
                if added or removed:
                    delta.append({'model': model, 'added': added, 'removed': removed})
            result.append({
                'assignment_id': assignment.id, 'user_id': user.id,
                'from_version': assignment.version_id.id, 'to_version': target.id or False,
                'before': user._sc_authority_review_snapshot(),
                'after_sources': {key: sorted(values) for key, values in new_sources.items()},
                'target_mapping': deepcopy(target.sudo().authority_snapshot) if target else None,
                'before_model_permissions': before, 'after_model_permissions': after,
                'model_permission_delta': delta,
                'before_business_facts': {} if self.operation == 'grant' else deepcopy(assignment.version_id.sudo().authority_snapshot['capability_facts']),
                'after_business_facts': deepcopy(target.sudo().authority_snapshot['capability_facts']) if target else {},
                'removed_capabilities': sorted(set([] if self.operation == 'grant' else assignment.version_id.sudo().authority_snapshot['keys']) - set(target.sudo().authority_snapshot['keys'] if target else [])),
                'added_capabilities': sorted(set(target.sudo().authority_snapshot['keys'] if target else []) - set([] if self.operation == 'grant' else assignment.version_id.sudo().authority_snapshot['keys'])),
            })
        return {'role_id': self.role_id.id, 'operation': self.operation, 'target': target.id or False,
                'mapping': deepcopy(target.sudo().authority_snapshot) if target else None,
                'users': result}

    def _impact_text(self, plan):
        labels = {'read': _('查看'), 'create': _('新建'), 'write': _('修改'), 'unlink': _('删除')}
        model_labels = {m.model: m.name for m in self.env['ir.model'].sudo().search([])}
        lines = [_('以下变化已合并该用户的其他角色及独立授权；公司和项目范围保持不变。'),
                 _('可办理范围仍以公司、项目及业务约束为准。')]
        for row in plan['users']:
            user = self.env['res.users'].browse(row['user_id'])
            lines.append(user.name)
            lines.append(_('  角色职责新增：%s') % ('、'.join(row['after_business_facts'][key]['label'] for key in row['added_capabilities']) or _('无')))
            lines.append(_('  角色职责移除：%s') % ('、'.join(row['before_business_facts'][key]['label'] for key in row['removed_capabilities']) or _('无')))
            if not row['model_permission_delta']:
                lines.append(_('  最终业务数据操作权限无增减；仅变更授权依据。'))
            for delta in row['model_permission_delta']:
                lines.append('  %s: %s %s; %s %s' % (
                    model_labels.get(delta['model'], delta['model']), _('新增'),
                    '、'.join(labels[x] for x in delta['added']) or _('无'), _('撤销'),
                    '、'.join(labels[x] for x in delta['removed']) or _('无')))
        return '\n'.join(lines)

    def action_preview(self):
        if len(self) > 1:
            with self.env.cr.savepoint():
                for batch in self.sorted('id'):
                    batch.action_preview()
            return True
        self.ensure_one()
        self._check_management()
        if self.state != 'draft':
            raise UserError(_('本批已有固定预览，请新建调整批次。'))
        plan = self._plan()
        active_count = self.env['sc.user.role.assignment'].search_count([('role_id', '=', self.role_id.id), ('state', '=', 'active')])
        super(BusinessRoleChange, self.sudo()).write({'state': 'preview', 'preview_by': self.env.uid, 'preview_at': fields.Datetime.now(),
                       'target_version_id': plan['target'], 'preview_snapshot': plan,
                       'affected_count': len(plan['users']), 'retained_count': active_count if self.operation == 'grant' else active_count - len(plan['users']),
                       'impact_text': self._impact_text(plan)})
        return True

    def action_schedule(self):
        """Native cron supplies one transaction per batch; no manual commits."""
        self._check_management()
        with self.env.cr.savepoint():
            for batch in self.sorted('id'):
                if batch.state != 'preview' or batch.preview_by != self.env.user:
                    raise UserError(_('请先预览所选批次，并由预览人确认提交。'))
                if batch.queue_state == 'queued':
                    continue
                if batch.queue_state != 'none' or batch.review_ids:
                    raise UserError(_('本批已经办理或提交审批，请查看处理记录。'))
                if batch._plan() != batch.sudo().preview_snapshot:
                    raise UserError(_('授权事实已变化，请新建调整预览。'))
                # The system dispatcher owns scheduling/failure metadata.
                # _run_scheduled MUST drop sudo before any business execution;
                # otherwise a revoked actor would also prevent failure auditing.
                job = self.env['ir.cron'].sudo().create({
                    'name': _('角色授权调整 #%s') % batch.id,
                    'model_id': self.env['ir.model']._get_id(self._name),
                    'state': 'code', 'code': 'model.browse(%d)._run_scheduled()' % batch.id,
                    'user_id': SUPERUSER_ID, 'active': True, 'numbercall': 1,
                    'interval_number': 1, 'interval_type': 'minutes', 'nextcall': fields.Datetime.now(),
                })
                super(BusinessRoleChange, batch.sudo()).write({
                    'scheduled_job_id': job.id, 'scheduled_by': self.env.uid,
                    'scheduled_at': fields.Datetime.now(), 'queue_state': 'queued',
                })
        return True

    def _run_scheduled(self):
        self.ensure_one()
        # Read dispatch metadata and retain a failure audit even if the actor
        # lost access. Business actions below always drop sudo with with_user.
        self = self.sudo()
        self.env.cr.execute('SELECT id FROM sc_business_role_change WHERE id = %s FOR UPDATE', (self.id,))
        self.invalidate_recordset()
        if self.queue_state != 'queued' or self.state != 'preview':
            return True
        actor = self.sudo().scheduled_by
        try:
            with self.env.cr.savepoint():
                if not actor.active or actor != self.sudo().preview_by:
                    raise AccessError(_('批量提交人已停用或与预览人不一致。'))
                super(BusinessRoleChange, self.sudo()).write({'queue_state': 'dispatched'})
                batch = self.with_user(actor).with_context(allowed_company_ids=self.company_id.ids)
                batch.action_execute()
                if batch.state == 'failed':
                    super(BusinessRoleChange, self.sudo()).write({'queue_state': 'failed'})
        except (UserError, GroupAuthorityGap) as error:
            super(BusinessRoleChange, self.sudo().with_context(skip_validation_check=True)).write({
                'state': 'failed', 'queue_state': 'failed', 'executed_count': 0,
                'failed_count': self.affected_count, 'completed_at': fields.Datetime.now(),
                'result_text': str(error),
            })
        return True

    def request_validation(self):
        self.ensure_one()
        self._check_management()
        if self.state != 'preview' or self.preview_by != self.env.user:
            raise UserError(_('请先预览本批调整，再由发起人提交审批。'))
        if self._plan() != self.sudo().preview_snapshot:
            raise UserError(_('授权事实已变化，请新建调整预览。'))
        return super().request_validation()

    def restart_validation(self):
        # A fresh business batch is the retry boundary; retain the original review.
        raise UserError(_('本批审批记录必须保留；请新建调整批次重新预览。'))

    def validate_tier(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if self.state != 'preview' or not self.can_review:
            raise AccessError(_('当前用户不是本步骤审批人。'))
        return super().validate_tier()

    def reject_tier(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if self.state != 'preview' or not self.can_review:
            raise AccessError(_('当前用户不是本步骤审批人。'))
        return super().reject_tier()

    def _review_facts(self):
        self.ensure_one()
        reviews = [{
            'id': review.id, 'name': review.name, 'status': review.status,
            'status_label': review.display_status,
            'reviewer_ids': review.reviewer_ids.ids, 'reviewer_names': review.reviewer_ids.mapped('name'),
            'done_by': review.done_by.id or False, 'done_by_name': review.done_by.name or False,
            'reviewed_at': str(review.reviewed_date) if review.reviewed_date else False,
            'comment': review.comment or '',
        } for review in self.review_ids.sorted('sequence')]
        text = '\n'.join('%s · %s · %s' % (row['name'], row['status_label'], '、'.join(row['reviewer_names'])) for row in reviews)
        return reviews, text

    def action_cancel(self):
        self.ensure_one()
        self._check_management()
        if self.state == 'cancelled':
            return True
        if self.state not in ('draft', 'preview'):
            raise UserError(_('已经生效的授权不能取消待办，请另行办理撤销授权。'))
        # Native tier cancellation removes live tasks. Preserve their facts first.
        reviews, text = self._review_facts()
        # No user write, source projection, assignment update or token invalidation.
        super(BusinessRoleChange, self.sudo()).write({
            'state': 'cancelled', 'cancelled_by': self.env.uid, 'cancelled_at': fields.Datetime.now(),
            'queue_state': 'cancelled' if self.queue_state == 'queued' else self.queue_state,
            'cancelled_review_snapshot': reviews, 'cancelled_review_text': text,
            'result_text': _('本次未生效的调整已取消；用户现有授权保持不变。'),
        })
        self._update_counter({'review_deleted': True})
        return True

    def action_execute(self):
        # A single request executes exactly one bounded batch; no internal commits.
        self.ensure_one()
        self._check_management()
        if self.state == 'done':
            return True
        if self.queue_state == 'queued':
            raise UserError(_('本批已提交后台办理，请勿重复执行；尚未生效时可取消。'))
        if self.state != 'preview' or self.preview_by != self.env.user:
            raise UserError(_('请由预览本批的管理员明确确认；其他人需要重新预览。'))
        # Existing instances win over later edits to company/default policy.
        if self.review_ids:
            if self.validation_status != 'validated':
                raise UserError(_('本批审批尚未通过，授权保持不变。'))
        elif self.env['sc.approval.policy']._start_submission_review(self):
            return True
        return self._execute_confirmed()

    def _validate_tier(self, tiers=False):
        self.ensure_one()
        # Approval, cancellation and application serialize on the same batch
        # before native review rows are written, avoiding opposite lock orders.
        self.env.cr.execute('SELECT id FROM sc_business_role_change WHERE id = %s FOR UPDATE', (self.id,))
        self.invalidate_recordset()
        if self.state != 'preview':
            raise UserError(_('本次待办已结束，不能继续审批。'))
        result = super()._validate_tier(tiers)
        if self.state == 'preview' and self.review_ids and self.validation_status == 'validated':
            # Native approval has completed. Execute the already confirmed batch,
            # never call action_execute/request_validation again.
            try:
                with self.env.cr.savepoint():
                    if not self.preview_by.active:
                        raise AccessError(_('发起人已停用，已批准的调整尚未生效。'))
                    self.with_user(self.preview_by).with_context(
                        allowed_company_ids=self.company_id.ids,
                    )._execute_confirmed()
            except UserError as error:
                super(BusinessRoleChange, self.sudo().with_context(skip_validation_check=True)).write({
                    'state': 'failed', 'executed_count': 0, 'failed_count': self.affected_count,
                    'completed_at': fields.Datetime.now(), 'result_text': str(error),
                })
        return result

    def _execute_confirmed(self):
        self.ensure_one()
        self._check_management()
        if self.state != 'preview' or self.preview_by != self.env.user:
            raise UserError(_('本批不处于可生效状态。'))
        if self.review_ids and self.validation_status != 'validated':
            raise UserError(_('审批未通过，不能应用授权。'))
        expected = deepcopy(self.sudo().preview_snapshot)
        try:
            with self.env.cr.savepoint():
                if self._plan() != expected:
                    raise UserError(_('预览后授权来源、角色方案或用户范围发生变化，请新建预览，未覆盖新的授权事实。'))
                readback = []
                for row in expected['users']:
                    assignment = self.env['sc.user.role.assignment'].browse(row['assignment_id'])
                    if self.operation == 'revoke':
                        assignment._apply_revocation()
                    elif self.operation == 'grant':
                        assignment._apply_activation()
                    else:
                        old_version = assignment.version_id
                        user = assignment.user_id
                        user._sc_replace_group_authority_source(assignment._source(), [])
                        super(UserRoleAssignment, assignment).write({'version_id': self.target_version_id.id})
                        user._sc_replace_group_authority_source(assignment._source(), self.target_version_id._grant_roots())
                        assignment.role_id._event('migrate', self.target_version_id, assignment,
                                                  {'from_version': old_version.id, 'batch_id': self.id})
                    user = assignment.user_id
                    user._sc_explicit_group_roots()
                    sources = {key: sorted(values) for key, values in verified_sources(user.sudo().sc_group_authority_state).items()}
                    if sources != row['after_sources'] or self._model_permissions(set(user.sudo().groups_id.ids)) != row['after_model_permissions']:
                        raise UserError(_('授权回读与预览不一致，本批全部回滚。'))
                    readback.append(user._sc_authority_review_snapshot())
                review_facts, review_text = self._review_facts()
                super(BusinessRoleChange, self.sudo()).write({'state': 'done', 'confirmed_by': self.env.uid, 'completed_at': fields.Datetime.now(),
                               'executed_count': len(readback), 'failed_count': 0, 'readback_snapshot': readback,
                               'completed_review_snapshot': review_facts,
                               'completed_review_text': review_text or _('按企业审批默认机制生效。'),
                               'result_text': _('本批已全部执行并回读，其他来源和公司、项目范围保持不变。')})
        except (UserError, GroupAuthorityGap) as error:
            # The savepoint rolls back every user's binding, projection, token and audit.
            super(BusinessRoleChange, self.sudo().with_context(skip_validation_check=True)).write({'state': 'failed', 'confirmed_by': self.env.uid, 'completed_at': fields.Datetime.now(),
                           'executed_count': 0, 'failed_count': len(expected['users']),
                           'result_text': str(error)})
        return True
