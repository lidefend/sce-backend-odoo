#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The reverse proxy must not own the database default.

`/api/` (and the other proxied locations) always forward a database hint to the
backend.  When a request carries no `?db=` and no `X-Odoo-DB`, the nginx
template supplies a fallback.  That fallback is a *profile* fact, so it has to
be rendered from the registered profile environment (`DB_NAME`); a literal db
name in the template silently routes every hint-less request to whichever
database was inlined, and on any other profile that is a different, usually
non-existent, database.  The backend then answers `AUTH_REQUIRED 用户名或密码错误`,
which reads exactly like a wrong password even though the credential was fine.

This guard locks the mechanism, not a particular database name: the template
resolves the fallback from the injected variable, the compose service injects it
from the profile env, and no literal may come back.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "config/nginx/templates/default.conf.template"
COMPOSE = ROOT / "docker-compose.yml"
LEGACY_LITERAL_CONF = ROOT / "config/nginx/conf.d/default.conf"

FALLBACK_VAR = "${SC_PROXY_DEFAULT_DB}"
QUERY_MAP_DECLARATION_LINE = "map $arg_db $sc_proxy_query_db {\n"
HEADER_MAP_DECLARATION_LINE = "map $http_x_odoo_db $sc_proxy_header_db {\n"
PRECEDENCE_MAP_LINE = "map $sc_proxy_header_db $sc_proxy_hinted_db {\n"
EFFECTIVE_MAP_LINE = "map $sc_proxy_hinted_db $sc_proxy_db {\n"
FALLBACK_LINE = f"  ''      {FALLBACK_VAR};"
ALLOWED_MAP_LINE = "map $sc_proxy_db $sc_proxy_db_allowed {\n"
ALLOWED_PATTERN_LINE = "  ${SC_PROXY_ALLOWED_DB_PATTERN} 1;"
UNKNOWN_REFUSAL_LINE = "    return 400 '{\"error\":\"unknown_database\"}';"
TEMPLATE_MOUNT = "./config/nginx/templates:/etc/nginx/templates:ro"
COMPOSE_INJECTION = "SC_PROXY_DEFAULT_DB: ${DB_NAME}"
COMPOSE_PLATFORM_DB = "SC_PROXY_PLATFORM_DB: ${SC_PROXY_PLATFORM_DB:-sc_platform_control}"
COMPOSE_PLATFORM_UPSTREAM = "SC_PROXY_PLATFORM_UPSTREAM: ${SC_PROXY_PLATFORM_UPSTREAM:-odoo:8069}"
COMPOSE_ALLOWED_DB = "SC_PROXY_ALLOWED_DB_PATTERN:"
COMPOSE_FILTER = "NGINX_ENVSUBST_FILTER: '^SC_PROXY_(DEFAULT_DB|PLATFORM_DB|PLATFORM_UPSTREAM|ALLOWED_DB_PATTERN)$'"
UPSTREAM_MAP = "map $sc_proxy_db $sc_proxy_upstream {"
VARIABLE_PROXY_PASS = "proxy_pass http://$sc_proxy_upstream;"


def _read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _nginx_service(compose: str) -> str:
    lines = compose.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "nginx:" and line.startswith("  "))
    except StopIteration:
        return ""
    block = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith("  ") and not line.startswith("   ") and line.strip() and not line.lstrip().startswith("-"):
            break
        block.append(line)
    return "\n".join(block)


def probe(
    *,
    template: str | None = None,
    compose: str | None = None,
    legacy_conf_exists: bool | None = None,
) -> list[str]:
    errors: list[str] = []
    template = _read(TEMPLATE, errors) if template is None else template
    compose = _read(COMPOSE, errors) if compose is None else compose
    if legacy_conf_exists is None:
        legacy_conf_exists = LEGACY_LITERAL_CONF.exists()

    if template:
        if FALLBACK_LINE not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the no-hint database fallback must be "
                f"`{FALLBACK_LINE}` so the profile supplies the database"
            )
        if (
            QUERY_MAP_DECLARATION_LINE not in template
            or HEADER_MAP_DECLARATION_LINE not in template
            or PRECEDENCE_MAP_LINE not in template
            or EFFECTIVE_MAP_LINE not in template
        ):
            errors.append(
                "config/nginx/templates/default.conf.template: explicit ?db= / X-Odoo-DB must still resolve through "
                "the declared header > query > default precedence "
                f"(`{QUERY_MAP_DECLARATION_LINE.strip()}`, `{HEADER_MAP_DECLARATION_LINE.strip()}`, "
                f"`{PRECEDENCE_MAP_LINE.strip()}`, `{EFFECTIVE_MAP_LINE.strip()}`)"
            )
        if ALLOWED_MAP_LINE not in template or ALLOWED_PATTERN_LINE not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the effective database must be checked against the "
                f"entry's allowed set (`{ALLOWED_MAP_LINE.strip()}` and `{ALLOWED_PATTERN_LINE}`)"
            )
        if "if ($sc_proxy_db_allowed = 0) {" not in template or UNKNOWN_REFUSAL_LINE not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: an undeclared database hint must be refused with "
                "HTTP 400 `unknown_database`"
            )
        if UPSTREAM_MAP not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the database-to-upstream map must be declared "
                f"(`{UPSTREAM_MAP}`)"
            )
        if VARIABLE_PROXY_PASS not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: proxied locations must use the mapped upstream "
                f"(`{VARIABLE_PROXY_PASS}`)"
            )

    service = _nginx_service(compose)
    if not service:
        errors.append("docker-compose.yml: nginx service block not found")
    else:
        if COMPOSE_INJECTION not in service:
            errors.append(
                f"docker-compose.yml nginx service must inject the profile database (`{COMPOSE_INJECTION}`)"
            )
        if COMPOSE_PLATFORM_DB not in service:
            errors.append(
                f"docker-compose.yml nginx service must inject the platform database route (`{COMPOSE_PLATFORM_DB}`)"
            )
        if COMPOSE_PLATFORM_UPSTREAM not in service:
            errors.append(
                f"docker-compose.yml nginx service must inject the platform upstream route (`{COMPOSE_PLATFORM_UPSTREAM}`)"
            )
        if COMPOSE_ALLOWED_DB not in service:
            errors.append(
                f"docker-compose.yml nginx service must inject the allowed database pattern (`{COMPOSE_ALLOWED_DB}`)"
            )
        if COMPOSE_FILTER not in service:
            errors.append(
                f"docker-compose.yml nginx service must restrict envsubst to the proxy database variable (`{COMPOSE_FILTER}`)"
            )
        if TEMPLATE_MOUNT not in service:
            errors.append(
                f"docker-compose.yml nginx service must render the template (`{TEMPLATE_MOUNT}`)"
            )
        if "config/nginx/conf.d/default.conf" in service:
            errors.append(
                "docker-compose.yml nginx service must not mount a pre-rendered literal config"
            )

    if legacy_conf_exists:
        errors.append(
            "config/nginx/conf.d/default.conf must not exist: the proxy config is a template rendered per profile"
        )
    return errors


def main() -> int:
    errors = probe()
    if errors:
        print("[nginx.proxy_db_authority_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[nginx.proxy_db_authority_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
