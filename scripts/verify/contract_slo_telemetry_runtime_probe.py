# -*- coding: utf-8 -*-
"""Runtime half of the contract SLO telemetry gap.

Run with:
  make verify.backend.contract_slo_telemetry.runtime

This script is executed by ``odoo shell`` against the isolated
contract-lifecycle profile (project ``sc-contract-lifecycle-v1``, database
``sc_contract_lifecycle``). It drives real ``ui.contract.v2`` deliveries through
the production handler, captures the ``contractSlo`` line the production sink
actually emits, and binds each observation back through the declaration
consumer (``contract_slo_telemetry``), so a passing run means the runtime
delivery path emitted a schema-valid, identity-complete observation rather than
that a string merely appeared.

Baseline first: the normal path must emit ``success`` before any injected state
is treated as detected. Injection proof lives outside this script (neuter the
emission boundary, prove zero lines, restore byte-identical); this script only
records the healthy baseline into a machine-readable report consumed by the
host-side schema guard.
"""

import json
import logging

from odoo.addons.smart_core.core import contract_slo_persistence as store
from odoo.addons.smart_core.core import contract_slo_telemetry as slo
from odoo.addons.smart_core.handlers.contract_slo_snapshot import ContractSloSnapshotHandler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.handlers import ui_contract_v2_authority as authority


PROBE_PATH = "/tmp/contract_slo_telemetry_runtime_probe.json"
LOG_TARGET = "odoo.addons.smart_core.handlers.ui_contract_v2_authority"
LINE_PREFIX = slo.OBSERVATION_LINE_KEY + " "


class _LineCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.lines = []

    def emit(self, record):
        try:
            self.lines.append(record.getMessage())
        except Exception as exc:  # never break the delivery under measurement
            self.lines.append("CAPTURE_ERROR:%s" % exc)


def _env():
    return globals()["env"]


def _deliver(request):
    """One real ui.contract.v2 delivery through the production handler."""
    payload = {"params": dict(request)}
    handler = UiContractV2Handler(env=_env(), su_env=_env())
    result = handler.handle(payload=payload, ctx=dict(_env().context or {}))
    envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    meta = envelope.get("meta") if isinstance(envelope, dict) else {}
    return envelope, (meta if isinstance(meta, dict) else {})


def _slo_lines(lines):
    return [line for line in lines if isinstance(line, str) and line.startswith(LINE_PREFIX)]


def _request(model, view_type):
    return {
        "model": model,
        "view_type": view_type,
        "source_type": "ui.contract",
        "client_type": "web_pc",
        "delivery_profile": "full",
        "force_refresh": True,
    }


