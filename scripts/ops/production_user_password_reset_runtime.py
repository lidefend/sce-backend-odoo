#!/usr/bin/env python3
"""Reconstruct the current production Compose context and launch password reset."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROJECT = "sc_production"
DATABASE = "sc_production"
DIGEST_IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9_.@+-]{1,128}$")
BASE_URL_PATTERN = re.compile(r"^https?://[A-Za-z0-9._:-]+/?$")
RUNTIME_SECRET_NAMES = ("DB_USER", "DB_PASSWORD", "JWT_SECRET", "ADMIN_PASSWD")


class RuntimeContextError(RuntimeError):
    pass


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if completed.returncode:
        raise RuntimeContextError(f"{command[0]} read-only inspection failed")
    return completed.stdout.strip()


def _containers() -> dict[str, dict[str, Any]]:
    identifiers = _run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
            "--format",
            "{{.ID}}",
        ]
    ).splitlines()
    if len(identifiers) != 4:
        raise RuntimeContextError("exactly four running production service containers are required")
    payload = json.loads(_run(["docker", "inspect", *identifiers]))
    indexed: dict[str, dict[str, Any]] = {}
    for container in payload:
        labels = (container.get("Config") or {}).get("Labels") or {}
        if labels.get("com.docker.compose.project") != PROJECT:
            raise RuntimeContextError("production container project identity differs")
        service = str(labels.get("com.docker.compose.service") or "")
        if service in indexed or service not in {"db", "redis", "odoo", "nginx"}:
            raise RuntimeContextError("production service inventory differs")
        state = container.get("State") or {}
        if not state.get("Running"):
            raise RuntimeContextError("a production service container is not running")
        indexed[service] = container
    if set(indexed) != {"db", "redis", "odoo", "nginx"}:
        raise RuntimeContextError("production service inventory is incomplete")
    return indexed


def _environment(container: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in (container.get("Config") or {}).get("Env") or []:
        key, separator, value = str(item).partition("=")
        if separator:
            result[key] = value
    return result


def _mount(container: Mapping[str, Any], destination: str, *, volume: bool) -> str:
    matches = [item for item in container.get("Mounts") or [] if item.get("Destination") == destination]
    if len(matches) != 1:
        raise RuntimeContextError(f"production mount {destination} must resolve uniquely")
    item = matches[0]
    value = str(item.get("Name") if volume else item.get("Source") or "")
    if not value:
        raise RuntimeContextError(f"production mount {destination} identity is empty")
    return value


def resolve_compose_environment(
    containers: Mapping[str, Mapping[str, Any]], active_env: Mapping[str, str]
) -> dict[str, str]:
    odoo_container = containers["odoo"]
    nginx_container = containers["nginx"]
    runtime = _environment(odoo_container)
    image_ref = str((odoo_container.get("Config") or {}).get("Image") or "")
    nginx_image_ref = str((nginx_container.get("Config") or {}).get("Image") or "")
    if not DIGEST_IMAGE.fullmatch(image_ref) or nginx_image_ref != image_ref:
        raise RuntimeContextError("production application image identity differs")
    expected_digest = "sha256:" + image_ref.rsplit("@sha256:", 1)[1]
    required_runtime = {
        "TARGET_DB": DATABASE,
        "DB_NAME": DATABASE,
        "ODOO_DB": DATABASE,
        "ODOO_DBFILTER": f"^{DATABASE}$",
        "PLATFORM_RELEASE_DB": DATABASE,
        "SC_ENVIRONMENT": "production",
        "EXPECTED_IMAGE_DIGEST": expected_digest,
    }
    for key, expected in required_runtime.items():
        if runtime.get(key) != expected:
            raise RuntimeContextError(f"production runtime identity {key} differs")
    source_sha = runtime.get("EXPECTED_RELEASE_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise RuntimeContextError("production release source identity is invalid")
    for name in RUNTIME_SECRET_NAMES:
        if not runtime.get(name):
            raise RuntimeContextError(f"running production secret {name} is unavailable")

    resolved = dict(active_env)
    resolved.update(
        {
            "PRODUCTION_COMPOSE_PROJECT": PROJECT,
            "TARGET_DB": DATABASE,
            "DB_NAME": DATABASE,
            "PLATFORM_RELEASE_DB": DATABASE,
            "ODOO_IMAGE_REF": image_ref,
            "NGINX_IMAGE_REF": nginx_image_ref,
            "SC_ENVIRONMENT": "production",
            "EXPECTED_RELEASE_SHA": source_sha,
            "EXPECTED_IMAGE_DIGEST": expected_digest,
            "RELEASE_MANIFEST_PATH": _mount(
                odoo_container, "/opt/sce-release/product-release-manifest.json", volume=False
            ),
            "RELEASE_MANIFEST_CHECKSUM_PATH": _mount(
                odoo_container,
                "/opt/sce-release/product-release-manifest.sha256",
                volume=False,
            ),
            "SC_CUSTOMER_ADDONS_ROOT": _mount(
                odoo_container, "/mnt/customer-addons", volume=False
            ),
            "SC_DATABASE_VOLUME": _mount(
                containers["db"], "/var/lib/postgresql/data", volume=True
            ),
            "SC_REDIS_VOLUME": _mount(containers["redis"], "/data", volume=True),
            "SC_FILESTORE_VOLUME": _mount(
                odoo_container, "/opt/sce-runtime/filestore", volume=True
            ),
            "SC_SESSION_VOLUME": _mount(
                odoo_container, "/opt/sce-runtime/sessions", volume=True
            ),
            "SC_TMP_VOLUME": _mount(odoo_container, "/opt/sce-runtime/tmp", volume=True),
            "SC_LOG_VOLUME": _mount(odoo_container, "/opt/sce-runtime/logs", volume=True),
        }
    )
    for name in RUNTIME_SECRET_NAMES:
        resolved[name] = runtime[name]
    return resolved


def command(tool_root: Path, login: str, base_url: str) -> list[str]:
    candidate = tool_root / "docker-compose.production-candidate.yml"
    customer = tool_root / "docker-compose.production-customer.yml"
    reset_script = tool_root / "scripts/ops/production_user_password_reset.py"
    for path in (candidate, customer, reset_script):
        if not path.is_file() or path.is_symlink():
            raise RuntimeContextError("immutable password-reset tool inventory differs")
    shell_command = (
        "python3 /usr/local/bin/production_db_contract.py health; "
        'python3 /usr/local/bin/render_odoo_conf.py /etc/odoo/odoo.conf.template "${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"; '
        f'exec python3 "{reset_script}" --database "{DATABASE}" --login "{login}" '
        '--config "${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}" '
        f'--base-url "{base_url}" --tool-root "{tool_root}"'
    )
    return [
        "docker",
        "compose",
        "-p",
        PROJECT,
        "-f",
        str(candidate),
        "-f",
        str(customer),
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "ENV=prod",
        "-e",
        "PROD_DANGER=1",
        "-v",
        f"{tool_root}:{tool_root}:ro",
        "--entrypoint",
        "/bin/sh",
        "odoo",
        "-eu",
        "-c",
        shell_command,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--tool-root", required=True)
    args = parser.parse_args()
    try:
        if args.database != DATABASE:
            raise RuntimeContextError("database must be sc_production")
        if not LOGIN_PATTERN.fullmatch(args.login):
            raise RuntimeContextError("login format is invalid")
        if not BASE_URL_PATTERN.fullmatch(args.base_url):
            raise RuntimeContextError("HTTP verification base URL is invalid")
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeContextError("a real interactive terminal is required")
        tool_root = Path(args.tool_root).resolve(strict=True)
        marker = tool_root / "DEPLOYMENT_TOOL_SHA"
        if (
            tool_root.parent != Path("/opt/sce/deployment-tools")
            or tool_root.is_symlink()
            or not marker.is_file()
            or marker.read_text().strip() != tool_root.name
        ):
            raise RuntimeContextError("immutable deployment-tool identity differs")
        compose_env = resolve_compose_environment(_containers(), os.environ)
        argv = command(tool_root, args.login, args.base_url)
    except RuntimeContextError as exc:
        raise SystemExit(f"[ops.user.password-reset.runtime] BLOCKED: {exc}") from None
    except Exception as exc:
        raise SystemExit(
            "[ops.user.password-reset.runtime] BLOCKED: unexpected failure "
            f"({type(exc).__name__})"
        ) from None
    os.execvpe(argv[0], argv, compose_env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
