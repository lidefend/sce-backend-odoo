# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import api, fields, models

from odoo.addons.smart_core.core import contract_slo_persistence as slo_store
from odoo.addons.smart_core.core import model_table_recovery


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
        """按版本 + 时间聚合是主要读法，用复合索引固定下来。

        ``Registry.check_tables_exist`` 对缺表模型只调用本方法、不调用
        ``_auto_init``，所以这里必须先确保基表存在，否则任何缺少该表的数据库在模块
        升级时都会以 ``UndefinedTable`` 崩溃（回归锁定见
        tests/test_smart_core_model_init_table_recovery.py）。
        """
        model_table_recovery.ensure_table_on_init(self)
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

    @api.model
    def cron_prune(self):
        """Retention sweep for the observation store (fail-open).

        The retention horizon was declared but never enforced, so the store grew
        without bound once persistence was on. This is the scheduled half: it
        drops only rows older than ``smart_core.contract_slo.retention_days`` and
        returns how many it removed.

        It deliberately does not gate on ``persist_enabled``: rows written while
        persistence was on must still age out after it is switched off. The
        sweep is fail-open because telemetry must never harm the platform, so a
        failure leaves rows in place instead of failing the cron run.
        """
        return slo_store.prune_observations(self.env)
