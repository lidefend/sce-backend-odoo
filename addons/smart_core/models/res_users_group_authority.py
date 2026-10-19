"""Track submitted native group roots; unknown legacy grants are never inferred."""
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from ..security.group_assignment import (
    GroupAuthorityGap, apply_commands, verified_roots, replace_roles,
)

STATE_FIELD = 'sc_group_authority_state'


class ResUsersGroupAuthority(models.Model):
    _inherit = 'res.users'

    sc_group_authority_state = fields.Json(
        string='Explicit group authority snapshot', readonly=True, copy=False,
        groups='base.group_system',
        help='Submitted group roots and observed projection; absent or drifted history requires reconciliation.',
    )

    def _sc_lock_group_authority(self):
        if self.ids:
            self.env.cr.execute('SELECT id FROM res_users WHERE id = ANY(%s) ORDER BY id FOR UPDATE', (self.ids,))
            self.invalidate_recordset([STATE_FIELD, 'groups_id'])

    def _sc_store_group_authority(self, roots, reason=''):
        for user in self.sudo():
            previous = user.sc_group_authority_state or {}
            observed = sorted(user.groups_id.ids)
            state = {'version': 1, 'status': 'unresolved', 'reason': reason,
                     'revision': int(previous.get('revision', 0)) + 1, 'actor_uid': self.env.uid}
            if roots is not None:
                groups = self.env['res.groups'].sudo().browse(sorted(roots)).exists()
                closure = set((groups | groups.trans_implied_ids).ids)
                if set(groups.ids) == set(roots) and closure == set(observed):
                    state.update(status='tracked', roots=sorted(roots), observed=observed, reason='')
                else:
                    state['reason'] = 'GROUP_AUTHORITY_PROJECTION_DRIFT'
            # This private method alone may write provenance. No client context bypass.
            super(ResUsersGroupAuthority, user).write({STATE_FIELD: state})

    def _sc_explicit_group_roots(self, *, lock=True):
        self.ensure_one()
        if lock:
            self._sc_lock_group_authority()
        user = self.sudo()
        state = user.sc_group_authority_state or {}
        groups = self.env['res.groups'].sudo().browse(state.get('roots') or []).exists()
        return verified_roots(state, user.groups_id.ids, (groups | groups.trans_implied_ids).ids)

    def _sc_role_group_projection(self, assignable, commands, technical=()):
        self.ensure_one()
        try:
            roots = self._sc_explicit_group_roots()
            requested = apply_commands(roots & set(assignable), commands)
            return replace_roles(roots, assignable, requested, technical)
        except GroupAuthorityGap as error:
            raise UserError(_(
                '无法完成角色权限变更：授权来源未确认、已有投影发生变化或角色请求不合法。'
                '请由权限管理员核对显式授权；当前授权保持不变。错误码：%s'
            ) % str(error)) from error

    def _sc_check_authority_reconciliation(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('GROUP_AUTHORITY_RECONCILIATION_ADMIN_REQUIRED')
        self.check_access_rights('write')
        self.check_access_rule('write')

    def _sc_authority_review_snapshot(self):
        self.ensure_one()
        self.invalidate_recordset([STATE_FIELD, 'groups_id', 'company_id', 'company_ids', 'active'])
        groups = self.sudo().groups_id
        groups.invalidate_recordset(['implied_ids', 'trans_implied_ids'])
        return {
            'user_id': self.id, 'groups': sorted(groups.ids), 'state': self.sudo().sc_group_authority_state or None,
            'graph': [[group.id, sorted(group.implied_ids.ids)] for group in groups.sorted('id')],
            'company_id': self.company_id.id, 'company_ids': sorted(self.company_ids.ids),
            'active': self.active,
        }

    def action_sc_review_group_authority(self):
        self.ensure_one()
        self._sc_check_authority_reconciliation()
        review = self.env['sc.group.authority.reconcile'].create({'user_id': self.id})
        return {
            'type': 'ir.actions.act_window', 'name': _('确认授权来源'),
            'res_model': review._name, 'res_id': review.id,
            'view_mode': 'form', 'target': 'new',
        }

    def action_sc_group_authority_confirmations(self):
        self.ensure_one()
        self._sc_check_authority_reconciliation()
        return {
            'type': 'ir.actions.act_window', 'name': _('授权来源确认记录'),
            'res_model': 'sc.group.authority.confirmation', 'view_mode': 'tree,form',
            'domain': [('user_id', '=', self.id)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        if any(STATE_FIELD in vals for vals in vals_list):
            raise AccessError('GROUP_AUTHORITY_STATE_SERVER_OWNED')
        plans = []
        for vals in vals_list:
            try:
                # No submitted groups means native defaults, whose origin is unknown here.
                roots = apply_commands(set(), vals['groups_id']) if 'groups_id' in vals else None
                if any(key.startswith(('sel_groups_', 'in_group_')) for key in vals):
                    roots = None
            except GroupAuthorityGap:
                roots = None
            plans.append(roots)
        users = super().create(vals_list)
        for user, roots in zip(users, plans):
            user._sc_store_group_authority(roots, 'GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
        return users

    def write(self, vals):
        if STATE_FIELD in vals:
            raise AccessError('GROUP_AUTHORITY_STATE_SERVER_OWNED')
        reified = any(key.startswith(('sel_groups_', 'in_group_')) for key in vals)
        if 'groups_id' not in vals and not reified:
            return super().write(vals)
        self._sc_lock_group_authority()
        plans = {}
        for user in self:
            try:
                try:
                    initial = user._sc_explicit_group_roots()
                except GroupAuthorityGap:
                    initial = None
                roots = None if reified else apply_commands(initial, vals['groups_id'])
            except GroupAuthorityGap:
                roots = None
            plans[user.id] = roots
        result = super().write(vals)
        for user in self:
            user._sc_store_group_authority(plans[user.id], 'GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
        return result


class ResGroupsAuthorityInvalidation(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        affected = self.users if {'users', 'implied_ids'} & set(vals) else self.env['res.users']
        affected._sc_lock_group_authority()
        result = super().write(vals)
        if {'users', 'implied_ids'} & set(vals):
            affected |= self.users
            affected._sc_store_group_authority(None, 'GROUP_AUTHORITY_REVERSE_OR_DEFINITION_WRITE')
            affected._sc_bump_token_epoch()
        return result

    def unlink(self):
        affected = self.users
        affected._sc_lock_group_authority()
        result = super().unlink()
        affected = affected.exists()
        affected.invalidate_recordset(['groups_id'])
        affected._sc_store_group_authority(None, 'GROUP_AUTHORITY_GROUP_DELETED')
        affected._sc_bump_token_epoch()
        return result
