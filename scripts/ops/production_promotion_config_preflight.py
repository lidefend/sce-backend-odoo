#!/usr/bin/env python3
"""Fail-closed readiness gate that runs before any production container change."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import production_acceptance_harness as acceptance


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path(__file__).with_name(
    "production_promotion_config_contract_v1.json"
)
PLACEHOLDER = re.compile(
    r"^(?:<.*>|changeme|change_me|replace_me|placeholder|todo|unset|none|null)$",
    re.IGNORECASE,
)
KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ReadinessError(RuntimeError):
    pass


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ReadinessError(f"configuration file is unavailable: {path}")
    result: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ReadinessError(f"invalid configuration syntax at line {number}")
        name, value = line.split("=", 1)
        name = name.strip()
        if not KEY.fullmatch(name):
            raise ReadinessError(f"invalid configuration key at line {number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[name] = value
    return result


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "production_promotion_config_contract.v1":
        raise ReadinessError("unsupported promotion configuration contract")
    return payload


def is_nonempty(value: str) -> bool:
    return bool(value.strip()) and not PLACEHOLDER.fullmatch(value.strip())


def resolve_values(
    contract: dict[str, Any],
    config_values: dict[str, str],
    secret_values: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], list[str], list[str]]:
    resolved: dict[str, str] = {}
    sources: dict[str, str] = {}
    missing: list[str] = []
    invalid: list[str] = []
    for field in contract["required_fields"]:
        name = field["key"]
        required_source = field["source"]
        source_values = secret_values if required_source == "secret" else config_values
        value = source_values.get(name, "")
        if not is_nonempty(value):
            missing.append(name)
            continue
        if name == "SC_BOOTSTRAP_LOGIN" and value.strip().lower() in set(
            contract["forbidden_login_values"]
        ):
            invalid.append(name)
            continue
        resolved[name] = value.strip()
        sources[name] = required_source
    return resolved, sources, sorted(missing), sorted(invalid)


def validate_static_contract(
    contract: dict[str, Any],
    values: dict[str, str],
    *,
    expected_environment: str,
    root: Path = ROOT,
) -> list[str]:
    failed: list[str] = []
    if values["PROMOTION_ENVIRONMENT"] != expected_environment:
        failed.append("PROMOTION_ENVIRONMENT")
    profile = contract["target_profiles"].get(expected_environment)
    if not isinstance(profile, dict):
        raise ReadinessError("unsupported promotion target environment")
    base_url = values["ACCEPTANCE_BASE_URL"].rstrip("/")
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or base_url not in profile["allowed_base_urls"]
    ):
        failed.append("ACCEPTANCE_BASE_URL")
    if parsed.scheme == "https" and values["ACCEPTANCE_TLS_VERIFY"].lower() != "true":
        failed.append("ACCEPTANCE_TLS_VERIFY")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        failed.append("ACCEPTANCE_TLS_VERIFY")
    if values["ACCEPTANCE_TLS_VERIFY"].lower() not in {"true", "false"}:
        failed.append("ACCEPTANCE_TLS_VERIFY")
    if values["DB_NAME"] != profile["database"]:
        failed.append("DB_NAME")
    if values["ACCEPTANCE_PRODUCT_KEY"] != contract["expected_product_key"]:
        failed.append("ACCEPTANCE_PRODUCT_KEY")
    if (
        values["ACCEPTANCE_EXPECTED_ROLE_CODE"]
        != contract["expected_role_code"]
    ):
        failed.append("ACCEPTANCE_EXPECTED_ROLE_CODE")
    if (
        values["ACCEPTANCE_PACKAGE_DIGEST"]
        != contract["acceptance_package_digest"]
    ):
        failed.append("ACCEPTANCE_PACKAGE_DIGEST")
    if values["DEPLOYMENT_IMAGE_REF"] != contract["fixed_deployment_image_id"]:
        failed.append("DEPLOYMENT_IMAGE_REF")
    try:
        timeout = int(values["ACCEPTANCE_HTTP_TIMEOUT"])
        if not 1 <= timeout <= 120:
            failed.append("ACCEPTANCE_HTTP_TIMEOUT")
    except ValueError:
        failed.append("ACCEPTANCE_HTTP_TIMEOUT")
    configured_contract = Path(values["ACCEPTANCE_CONTRACT_PATH"])
    if not configured_contract.is_absolute():
        configured_contract = root / configured_contract
    expected_contract = root / contract["acceptance_contract_path"]
    if configured_contract.resolve() != expected_contract.resolve():
        failed.append("ACCEPTANCE_CONTRACT_PATH")
    else:
        acceptance_contract = json.loads(configured_contract.read_text(encoding="utf-8"))
        roles = acceptance_contract.get("expected_role_codes") or []
        if contract["expected_role_code"] not in roles:
            failed.append("ACCEPTANCE_EXPECTED_ROLE_CODE")
    if acceptance.package_digest() != contract["acceptance_package_digest"]:
        failed.append("ACCEPTANCE_PACKAGE_DIGEST")
    return sorted(set(failed))


def docker_image_available(image_ref: str) -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", image_ref, "--format", "{{.Id}}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return completed.returncode == 0 and completed.stdout.strip() == image_ref


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ReadinessError("readiness evidence path already exists")
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def evaluate(
    *,
    contract: dict[str, Any],
    config_values: dict[str, str],
    secret_values: dict[str, str],
    run_http: bool,
    run_count: int,
    check_image: bool,
    expected_environment: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    values, sources, missing, invalid = resolve_values(
        contract, config_values, secret_values
    )
    static_failures: list[str] = []
    if not missing and not invalid:
        static_failures = validate_static_contract(
            contract,
            values,
            expected_environment=expected_environment,
            root=root,
        )
    package_pass = acceptance.package_digest() == contract["acceptance_package_digest"]
    image_pass = False
    if not missing and not invalid and "DEPLOYMENT_IMAGE_REF" not in static_failures:
        image_pass = (
            docker_image_available(values["DEPLOYMENT_IMAGE_REF"])
            if check_image
            else True
        )
    http_report: dict[str, Any] = {}
    http_error = ""
    if (
        run_http
        and not missing
        and not invalid
        and not static_failures
        and package_pass
        and image_pass
    ):
        try:
            http_report = acceptance.run_acceptance(
                base_url=values["ACCEPTANCE_BASE_URL"],
                db_name=values["DB_NAME"],
                login=values["SC_BOOTSTRAP_LOGIN"],
                password=values["FORMAL_ACCEPTANCE_PASSWORD"],
                run_count=run_count,
                timeout=int(values["ACCEPTANCE_HTTP_TIMEOUT"]),
            )
        except acceptance.AcceptanceError:
            http_error = "HTTP_ACCEPTANCE_FAILED"
    http_pass = bool(http_report) and http_report.get("status") == "PASS"
    schema_pass = not missing and not invalid and not static_failures
    safe = schema_pass and package_pass and image_pass and (http_pass if run_http else True)
    first_run = (http_report.get("runs") or [{}])[0]
    return {
        "schema_version": "production_promotion_config_readiness_evidence.v1",
        "status": "PASS" if safe else "PREDEPLOY_CONFIG_NOT_READY",
        "required_config_fields": [
            field["key"] for field in contract["required_fields"]
        ],
        "missing_config_fields": missing,
        "invalid_config_fields": sorted(set(invalid + static_failures)),
        "failed_readiness_checks": [http_error] if http_error else [],
        "config_sources": sources,
        "secret_values_exposed": False,
        "promotion_config_contract_pass": schema_pass,
        "promotion_required_fields_present": not missing,
        "formal_login_configured": "SC_BOOTSTRAP_LOGIN" in values,
        "formal_login_account_exists": http_pass,
        "formal_login_account_active": http_pass,
        "formal_login_current_production_pass": bool(first_run.get("login_pass")),
        "production_system_init_preflight_pass": bool(
            first_run.get("system_init_pass")
        ),
        "production_core_read_preflight_pass": bool(
            first_run.get("core_read_acceptance_pass")
        ),
        "production_target_identity_pass": schema_pass,
        "rc5_fixed_image_available": image_pass,
        "rc5_fixed_image_check_performed": check_image,
        "acceptance_package_integrity_pass": package_pass,
        "repeated_clean_session_run_count": (
            http_report.get("run_count", 0) if http_pass else 0
        ),
        "safe_to_replace_production_container": safe,
        "production_container_replaced": False,
        "rc5_deployment_performed": False,
        "production_write_performed": False,
        "http_acceptance": http_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-http", action="store_true")
    parser.add_argument("--run-count", type=int, default=1)
    parser.add_argument(
        "--expected-environment", choices=("daily", "production"), required=True
    )
    parser.add_argument("--skip-image-check", action="store_true")
    args = parser.parse_args()
    try:
        contract = load_contract(args.contract)
        report = evaluate(
            contract=contract,
            config_values=read_env_file(args.config_file),
            secret_values=read_env_file(args.secret_file),
            run_http=args.run_http,
            run_count=args.run_count,
            check_image=not args.skip_image_check,
            expected_environment=args.expected_environment,
        )
        atomic_json(args.output, report)
    except (ReadinessError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"[production_promotion_config_preflight] PREDEPLOY_CONFIG_NOT_READY "
            f"reason={type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    missing = ",".join(report["missing_config_fields"]) or "NONE"
    invalid = ",".join(report["invalid_config_fields"]) or "NONE"
    print(
        f"[production_promotion_config_preflight] {report['status']} "
        f"missing={missing} invalid={invalid} output={args.output}"
    )
    return 0 if report["safe_to_replace_production_container"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