def _run():
    checks = []
    observations = []
    logger = logging.getLogger(LOG_TARGET)
    capture = _LineCapture()
    previous_level = logger.level
    logger.addHandler(capture)
    logger.setLevel(logging.INFO)
    try:
        # Baseline: the un-injected path must deliver and emit one success line.
        envelope, meta = _deliver(_request("res.partner", "form"))
        checks.append(("baseline_delivery_ok", isinstance(envelope, dict) and envelope.get("ok") is True,
                       {"ok": bool(isinstance(envelope, dict) and envelope.get("ok") is True),
                        "intent": str(meta.get("intent") or "")}))

        lines = _slo_lines(capture.lines)
        checks.append(("baseline_emits_exactly_one_line", len(lines) == 1, {"lineCount": len(lines)}))

        parsed = slo.parse_observation_line(lines[0]) if lines else None
        checks.append(("emitted_line_parses_as_observation", isinstance(parsed, dict), {}))

        identity = parsed.get("identity") if isinstance(parsed, dict) else None
        complete = bool(isinstance(identity, dict))
        missing = []
        if complete:
            for field in slo.IDENTITY_FIELDS:
                if not str(identity.get(field) or "").strip():
                    missing.append(field)
            complete = not missing
        checks.append(("observation_identity_complete", complete, {"missing": missing}))
        checks.append(("emission_stage_is_runtime_delivery",
                       isinstance(identity, dict) and identity.get("stage") == "runtime_delivery",
                       {"stage": (identity or {}).get("stage")}))
        checks.append(("baseline_outcome_success",
                       isinstance(parsed, dict) and parsed.get("outcome") == slo.OUTCOME_SUCCESS,
                       {"outcome": (parsed or {}).get("outcome")}))

        # Declaration consumer must accept the observation unchanged.
        if isinstance(parsed, dict):
            observations.append(parsed)
        first_aggregate = slo.aggregate_observations(observations)
        checks.append(("declaration_consumer_accepts_observation",
                       first_aggregate["acceptedObservations"] == len(observations)
                       and first_aggregate["rejectedObservations"] == 0,
                       {"accepted": first_aggregate["acceptedObservations"],
                        "rejected": first_aggregate["rejectedObservations"]}))
        checks.append(("baseline_success_rate_is_one",
                       bool(first_aggregate["versions"])
                       and first_aggregate["versions"][0]["successRate"] == 1.0,
                       {"successRate": first_aggregate["versions"][0]["successRate"]
                        if first_aggregate["versions"] else None}))

        # Repeat the same delivery: identical identity must group into one row.
        capture.lines = []
        _deliver(_request("res.partner", "form"))
        second_lines = _slo_lines(capture.lines)
        second = slo.parse_observation_line(second_lines[0]) if len(second_lines) == 1 else None
        checks.append(("repeat_delivery_emits_one_line", len(second_lines) == 1,
                       {"lineCount": len(second_lines)}))
        if isinstance(second, dict):
            observations.append(second)
        grouped = slo.aggregate_observations(observations)
        checks.append(("same_identity_groups_into_one_row",
                       grouped["versionCount"] == 1 and grouped["versions"][0]["observations"] == len(observations),
                       {"versionCount": grouped["versionCount"],
                        "observations": grouped["versions"][0]["observations"] if grouped["versions"] else None}))

        # A different surface must emit under its own identity, not borrow one.
        capture.lines = []
        list_envelope, _list_meta = _deliver(_request("res.partner", "list"))
        list_lines = _slo_lines(capture.lines)
        checks.append(("distinct_surface_delivery_ok",
                       isinstance(list_envelope, dict) and list_envelope.get("ok") is True,
                       {"ok": bool(isinstance(list_envelope, dict) and list_envelope.get("ok") is True)}))
        checks.append(("distinct_surface_emits_one_line", len(list_lines) == 1, {"lineCount": len(list_lines)}))
        list_obs = slo.parse_observation_line(list_lines[0]) if len(list_lines) == 1 else None
        checks.append(("distinct_surface_observation_valid", isinstance(list_obs, dict), {}))
        if isinstance(list_obs, dict):
            observations.append(list_obs)
        final = slo.aggregate_observations(observations)
        checks.append(("every_emitted_observation_accepted",
                       final["acceptedObservations"] == len(observations) and final["rejectedObservations"] == 0,
                       {"accepted": final["acceptedObservations"], "rejected": final["rejectedObservations"],
                        "versionCount": final["versionCount"]}))
        checks.append(("no_delivery_reported_integrity_failure",
                       all(obs.get("outcome") != slo.OUTCOME_INTEGRITY_FAILURE for obs in observations),
                       {}))
    finally:
        logger.removeHandler(capture)
        logger.setLevel(previous_level)

    checks.extend(_run_persistence())
    checks.extend(_run_retention_cron())

    failed = [name for name, ok, _detail in checks if not ok]
    return {
        "probe": "contract_slo_telemetry_runtime",
        "database": _env().cr.dbname,
        "logTarget": LOG_TARGET,
        "checkCount": len(checks),
        "failedCount": len(failed),
        "failed": failed,
        "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
        "observations": observations,
        "aggregate": final,
    }


