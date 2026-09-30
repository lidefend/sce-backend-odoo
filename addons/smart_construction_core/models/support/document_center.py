# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.exceptions import UserError

_DOCUMENT_APPROVAL_TOKEN = object()


class ScProjectDocument(models.Model):
    """F. 工程资料中心"""
    _name = 'sc.project.document'
    _description = '工程资料'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tier.validation']
    _state_from = ['review']
    _state_to = ['approved']

    reject_reason = fields.Text('驳回原因', readonly=True, copy=False)
    _order = 'project_id, doc_type_id, create_date desc'

    name = fields.Char('资料名称', required=True, tracking=True)
    document_kind = fields.Selection(
        [
            ('site', '现场资料'),
            ('safety', '安全资料'),
            ('quality', '质量资料'),
            ('self_inspection', '自检资料'),
            ('archive', '归档备案'),
        ],
        string='资料业务分类',
        default='site',
        required=True,
        index=True,
        tracking=True,
    )

    project_id = fields.Many2one(
        'project.project', string='所属项目',
        required=True, index=True, tracking=True
    )
    wbs_id = fields.Many2one(
        'construction.work.breakdown', string='工程结构',
        index=True
    )
    task_id = fields.Many2one(
        'project.task', string='关联任务/工序',
        index=True
    )
    contract_id = fields.Many2one(
        'account.analytic.account',
        string='关联合同',
        index=True
    )

    # 资料分类：全走 sc.dictionary
    doc_type_id = fields.Many2one(
        'sc.dictionary', string='资料大类',
        domain=[('type', '=', 'doc_type')],
        required=True, index=True, tracking=True
    )
    doc_subtype_id = fields.Many2one(
        'sc.dictionary', string='资料细类',
        domain=[('type', '=', 'doc_subtype')],
        tracking=True
    )

    date_doc = fields.Date('资料日期')
    version = fields.Char('版本号/版次')

    is_mandatory = fields.Boolean(
        '是否必备资料',
        help='若勾选，在结算/验收/付款时可作为前置校验依据。'
    )

    responsible_id = fields.Many2one(
        'res.users', string='责任人',
        default=lambda self: self.env.user, index=True
    )
    company_id = fields.Many2one(
        'res.company', string='公司',
        default=lambda self: self.env.company,
        readonly=True
    )

    note = fields.Text('说明/备注')
    legacy_source_model = fields.Char('历史来源模型', index=True, readonly=True)
    legacy_record_id = fields.Char('历史记录ID', index=True, readonly=True)
    legacy_document_state = fields.Char('历史状态', index=True, readonly=True)

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'sc_project_document_attachment_rel',
        'document_id', 'attachment_id',
        string='附件'
    )

    state = fields.Selection([
        ('draft', '草稿'),
        ('review', '审核中'),
        ('approved', '已批准'),
        ('done', '已归档'),
        ('cancel', '作废'),
    ], string='状态', default='draft', tracking=True)

    attachment_count = fields.Integer(
        '附件数量', compute='_compute_attachment_count'
    )

    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('state', self.env.context.get('default_state', 'draft')) != 'draft' for vals in vals_list):
            raise UserError('资料状态必须通过办理动作产生。')
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals and self.env.context.get('sc_document_approval_token') is not _DOCUMENT_APPROVAL_TOKEN:
            raise UserError('资料状态必须通过办理动作产生。')
        protected = {'name', 'project_id', 'company_id', 'document_kind', 'doc_type_id', 'doc_subtype_id',
                     'wbs_id', 'task_id', 'contract_id', 'date_doc', 'version', 'is_mandatory', 'attachment_ids'}
        if protected.intersection(vals) and any(record.state != 'draft' for record in self):
            raise UserError('请先通过重置流程回到草稿，再修改资料审核内容。')
        return super().write(vals)

    def _write_approval_state(self, values):
        return self.with_context(sc_document_approval_token=_DOCUMENT_APPROVAL_TOKEN).write(values)

    def _check_document_operation(self, label):
        for record in self:
            if record.company_id != record.project_id.company_id:
                raise UserError('资料公司必须与所属项目一致。')
            record.project_id._ensure_operation_allowed(operation_label=label, blocked_states=('paused', 'closed'))

    def action_submit(self):
        for record in self:
            if record.state not in ('draft', 'review'):
                raise UserError('只有草稿或待重新提交的资料可以提交。')
        self._check_document_operation('提交资料')
        self.with_context(skip_validation_check=True)._write_approval_state({'state': 'review'})
        for record in self:
            if not self.env['sc.approval.policy']._start_submission_review(record):
                record._write_approval_state({'state': 'approved', 'reject_reason': False})
        return True

    def action_on_tier_approved(self):
        for record in self:
            if record.state == 'review' and record.review_ids and record.validation_status == 'validated':
                record._check_document_operation('审核资料')
                record._write_approval_state({'state': 'approved', 'reject_reason': False})

    def action_on_tier_rejected(self):
        for record in self:
            if record.state == 'review' and record.review_ids and record.validation_status == 'rejected':
                reviews = record.review_ids.filtered(lambda review: review.status == 'rejected' and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else '统一审批驳回（未填写原因）'
                record.with_context(skip_validation_check=True)._write_approval_state({'state': 'draft', 'reject_reason': reason})

    def action_archive(self):
        for record in self:
            if record.state != 'approved':
                raise UserError('只有已批准资料可以归档。')
            self.env['sc.approval.policy']._assert_submission_approved(record, ('approved',))
        self._check_document_operation('归档资料')
        self._write_approval_state({'state': 'done'})
        return True

    def action_approve(self):
        # Historical callers used this method for archival, not a review decision.
        return self.action_archive()

    def action_cancel(self):
        if any(record.state == 'cancel' for record in self):
            raise UserError('资料已作废。')
        self.with_context(skip_validation_check=True)._write_approval_state({'state': 'cancel'})
        return True

    def action_reset_to_draft(self):
        if any(record.state not in ('done', 'cancel') for record in self):
            raise UserError('只有归档或作废资料可以重新办理。')
        self.restart_validation()
        self.with_context(skip_validation_check=True)._write_approval_state({'state': 'draft'})
        return True
