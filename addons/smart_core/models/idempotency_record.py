# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields, models


class ScIdempotencyRecord(models.Model):
    """统一写动作幂等记录（G7 幂等基建）。

    一行 = 一次写动作执行的仲裁记录：
    - (company_id, actor_uid, idempotency_key) 部分唯一索引在数据库层仲裁并发重复
      （两个同键请求并发插入时仅一个成功，另一个触发唯一冲突→回读→replay/conflict）；
    - status=inflight 为执行期瞬态（随请求事务提交为 done，或整体回滚消失）；
    - result_json 保存可重放响应；sc.audit.log 仍是审计轨迹权威，本模型是去重权威。
    """

    _name = "sc.idempotency.record"
    _description = "SC Write Idempotency Record"
    _order = "id desc"

    name = fields.Char(
        required=True,
        index=True,
        help="Dedup scope label, e.g. intent/event code (MY_WORK_COMPLETE_BATCH).",
    )
    idempotency_key = fields.Char(required=True, index=True)
    idempotency_fingerprint = fields.Char(required=True)
    status = fields.Selection(
        [("inflight", "In Flight"), ("done", "Done"), ("failed", "Failed")],
        default="inflight",
        required=True,
        index=True,
    )
    actor_uid = fields.Many2one("res.users", index=True, ondelete="set null")
    company_id = fields.Many2one("res.company", index=True, ondelete="set null")
    model = fields.Char()
    res_id = fields.Integer()
    result_json = fields.Json()
    trace_id = fields.Char(index=True)
    created_at = fields.Datetime(index=True)
    finished_at = fields.Datetime()

    def init(self):
        """DB 层并发仲裁：同 (company, actor, key) 永久唯一（部分索引）。"""
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS sc_idempotency_record_key_unique
                ON sc_idempotency_record (company_id, actor_uid, idempotency_key)
             WHERE idempotency_key IS NOT NULL
            """
        )