def _run_persistence():
    """Durable store + trend read model, on top of the deliveries just made.

    Enabling persistence is a test configuration write, so the original value is
    captured first and restored before the transaction is committed; the check
    set fails if the restore does not hold. The committed rows are the durable
    evidence the read model is asked to reproduce.
    """
    checks = []
    env = _env()
    param = env["ir.config_parameter"].sudo()
    original = param.get_param(store.PERSIST_PARAM, None)
    try:
        param.set_param(store.PERSIST_PARAM, "1")
        checks.append(("persistence_enabled_for_the_check", store.persistence_enabled(env), {}))

        before = env[store.MODEL_NAME].sudo().search_count([])
        logger = logging.getLogger(LOG_TARGET)
        capture = _LineCapture()
        previous_level = logger.level
        logger.addHandler(capture)
        logger.setLevel(logging.INFO)
        try:
            for request in (_request("res.partner", "form"), _request("res.partner", "form"),
                            _request("res.partner", "list")):
                _deliver(request)
        finally:
            logger.removeHandler(capture)
            logger.setLevel(previous_level)
        emitted = [slo.parse_observation_line(line) for line in _slo_lines(capture.lines)]
        emitted = [item for item in emitted if item]
        after = env[store.MODEL_NAME].sudo().search_count([])
        checks.append(("each_delivery_persisted_one_row", after - before == len(emitted) == 3,
                       {"before": before, "after": after, "emitted": len(emitted)}))

        rows = store.read_observations(env, limit=200)
        stored = {(o["identity"].get("sourceType"), o["identity"].get("contractVersion"), o["outcome"]) for o in rows}
        wanted = {(o["identity"].get("sourceType"), o["identity"].get("contractVersion"), o["outcome"]) for o in emitted}
        checks.append(("stored_rows_round_trip_the_emitted_identity", wanted <= stored,
                       {"wanted": sorted(wanted), "storedSample": sorted(stored)}))

        aggregate = store.aggregate_window(env, window_seconds=3600)
        checks.append(("store_aggregate_accepts_the_persisted_rows",
                       aggregate["acceptedObservations"] >= 3 and aggregate["rejectedObservations"] == 0,
                       {"accepted": aggregate["acceptedObservations"],
                        "rejected": aggregate["rejectedObservations"],
                        "versionCount": aggregate["versionCount"]}))

        trend = store.window_trend(env, window_seconds=3600, bucket_seconds=600)
        placed = sum(bucket["aggregate"]["totalObservations"] for bucket in trend["buckets"])
        checks.append(("trend_places_every_row_in_one_bucket",
                       placed == aggregate["acceptedObservations"] and trend["unplacedObservations"] == 0,
                       {"placed": placed, "unplaced": trend["unplacedObservations"],
                        "bucketCount": trend["bucketCount"]}))
        checks.append(("trend_keeps_versions_in_separate_rows",
                       any(bucket["aggregate"]["versionCount"] >= 2 for bucket in trend["buckets"]),
                       {"versionCounts": [b["aggregate"]["versionCount"] for b in trend["buckets"]]}))

        handler = ContractSloSnapshotHandler(
            env=env,
            su_env=env,
            payload={"params": {"window_seconds": 3600, "bucket_seconds": 600}},
        )
        snapshot = handler.handle(payload={"params": {"window_seconds": 3600, "bucket_seconds": 600}},
                                  ctx=dict(env.context or {}))
        data = snapshot.get("data") if isinstance(snapshot, dict) else {}
        checks.append(("read_intent_reports_the_store",
                       bool(snapshot.get("ok"))
                       and (data.get("store") or {}).get("observationCount", 0) >= 3
                       and (data.get("aggregate") or {}).get("acceptedObservations", 0) >= 3,
                       {"store": (data.get("store") or {}).get("observationCount"),
                        "accepted": (data.get("aggregate") or {}).get("acceptedObservations")}))

        checks.append(("retention_prune_keeps_the_fresh_rows",
                       store.prune_observations(env, retention_days_value=1) == 0, {}))
    finally:
        if original is None:
            param.search([("key", "=", store.PERSIST_PARAM)]).unlink()
        else:
            param.set_param(store.PERSIST_PARAM, original)
        restored = param.get_param(store.PERSIST_PARAM, None)
        checks.append(("test_configuration_restored", restored == original,
                       {"original": original, "restored": restored}))
        env.cr.commit()
    return checks


