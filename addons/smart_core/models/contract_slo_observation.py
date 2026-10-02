# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields, models


class ScContractSloObservation(models.Model):
    """统一页面契约投递的 SLO 观测持久层（L5 契约 SLO 遥测）。

    一行 = 一次运行时契约投递的可聚合观测，身份取自契约自身已经发出的
    ``meta.lifecycle`` 证据（schema/contract 版本、来源类型与摘要、stage），
    因此聚合按版本天然分组，不依赖请求侧任何猜测字段。

    本模型只做持久化与读取，不参与投递判定：写入失败必须被吞掉（fail-open），
    否则遥测会反向破坏它所度量的投递。保留期由
    ``smart_core.contract_slo.retention_days`` 配置，清理走既有观测入口。
    """

    _name = "sc.contract.slo.observation"
    _description = "Contract SLO Observation"
    _order = "observed_at desc, id desc"

    schema_id = fields.Char(string="Schema Id", required=True, index=True)
    schema_version = fields.Char(string="Schema Version", required=True, index=True)
    contract_version = fields.Char(string="Contract Version", required=True, index=True)
    source_type = fields.Char(string="Source Type", required=True, index=True)
    source_sha256 = fields.Char(string="Source Sha256", required=True, index=True)
    stage = fields.Char(string="Stage", required=True, index=True)
    published_version_ref = fields.Char(string="Published Version Ref", index=True)

    outcome = fields.Selection(
        selection=[
            ("success", "Success"),
            ("degraded", "Degraded"),
            ("integrity_failure", "Integrity Failure"),
        ],
        string="Outcome",
        required=True,
        index=True,
    )
    degradation_reasons_json = fields.Text(string="Degradation Reasons JSON")
    latency_ms = fields.Integer(string="Latency (ms)")
    observed_at = fields.Datetime(string="Observed At", required=True, index=True)
    client_type = fields.Char(string="Client Type", index=True)
    request_id = fields.Char(string="Request Id", index=True)
    company_id = fields.Many2one("res.company", string="Company", index=True, ondelete="set null")

    def init(self):
        """按版本 + 时间聚合是主要读法，用复合索引固定下来。"""
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS sc_contract_slo_observation_version_time
                ON sc_contract_slo_observation (contract_version, observed_at)
            """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS sc_contract_slo_observation_identity_time
                ON sc_contract_slo_observation
                   (schema_id, contract_version, stage, observed_at)
            """
        )
