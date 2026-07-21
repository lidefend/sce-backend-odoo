#!/usr/bin/env python3
"""Initialize one explicitly authorized database with owned-failure cleanup."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Protocol

from production_db_contract import ContractError, validate

ORPHAN_DATABASE_EXIT = 70


class InitializationError(RuntimeError):
    pass


class Admin(Protocol):
    def exists(self, database: str) -> bool: ...
    def create(self, database: str) -> None: ...
    def cleanup_created(self, database: str) -> None: ...


class PostgresAdmin:
    def __init__(self, env: Mapping[str, str]):
        self.env = env

    def _connect(self):
        import psycopg2

        return psycopg2.connect(
            host=self.env.get("DB_HOST", "db"),
            port=int(self.env.get("DB_PORT", "5432")),
            user=self.env.get("DB_USER"),
            password=self.env.get("DB_PASSWORD"),
            dbname="postgres",
        )

    def exists(self, database: str) -> bool:
        conn = self._connect()
        try:
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def create(self, database: str) -> None:
        from psycopg2 import sql

        conn = self._connect()
        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {} WITH TEMPLATE template0 ENCODING 'UTF8'").format(
                        sql.Identifier(database)
                    )
                )
        finally:
            conn.close()

    def cleanup_created(self, database: str) -> None:
        from psycopg2 import sql

        conn = self._connect()
        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=%s AND pid <> pg_backend_pid()",
                    (database,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database))
                )
        finally:
            conn.close()


def _odoo_command(config: str, database: str) -> list[str]:
    return [
        "odoo", "-c", config, "-d", database, "--no-http", "--workers=0",
        "--max-cron-threads=0", "-i", "base", "--without-demo=all", "--stop-after-init",
    ]


def initialize(
    config: str,
    env: dict[str, str] | None = None,
    admin: Admin | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    active_env = dict(os.environ if env is None else env)
    database = validate("init", active_env)
    database_admin = admin or PostgresAdmin(active_env)

    if database_admin.exists(database):
        raise InitializationError("target database already exists; refusing initialization and cleanup")

    try:
        database_admin.create(database)
    except Exception as exc:
        raise InitializationError("CREATE DATABASE failed; cleanup was not attempted") from exc

    print(f"[production-db-init] created database for this invocation: {database}")
    try:
        result = runner(_odoo_command(config, database), check=False, env=active_env)
        init_status = result.returncode if 0 < result.returncode < 256 else (0 if result.returncode == 0 else 1)
    except Exception as exc:
        print(f"[production-db-init] base initialization could not start: {type(exc).__name__}", file=sys.stderr)
        init_status = 1

    if init_status == 0:
        print(f"[production-db-init] initialized database: {database}")
        return 0

    try:
        # Re-run the complete contract, including the production confirmation,
        # before compensating the database owned by this invocation.
        validate("init", active_env)
        database_admin.cleanup_created(database)
    except Exception as cleanup_error:
        print(
            "[production-db-init] BLOCKED: base initialization failed and cleanup failed; "
            f"an orphan database may exist ({type(cleanup_error).__name__})",
            file=sys.stderr,
        )
        return ORPHAN_DATABASE_EXIT

    print(
        "[production-db-init] base initialization failed; removed the database created by this invocation",
        file=sys.stderr,
    )
    return init_status


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: production_db_init.py <odoo-config>")
    try:
        status = initialize(sys.argv[1])
    except (ContractError, InitializationError) as exc:
        raise SystemExit(f"[production-db-init] BLOCKED: {exc}") from exc
    raise SystemExit(status)


if __name__ == "__main__":
    main()
