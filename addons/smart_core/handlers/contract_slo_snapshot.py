# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from odoo.addons.smart_core.core import contract_slo_persistence as slo_store
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler


DEFAULT_WINDOW_SECONDS = 86400
DEFAULT_BUCKET_SECONDS = 3600
MAX_WINDOW_SECONDS = 30 * 86400
MIN_BUCKET_SECONDS = 60


class ContractSloSnapshotHandler(BaseIntentHandler):
    """契约 SLO 按版本窗口聚合与趋势读取（L5 契约 SLO 遥测读模型）。

    只读：从持久化的观测行读出窗口内的按版本成功率/降级率/完整性失败率，
    并按时间桶给出趋势。聚合复用纯核心 ``contract_slo_telemetry``，本入口
    不重新实现任何比率公式，也不回写任何数据。
    """

    INTENT_TYPE = "smart_core.contract_slo.snapshot"
    DESCRIPTION = "契约 SLO 按版本聚合与趋势（读模型）"
    VERSION = "1.0.0"
    MACHINE_ACCESS = "read"
    SOURCE_KIND = "contract_slo_observation_read_model"
    SOURCE_AUTHORITIES = ("sc.contract.slo.observation", "smart_core.contract_slo_telemetry")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": cls.INTENT_TYPE,
        }

    @staticmethod
    def _positive_int(value, default, *, minimum=1, maximum=None):
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        if number < minimum:
            return default
        if maximum is not None and number > maximum:
            return maximum
        return number

    def handle(self, payload=None, ctx=None):
        started = time.time()
        params = self.params if isinstance(self.params, dict) else {}
        window_seconds = self._positive_int(
            params.get("window_seconds") or params.get("windowSeconds"),
            DEFAULT_WINDOW_SECONDS,
            maximum=MAX_WINDOW_SECONDS,
        )
        bucket_seconds = self._positive_int(
            params.get("bucket_seconds") or params.get("bucketSeconds"),
            DEFAULT_BUCKET_SECONDS,
            minimum=MIN_BUCKET_SECONDS,
            maximum=window_seconds,
        )
        contract_version = str(params.get("contract_version") or params.get("contractVersion") or "").strip()
        now = slo_store.utcnow_epoch()

        aggregate = slo_store.aggregate_window(
            self.env, window_seconds=window_seconds, contract_version=contract_version or None, now=now
        )
        trend = slo_store.window_trend(
            self.env,
            window_seconds=window_seconds,
            bucket_seconds=bucket_seconds,
            contract_version=contract_version or None,
            now=now,
        )
        return {
            "status": "success",
            "ok": True,
            "data": {
                "query": {
                    "windowSeconds": window_seconds,
                    "bucketSeconds": bucket_seconds,
                    "contractVersion": contract_version,
                    "observedAt": now,
                },
                "store": slo_store.observation_store_summary(self.env),
                "aggregate": aggregate,
                "trend": trend,
            },
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - started) * 1000),
                "source_kind": self.SOURCE_KIND,
                "source_authorities": list(self.SOURCE_AUTHORITIES),
                "source_authority": self.source_authority_contract(),
            },
        }
