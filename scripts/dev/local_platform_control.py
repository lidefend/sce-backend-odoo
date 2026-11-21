#!/usr/bin/env python3
"""Governed local platform-control lifecycle.

The platform control database is a separate local lifecycle unit: its own
PostgreSQL role, database, compose project, volumes and Odoo instance. It
installs only ``smart_core`` and never customer or industry business data.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "config/ops/local_platform_control.v1.json"
SAFE_COMPOSE = re.compile(r"^sc-[a-z0-9-]+$")
SAFE_DATABASE = re.compile(r"^sc_[a-z0-9_]+$")
SAFE_ROLE = re.compile(r"^sc_[a-z0-9_]+$")


def run(command, *, check=True, input_text=None):
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(
            "LOCAL_PLATFORM_COMMAND_FAILED:"
            + " ".join(command)
            + ":"
            + (result.stderr or result.stdout).strip()[:1000]
        )
    return result


def load_declaration():
    payload = json.loads(DECLARATION.read_text(encoding="utf-8"))
    project = str(payload.get("project") or "")
    database = str(payload.get("database") or "")
    app_role = str(payload.get("database_role") or "")
    maintenance_role = str(payload.get("maintenance_role") or "")
    if not SAFE_COMPOSE.fullmatch(project):
        raise RuntimeError(f"LOCAL_PLATFORM_PROJECT_DENIED:{project}")
    if not SAFE_DATABASE.fullmatch(database):
        raise RuntimeError(f"LOCAL_PLATFORM_DATABASE_DENIED:{database}")
    if not SAFE_ROLE.fullmatch(app_role):
        raise RuntimeError(f"LOCAL_PLATFORM_APP_ROLE_DENIED:{app_role}")
    if not SAFE_ROLE.fullmatch(maintenance_role) or maintenance_role == app_role:
        raise RuntimeError(
            f"LOCAL_PLATFORM_MAINTENANCE_ROLE_DENIED:{maintenance_role}"
        )
    if payload.get("dbfilter") != f"^{database}$":
        raise RuntimeError("LOCAL_PLATFORM_DBFILTER_MISMATCH")
    if payload.get("module") != "smart_core":
        raise RuntimeError("LOCAL_PLATFORM_MODULE_MUST_BE_SMART_CORE")
    return payload


def parse_env(path):
    values = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def default_target_env(source_env):
    return Path(source_env).resolve().parent / ".env.local.platform"


def prepare_env(*, declaration, source_env, target_env):
    source_env = Path(source_env).resolve()
    target_env = Path(target_env).resolve()
    if not source_env.is_file():
        raise RuntimeError(f"LOCAL_PLATFORM_SOURCE_ENV_MISSING:{source_env}")
    source = parse_env(source_env)
    if target_env.is_file():
        target = parse_env(target_env)
        for key, expected in (
            ("COMPOSE_PROJECT_NAME", declaration["project"]),
            ("DB_NAME", declaration["database"]),
            ("DB_USER", declaration["database_role"]),
            ("DB_MAINTENANCE_USER", declaration["maintenance_role"]),
            ("ODOO_DBFILTER", declaration["dbfilter"]),
        ):
            if target.get(key) != expected:
                raise RuntimeError(
                    f"LOCAL_PLATFORM_ENV_IDENTITY_MISMATCH:{key}:"
                    f"{target.get(key, '')}"
                )
        return target_env
    if not source.get("SC_ENTRY_SHARED_SECRET"):
        raise RuntimeError("LOCAL_PLATFORM_ENTRY_SECRET_MISSING")
    revision = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    app_password = secrets.token_hex(24)
    maintenance_password = secrets.token_hex(24)
    admin_password = secrets.token_hex(24)
    jwt_secret = secrets.token_hex(32)
    bootstrap_secret = secrets.token_hex(32)
    values = {
        "DUTY_NAME": "platform_control",
        "COMPOSE_PROJECT_NAME": declaration["project"],
        "ENV": "dev",
        "SC_ENVIRONMENT": "dev",
        "SC_ALLOW_DEMO_DATA": "0",
        "SC_DEMO_USER_PASSWORD": "",
        "SC_PRODUCT_ROOT": str(ROOT),
        "SC_SOURCE_REVISION": revision,
        "SC_DEPLOY_ENV": "local",
        "FRONTEND_BUILD_SHA256": "0" * 64,
        "POSTGRES_IMAGE": "postgres:15",
        "DB_NAME": declaration["database"],
        "DB_USER": declaration["database_role"],
        "DB_PASSWORD": app_password,
        "DB_MAINTENANCE_USER": declaration["maintenance_role"],
        "DB_MAINTENANCE_PASSWORD": maintenance_password,
        "ODOO_DBFILTER": declaration["dbfilter"],
        "LIST_DB": "false",
        "DB_DATA": declaration["volumes"]["database"],
        "REDIS_DATA": declaration["volumes"]["redis"],
        "ODOO_DATA": declaration["volumes"]["odoo"],
        "ODOO_IMAGE": "odoo17-odoo:latest",
        "ODOO_PORT": str(declaration["ports"]["odoo"]),
        "NGINX_PORT": str(declaration["ports"]["nginx"]),
        "ODOO_BIND_HOST": "127.0.0.1",
        "NGINX_BIND_HOST": "127.0.0.1",
        "SC_PROXY_DEFAULT_NAMESPACE": "platform",
        "SC_PROXY_DEFAULT_UPSTREAM": "odoo:8069",
        "SC_PROXY_PLATFORM_UPSTREAM": "odoo:8069",
        "SC_DECLARED_NAMESPACE_ALIASES": "platform",
        "SC_ENTRY_SHARED_SECRET": source["SC_ENTRY_SHARED_SECRET"],
        "SC_ENTRY_ROUTE_VERSION": source.get("SC_ENTRY_ROUTE_VERSION", ""),
        "SC_ENTRY_PLATFORM_STRIP": "1",
        "SC_DAILY_ENTRY_NETWORK": "sc-daily-entry",
        "FRONTEND_DIST_DIR": str(ROOT / "frontend/apps/web/dist-clean"),
        "DEMO_ADDONS_ROOT": str(ROOT / declaration["stack"]["empty_addons"]),
        "CUSTOMER_ADDONS_ROOT": str(ROOT / declaration["stack"]["empty_addons"]),
        "ADMIN_PASSWD": admin_password,
        "SC_PLATFORM_ADMIN_PASSWORD": admin_password,
        "JWT_SECRET": jwt_secret,
        "SC_BOOTSTRAP_SECRET": bootstrap_secret,
        "SC_BOOTSTRAP_LOGIN": "admin",
        "SCENE_CHANNEL": "stable",
        "SCENE_USE_PINNED": "0",
        "SCENE_ROLLBACK": "0",
    }
    target_env.parent.mkdir(parents=True, exist_ok=True)
    old_umask = os.umask(0o077)
    try:
        target_env.write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )
    finally:
        os.umask(old_umask)
    target_env.chmod(0o600)
    return target_env


def compose(declaration, env_file, *args, check=True):
    return run([
        "docker",
        "compose",
        "-f",
        str(ROOT / declaration["stack"]["compose_file"]),
        "--project-name",
        declaration["project"],
        "--env-file",
        str(env_file),
        *args,
    ], check=check)


def psql(declaration, env_file, database, statement):
    env = parse_env(env_file)
    container = f"{declaration['project']}-db-1"
    return run([
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        env["DB_MAINTENANCE_USER"],
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
        "-Atc",
        statement,
    ])


def ensure_database(declaration, env_file):
    env = parse_env(env_file)
    database = declaration["database"]
    role = declaration["database_role"]
    quoted_database = '"' + database.replace('"', '""') + '"'
    quoted_role = '"' + role.replace('"', '""') + '"'
    password = env["DB_PASSWORD"].replace("'", "''")
    exists = psql(
        declaration,
        env_file,
        "postgres",
        f"SELECT 1 FROM pg_database WHERE datname = '{database}'",
    ).stdout.strip()
    if exists != "1":
        psql(
            declaration,
            env_file,
            "postgres",
            (
                "DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "
                f"THEN CREATE ROLE {quoted_role} LOGIN NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT; END IF; "
                f"ALTER ROLE {quoted_role} PASSWORD '{password}'; "
                "END $$;"
            ),
        )
        psql(
            declaration,
            env_file,
            "postgres",
            (
                f"CREATE DATABASE {quoted_database} OWNER {quoted_role} "
                "ENCODING 'UTF8' TEMPLATE template0"
            ),
        )
    psql(
        declaration,
        env_file,
        database,
        f"REVOKE CONNECT ON DATABASE {quoted_database} FROM PUBLIC",
    )
    psql(
        declaration,
        env_file,
        database,
        f"GRANT CONNECT ON DATABASE {quoted_database} TO {quoted_role}",
    )
    psql(
        declaration,
        env_file,
        database,
        f"GRANT USAGE, CREATE ON SCHEMA public TO {quoted_role}",
    )


def render_config(declaration, env_file):
    compose(
        declaration,
        env_file,
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "/bin/sh",
        "odoo",
        "-c",
        "python3 /usr/local/bin/render_odoo_conf.py "
        "/etc/odoo/odoo.conf.template /var/lib/odoo/odoo.conf",
    )


def install_module(declaration, env_file):
    env = parse_env(env_file)
    render_config(declaration, env_file)
    compose(
        declaration,
        env_file,
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "/usr/bin/odoo",
        "odoo",
        "--config=/var/lib/odoo/odoo.conf",
        "-d",
        declaration["database"],
        "--db_host=db",
        "--db_port=5432",
        "--db_user=" + env["DB_USER"],
        "--db_password=" + env["DB_PASSWORD"],
        "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,"
        "/mnt/source-addons,/mnt/demo-addons,/mnt/customer-addons",
        "-i",
        declaration["module"],
        "--without-demo=all",
        "--no-http",
        "--workers=0",
        "--max-cron-threads=0",
        "--stop-after-init",
    )


def health(declaration, env_file):
    ensure_database(declaration, env_file)
    module_state = psql(
        declaration,
        env_file,
        declaration["database"],
        "SELECT state FROM ir_module_module WHERE name = 'smart_core'",
    ).stdout.strip()
    owner = psql(
        declaration,
        env_file,
        "postgres",
        (
            "SELECT pg_get_userbyid(datdba) FROM pg_database "
            f"WHERE datname = '{declaration['database']}'"
        ),
    ).stdout.strip()
    role = psql(
        declaration,
        env_file,
        "postgres",
        (
            "SELECT rolsuper::text || '|' || rolcreatedb::text || '|' || "
            "rolcreaterole::text || '|' || rolcanlogin::text FROM pg_roles "
            f"WHERE rolname = '{declaration['database_role']}'"
        ),
    ).stdout.strip()
    if module_state != "installed":
        raise RuntimeError(f"LOCAL_PLATFORM_MODULE_NOT_INSTALLED:{module_state}")
    if owner != declaration["database_role"]:
        raise RuntimeError(f"LOCAL_PLATFORM_DATABASE_OWNER_MISMATCH:{owner}")
    if role != "false|false|false|true":
        raise RuntimeError(f"LOCAL_PLATFORM_ROLE_ATTRIBUTES_MISMATCH:{role}")
    print(json.dumps({
        "status": "PASS",
        "project": declaration["project"],
        "database": declaration["database"],
        "database_owner": owner,
        "database_role": declaration["database_role"],
        "role_attributes": role,
        "module": declaration["module"],
        "module_state": module_state,
        "dbfilter": declaration["dbfilter"],
    }, ensure_ascii=False, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("prepare", "up", "install", "health", "down", "rebuild", "shell"),
    )
    parser.add_argument("--source-env", required=True)
    parser.add_argument("--target-env", default="")
    args = parser.parse_args()

    declaration = load_declaration()
    target_env = Path(args.target_env).resolve() if args.target_env else default_target_env(
        args.source_env
    )
    env_file = prepare_env(
        declaration=declaration,
        source_env=args.source_env,
        target_env=target_env,
    )
    if args.action == "prepare":
        print(f"LOCAL_PLATFORM_ENV={env_file}")
        return
    if args.action == "rebuild":
        if os.environ.get("CONFIRM_LOCAL_PLATFORM_REBUILD") != (
            "REBUILD_LOCAL_PLATFORM_CONTROL"
        ):
            raise RuntimeError("LOCAL_PLATFORM_REBUILD_CONFIRMATION_REQUIRED")
        compose(declaration, env_file, "down", "--volumes", "--remove-orphans")
        compose(declaration, env_file, "up", "-d", "--wait", "db", "redis")
        ensure_database(declaration, env_file)
        install_module(declaration, env_file)
        compose(declaration, env_file, "up", "-d", "--wait", "odoo")
        health(declaration, env_file)
        return
    if args.action == "up":
        compose(declaration, env_file, "up", "-d", "--wait", "db", "redis")
        ensure_database(declaration, env_file)
        compose(declaration, env_file, "up", "-d", "--wait", "odoo")
        health(declaration, env_file)
        return
    if args.action == "install":
        compose(declaration, env_file, "up", "-d", "--wait", "db", "redis")
        ensure_database(declaration, env_file)
        install_module(declaration, env_file)
        compose(declaration, env_file, "up", "-d", "--wait", "odoo")
        health(declaration, env_file)
        return
    if args.action == "health":
        health(declaration, env_file)
        return
    if args.action == "shell":
        health(declaration, env_file)
        artifact = os.environ.get("PRODUCT_RELEASE_ARTIFACT", "").strip()
        script = os.environ.get("PLATFORM_SHELL_SCRIPT", "").strip()
        if not script:
            raise RuntimeError("LOCAL_PLATFORM_SHELL_SCRIPT_REQUIRED")
        shell_command = (
            "odoo shell -d "
            + shlex.quote(declaration["database"])
            + " -c /var/lib/odoo/odoo.conf < "
            + shlex.quote(script)
        )
        result = run([
            "docker",
            "compose",
            "-f",
            str(ROOT / declaration["stack"]["compose_file"]),
            "--project-name",
            declaration["project"],
            "--env-file",
            str(env_file),
            "exec",
            "-T",
            "-e",
            "PRODUCT_RELEASE_ARTIFACT=" + artifact,
            "odoo",
            "sh",
            "-c",
            shell_command,
        ], check=False)
        if result.returncode:
            raise RuntimeError(
                "LOCAL_PLATFORM_SHELL_FAILED:"
                + (result.stderr or result.stdout).strip()[-2000:]
            )
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return
    if args.action == "down":
        compose(declaration, env_file, "down", "--remove-orphans")


if __name__ == "__main__":
    main()
