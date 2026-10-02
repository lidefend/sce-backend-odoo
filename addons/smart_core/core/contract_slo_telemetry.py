# -*- coding: utf-8 -*-
"""Contract SLO telemetry core.

The first L5 gap of the backend contract lifecycle is the missing
contract-version SLO telemetry: success rate, degradation rate and
integrity-failure rate aggregated per contract version.

This module owns the pure half of that feature:

* the identity a delivery is aggregated under (derived from the lifecycle
  evidence ``smart_core.contract_lifecycle`` already emits);
* the outcome classification (``success`` / ``degraded`` / ``integrity_failure``);
* the aggregation, with exact-sum counts and rates that are never fabricated for
  an empty window.

It imports nothing from Odoo so the semantics stay offline-verifiable and any
sink (structured log, metrics pipeline, future read model) can reuse them
unchanged.

Emission is provided only as a sink-agnostic boundary: the module validates an
observation and hands it (or a canonical log line) to a caller-supplied sink,
fail-open, so a delivery is never broken by a missing or broken telemetry sink.
Choosing the sink and persisting or trending the observations are deliberately
out of scope here.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


SCHEMA_VERSION = "1.0.0"

OUTCOME_SUCCESS = "success"
OUTCOME_DEGRADED = "degraded"
OUTCOME_INTEGRITY_FAILURE = "integrity_failure"
CONTRACT_SLO_OUTCOMES = (OUTCOME_SUCCESS, OUTCOME_DEGRADED, OUTCOME_INTEGRITY_FAILURE)

RATE_FIELDS = ("successRate", "degradationRate", "integrityFailureRate")
OBSERVATION_LINE_KEY = "contractSlo"
IDENTITY_FIELDS = (
    "schemaId",
    "schemaVersion",
    "contractVersion",
    "sourceType",
    "sourceSha256",
    "stage",
)
PUBLISHED_VERSION_FIELD = "publishedVersionRef"
GROUPING_FIELDS = IDENTITY_FIELDS + (PUBLISHED_VERSION_FIELD,)
REJECTED_SAMPLE_LIMIT = 10


class ContractSloError(ValueError):
    """Raised when an identity or classification input cannot be trusted."""


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _degradation_reasons(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise ContractSloError("degradation_reasons must be an iterable of strings")
    reasons = []
    for item in value:
        text = _text(item)
        if text:
            reasons.append(text)
    return sorted(set(reasons))


def delivery_identity(contract: Any = None, *, lifecycle: Any = None) -> dict[str, str]:
    """Return the immutable identity a runtime delivery is aggregated under.

    The lifecycle evidence is the single source: it already binds the schema
    identity, the source identity and the runtime stage. A delivery that cannot
    present that identity is not telemetry-eligible and fails closed instead of
    being aggregated under a guessed key.
    """
    body = _dict(lifecycle)
    if not body:
        meta = _dict(_dict(contract).get("meta"))
        body = _dict(meta.get("lifecycle"))
    if not body:
        raise ContractSloError("contract lifecycle evidence is missing")
    definition = _dict(body.get("definition"))
    generation = _dict(body.get("generation"))
    identity = {
        "schemaId": _text(definition.get("schemaId")),
        "schemaVersion": _text(definition.get("schemaVersion")),
        "contractVersion": _text(definition.get("contractVersion")),
        "sourceType": _text(generation.get("sourceType")),
        "sourceSha256": _text(generation.get("sourceSha256")),
        "stage": _text(body.get("stage")),
    }
    missing = sorted(field for field, value in identity.items() if not value)
    if missing:
        raise ContractSloError("contract lifecycle identity is incomplete: %s" % ", ".join(missing))
    published = _text(definition.get(PUBLISHED_VERSION_FIELD) or body.get(PUBLISHED_VERSION_FIELD))
    if published:
        identity[PUBLISHED_VERSION_FIELD] = published
    return identity


def classify_delivery(*, integrity_ok: Any, degradation_reasons: Any = None) -> str:
    """Classify one runtime delivery into a contract SLO outcome.

    Integrity failure outranks degradation: a delivery whose seal cannot be
    re-verified is never reported as a healthy-but-degraded success.
    """
    if not isinstance(integrity_ok, bool):
        raise ContractSloError("integrity_ok must be a bool")
    if not integrity_ok:
        return OUTCOME_INTEGRITY_FAILURE
    if _degradation_reasons(degradation_reasons):
        return OUTCOME_DEGRADED
    return OUTCOME_SUCCESS


def build_observation(
    *,
    integrity_ok: Any,
    identity: Any = None,
    contract: Any = None,
    lifecycle: Any = None,
    degradation_reasons: Any = None,
    latency_ms: Any = None,
    observed_at: Any = None,
    client_type: Any = "",
    request_id: Any = "",
) -> dict[str, Any]:
    """Build one validated SLO observation from an observed delivery."""
    resolved = dict(identity) if _is_identity(identity) else delivery_identity(contract, lifecycle=lifecycle)
    reasons = _degradation_reasons(degradation_reasons)
    outcome = classify_delivery(integrity_ok=integrity_ok, degradation_reasons=reasons)
    if latency_ms is not None:
        if isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float)) or latency_ms < 0:
            raise ContractSloError("latency_ms must be a non-negative number")
        latency_ms = int(latency_ms)
    moment = observed_at if observed_at is not None else datetime.now(timezone.utc).timestamp()
    if isinstance(moment, bool) or not isinstance(moment, (int, float)):
        raise ContractSloError("observed_at must be a number")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "identity": resolved,
        "outcome": outcome,
        "degradationReasons": reasons,
        "latencyMs": latency_ms,
        "observedAt": float(moment),
        "clientType": _text(client_type),
        "requestId": _text(request_id),
    }


def _is_identity(value: Any) -> bool:
    return isinstance(value, dict) and all(_text(value.get(field)) for field in IDENTITY_FIELDS)


def _reject_reason(observation: Any) -> str:
    if not isinstance(observation, dict):
        return "observation_not_object"
    if observation.get("schemaVersion") != SCHEMA_VERSION:
        return "unsupported_schema_version"
    identity = observation.get("identity")
    if not _is_identity(identity):
        missing = [field for field in IDENTITY_FIELDS if not _text(_dict(identity).get(field))]
        return "incomplete_identity:%s" % ",".join(missing) if missing else "identity_not_object"
    if observation.get("outcome") not in CONTRACT_SLO_OUTCOMES:
        return "unknown_outcome"
    moment = observation.get("observedAt")
    if isinstance(moment, bool) or not isinstance(moment, (int, float)):
        return "invalid_observed_at"
    return ""


def _rate(count: int, accepted: int) -> float | None:
    if accepted <= 0:
        return None
    return round(count / accepted, 6)


def _identity_from_key(key: tuple[str, ...]) -> dict[str, str]:
    """Rebuild the row identity from its grouping key, nothing inferred."""
    identity = {field: key[index] for index, field in enumerate(IDENTITY_FIELDS)}
    published = key[len(IDENTITY_FIELDS)]
    if published:
        identity[PUBLISHED_VERSION_FIELD] = published
    return identity


def aggregate_observations(
    observations: Any,
    *,
    window_seconds: Any = None,
    now: Any = None,
) -> dict[str, Any]:
    """Aggregate observations per contract identity.

    Counts are exact; rates are computed only over accepted observations. An
    identity with no accepted observation reports ``None`` rates rather than a
    fabricated zero. Malformed observations are counted and sampled, never
    silently dropped.

    Rows are keyed by the whole identity including ``publishedVersionRef``, so
    two published versions never merge into one SLO row and an unattributed
    delivery never borrows another delivery's version.
    """
    if observations is None:
        observations = []
    if isinstance(observations, (str, bytes)) or not isinstance(observations, Iterable):
        raise ContractSloError("observations must be an iterable of observations")
    window = None
    if window_seconds is not None:
        if isinstance(window_seconds, bool) or not isinstance(window_seconds, (int, float)) or window_seconds <= 0:
            raise ContractSloError("window_seconds must be a positive number")
        moment = now if now is not None else datetime.now(timezone.utc).timestamp()
        if isinstance(moment, bool) or not isinstance(moment, (int, float)):
            raise ContractSloError("now must be a number")
        window = float(moment) - float(window_seconds)

    buckets: dict[tuple[str, ...], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    rejected_total = 0
    window_excluded = 0
    total = 0
    for index, observation in enumerate(observations):
        total += 1
        reason = _reject_reason(observation)
        if reason:
            rejected_total += 1
            if len(rejected) < REJECTED_SAMPLE_LIMIT:
                rejected.append({"index": index, "reason": reason})
            continue
        if window is not None and float(observation["observedAt"]) < window:
            window_excluded += 1
            continue
        key = tuple(_text(observation["identity"].get(field)) for field in GROUPING_FIELDS)
        bucket = buckets.setdefault(
            key,
            {"identity": _identity_from_key(key), "observations": 0, "outcomes": {name: 0 for name in CONTRACT_SLO_OUTCOMES}},
        )
        bucket["observations"] += 1
        bucket["outcomes"][observation["outcome"]] += 1

    versions = []
    for key in sorted(buckets):
        bucket = buckets[key]
        accepted = bucket["observations"]
        outcomes = bucket["outcomes"]
        entry = dict(bucket["identity"])
        entry.update(
            {
                "observations": accepted,
                "outcomes": outcomes,
                "successRate": _rate(outcomes[OUTCOME_SUCCESS], accepted),
                "degradationRate": _rate(outcomes[OUTCOME_DEGRADED], accepted),
                "integrityFailureRate": _rate(outcomes[OUTCOME_INTEGRITY_FAILURE], accepted),
            }
        )
        versions.append(entry)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "windowSeconds": None if window_seconds is None else int(window_seconds),
        "totalObservations": total,
        "acceptedObservations": total - rejected_total - window_excluded,
        "rejectedObservations": rejected_total,
        "rejectedSample": rejected,
        "windowExcludedObservations": window_excluded,
        "versionCount": len(versions),
        "versions": versions,
    }


def emit_observation(observation: Any, *, sink: Callable[[Any], Any] | None) -> bool:
    """Hand one validated observation to ``sink`` without breaking delivery.

    Fail-open by construction: telemetry is secondary to the delivery it
    measures, so an unusable observation, a missing sink or a sink that raises
    all resolve to ``False`` instead of propagating into the delivery path. A
    sink that returns without raising is treated as accepted; returning the
    literal ``False`` is honoured as an explicit rejection. The return value
    reports whether the observation was accepted, never the delivery outcome.
    """
    if not callable(sink):
        return False
    if _reject_reason(observation):
        return False
    try:
        accepted = sink(observation)
    except Exception:
        return False
    return accepted is not False


def observation_log_line(observation: Any) -> str | None:
    """Return the canonical single-line rendering of an observation.

    The line is the observation key followed by compact, key-sorted JSON so it
    stays greppable and stable across processes. An observation that cannot be
    trusted has no line at all, so nothing invalid is ever emitted.
    """
    if _reject_reason(observation):
        return None
    payload = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "%s %s" % (OBSERVATION_LINE_KEY, payload)


def parse_observation_line(line: Any) -> dict[str, Any] | None:
    """Recover an observation from its canonical line, or ``None`` if invalid."""
    if not isinstance(line, str):
        return None
    prefix = OBSERVATION_LINE_KEY + " "
    if not line.startswith(prefix):
        return None
    try:
        parsed = json.loads(line[len(prefix) :])
    except (TypeError, ValueError):
        return None
    if _reject_reason(parsed):
        return None
    return parsed


def emit_observation_line(observation: Any, *, sink: Callable[[str], Any] | None) -> bool:
    """Emit the canonical log line of an observation, fail-open like ``emit_observation``."""
    if not callable(sink):
        return False
    line = observation_log_line(observation)
    if line is None:
        return False
    try:
        accepted = sink(line)
    except Exception:
        return False
    return accepted is not False
