#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The entry decides the namespace; it never lets a client pick a database.

ADR-007 batch C changed the mechanism this guard protects:

* the path prefix (``/t/<alias>`` or ``/platform-admin``) is the only selector;
* every client database hint (``X-Odoo-DB`` / ``X-DB`` / ``X-Odoo-DB-Locked`` /
  ``?db=``) is stripped at the entry and refused by Odoo as a conflict;
* the entry stamps the namespace, audience, route version and shared secret so
  Odoo can verify the request came through the single public face;
* the platform namespace is a declared two-layer hop: the serving entry face
  forwards ``/platform-admin/...`` unchanged, and only the platform duty face
  strips the prefix for its own Odoo (``SC_ENTRY_PLATFORM_STRIP``).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "config/nginx/templates/default.conf.template"
COMPOSE = ROOT / "docker-compose.yml"
RENDERER = ROOT / "scripts/render_nginx_conf.sh"
DUTY_STACK = ROOT / "config/ops/daily_runtime_duty_stack.yml"
DUTY_ENV = ROOT / "config/ops/daily_runtime_duty_stack.env"
LEGACY_LITERAL_CONF = ROOT / "config/nginx/conf.d/default.conf"

PATH_MAP = "map $uri $sc_path_ns {"
TENANT_RULE = "~^/t/([a-z0-9][a-z0-9-]*)(/|$)  $1;"
PLATFORM_RULE = "~^/platform-admin(/|$)               platform;"
AUDIENCE_MAP = "map $sc_path_ns $sc_ns_audience {"
UPSTREAM_MAP = "map $sc_path_ns $sc_proxy_upstream {"
ALIAS_MAP = "map $sc_path_ns $sc_declared_ns {"
ALIAS_PATTERN = "~^(${SC_DECLARED_NAMESPACE_ALIASES})$"
EMPTY_DB_HEADER = 'proxy_set_header X-Odoo-DB         "";'
NAMESPACE_HEADER = "proxy_set_header X-SC-Namespace"
SECRET_HEADER = "proxy_set_header X-SC-Entry-Secret"
VERSION_HEADER = "proxy_set_header X-SC-Route-Version"
MISSING_REFUSAL = 'return 400 \'{"error":"NS_NAMESPACE_REQUIRED"}\';'
ROOT_API_REFUSAL = re.compile(
    r"location /api/ \{[^}]*return 400 '\{\"error\":\"NS_NAMESPACE_REQUIRED\"\}'",
    re.S,
)
HINT_REFUSAL = 'return 409 \'{"error":"NS_DATABASE_HINT_CONFLICT"}\';'
TENANT_FALLBACK = "location ~ ^/t/ {"
UNKNOWN_NAMESPACE_REFUSAL = 'return 404 \'{"error":"NS_UNKNOWN_NAMESPACE"}\';'
VARIABLE_PROXY_PASSES = (
    "proxy_pass http://$sc_entry_upstream;",
    "proxy_pass http://$sc_proxy_upstream;",
)
# These variables may only appear as the *key* of a detection map.  Using them
# as a header value or an upstream would make a client hint a routing input.
HINT_VARIABLES = ("$http_x_odoo_db", "$arg_db", "$sc_proxy_db")
COOKIE_PATH_MAP = "map $sc_entry_platform_strip $sc_proxy_cookie_path {"
COOKIE_PATH_REWRITE = "proxy_cookie_path / $sc_proxy_cookie_path;"
COOKIE_PATH_DOUBLE_REWRITE = "proxy_cookie_path / $sc_entry_cookie_path;"
PLATFORM_STRIP_GUARD = 'if ($sc_entry_platform_strip = "1") {'
PLATFORM_API_REWRITE = "rewrite ^/platform-admin(/api/.*)$ $1 break;"
PLATFORM_WEB_REWRITE = "rewrite ^/platform-admin(/.*)$ $1 break;"
PLATFORM_STRIP_BLOCK = re.compile(
    r'if \(\$sc_entry_platform_strip = "1"\) \{\s*\n(?P<body>.*?)\n\s*\}', re.S
)
COMPOSE_REQUIRED = (
    "SC_PROXY_DEFAULT_UPSTREAM:",
    "SC_PROXY_PLATFORM_UPSTREAM:",
    "SC_DECLARED_NAMESPACE_ALIASES: ${SC_DECLARED_NAMESPACE_ALIASES:-demo}",
    "SC_ENTRY_SHARED_SECRET:",
    "SC_ENTRY_ROUTE_VERSION:",
    "SC_ENTRY_PLATFORM_STRIP:",
)
STACK_REQUIRED = (
    "SC_PROXY_DEFAULT_UPSTREAM:",
    "SC_PROXY_PLATFORM_UPSTREAM:",
    "SC_DECLARED_NAMESPACE_ALIASES:",
    "SC_ENTRY_SHARED_SECRET:",
    "SC_ENTRY_ROUTE_VERSION:",
    "SC_ENTRY_PLATFORM_STRIP:",
)
STACK_RETIRED = (
    "SC_PROXY_DEFAULT_DB",
    "SC_PROXY_PLATFORM_DB",
    "SC_PROXY_ALLOWED_DB_PATTERN",
)
ENV_REQUIRED = (
    "SC_PROXY_DEFAULT_UPSTREAM=@SC_PROXY_DEFAULT_UPSTREAM@",
    "SC_PROXY_PLATFORM_UPSTREAM=@SC_PROXY_PLATFORM_UPSTREAM@",
    "SC_DECLARED_NAMESPACE_ALIASES=@SC_DECLARED_NAMESPACE_ALIASES@",
    "SC_ENTRY_SHARED_SECRET=@SC_ENTRY_SHARED_SECRET@",
    "SC_ENTRY_ROUTE_VERSION=@SC_ENTRY_ROUTE_VERSION@",
    "SC_ENTRY_PLATFORM_STRIP=@SC_ENTRY_PLATFORM_STRIP@",
)


