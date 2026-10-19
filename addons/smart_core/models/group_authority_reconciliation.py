"""Explicit administrator confirmation of present group roots, never history inference."""
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class GroupAuthorityReconciliation(models.TransientModel):
    _name = 'sc.group.authority.reconcile'
    _description = '授权来源确认'

    user_id = fields.Many2one('res.users', required=True, readonly=True)
    observed_group_ids = fields.Many2many(
        'res.groups', 'sc_authority_review_observed_rel', 'review_id', 'group_id',
        string='当前有效组', readonly=True)
    root_group_ids = fields.Many2many(
        'res.groups', 'sc_authority_review_root_rel', 'review_id', 'group_id',
        string='明确授权的根组')
    note = fields.Text(string='确认依据')
    snapshot = fields.Json(readonly=True, copy=False)
    confirmed = fields.Boolean(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            if {'snapshot', 'observed_group_ids', 'confirmed'} & set(vals):
                raise AccessError('GROUP_AUTHORITY_REVIEW_SERVER_OWNED')
            user = self.env['res.users'].browse(vals.get('user_id')).exists()
            user.ensure_one()
            user._sc_check_authority_reconciliation()
            user._sc_lock_group_authority()
            snapshot = user._sc_authority_review_snapshot()
            prepared.append(dict(vals, snapshot=snapshot, confirmed=False,
                                 observed_group_ids=[(6, 0, snapshot['groups'])]))
        return super().create(prepared)

    def write(self, vals):
        if {'user_id', 'snapshot', 'observed_group_ids', 'confirmed'} & set(vals):
            raise AccessError('GROUP_AUTHORITY_REVIEW_SERVER_OWNED')
        self.check_access_rights('write')
        self.check_access_rule('write')
        if self.ids:
            # Serialize editor writes with confirmation on the same wizard row.
            self.env.cr.execute(
                'SELECT id FROM sc_group_authority_reconcile WHERE id = ANY(%s) ORDER BY id FOR UPDATE',
                (self.ids,),
            )
            self.invalidate_recordset(['confirmed'])
            if any(self.mapped('confirmed')):
                raise AccessError('GROUP_AUTHORITY_REVIEW_IMMUTABLE')
        return super().write(vals)

    def action_confirm(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        self.env.cr.execute('SELECT id FROM sc_group_authority_reconcile WHERE id = %s FOR UPDATE', (self.id,))
        self.invalidate_recordset()
        user = self.user_id
        user._sc_check_authority_reconciliation()
        user._sc_lock_group_authority()
        snapshot = user._sc_authority_review_snapshot()
        if self.confirmed or self.snapshot != snapshot:
            raise UserError(_('授权状态已变化或确认已完成，请重新打开确认入口。'))
        note = (self.note or '').strip()
        if not note:
            raise UserError(_('请填写授权来源的确认依据。'))
        roots = self.root_group_ids
        if not roots or set((roots | roots.trans_implied_ids).ids) != set(snapshot['groups']):
            raise UserError(_('所选根组的权限闭包必须与当前有效权限完全一致；本操作不增删权限。'))
        user._sc_store_group_authority(set(roots.ids))
        user._sc_explicit_group_roots()
        self.env['sc.group.authority.confirmation']._record_confirmation(user, roots, snapshot, note)
        super(GroupAuthorityReconciliation, self).write({'confirmed': True})
        return {'type': 'ir.actions.act_window_close'}


class GroupAuthorityConfirmation(models.Model):
    _name = 'sc.group.authority.confirmation'
    _description = '授权来源确认记录'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', readonly=True, ondelete='set null')
    actor_id = fields.Many2one('res.users', readonly=True, ondelete='set null')
    root_group_ids_json = fields.Json(readonly=True)
    before_snapshot = fields.Json(readonly=True)
    after_state = fields.Json(readonly=True)
    note = fields.Text(readonly=True)

    @api.model
    def _record_confirmation(self, user, roots, snapshot, note):
        return super(GroupAuthorityConfirmation, self.sudo()).create({
            'user_id': user.id, 'actor_id': self.env.uid,
            'root_group_ids_json': sorted(roots.ids), 'before_snapshot': snapshot,
            'after_state': user.sudo().sc_group_authority_state, 'note': note,
        })

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError('GROUP_AUTHORITY_AUDIT_SERVER_OWNED')

    def write(self, vals):
        raise AccessError('GROUP_AUTHORITY_AUDIT_IMMUTABLE')

    def unlink(self):
        raise AccessError('GROUP_AUTHORITY_AUDIT_IMMUTABLE')
