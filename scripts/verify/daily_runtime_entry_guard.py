#!/usr/bin/env python3
"""The daily development server must expose exactly one public entry.

The platform control duty and the demo duty keep separate databases, clusters
and application containers.  What they must not keep are two public faces: the
serving duty's nginx owns the only public port, and the database hint carried by
the SPA chooses which duty's nginx answers.  This guard locks the declaration,
the proxy template and the duty stack together so a port, upstream or database
name cannot drift into a second entry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))
import daily_runtime_database_duty as duty_entry  # noqa: E402


ENTRY = ROOT / "config/ops/daily_runtime_entry.v1.json"
DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
TEMPLATE = ROOT / "config/nginx/templates/default.conf.template"
STACK = ROOT / "config/ops/daily_runtime_duty_stack.yml"
ENV_TEMPLATE = ROOT / "config/ops/daily_runtime_duty_stack.env"


def _read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def probe() -> list[str]:
    errors: list[str] = []
    try:
        entry = json.loads(ENTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"config/ops/daily_runtime_entry.v1.json: {error}"]
    declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
    errors.extend(duty_entry.validate_entry(entry, declaration))

    template = _read(TEMPLATE, errors)
    stack = _read(STACK, errors)
    env_template = _read(ENV_TEMPLATE, errors)

    if template:
        for token in (
            "map $sc_proxy_db $sc_proxy_upstream {",
            "${SC_PROXY_PLATFORM_DB}  ${SC_PROXY_PLATFORM_UPSTREAM};",
            "proxy_pass http://$sc_proxy_upstream;",
            "resolver 127.0.0.11 valid=10s ipv6=off;",
        ):
            if token not in template:
                errors.append(f"config/nginx/templates/default.conf.template: missing `{token}`")

    if stack:
        for token in (
            '"${ODOO_BIND_HOST:-0.0.0.0}:${ODOO_PORT}:8069"',
            '"${NGINX_BIND_HOST:-0.0.0.0}:${NGINX_PORT}:80"',
            "SC_PROXY_PLATFORM_DB: ${SC_PROXY_PLATFORM_DB}",
            "SC_PROXY_PLATFORM_UPSTREAM: ${SC_PROXY_PLATFORM_UPSTREAM}",
            "NGINX_ENVSUBST_FILTER: '^SC_PROXY_(DEFAULT_DB|PLATFORM_DB|PLATFORM_UPSTREAM)$'",
            "sc-daily-entry:",
            "name: ${SC_DAILY_ENTRY_NETWORK:-sc-daily-entry}",
        ):
            if token not in stack:
                errors.append(f"config/ops/daily_runtime_duty_stack.yml: missing `{token}`")

    if env_template:
        for key in (
            "ODOO_BIND_HOST=@ODOO_BIND_HOST@",
            "NGINX_BIND_HOST=@NGINX_BIND_HOST@",
            "SC_PROXY_PLATFORM_DB=@SC_PROXY_PLATFORM_DB@",
            "SC_PROXY_PLATFORM_UPSTREAM=@SC_PROXY_PLATFORM_UPSTREAM@",
            "SC_DAILY_ENTRY_NETWORK=@SC_DAILY_ENTRY_NETWORK@",
        ):
            if key not in env_template:
                errors.append(f"config/ops/daily_runtime_duty_stack.env: missing `{key}`")
    return errors


def main() -> int:
    errors = probe()
    if errors:
        print("[daily.runtime.entry.guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[daily.runtime.entry.guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
