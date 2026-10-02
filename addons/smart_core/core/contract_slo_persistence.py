# -*- coding: utf-8 -*-
"""Durable persistence and per-version trend read model for contract SLO telemetry.

The pure half of the contract SLO feature (``contract_slo_telemetry``) defines the
identity, the outcome classification and the aggregation, and emits observations
through a sink. This module owns the second half of the L5 gap: keeping those
observations past process exit and reading them back as a per-version trend.

The row <-> observation conversion and the bucket/trend math are pure and take no
Odoo import, so they stay offline-verifiable; only the thin create/search/prune
wrappers touch ``env``. Every write is fail-open: telemetry must never break the
delivery it measures, so persistence failures are swallowed and reported as
``False``.

Retention and the on/off switch are existing platform configuration, not new
authority:

* ``smart_core.contract_slo.persist_enabled`` — ``1`` to persist (default off, so
  an unconfigured deployment keeps today's log-only behaviour);
* ``smart_core.contract_slo.retention_days`` — prune horizon, default 30.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from . import contract_slo_telemetry as slo


MODEL_NAME = "sc.contract.slo.observation"
PERSIST_PARAM = "smart_core.contract_slo.persist_enabled"
RETENTION_PARAM = "smart_core.contract_slo.retention_days"
DEFAULT_RETENTION_DAYS = 30

# The lifecycle identity field -> stored column. `published_version_ref` is
# optional and only written when the lifecycle carries it, so published-version
# keying stays additive.
IDENTITY_COLUMN_MAP = (
    ("schemaId", "schema_id"),
    ("schemaVersion", "schema_version"),
    ("contractVersion", "contract_version"),
    ("sourceType", "source_type"),
    ("sourceSha256", "source_sha256"),
    ("stage", "stage"),
    ("publishedVersionRef", "published_version_ref"),
)
MYSQL_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _column_text(value: Any) -> str:
    """Stored-column text for an optional value, where an unset column is empty.

    ``_text`` would render a stored ``False`` (Odoo's empty Char) as the literal
    string ``"False"``, which would fabricate an identity field value on read.
    """
    if value is None or value is False or value == "":
        return ""
    return str(value).strip()


def _epoch(value: Any) -> float | None:
    """Epoch seconds for an Odoo (naive UTC) datetime or a stored timestamp string."""
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.timestamp()
    text = _text(value)
    if not text:
        return None
    for fmt in (MYSQL_DATETIME_FORMAT, "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def _datetime_text(epoch: Any) -> str | None:
    try:
        moment = float(epoch)
    except (TypeError, ValueError):
        return None
    if moment < 0:
        return None
    return datetime.fromtimestamp(moment, tz=timezone.utc).strftime(MYSQL_DATETIME_FORMAT)


def row_values(observation: Any, *, company_id: Any = None) -> dict[str, Any]:
    """Map one validated observation onto its stored columns (pure)."""
    if slo._reject_reason(observation):
        raise slo.ContractSloError("cannot persist an untrusted observation")
    identity = observation["identity"]
    values = {column: _text(identity.get(field)) or False for field, column in IDENTITY_COLUMN_MAP}
    # Normalize the stored column through the same rule the classifier uses, so a
    # row written from any caller keeps the canonical, sorted, de-duplicated form.
    reasons = slo._degradation_reasons(observation.get("degradationReasons") or [])
    values.update(
        {
            "outcome": observation["outcome"],
            "degradation_reasons_json": json.dumps(list(reasons), ensure_ascii=False),
            "latency_ms": observation.get("latencyMs"),
            "observed_at": _datetime_text(observation["observedAt"]),
            "client_type": _text(observation.get("clientType")) or False,
            "request_id": _text(observation.get("requestId")) or False,
            "company_id": company_id or False,
        }
    )
    return values


def observation_from_row(row: Any) -> dict[str, Any] | None:
    """Rebuild a canonical observation from a stored row, or ``None`` if unusable (pure).

    Reads go back through the same validator the emitter uses, so a corrupted row
    is reported as unreadable instead of being aggregated under a guessed identity.
    """
    if not isinstance(row, dict):
        return None
    identity: dict[str, str] = {}
    for field, column in IDENTITY_COLUMN_MAP:
        value = _column_text(row.get(column))
        if value:
            identity[field] = value
    moment = _epoch(row.get("observed_at"))
    if moment is None:
        return None
    reasons = row.get("degradation_reasons_json")
    if isinstance(reasons, str) and reasons.strip():
        try:
            reasons = json.loads(reasons)
        except ValueError:
            return None
    observation = {
        "schemaVersion": slo.SCHEMA_VERSION,
        "identity": identity,
        "outcome": _text(row.get("outcome")),
        "degradationReasons": list(reasons) if isinstance(reasons, list) else [],
        "latencyMs": row.get("latency_ms") if row.get("latency_ms") is not None else None,
        "observedAt": moment,
        "clientType": _column_text(row.get("client_type")),
        "requestId": _column_text(row.get("request_id")),
    }
    return None if slo._reject_reason(observation) else observation


def bucket_windows(*, window_seconds: Any, bucket_seconds: Any, now: Any) -> list[tuple[float, float]]:
    """Split a window into ``(start, end)`` epoch buckets, oldest first (pure).

    The newest bucket always ends at ``now``; the window is covered exactly with
    no overlap, and a partial leading bucket is dropped rather than reported as a
    full one.
    """
    window = float(window_seconds)
    bucket = float(bucket_seconds)
    if window <= 0 or bucket <= 0:
        raise slo.ContractSloError("window_seconds and bucket_seconds must be positive")
    moment = float(now)
    bucket_count = int(window // bucket)
    if bucket_count < 1:
        raise slo.ContractSloError("window_seconds must cover at least one bucket")
    windows = []
    for index in range(bucket_count - 1, -1, -1):
        end = moment - index * bucket
        windows.append((end - bucket, end))
    return windows


def build_trend(
    observations: Any,
    *,
    window_seconds: Any,
    bucket_seconds: Any,
    now: Any,
) -> dict[str, Any]:
    """Per-version SLO trend over time buckets, reusing the pure aggregator (pure).

    Each observation is placed in exactly one half-open ``[start, end)`` bucket,
    and each bucket is aggregated by the same pure
    ``contract_slo_telemetry.aggregate_observations`` any other window uses — never
    by a second, divergent formula. An observation with no readable timestamp
    cannot be placed in time, so it is counted once at the trend level instead of
    being silently dropped or leaked into an adjacent bucket.
    """
    placed: list[tuple[float, dict[str, Any]]] = []
    unplaced = 0
    for observation in list(observations or []):
        moment = _observation_epoch(observation)
        if moment is None:
            unplaced += 1
            continue
        placed.append((moment, observation))
    buckets = []
    for start, end in bucket_windows(window_seconds=window_seconds, bucket_seconds=bucket_seconds, now=now):
        bucket_rows = [observation for moment, observation in placed if start <= moment < end]
        buckets.append(
            {
                "bucketStart": start,
                "bucketEnd": end,
                "aggregate": slo.aggregate_observations(bucket_rows),
            }
        )
    return {
        "schemaVersion": slo.SCHEMA_VERSION,
        "windowSeconds": int(float(window_seconds)),
        "bucketSeconds": int(float(bucket_seconds)),
        "bucketCount": len(buckets),
        "unplacedObservations": unplaced,
        "buckets": buckets,
    }


def _observation_epoch(observation: Any) -> float | None:
    """Epoch seconds for a placeable observation, or ``None`` if it has none (pure)."""
    if not isinstance(observation, dict):
        return None
    moment = observation.get("observedAt")
    if isinstance(moment, bool) or not isinstance(moment, (int, float)):
        return None
    return float(moment)


def _company_id(env: Any) -> Any:
    company = getattr(env, "company", None)
    return getattr(company, "id", None)


def _int_param(env: Any, key: str, default: int) -> int:
    try:
        raw = env["ir.config_parameter"].sudo().get_param(key, default)
        return int(str(raw).strip())
    except Exception:
        return default


def persistence_enabled(env: Any) -> bool:
    try:
        raw = env["ir.config_parameter"].sudo().get_param(PERSIST_PARAM, "0")
    except Exception:
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def retention_days(env: Any) -> int:
    days = _int_param(env, RETENTION_PARAM, DEFAULT_RETENTION_DAYS)
    return days if days > 0 else DEFAULT_RETENTION_DAYS


def persist_observation(env: Any, observation: Any, *, company_id: Any = None) -> bool:
    """Store one observation, fail-open. Returns whether a row was written."""
    try:
        if env is None or not persistence_enabled(env):
            return False
        values = row_values(observation, company_id=company_id if company_id is not None else _company_id(env))
        env[MODEL_NAME].sudo().create(values)
        return True
    except Exception:
        return False


def persist_line(env: Any, line: Any, *, company_id: Any = None) -> bool:
    """Store the observation carried by its canonical log line, fail-open."""
    observation = slo.parse_observation_line(line)
    if observation is None:
        return False
    return persist_observation(env, observation, company_id=company_id)


def read_observations(
    env: Any,
    *,
    window_seconds: Any = None,
    contract_version: Any = None,
    now: Any = None,
    limit: Any = None,
) -> list[dict[str, Any]]:
    """Read stored observations back in canonical form, newest first."""
    if env is None:
        return []
    domain = []
    if contract_version:
        domain.append(("contract_version", "=", _text(contract_version)))
    if window_seconds is not None:
        moment = float(now) if now is not None else datetime.now(timezone.utc).timestamp()
        cutoff = _datetime_text(moment - float(window_seconds))
        if cutoff:
            domain.append(("observed_at", ">=", cutoff))
    try:
        records = env[MODEL_NAME].sudo().search(domain, order="observed_at desc, id desc", limit=limit)
    except Exception:
        return []
    observations = []
    for record in records:
        row = {column: record[column] for _field, column in IDENTITY_COLUMN_MAP}
        row.update(
            {
                "outcome": record.outcome,
                "degradation_reasons_json": record.degradation_reasons_json,
                "latency_ms": record.latency_ms,
                "observed_at": record.observed_at,
                "client_type": record.client_type,
                "request_id": record.request_id,
            }
        )
        observation = observation_from_row(row)
        if observation is not None:
            observations.append(observation)
    return observations


def aggregate_window(env: Any, *, window_seconds: Any, contract_version: Any = None, now: Any = None) -> dict[str, Any]:
    """Aggregate the persisted window with the pure aggregator."""
    observations = read_observations(
        env, window_seconds=window_seconds, contract_version=contract_version, now=now
    )
    return slo.aggregate_observations(observations, window_seconds=window_seconds, now=now)


def window_trend(
    env: Any,
    *,
    window_seconds: Any,
    bucket_seconds: Any,
    contract_version: Any = None,
    now: Any = None,
) -> dict[str, Any]:
    """Per-version SLO trend over the persisted window."""
    moment = float(now) if now is not None else datetime.now(timezone.utc).timestamp()
    observations = read_observations(env, window_seconds=window_seconds, contract_version=contract_version, now=moment)
    return build_trend(
        observations, window_seconds=window_seconds, bucket_seconds=bucket_seconds, now=moment
    )


def prune_observations(env: Any, *, retention_days_value: Any = None, now: Any = None) -> int:
    """Drop observations older than the retention horizon. Returns rows removed."""
    if env is None:
        return 0
    days = int(retention_days_value) if retention_days_value else retention_days(env)
    if days <= 0:
        return 0
    moment = float(now) if now is not None else datetime.now(timezone.utc).timestamp()
    cutoff = _datetime_text(moment - days * 86400)
    if not cutoff:
        return 0
    try:
        records = env[MODEL_NAME].sudo().search([("observed_at", "<", cutoff)])
        count = len(records)
        records.unlink()
        return count
    except Exception:
        return 0


def observation_store_summary(env: Any) -> dict[str, Any]:
    """Cheap store identity for a read intent: is it on, what is retained, how much."""
    summary = {
        "model": MODEL_NAME,
        "persistEnabled": False,
        "retentionDays": DEFAULT_RETENTION_DAYS,
        "observationCount": 0,
    }
    if env is None:
        return summary
    summary["persistEnabled"] = persistence_enabled(env)
    summary["retentionDays"] = retention_days(env)
    try:
        summary["observationCount"] = env[MODEL_NAME].sudo().search_count([])
    except Exception:
        pass
    return summary


def retention_cutoff(*, retention_days_value: Any, now: Any) -> str | None:
    """The stored-format cutoff for a retention horizon (pure helper for tooling)."""
    try:
        days = int(retention_days_value)
        moment = float(now)
    except (TypeError, ValueError):
        return None
    if days <= 0:
        return None
    return _datetime_text(moment - days * 86400)


def utcnow_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def epoch_to_text(epoch: Any) -> str | None:
    return _datetime_text(epoch)


def text_to_epoch(text: Any) -> float | None:
    return _epoch(text)


def retention_horizon_text(*, retention_days_value: Any = DEFAULT_RETENTION_DAYS) -> str:
    """Readable horizon label (used by the read intent meta)."""
    return (datetime.now(timezone.utc) - timedelta(days=int(retention_days_value))).strftime(MYSQL_DATETIME_FORMAT)