def _run_retention_cron():
    """The scheduled retention sweep, exercised through the shipped cron record.

    The horizon was declared but nothing invoked it, so this proves the carrier
    as well as the behaviour: the cron record must exist, be active, target this
    model and call the method the model exposes. Then the sweep is run through
    that model method against three planted rows - one past the horizon, one just
    inside it and one fresh - so "deletes the old rows" cannot be satisfied by
    "deletes every row".
    """
    checks = []
    env = _env()
    model = env[store.MODEL_NAME].sudo()
    cron = env.ref("smart_core.ir_cron_sc_contract_slo_observation_prune", raise_if_not_found=False)
    checks.append(("retention_cron_record_exists", bool(cron), {}))
    checks.append(("retention_cron_is_active", bool(cron and cron.active), {}))
    checks.append(("retention_cron_targets_the_observation_model",
                   bool(cron) and cron.model_id.model == store.MODEL_NAME,
                   {"model": cron.model_id.model if cron else None}))
    checks.append(("retention_cron_calls_the_model_sweep",
                   bool(cron) and (cron.code or "").strip() == "model.cron_prune()",
                   {"code": (cron.code or "").strip() if cron else None}))

    rows = store.read_observations(env, limit=1)
    if not rows:
        checks.append(("retention_cron_has_an_observation_to_work_from", False, {}))
        return checks
    template = rows[0]

    now = store.utcnow_epoch()
    planted = []
    for stale_days in (90, 29, 0):
        record = model.create(store.row_values(template, company_id=None))
        record.write({"observed_at": store.epoch_to_text(now - stale_days * 86400)})
        planted.append(record.id)
    stale_id, inside_id, fresh_id = planted

    # The swept rows are planted by this probe, so a broken sweep must not be
    # able to leave a stale row behind and poison the next run's "prune keeps the
    # fresh rows" check. Cleanup is unconditional.
    try:
        removed = None
        try:
            removed = model.cron_prune()
        except Exception as exc:  # the sweep is fail-open by contract
            checks.append(("retention_cron_sweep_does_not_raise", False, {"error": str(exc)}))
        remaining = set(model.browse(planted).exists().ids)
        checks.append(("retention_sweep_removes_only_rows_past_the_horizon",
                       removed == 1 and stale_id not in remaining,
                       {"removed": removed, "remaining": sorted(remaining)}))
        checks.append(("retention_sweep_keeps_rows_inside_the_horizon",
                       inside_id in remaining and fresh_id in remaining,
                       {"insideKept": inside_id in remaining, "freshKept": fresh_id in remaining}))
        checks.append(("retention_sweep_is_repeatable_and_fail_open",
                       model.cron_prune() == 0, {}))
    finally:
        leftovers = model.browse(planted).exists()
        if leftovers:
            leftovers.unlink()
        env.cr.commit()
    checks.append(("retention_probe_rows_cleaned_up",
                   not model.browse(planted).exists(),
                   {"planted": planted}))
    return checks


def main():
    report = _run()
    with open(PROBE_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
    print("CONTRACT_SLO_RUNTIME_PROBE=%s checks=%d failed=%d"
          % ("PASS" if report["failedCount"] == 0 else "FAIL",
             report["checkCount"], report["failedCount"]))
    if report["failedCount"]:
        print("CONTRACT_SLO_RUNTIME_PROBE_FAILED=" + ",".join(report["failed"]))


main()
