# -*- coding: utf-8 -*-
"""Client contract version and carrier negotiation.

This module decides one delivery projection for one request. It is deliberately
independent of Odoo and rendering so the compatibility matrix is executable
without a database. The contracts themselves remain owned by Contract V2,
Page Orchestration and the semantic registry.
"""
from __future__ import annotations

from typing import Any, Iterable


NEGOTIATION_VERSION = "1.0.0"
LEGACY_CONTRACT_VERSION = "2.5.0"
CURRENT_CONTRACT_VERSION = "2.6.0"
LEGACY_PAGE_ORCHESTRATION_VERSION = "2.0.0"
CURRENT_PAGE_ORCHESTRATION_VERSION = "2.1.0"

PAGE_BLOCK_DATA_CAPABILITY = "page_block_data.v1"
ATTACHMENT_FACT_CAPABILITY = "attachment_fact.v1"
PAGE_BLOCK_ACTION_CAPABILITY = "page_block_action.v1"
KNOWN_CARRIERS = (
    PAGE_BLOCK_DATA_CAPABILITY,
    ATTACHMENT_FACT_CAPABILITY,
    PAGE_BLOCK_ACTION_CAPABILITY,
)
STABLE_CLIENT_TYPES = ("web_pc", "wx_mini", "harmony_h5")

REASON_CONTRACT_VERSION_UNSUPPORTED = "CONTRACT_VERSION_UNSUPPORTED"


class ContractNegotiationError(ValueError):
    """Typed refusal with one stable transport reason."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        source: Iterable[Any] = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        source = value
    else:
        source = ()
    return sorted({_text(item) for item in source if _text(item)})


def accepted_minors(value: Any) -> tuple[int, ...]:
    """Return supported Contract V2 minor versions declared by the client."""

    minors: set[int] = set()
    for token in _string_list(value):
        normalized = token.lower()
        if not normalized.startswith("2."):
            continue
        suffix = normalized[2:]
        minor = suffix.split(".", 1)[0]
        if not minor.isdigit():
            continue
        parsed = int(minor)
        if 0 <= parsed <= 6:
            minors.add(parsed)
    return tuple(sorted(minors, reverse=True))


def _legacy_result(
    *,
    client_type: str,
    accepted_versions: list[str],
    capabilities: list[str],
    compatibility_mode: str,
) -> dict[str, Any]:
    return {
        "negotiationVersion": NEGOTIATION_VERSION,
        "status": "legacy",
        "clientType": client_type,
        "compatibilityMode": compatibility_mode,
        "acceptedContractVersions": accepted_versions,
        "clientContractCapabilities": capabilities,
        "contractVersion": LEGACY_CONTRACT_VERSION,
        "pageOrchestrationVersion": LEGACY_PAGE_ORCHESTRATION_VERSION,
        "carriers": {
            PAGE_BLOCK_DATA_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": False},
            ATTACHMENT_FACT_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": False},
            PAGE_BLOCK_ACTION_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": False},
        },
    }


def negotiate_client_contract(
    *,
    client_type: Any,
    accepted_contract_versions: Any = None,
    client_contract_capabilities: Any = None,
) -> dict[str, Any]:
    """Choose one complete contract projection.

    Pre-negotiation clients that send neither a client type, accepted version nor
    capability receive the complete 2.5/2.0 legacy projection. Once any
    negotiation field is present, an unknown/missing client type fails closed.
    """

    resolved_client = _text(client_type)
    versions = _string_list(accepted_contract_versions)
    capabilities = _string_list(client_contract_capabilities)
    if not resolved_client:
        if not versions and not capabilities:
            return _legacy_result(
                client_type="web_pc",
                accepted_versions=[],
                capabilities=[],
                compatibility_mode="pre_negotiation_client",
            )
        raise ContractNegotiationError(
            REASON_CONTRACT_VERSION_UNSUPPORTED,
            "client_type is required when contract versions or capabilities are declared",
        )
    if resolved_client not in STABLE_CLIENT_TYPES:
        raise ContractNegotiationError(
            REASON_CONTRACT_VERSION_UNSUPPORTED,
            f"unsupported client type: {resolved_client}",
        )
    if not versions:
        return _legacy_result(
            client_type=resolved_client,
            accepted_versions=[],
            capabilities=capabilities,
            compatibility_mode="known_client_without_versions",
        )
    minors = accepted_minors(versions)
    if not minors:
        raise ContractNegotiationError(
            REASON_CONTRACT_VERSION_UNSUPPORTED,
            "no common Contract V2 version",
        )
    if minors[0] <= 5:
        return _legacy_result(
            client_type=resolved_client,
            accepted_versions=versions,
            capabilities=capabilities,
            compatibility_mode="legacy_common_version",
        )
    if PAGE_BLOCK_DATA_CAPABILITY not in capabilities:
        return _legacy_result(
            client_type=resolved_client,
            accepted_versions=versions,
            capabilities=capabilities,
            compatibility_mode="new_version_without_page_block_capability",
        )
    return {
        "negotiationVersion": NEGOTIATION_VERSION,
        "status": "current",
        "clientType": resolved_client,
        "compatibilityMode": "page_block_data_v1",
        "acceptedContractVersions": versions,
        "clientContractCapabilities": capabilities,
        "contractVersion": CURRENT_CONTRACT_VERSION,
        "pageOrchestrationVersion": CURRENT_PAGE_ORCHESTRATION_VERSION,
        "carriers": {
            PAGE_BLOCK_DATA_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": True},
            ATTACHMENT_FACT_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": False},
            PAGE_BLOCK_ACTION_CAPABILITY: {"schemaVersion": "1.0.0", "enabled": False},
        },
    }


def carrier_enabled(negotiation: dict[str, Any], carrier: str) -> bool:
    carriers = negotiation.get("carriers") if isinstance(negotiation, dict) else {}
    row = carriers.get(carrier) if isinstance(carriers, dict) else {}
    return bool(isinstance(row, dict) and row.get("enabled") is True)


def negotiate_payload(
    payload: Any,
    *,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Negotiate from an Odoo intent payload without importing Odoo."""

    envelope = payload if isinstance(payload, dict) else {}
    params = envelope.get("params") if isinstance(envelope.get("params"), dict) else envelope
    source_headers = headers if isinstance(headers, dict) else {}
    client_type = (
        source_headers.get("X-SC-Client-Type")
        or source_headers.get("x-sc-client-type")
        or params.get("client_type")
        or params.get("clientType")
    )
    return negotiate_client_contract(
        client_type=client_type,
        accepted_contract_versions=(
            params.get("accepted_contract_versions")
            or params.get("acceptedContractVersions")
        ),
        client_contract_capabilities=(
            params.get("client_contract_capabilities")
            or params.get("clientContractCapabilities")
        ),
    )
