#!/usr/bin/env python3
"""Atomic, fail-closed closure of the three approved production modules."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BACKUP_CONFIG_PATH = Path("/etc/scems/production-backup.env")
BACKUP_ROOT = "/data/backups/sc_production"
BACKUP_CONFIG_KEYS = (
    "BACKUP_ROOT",
    "BACKUP_TARGET_DB",
    "BACKUP_DB_CONTAINER",
    "BACKUP_ODOO_CONTAINER",
    "BACKUP_DB_USER",
    "BACKUP_FILESTORE_ROOT",
)
TARGET_DATABASE = "sc_production"
TARGET_PROJECT = "sc_production"
DEPLOYMENT_MODE = "FIRST_FRESH_DEPLOY"
CONFIRMATION = "YES_INSTALL_MISSING_FORMAL_MODULES"
EXPECTED_SOURCE_SHA = "e996239f1779cf510a0ca2ca5cd169121406a48b"
EXPECTED_IMAGE_DIGEST = (
    "sha256:ab1d4154201246b20c85c3619d756d8b4c9a5c8e9543d76d0f5eea308b7c99ad"
)
EXPECTED_IMAGE_REFERENCE = (
    "ghcr.io/lidefend/sce-product@" + EXPECTED_IMAGE_DIGEST
)
TARGET_MODULES = (
    "smart_construction_bootstrap",
    "smart_construction_seed",
    "sc_norm_engine",
)
EXPECTED_DEPENDENCIES = {
    "smart_construction_bootstrap": ("base",),
    "smart_construction_seed": (
        "smart_construction_bootstrap",
        "account",
        "smart_construction_core",
    ),
    "sc_norm_engine": ("smart_construction_core", "uom"),
}
EXPECTED_DATA_FILES = {
    "smart_construction_bootstrap": (
        "data/baseline_currency.xml",
        "data/baseline_preferences.xml",
    ),
    "smart_construction_seed": (
        "data/sc_seed_dictionary_contract.xml",
        "data/sc_seed_tax.xml",
    ),
    "sc_norm_engine": (
        "security/ir.model.access.csv",
        "views/norm_views.xml",
        "views/norm_import_views.xml",
        "views/norm_menu.xml",
    ),
}
BUSINESS_MODELS = (
    "project.project",
    "construction.contract",
    "sc.settlement.order",
    "payment.request",
)
VOLUME_VARIABLES = (
    "SC_DATABASE_VOLUME",
    "SC_REDIS_VOLUME",
    "SC_FILESTORE_VOLUME",
    "SC_SESSION_VOLUME",
    "SC_TMP_VOLUME",
    "SC_LOG_VOLUME",
)
PRODUCTION_CONTAINERS = (
    "sc_production-db-1",
    "sc_production-redis-1",
    "sc_production-odoo-1",
    "sc_production-nginx-1",
)
CALLER_MODULE_VARIABLES = (
    "TARGET_MODULE",
    "TARGET_MODULES",
    "FORMAL_MODULES",
    "INSTALL_MODULES",
)


class FormalModuleInstallError(RuntimeError):
    pass


def load_backup_configuration(
    path: Path,
    active_env: Mapping[str, str],
    *,
    expected_uid: int = 0,
    expected_gid: int = 0,
) -> dict[str, str]:
    if path != BACKUP_CONFIG_PATH:
        raise FormalModuleInstallError("backup configuration path is not approved")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise FormalModuleInstallError(
            "approved backup configuration is unavailable"
        ) from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise FormalModuleInstallError(
            "backup configuration must be a regular non-symlink file"
        )
    if metadata.st_uid != expected_uid or metadata.st_gid != expected_gid:
        raise FormalModuleInstallError(
            "backup configuration must be owned by root:root"
        )
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise FormalModuleInstallError("backup configuration mode must be 0600")
    if metadata.st_size <= 0 or metadata.st_size > 16 * 1024:
        raise FormalModuleInstallError("backup configuration size is invalid")

    configured: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise FormalModuleInstallError(
            "backup configuration cannot be read safely"
        ) from exc
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise FormalModuleInstallError(
                f"invalid backup configuration line {line_number}"
            )
        name, value = line.split("=", 1)
        if name not in BACKUP_CONFIG_KEYS:
            raise FormalModuleInstallError(
                f"unsupported backup configuration key: {name}"
            )
        if name in configured:
            raise FormalModuleInstallError(
                f"duplicate backup configuration key: {name}"
            )
        if not value or value != value.strip() or any(
            character in value for character in ("\x00", "\n", "\r")
        ):
            raise FormalModuleInstallError(
                f"invalid backup configuration value: {name}"
            )
        configured[name] = value

    if set(configured) != set(BACKUP_CONFIG_KEYS):
        raise FormalModuleInstallError(
            "backup configuration keys differ from the fixed contract"
        )
    for name in BACKUP_CONFIG_KEYS:
        if active_env.get(name):
            raise FormalModuleInstallError(
                f"process environment backup override is forbidden: {name}"
            )
    expected = {
        "BACKUP_ROOT": BACKUP_ROOT,
        "BACKUP_TARGET_DB": TARGET_DATABASE,
        "BACKUP_DB_CONTAINER": "sc_production-db-1",
        "BACKUP_ODOO_CONTAINER": "sc_production-odoo-1",
        "BACKUP_FILESTORE_ROOT": "/opt/sce-runtime/filestore",
    }
    for name, value in expected.items():
        if configured[name] != value:
            raise FormalModuleInstallError(
                f"backup configuration identity differs: {name}"
            )
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", configured["BACKUP_DB_USER"]):
        raise FormalModuleInstallError("backup database user identity is invalid")

    resolved = dict(active_env)
    resolved.update(configured)
    resolved["BACKUP_CONFIG_SOURCE"] = str(path)
    return resolved


def _load_product_modules() -> tuple[str, ...]:
    path = ROOT / "config/tenant/module_sets.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    modules = tuple(payload.get("product_modules") or ())
    if len(modules) != 10 or len(set(modules)) != 10:
        raise FormalModuleInstallError(
            "formal product contract must contain 10 unique modules"
        )
    if not set(TARGET_MODULES).issubset(modules):
        raise FormalModuleInstallError(
            "fixed module allowlist differs from the formal product contract"
        )
    return modules


def validate_invocation(active_env: Mapping[str, str]) -> None:
    expected = {
        "ENV": "prod",
        "PROD_DANGER": "1",
        "TARGET_DB": TARGET_DATABASE,
        "PRODUCTION_COMPOSE_PROJECT": TARGET_PROJECT,
        "DEPLOYMENT_MODE": DEPLOYMENT_MODE,
        "CONFIRM_FORMAL_MODULE_INSTALL": CONFIRMATION,
        "EXPECTED_RELEASE_SHA": EXPECTED_SOURCE_SHA,
        "EXPECTED_IMAGE_DIGEST": EXPECTED_IMAGE_DIGEST,
        "ODOO_IMAGE_REF": EXPECTED_IMAGE_REFERENCE,
        "NGINX_IMAGE_REF": EXPECTED_IMAGE_REFERENCE,
        "BACKUP_CONFIG_SOURCE": str(BACKUP_CONFIG_PATH),
        "BACKUP_ROOT": BACKUP_ROOT,
        "BACKUP_TARGET_DB": TARGET_DATABASE,
        "BACKUP_DB_CONTAINER": "sc_production-db-1",
        "BACKUP_ODOO_CONTAINER": "sc_production-odoo-1",
        "BACKUP_FILESTORE_ROOT": "/opt/sce-runtime/filestore",
    }
    for name, value in expected.items():
        if active_env.get(name) != value:
            raise FormalModuleInstallError(f"{name} must be {value}")
    for name in CALLER_MODULE_VARIABLES:
        if active_env.get(name):
            raise FormalModuleInstallError(
                f"caller-controlled module selection is forbidden: {name}"
            )
    if not re.fullmatch(
        r"[a-z_][a-z0-9_]{0,62}", active_env.get("BACKUP_DB_USER", "")
    ):
        raise FormalModuleInstallError("BACKUP_DB_USER is invalid")


def dependency_order(manifests: Mapping[str, dict[str, Any]]) -> tuple[str, ...]:
    remaining = set(TARGET_MODULES)
    ordered: list[str] = []
    while remaining:
        ready = [
            name
            for name in TARGET_MODULES
            if name in remaining
            and not (set(manifests[name]["depends"]) & remaining)
        ]
        if not ready:
            raise FormalModuleInstallError("target module dependency cycle detected")
        for name in ready:
            ordered.append(name)
            remaining.remove(name)
    if ordered.index("smart_construction_bootstrap") > ordered.index(
        "smart_construction_seed"
    ):
        raise FormalModuleInstallError("bootstrap must precede seed")
    return tuple(ordered)


def validate_source_boundary(state: Mapping[str, Any]) -> tuple[str, ...]:
    manifests = state.get("target_manifests") or {}
    if set(manifests) != set(TARGET_MODULES):
        raise FormalModuleInstallError("target manifest inventory differs")
    for name in TARGET_MODULES:
        manifest = manifests[name]
        if not manifest.get("source_exists") or not manifest.get("installable"):
            raise FormalModuleInstallError(f"target module is unavailable: {name}")
        if tuple(manifest.get("depends") or ()) != EXPECTED_DEPENDENCIES[name]:
            raise FormalModuleInstallError(f"dependency drift detected: {name}")
        if tuple(manifest.get("data") or ()) != EXPECTED_DATA_FILES[name]:
            raise FormalModuleInstallError(f"data-file drift detected: {name}")
        if manifest.get("demo"):
            raise FormalModuleInstallError(f"demo data is forbidden: {name}")

    seed_operations = manifests["smart_construction_seed"].get(
        "xml_operations"
    ) or []
    seed_records = [
        item for item in seed_operations if item.get("kind") == "record"
    ]
    seed_functions = [
        item for item in seed_operations if item.get("kind") == "function"
    ]
    if (
        len(seed_records) != 5
        or {item.get("model") for item in seed_records} != {"sc.dictionary"}
        or seed_functions
        != [
            {
                "file": "data/sc_seed_tax.xml",
                "kind": "function",
                "model": "construction.contract",
                "name": "_sc_ensure_contract_tax_seeds",
            }
        ]
    ):
        raise FormalModuleInstallError(
            "smart_construction_seed data boundary differs from the approved baseline"
        )
    return dependency_order(manifests)


def _validate_common_state(
    state: Mapping[str, Any], formal_modules: tuple[str, ...]
) -> None:
    if state.get("database") != TARGET_DATABASE:
        raise FormalModuleInstallError("database identity is not sc_production")
    if tuple(state.get("formal_modules") or ()) != formal_modules:
        raise FormalModuleInstallError("runtime formal module contract differs")
    if state.get("pending_module_operations") != 0:
        raise FormalModuleInstallError("pending module operations must be zero")
    if state.get("demo_fixture_module_count") != 0:
        raise FormalModuleInstallError("demo/fixture module detected")
    counts = state.get("business_record_counts") or {}
    if set(counts) != set(BUSINESS_MODELS) or any(counts.values()):
        raise FormalModuleInstallError("fresh business record boundary differs")
    if state.get("historical_data_imported") is not False:
        raise FormalModuleInstallError("historical data must not be imported")
    if (
        state.get("admin_login") != "admin"
        or state.get("active_admin_count") != 1
        or state.get("active_admin_is_target") is not True
    ):
        raise FormalModuleInstallError("active Web administrator boundary differs")
    if str(state.get("seed_enabled")) != "0":
        raise FormalModuleInstallError("dynamic seed execution must be disabled")
    if state.get("seed_profile_configured"):
        raise FormalModuleInstallError("dynamic seed profile must be empty")
    if state.get("seed_runtime_overrides"):
        raise FormalModuleInstallError("dynamic seed runtime override detected")

    host = state.get("host") or {}
    if host.get("compose_project") != TARGET_PROJECT:
        raise FormalModuleInstallError("Compose project identity differs")
    if set(host.get("healthy_containers") or ()) != set(PRODUCTION_CONTAINERS):
        raise FormalModuleInstallError("production container health differs")
    if host.get("volume_count") != 6:
        raise FormalModuleInstallError("production volume identity differs")
    if host.get("image_digest_match") is not True:
        raise FormalModuleInstallError("rc.4 digest differs")
    if host.get("oci_revision_match") is not True:
        raise FormalModuleInstallError("OCI revision differs")
    if host.get("container_revision_match") is not True:
        raise FormalModuleInstallError("container source revision differs")


def validate_before(
    state: Mapping[str, Any], formal_modules: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    _validate_common_state(state, formal_modules)
    order = validate_source_boundary(state)
    module_states = state.get("module_states") or {}
    if set(module_states) != set(formal_modules):
        raise FormalModuleInstallError("formal module state inventory differs")
    if any(
        module_states[name] != "installed"
        for name in formal_modules
        if name not in TARGET_MODULES
    ):
        raise FormalModuleInstallError("non-target formal module state differs")
    if any(
        module_states[name] not in {"installed", "uninstalled"}
        for name in TARGET_MODULES
    ):
        raise FormalModuleInstallError("target module state is unsafe")
    missing = tuple(name for name in order if module_states[name] == "uninstalled")
    return order, missing


def validate_after(state: Mapping[str, Any], formal_modules: tuple[str, ...]) -> None:
    _validate_common_state(state, formal_modules)
    module_states = state.get("module_states") or {}
    if set(module_states) != set(formal_modules) or any(
        module_states[name] != "installed" for name in formal_modules
    ):
        raise FormalModuleInstallError("formal module closure is not 10/10")


class ProductionOperations:
    def __init__(self, active_env: Mapping[str, str]):
        self.env = dict(active_env)
        self.compose = [
            "docker",
            "compose",
            "-f",
            str(ROOT / "docker-compose.production-candidate.yml"),
        ]

    def _run(
        self, args: list[str], *, input_text: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            raise FormalModuleInstallError(
                f"controlled command failed: {Path(args[0]).name}"
            )
        return result

    def _inspect(self, *names: str) -> list[dict[str, Any]]:
        output = self._run(["docker", "inspect", *names]).stdout
        payload = json.loads(output)
        if not isinstance(payload, list):
            raise FormalModuleInstallError("docker inspect result is invalid")
        return payload

    def collect_state(self, formal_modules: tuple[str, ...]) -> dict[str, Any]:
        probe = (
            ROOT / "scripts/release/production_formal_module_state.py"
        ).read_text(encoding="utf-8")
        result = self._run(
            self.compose
            + [
                "exec",
                "-T",
                "-e",
                "FORMAL_MODULE_CONTRACT=" + ",".join(formal_modules),
                "odoo",
                "odoo",
                "shell",
                "-c",
                "/opt/sce-runtime/config/odoo.conf",
                "-d",
                TARGET_DATABASE,
            ],
            input_text=probe,
        )
        marker = next(
            (
                line.removeprefix("FORMAL_MODULE_STATE=")
                for line in result.stdout.splitlines()
                if line.startswith("FORMAL_MODULE_STATE=")
            ),
            "",
        )
        if not marker:
            raise FormalModuleInstallError("formal module state probe returned no result")
        state = json.loads(marker)

        containers = self._inspect(*PRODUCTION_CONTAINERS)
        healthy = sorted(
            item["Name"].lstrip("/")
            for item in containers
            if (item.get("State", {}).get("Health") or {}).get("Status")
            == "healthy"
        )
        expected_volumes = []
        for variable in VOLUME_VARIABLES:
            value = self.env.get(variable, "")
            if not value:
                raise FormalModuleInstallError(f"{variable} is required")
            expected_volumes.append(value)
        if len(set(expected_volumes)) != 6:
            raise FormalModuleInstallError("production volume names are not unique")
        self._run(["docker", "volume", "inspect", *expected_volumes])

        image_digest_match = True
        oci_revision_match = True
        container_revision_match = True
        for item in containers:
            name = item["Name"].lstrip("/")
            if name not in {"sc_production-odoo-1", "sc_production-nginx-1"}:
                continue
            image_digest_match &= (
                item.get("Config", {}).get("Image") == EXPECTED_IMAGE_REFERENCE
            )
            image = json.loads(
                self._run(["docker", "image", "inspect", item["Image"]]).stdout
            )[0]
            labels = image.get("Config", {}).get("Labels") or {}
            oci_revision_match &= (
                labels.get("org.opencontainers.image.revision")
                == EXPECTED_SOURCE_SHA
            )
            container_env = {
                value.split("=", 1)[0]: value.split("=", 1)[1]
                for value in item.get("Config", {}).get("Env") or []
                if "=" in value
            }
            container_revision_match &= (
                container_env.get("SC_SOURCE_REVISION") == EXPECTED_SOURCE_SHA
            )
        state["host"] = {
            "compose_project": self.env.get("PRODUCTION_COMPOSE_PROJECT"),
            "healthy_containers": healthy,
            "volume_count": len(expected_volumes),
            "image_digest_match": bool(image_digest_match),
            "oci_revision_match": bool(oci_revision_match),
            "container_revision_match": bool(container_revision_match),
        }
        return state

    def nginx_fingerprint(self) -> str:
        result = self._run(["nginx", "-T"])
        return hashlib.sha256(
            (result.stdout + result.stderr).encode("utf-8")
        ).hexdigest()

    def backup(self) -> str:
        path = ROOT / "scripts/release/production_colocated_backup.py"
        spec = importlib.util.spec_from_file_location(
            "production_colocated_backup", path
        )
        if not spec or not spec.loader:
            raise FormalModuleInstallError("production backup mechanism is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        backup_env = {
            name: self.env[name] for name in BACKUP_CONFIG_KEYS
        }
        previous = {name: os.environ.get(name) for name in backup_env}
        try:
            os.environ.update(backup_env)
            directory = module.backup(Path(backup_env["BACKUP_ROOT"]))
            module.validate_backup(directory)
        except Exception as exc:
            raise FormalModuleInstallError("production backup failed validation") from exc
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        return str(directory)

    def install(self, modules: tuple[str, ...]) -> None:
        if not modules:
            return
        if any(name not in TARGET_MODULES for name in modules):
            raise FormalModuleInstallError("installation list exceeds the fixed allowlist")
        module_list = ",".join(modules)
        command = (
            "python3 /usr/local/bin/production_db_contract.py health; "
            "python3 /usr/local/bin/render_odoo_conf.py "
            "/etc/odoo/odoo.conf.template "
            '"${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}"; '
            'exec odoo -c "${ODOO_CONF_OUT:-/opt/sce-runtime/config/odoo.conf}" '
            f"-d {TARGET_DATABASE} --no-http --workers=0 --max-cron-threads=0 "
            '-i "$FORMAL_MODULE_ALLOWLIST" --without-demo=all --stop-after-init'
        )
        self._run(
            self.compose
            + [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                "FORMAL_MODULE_ALLOWLIST=" + module_list,
                "--entrypoint",
                "/bin/sh",
                "odoo",
                "-eu",
                "-c",
                command,
            ]
        )


def orchestrate(
    active_env: Mapping[str, str], operations: Any
) -> dict[str, Any]:
    validate_invocation(active_env)
    formal_modules = _load_product_modules()
    nginx_before = operations.nginx_fingerprint()
    before = operations.collect_state(formal_modules)
    order, missing = validate_before(before, formal_modules)
    if not missing:
        validate_after(before, formal_modules)
        if operations.nginx_fingerprint() != nginx_before:
            raise FormalModuleInstallError("Nginx configuration changed")
        return {
            "status": "PASS",
            "backup": "NOT_REQUIRED_ALREADY_COMPLETE",
            "installed_modules": [],
            "formal_modules_installed": 10,
        }

    ordered_missing = tuple(name for name in order if name in missing)
    backup_directory = operations.backup()
    if not backup_directory:
        raise FormalModuleInstallError("validated production backup is required")
    operations.install(ordered_missing)
    after = operations.collect_state(formal_modules)
    validate_after(after, formal_modules)
    if operations.nginx_fingerprint() != nginx_before:
        raise FormalModuleInstallError("Nginx configuration changed")
    return {
        "status": "PASS",
        "backup": backup_directory,
        "installed_modules": list(ordered_missing),
        "formal_modules_installed": 10,
    }


def main() -> int:
    if sys.argv[1:] != ["execute"]:
        raise SystemExit("usage: production_formal_module_install.py execute")
    try:
        active_env = load_backup_configuration(BACKUP_CONFIG_PATH, os.environ)
        result = orchestrate(active_env, ProductionOperations(active_env))
    except FormalModuleInstallError as exc:
        raise SystemExit(
            f"[production.formal-modules.install] BLOCKED: {exc}"
        ) from exc
    print(
        "[production.formal-modules.install] "
        + json.dumps(result, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