def _read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def probe(
    *,
    template: str | None = None,
    compose: str | None = None,
    renderer: str | None = None,
    duty_stack: str | None = None,
    duty_env: str | None = None,
    legacy_conf_exists: bool | None = None,
) -> list[str]:
    errors: list[str] = []
    template = _read(TEMPLATE, errors) if template is None else template
    compose = _read(COMPOSE, errors) if compose is None else compose
    renderer = _read(RENDERER, errors) if renderer is None else renderer
    duty_stack = _read(DUTY_STACK, errors) if duty_stack is None else duty_stack
    duty_env = _read(DUTY_ENV, errors) if duty_env is None else duty_env
    if legacy_conf_exists is None:
        legacy_conf_exists = LEGACY_LITERAL_CONF.exists()

    if template:
        for needle, reason in (
            (PATH_MAP, "the path namespace map must be declared"),
            (TENANT_RULE, "the /t/<alias> prefix must resolve to the alias"),
            (PLATFORM_RULE, "the /platform-admin prefix must resolve to the platform namespace"),
            (AUDIENCE_MAP, "the audience must be derived from the namespace"),
            (UPSTREAM_MAP, "the upstream must be derived from the namespace, not a database hint"),
            (ALIAS_MAP, "the declared-alias whitelist must gate path namespaces"),
            (ALIAS_PATTERN, "the declared-alias whitelist must be rendered by the entry"),
        ):
            if needle not in template:
                errors.append(f"config/nginx/templates/default.conf.template: {reason} (`{needle}`)")
        for line in template.splitlines():
            if not any(token in line for token in HINT_VARIABLES):
                continue
            if line.strip().startswith("map "):
                continue
            errors.append(
                "config/nginx/templates/default.conf.template: a client database hint is still a routing "
                f"input (`{line.strip()}`)"
            )
        # nginx cannot lex a `{n,m}` regex quantifier in map keys or location
        # patterns; quoting does not help, and the failure only appears after
        # the container renders the template. Bound the alias length in the
        # resolver instead and keep the nginx pattern equivalent but brace-free.
        if re.search(r"\{\d+,\d*\}", template):
            errors.append(
                "config/nginx/templates/default.conf.template: nginx cannot parse a `{n,m}` regex "
                "quantifier; use an equivalent brace-free pattern and validate length in the resolver"
            )
        if template.count(EMPTY_DB_HEADER) < 8:
            errors.append(
                "config/nginx/templates/default.conf.template: every proxied location must blank "
                f"`X-Odoo-DB` (`{EMPTY_DB_HEADER}`)"
            )
        if template.count(NAMESPACE_HEADER) < 8:
            errors.append(
                "config/nginx/templates/default.conf.template: every proxied location must stamp "
                f"`X-SC-Namespace`"
            )
        if SECRET_HEADER not in template or VERSION_HEADER not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the entry stamp must carry the shared secret "
                "and route version"
            )
        if MISSING_REFUSAL not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: a missing namespace must be refused with "
                "HTTP 400 `NS_NAMESPACE_REQUIRED`"
            )
        if not ROOT_API_REFUSAL.search(template):
            errors.append(
                "config/nginx/templates/default.conf.template: the namespace-less `/api/` entry must be "
                "refused with HTTP 400 `NS_NAMESPACE_REQUIRED`, not served the SPA fallback"
            )
        for needle in VARIABLE_PROXY_PASSES:
            if needle not in template:
                errors.append(
                    "config/nginx/templates/default.conf.template: proxied locations must use the namespace upstream"
                )
        if HINT_REFUSAL not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: a client database hint must be refused with "
                "HTTP 409 `NS_DATABASE_HINT_CONFLICT`"
            )
        if "$http_x_odoo_database" not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the declared `X-Odoo-Database` hint must "
                "be detected, not silently ignored"
            )
        # The platform namespace crosses two nginx faces.  Only the serving face
        # may map `Path=/` to the public prefix; the duty face must leave the
        # path unchanged or the browser receives `/platform-admin/platform-admin/`.
        if COOKIE_PATH_MAP not in template or COOKIE_PATH_REWRITE not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the session cookie path must be scoped "
                "through the platform-strip-aware map"
            )
        if COOKIE_PATH_DOUBLE_REWRITE in template:
            errors.append(
                "config/nginx/templates/default.conf.template: both nginx faces rewrite the cookie path; "
                "the platform hop would double the namespace prefix"
            )
        if not re.search(r"server\s*\{[^}]*absolute_redirect off;", template):
            errors.append(
                "config/nginx/templates/default.conf.template: the bare-root redirect must set "
                "`absolute_redirect off` at server level, or the public port is dropped from Location"
            )
        if not re.search(r"server\s*\{[^}]*default_type application/json;", template):
            errors.append(
                "config/nginx/templates/default.conf.template: refusals must default to "
                "`application/json` at server level"
            )
        if TENANT_FALLBACK not in template or UNKNOWN_NAMESPACE_REFUSAL not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: an illegal `/t/` prefix must be refused "
                "with HTTP 404 `NS_UNKNOWN_NAMESPACE`, never served the SPA fallback"
            )
        if "$sc_declared_ns" not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: every tenant route must gate on the "
                "rendered declared-alias whitelist, never on the alias-shaped path alone"
            )
        if "SC_ENTRY_PLATFORM_STRIP" not in template or PLATFORM_STRIP_GUARD not in template:
            errors.append(
                "config/nginx/templates/default.conf.template: the platform two-layer hop must be declared "
                "with `SC_ENTRY_PLATFORM_STRIP`"
            )
        blocks = [match.group("body") for match in PLATFORM_STRIP_BLOCK.finditer(template)]
        guarded_rewrites = sum(block.count("rewrite ^/platform-admin") for block in blocks)
        declared_rewrites = template.count("rewrite ^/platform-admin")
        if guarded_rewrites != declared_rewrites or not declared_rewrites:
            errors.append(
                "config/nginx/templates/default.conf.template: every platform rewrite must sit inside the "
                "`SC_ENTRY_PLATFORM_STRIP` guard (the entry face must not strip the platform prefix)"
            )
        else:
            joined = "\n".join(blocks)
            for rewrite, reason in (
                (PLATFORM_API_REWRITE, "the platform API prefix must be stripped by the duty face"),
                (PLATFORM_WEB_REWRITE, "the platform web faces must be stripped by the duty face"),
            ):
                if rewrite not in joined:
                    errors.append(
                        f"config/nginx/templates/default.conf.template: {reason} (`{rewrite}`)"
                    )
    if compose:
        for needle in COMPOSE_REQUIRED:
            if needle not in compose:
                errors.append(f"docker-compose.yml: nginx/odoo environment must inject `{needle}`")
        if "SC_PROXY_DEFAULT_DB:" in compose:
            errors.append("docker-compose.yml: the database-name injection must be retired")
        if "SC_PROXY_ALLOWED_DB_PATTERN:" in compose:
            errors.append("docker-compose.yml: the allowed-database pattern must be retired")
    if renderer:
        if "SC_ENTRY_SHARED_SECRET" not in renderer or "SC_ENTRY_ROUTE_VERSION" not in renderer:
            errors.append("scripts/render_nginx_conf.sh: the entry stamp variables must be substituted")
        if "SC_ENTRY_PLATFORM_STRIP" not in renderer:
            errors.append(
                "scripts/render_nginx_conf.sh: the platform two-layer hop variable must be substituted"
            )
        if "odooDb" in renderer:
            errors.append("scripts/render_nginx_conf.sh: runtime-config must not publish a database name")
        if '"entryContract":"v2"' not in renderer:
            errors.append("scripts/render_nginx_conf.sh: runtime-config must publish the v2 entry contract")
    if duty_stack:
        for needle in STACK_REQUIRED:
            if needle not in duty_stack:
                errors.append(
                    "config/ops/daily_runtime_duty_stack.yml: the duty stack must inject "
                    f"`{needle}`"
                )
        for retired in STACK_RETIRED:
            if retired in duty_stack:
                errors.append(
                    "config/ops/daily_runtime_duty_stack.yml: the database selector must be retired "
                    f"(`{retired}`)"
                )
    if duty_env:
        for needle in ENV_REQUIRED:
            if needle not in duty_env:
                errors.append(
                    "config/ops/daily_runtime_duty_stack.env: the duty env template must declare "
                    f"`{needle}`"
                )
        for retired in STACK_RETIRED:
            if retired + "=" in duty_env:
                errors.append(
                    "config/ops/daily_runtime_duty_stack.env: the database selector must be retired "
                    f"(`{retired}`)"
                )
    if legacy_conf_exists:
        errors.append(
            "config/nginx/conf.d/default.conf exists and would shadow the templated entry"
        )
    return errors


def main() -> int:
    errors = probe()
    if errors:
        print("FAIL nginx_proxy_db_authority_guard")
        for item in errors:
            print(f" - {item}")
        return 1
    print("OK nginx_proxy_db_authority_guard: path namespace is the only database selector")
    return 0


if __name__ == "__main__":
    sys.exit(main())
