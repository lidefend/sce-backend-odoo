#!/usr/bin/env python3
"""Governed lifecycle for a fully disposable Odoo registry audit runtime."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SAFE_PREFIX = "sc-admin-vis-p3-registry-audit"
RUN_ID_RE = re.compile(rf"^{SAFE_PREFIX}-[a-z0-9]{{12}}$")
RESOURCE_LABELS = {
    "com.smartconstruction.audit.managed": "true",
    "com.smartconstruction.audit.kind": "admin-vis-p3-registry",
}
REQUIRED_EXPORT_KEYS = {
    "run_metadata",
    "installed_modules",
    "extension_modules",
    "extension_contributions",
    "handler_registry",
    "aliases",
    "route_policies",
    "generic_api_policies",
    "runtime_models",
    "project_models",
    "project_field_definitions",
    "model_default_sources",
    "overridden_create_write_unlink",
    "public_rpc_candidates",
    "unresolved_runtime_nodes",
}
REQUIRED_GENERIC_POLICY_KEYS = {
    "generic_policy_id",
    "registry_key",
    "contribution_module",
    "source_file",
    "source_symbol",
    "canonical_handler",
    "aliases",
    "effective_implementation",
    "replaced_implementations",
    "load_order_index",
    "load_order_evidence",
    "policy_provider_type",
    "policy_metadata_source",
    "policy_metadata_statically_readable",
    "model_selector_type",
    "allowed_models",
    "denied_models",
    "default_model_decision",
    "model_operation_policies",
    "field_policies",
    "method_policies",
    "domain_policy",
    "context_policy",
    "project_id_input_sources",
    "model_default_injection",
    "dynamic_generator_source",
    "dynamic_inputs",
    "enumeration_status",
    "unresolved_reason",
}
REQUIRED_ROUTE_POLICY_KEYS = {
    "route_policy_id",
    "route",
    "controller",
    "controller_source_file",
    "method",
    "method_symbol",
    "method_source_file",
    "module",
    "route_surface",
    "auth",
    "type",
    "methods",
    "csrf",
    "cors",
    "readonly",
    "save_session",
    "routing_metadata",
    "override_chain",
    "registration_order",
    "registration_evidence",
    "executed_during_audit",
}
ROUTE_SURFACES = {
    "CUSTOM_FRONTEND_PAGE_ROUTE",
    "CUSTOM_FRONTEND_BACKEND_API",
    "ODOO_NATIVE_WEB_ROUTE",
    "ODOO_NATIVE_RPC",
    "INTERNAL_ROUTE",
}
REQUIRED_FRAMEWORK_RULE_KEYS = {
    "routing_map_id",
    "routing_map_class",
    "routing_map_order",
    "route",
    "methods",
    "endpoint_symbol",
    "effective_implementation",
    "route_surface",
    "match_dimensions",
    "dispatch_dimensions",
    "security_dimensions",
    "ordering_key_repr",
    "ordering_key_executed",
    "endpoint_executed",
    "matcher_executed",
}
REQUIRED_ROUTE_CONFLICT_KEYS = {
    "route_conflict_id",
    "route_path",
    "http_methods",
    "route_surfaces",
    "contributions",
    "contribution_modules",
    "source_files",
    "source_symbols",
    "controller_inheritance",
    "module_dependency_order",
    "controller_registration_order",
    "routing_map_order",
    "final_routing_map_ids",
    "same_final_routing_map",
    "final_rule_count",
    "final_rules",
    "rule_endpoints",
    "effective_endpoint",
    "effective_implementation",
    "replaced_implementations",
    "conflict_classification",
    "false_conflict_reason",
    "overlap_blockers",
    "overlap_unresolved_inputs",
    "winner_analysis_permitted",
    "winner_analysis_status",
    "winner_decision_rule",
    "winner_evidence",
    "external_reachability",
    "policy_change_across_override",
    "security_relevant_differences",
    "enumeration_status",
    "unresolved_reason",
    "request_match_executed",
    "endpoint_executed",
}
FORBIDDEN_ENV_KEYS = {
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
}
FORBIDDEN_DATABASE_NAMES = {
    "sc_demo",
    "sc_frontend_acceptance",
    "daily",
    "scbs",
    "legacy_source_b",
    "postgres",
    "template0",
    "template1",
}


class AuditError(RuntimeError):
    """Fail-closed registry audit error."""


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class Runner:
    def run(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        check: bool = True,
        capture: bool = True,
    ) -> CommandResult:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
        )
        result = CommandResult(
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            returncode=completed.returncode,
        )
        if check and result.returncode:
            rendered = " ".join(shlex.quote(part) for part in args)
            raise AuditError(
                f"command failed rc={result.returncode}: {rendered}\n"
                f"{result.stderr.strip()}"
            )
        return result


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"invalid JSON file: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be an object: {path}")
    return value


def _git_value(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AuditError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _new_run_id() -> str:
    return f"{SAFE_PREFIX}-{secrets.token_hex(6)}"


def _validate_run_id(run_id: str) -> str:
    value = str(run_id or "").strip().lower()
    if not RUN_ID_RE.fullmatch(value):
        raise AuditError(
            f"invalid run id; expected {SAFE_PREFIX}- plus 12 lowercase hex characters"
        )
    return value


def _safe_modules(raw: str) -> list[str]:
    modules = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if not modules:
        raise AuditError("REGISTRY_AUDIT_MODULES must not be empty")
    for module in modules:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", module):
            raise AuditError(f"invalid module name: {module!r}")
    return sorted(set(modules))


def _output_root() -> Path:
    root = Path(
        os.environ.get(
            "REGISTRY_AUDIT_OUTPUT_ROOT",
            f"/tmp/{SAFE_PREFIX}",
        )
    ).resolve()
    repository = ROOT.resolve()
    if root == repository or repository in root.parents or root in repository.parents:
        raise AuditError("registry audit output root must be outside the repository")
    if str(root) in {"/", "/tmp"}:
        raise AuditError("registry audit output root is too broad")
    return root


def _paths(run_id: str) -> dict[str, Path]:
    output = _output_root() / run_id
    return {
        "output": output,
        "manifest": output / "creation-manifest.json",
        "credentials": output / ".database-credentials.json",
        "export": output / "registry-export.json",
        "pre_snapshot": output / "docker-resources-before.json",
        "post_snapshot": output / "docker-resources-after.json",
        "result": output / "audit-result.json",
    }


def _resource_names(run_id: str) -> dict[str, Any]:
    suffix = run_id.removeprefix(f"{SAFE_PREFIX}-")
    compose_project = run_id
    database = f"sc_admin_vis_p3_registry_audit_{suffix}"
    if database.lower() in FORBIDDEN_DATABASE_NAMES:
        raise AuditError(f"refusing forbidden database name: {database}")
    return {
        "compose_project": compose_project,
        "database": database,
        "database_user": f"registry_audit_{suffix}",
        "network": f"{compose_project}-internal",
        "volumes": [
            f"{compose_project}-pgdata",
            f"{compose_project}-odoodata",
            f"{compose_project}-extraaddons",
        ],
        "containers": [
            f"{compose_project}-postgres",
            f"{compose_project}-odoo-registry",
        ],
    }


def _docker_command() -> list[str]:
    raw = os.environ.get("COMPOSE_BIN", "docker compose")
    command = shlex.split(raw)
    if not command:
        raise AuditError("COMPOSE_BIN resolved to an empty command")
    return command


def _docker_binary() -> str:
    return os.environ.get("REGISTRY_AUDIT_DOCKER_BIN", "docker")


def _compose_file() -> Path:
    path = (
        ROOT
        / os.environ.get(
            "REGISTRY_AUDIT_COMPOSE_FILE",
            "docker-compose.registry-audit.yml",
        )
    ).resolve()
    if not path.is_file() or ROOT.resolve() not in path.parents:
        raise AuditError(f"registry audit compose file is unavailable: {path}")
    return path


def _compose_args(manifest: dict[str, Any]) -> list[str]:
    return [
        *_docker_command(),
        "--project-directory",
        str(ROOT),
        "-p",
        manifest["compose_project_name"],
        "-f",
        str(_compose_file()),
    ]


def _sanitized_environment(
    manifest: dict[str, Any], credentials: dict[str, str]
) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in FORBIDDEN_ENV_KEYS
        and not key.upper().endswith("_PROXY")
        and key
        not in {
            "DB_NAME",
            "DB",
            "BD",
            "DATABASE_URL",
            "PGHOST",
            "PGPORT",
            "PGDATABASE",
            "PGUSER",
            "PGPASSWORD",
        }
    }
    resources = manifest["resources"]
    env.update(
        {
            "REGISTRY_AUDIT_RUN_ID": manifest["run_id"],
            "REGISTRY_AUDIT_DATABASE_NAME": manifest["database_name"],
            "REGISTRY_AUDIT_DATABASE_USER": credentials["user"],
            "REGISTRY_AUDIT_DATABASE_PASSWORD": credentials["password"],
            "REGISTRY_AUDIT_MODULES": ",".join(manifest["modules"]),
            "REGISTRY_AUDIT_GIT_HEAD": manifest["git_head"],
            "REGISTRY_AUDIT_GIT_TREE": manifest["git_tree"],
            "REGISTRY_AUDIT_OUTPUT_DIRECTORY": manifest["output_directory"],
            "REGISTRY_AUDIT_NETWORK_NAME": resources["networks"][0],
            "REGISTRY_AUDIT_PGDATA_VOLUME": resources["volumes"][0],
            "REGISTRY_AUDIT_ODOODATA_VOLUME": resources["volumes"][1],
            "REGISTRY_AUDIT_EXTRAADDONS_VOLUME": resources["volumes"][2],
            "REGISTRY_AUDIT_POSTGRES_CONTAINER": resources["containers"][0],
            "REGISTRY_AUDIT_ODOO_CONTAINER": resources["containers"][1],
            "REGISTRY_AUDIT_ODOO_IMAGE": manifest["images"]["odoo"],
            "REGISTRY_AUDIT_POSTGRES_IMAGE": manifest["images"]["postgres"],
            "COMPOSE_PROJECT_NAME": manifest["compose_project_name"],
        }
    )
    return env


def _labels_for(run_id: str) -> dict[str, str]:
    return {**RESOURCE_LABELS, "com.smartconstruction.audit.run-id": run_id}


def _initial_manifest(run_id: str) -> dict[str, Any]:
    names = _resource_names(run_id)
    paths = _paths(run_id)
    modules = _safe_modules(
        os.environ.get("REGISTRY_AUDIT_MODULES", "smart_construction_core")
    )
    return {
        "schema_version": 2,
        "run_id": run_id,
        "task": "ESTABLISH_ADMIN_VIS_P3_EPHEMERAL_REGISTRY_AUDIT_ENVIRONMENT",
        "compose_project_name": names["compose_project"],
        "database_name": names["database"],
        "database_role": "ephemeral_noncustomer_registry_audit",
        "tenant_id": f"noncustomer-{run_id}",
        "environment_id": "test-ephemeral-registry-audit",
        "exact_dbfilter": f"^{re.escape(names['database'])}$",
        "filestore_identity": names["volumes"][1],
        "modules": modules,
        "git_head": _git_value("rev-parse", "HEAD"),
        "git_tree": _git_value("rev-parse", "HEAD^{tree}"),
        "output_directory": str(paths["output"]),
        "compose_file": str(_compose_file().relative_to(ROOT)),
        "images": {
            "odoo": os.environ.get(
                "REGISTRY_AUDIT_ODOO_IMAGE", "odoo17-odoo:latest"
            ),
            "postgres": os.environ.get(
                "REGISTRY_AUDIT_POSTGRES_IMAGE", "postgres:15"
            ),
        },
        "labels": _labels_for(run_id),
        "resources": {
            "containers": names["containers"],
            "networks": [names["network"]],
            "volumes": names["volumes"],
        },
        "resource_records": {
            kind: [
                {
                    "name": name,
                    "id": "",
                    "created": False,
                    "removed": False,
                }
                for name in values
            ]
            for kind, values in {
                "containers": names["containers"],
                "networks": [names["network"]],
                "volumes": names["volumes"],
            }.items()
        },
        "isolation_contract": {
            "customer_data_allowed": False,
            "fixture_allowed": False,
            "demo_allowed": False,
            "existing_database_server_allowed": False,
            "existing_container_reuse_allowed": False,
            "host_ports_allowed": False,
            "host_network_allowed": False,
            "external_network_allowed": False,
            "docker_socket_mount_allowed": False,
            "cron_enabled": False,
            "workers_enabled": False,
        },
        "lifecycle": {
            "validated": False,
            "resources_created": False,
            "export_created": False,
            "cleanup_complete": False,
        },
    }


def _write_credentials(path: Path, user: str) -> None:
    _atomic_json(path, {"user": user, "password": secrets.token_urlsafe(32)})


def _prepare(run_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    paths = _paths(run_id)
    paths["output"].mkdir(parents=True, exist_ok=False)
    # The Odoo image runs as its non-root ``odoo`` user.  A sticky, run-unique
    # directory lets that user create the export without allowing it to replace
    # the host-owned manifest or credentials.
    paths["output"].chmod(0o1777)
    manifest = _initial_manifest(run_id)
    _write_credentials(paths["credentials"], _resource_names(run_id)["database_user"])
    credentials = _read_json(paths["credentials"])
    _atomic_json(paths["manifest"], manifest)
    return manifest, {
        "user": str(credentials["user"]),
        "password": str(credentials["password"]),
    }


def _load(run_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    paths = _paths(run_id)
    manifest = _read_json(paths["manifest"])
    credentials = _read_json(paths["credentials"])
    _validate_manifest_identity(manifest, run_id)
    return manifest, {
        "user": str(credentials["user"]),
        "password": str(credentials["password"]),
    }


def _validate_manifest_identity(manifest: dict[str, Any], run_id: str) -> None:
    expected = _resource_names(run_id)
    if manifest.get("run_id") != run_id:
        raise AuditError("manifest run id mismatch")
    if manifest.get("compose_project_name") != expected["compose_project"]:
        raise AuditError("manifest compose project mismatch")
    if manifest.get("database_name") != expected["database"]:
        raise AuditError("manifest database name mismatch")
    resources = manifest.get("resources")
    if not isinstance(resources, dict):
        raise AuditError("manifest resources are missing")
    for kind in ("containers", "networks", "volumes"):
        actual = resources.get(kind)
        expected_values = (
            expected[kind]
            if kind != "networks"
            else [expected["network"]]
        )
        if actual != expected_values:
            raise AuditError(f"manifest {kind} mismatch")
        records = (manifest.get("resource_records") or {}).get(kind)
        if not isinstance(records, list) or [
            record.get("name") for record in records
        ] != expected_values:
            raise AuditError(f"manifest {kind} resource records mismatch")
    if manifest.get("labels") != _labels_for(run_id):
        raise AuditError("manifest labels mismatch")


def _resource_snapshot(runner: Runner) -> dict[str, list[dict[str, str]]]:
    docker = _docker_binary()
    commands = {
        "containers": [
            docker,
            "ps",
            "-a",
            "--format",
            "{{.ID}}\t{{.Names}}",
        ],
        "networks": [
            docker,
            "network",
            "ls",
            "--format",
            "{{.ID}}\t{{.Name}}",
        ],
        "volumes": [
            docker,
            "volume",
            "ls",
            "--format",
            "{{.Name}}\t{{.Driver}}",
        ],
    }
    snapshot: dict[str, list[dict[str, str]]] = {}
    for kind, args in commands.items():
        rows = []
        for line in runner.run(args).stdout.splitlines():
            if not line.strip():
                continue
            left, _, right = line.partition("\t")
            if kind == "volumes":
                rows.append(
                    {
                        "id": left.strip(),
                        "name": left.strip(),
                        "driver": right.strip(),
                    }
                )
            else:
                rows.append({"id": left.strip(), "name": right.strip()})
        snapshot[kind] = sorted(rows, key=lambda row: (row["name"], row["id"]))
    return snapshot


def _inspect_labels(
    runner: Runner, kind: str, name: str, *, allow_missing: bool = False
) -> dict[str, str] | None:
    docker = _docker_binary()
    if kind == "containers":
        args = [docker, "inspect", "--format", "{{json .Config.Labels}}", name]
    elif kind == "networks":
        args = [
            docker,
            "network",
            "inspect",
            "--format",
            "{{json .Labels}}",
            name,
        ]
    elif kind == "volumes":
        args = [
            docker,
            "volume",
            "inspect",
            "--format",
            "{{json .Labels}}",
            name,
        ]
    else:
        raise AuditError(f"unsupported resource kind: {kind}")
    result = runner.run(args, check=False)
    if result.returncode:
        if allow_missing:
            return None
        raise AuditError(f"cannot inspect expected {kind} resource: {name}")
    try:
        labels = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid labels for {kind} resource {name}") from exc
    return {str(key): str(value) for key, value in (labels or {}).items()}


def _inspect_resource_id(
    runner: Runner,
    kind: str,
    name: str,
    *,
    allow_missing: bool = False,
) -> str | None:
    docker = _docker_binary()
    if kind == "containers":
        args = [docker, "inspect", "--format", "{{.Id}}", name]
    elif kind == "networks":
        args = [docker, "network", "inspect", "--format", "{{.Id}}", name]
    elif kind == "volumes":
        args = [docker, "volume", "inspect", "--format", "{{.Name}}", name]
    else:
        raise AuditError(f"unsupported resource kind: {kind}")
    result = runner.run(args, check=False)
    if result.returncode:
        if allow_missing:
            return None
        raise AuditError(f"cannot inspect expected {kind} resource id: {name}")
    value = result.stdout.strip()
    if not value:
        raise AuditError(f"empty {kind} resource id: {name}")
    return value


def _record_created_resources(
    runner: Runner,
    manifest: dict[str, Any],
) -> None:
    changed = False
    for kind, records in manifest["resource_records"].items():
        for record in records:
            identity = _inspect_resource_id(
                runner,
                kind,
                record["name"],
                allow_missing=True,
            )
            if identity is None:
                continue
            _assert_labels(runner, kind, record["name"], manifest["labels"])
            if record.get("id") not in {"", identity}:
                raise AuditError(
                    f"{kind} resource identity changed: {record['name']}"
                )
            record["id"] = identity
            record["created"] = True
            changed = True
    if changed:
        _atomic_json(_paths(manifest["run_id"])["manifest"], manifest)


def _assert_labels(
    runner: Runner, kind: str, name: str, expected: dict[str, str]
) -> None:
    labels = _inspect_labels(runner, kind, name)
    mismatches = {
        key: {"expected": value, "actual": labels.get(key) if labels else None}
        for key, value in expected.items()
        if not labels or labels.get(key) != value
    }
    if mismatches:
        raise AuditError(
            f"refusing {kind} resource with mismatched labels: {name}: {mismatches}"
        )


def _assert_resources_absent(runner: Runner, manifest: dict[str, Any]) -> None:
    for kind, names in manifest["resources"].items():
        for name in names:
            if _inspect_labels(runner, kind, name, allow_missing=True) is not None:
                raise AuditError(f"refusing to reuse existing {kind} resource: {name}")


def _validate_compose_static(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required = (
        "internal: true",
        "ports:",
        "pull_policy: never",
        "read_only: true",
        "com.smartconstruction.audit.run-id",
        "registry_audit_pgdata",
        "registry_audit_odoodata",
    )
    missing = [token for token in required if token not in text]
    forbidden = (
        "network_mode: host",
        "/var/run/docker.sock",
        "external: true",
        "env_file:",
    )
    present = [token for token in forbidden if token in text]
    if missing or present:
        raise AuditError(
            f"compose isolation contract failed; missing={missing} forbidden={present}"
        )


def _validate_compose_render(
    runner: Runner, manifest: dict[str, Any], credentials: dict[str, str]
) -> dict[str, Any]:
    env = _sanitized_environment(manifest, credentials)
    result = runner.run(
        [*_compose_args(manifest), "config", "--format", "json"],
        env=env,
    )
    try:
        config = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AuditError("docker compose did not return JSON configuration") from exc
    services = config.get("services") or {}
    if set(services) != {"db", "registry-export"}:
        raise AuditError(f"unexpected registry audit services: {sorted(services)}")
    for service_name, service in services.items():
        if service.get("ports"):
            raise AuditError(f"{service_name} publishes host ports")
        if service.get("network_mode") == "host":
            raise AuditError(f"{service_name} uses host network")
        volumes = service.get("volumes") or []
        if any("docker.sock" in json.dumps(item) for item in volumes):
            raise AuditError(f"{service_name} mounts Docker socket")
    networks = config.get("networks") or {}
    if len(networks) != 1:
        raise AuditError("registry audit must use exactly one network")
    network = next(iter(networks.values()))
    if network.get("internal") is not True:
        raise AuditError("registry audit network is not internal")
    return config


def _validate_image_volume_coverage(
    runner: Runner,
    manifest: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, str]]:
    service_images = {
        "db": manifest["images"]["postgres"],
        "registry-export": manifest["images"]["odoo"],
    }
    expected_names = set(manifest["resources"]["volumes"])
    configured_volumes = config.get("volumes") or {}
    allowed_sources = set()
    coverage = []
    for volume_key, volume in configured_volumes.items():
        name = str(volume.get("name") or "")
        labels = {
            str(key): str(value)
            for key, value in (volume.get("labels") or {}).items()
        }
        if name not in expected_names:
            raise AuditError(f"unmanifested named volume in compose: {name}")
        if any(labels.get(key) != value for key, value in manifest["labels"].items()):
            raise AuditError(f"named volume lacks audit labels: {name}")
        allowed_sources.update({str(volume_key), name})
    for service_name, image in service_images.items():
        result = runner.run(
            [
                _docker_binary(),
                "image",
                "inspect",
                "--format",
                "{{json .Config.Volumes}}",
                image,
            ]
        )
        try:
            declared = set((json.loads(result.stdout.strip() or "{}") or {}).keys())
        except json.JSONDecodeError as exc:
            raise AuditError(f"invalid image volume metadata: {image}") from exc
        mounts = (config.get("services") or {}).get(service_name, {}).get(
            "volumes", []
        )
        by_target = {
            str(mount.get("target") or ""): mount
            for mount in mounts
            if isinstance(mount, dict)
        }
        missing = sorted(declared - set(by_target))
        if missing:
            raise AuditError(
                f"{service_name} image volumes lack explicit mounts: {missing}"
            )
        for target in declared:
            mount = by_target[target]
            if mount.get("type") not in {"volume", "tmpfs"}:
                raise AuditError(
                    f"{service_name} image volume has unsafe override: {target}"
                )
            if mount.get("type") == "volume":
                source = str(mount.get("source") or "")
                if not source or source not in allowed_sources:
                    raise AuditError(
                        f"{service_name} image volume is anonymous or "
                        f"unmanifested: {target}: source={source!r}"
                    )
            coverage.append(
                {
                    "service": service_name,
                    "image": image,
                    "path": target,
                    "override_type": str(mount.get("type")),
                    "source": str(mount.get("source") or ""),
                }
            )
    return sorted(
        coverage,
        key=lambda row: (row["service"], row["path"]),
    )


def validate(
    runner: Runner, run_id: str | None = None
) -> tuple[dict[str, Any], dict[str, str]]:
    resolved = _validate_run_id(run_id) if run_id else _new_run_id()
    paths = _paths(resolved)
    if paths["output"].exists():
        manifest, credentials = _load(resolved)
    else:
        manifest, credentials = _prepare(resolved)
    _validate_compose_static(_compose_file())
    for image in manifest["images"].values():
        runner.run([_docker_binary(), "image", "inspect", image])
    _assert_resources_absent(runner, manifest)
    config = _validate_compose_render(runner, manifest, credentials)
    manifest["image_volume_paths"] = _validate_image_volume_coverage(
        runner,
        manifest,
        config,
    )
    manifest["lifecycle"]["validated"] = True
    _atomic_json(paths["manifest"], manifest)
    print(f"AUDIT_RUN_ID={resolved}")
    print(f"COMPOSE_PROJECT_NAME={manifest['compose_project_name']}")
    print(f"EPHEMERAL_DATABASE_NAME={manifest['database_name']}")
    print(f"OUTPUT_DIRECTORY={manifest['output_directory']}")
    return manifest, credentials


def _validate_export(
    path: Path,
    manifest: dict[str, Any],
    forbidden_values: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = _read_json(path)
    missing = sorted(REQUIRED_EXPORT_KEYS - set(payload))
    extra_secret_keys = []
    secret_pattern = re.compile(
        r"(password|passwd|secret|token|cookie|database_url|connection_string)",
        re.IGNORECASE,
    )

    def walk(value: Any, path_parts: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if secret_pattern.search(str(key)):
                    extra_secret_keys.append(".".join((*path_parts, str(key))))
                walk(item, (*path_parts, str(key)))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                walk(item, (*path_parts, str(index)))

    walk(payload)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if missing:
        raise AuditError(f"registry export is missing keys: {missing}")
    if extra_secret_keys:
        raise AuditError(
            f"registry export contains secret-shaped keys: {extra_secret_keys}"
        )
    if any(value and value in serialized for value in forbidden_values):
        raise AuditError("registry export contains an ephemeral credential value")
    if re.search(r"<[^>]+ object at 0x[0-9a-fA-F]+>", serialized):
        raise AuditError("registry export contains an unstable object repr")
    metadata = payload.get("run_metadata") or {}
    for key, expected in {
        "run_id": manifest["run_id"],
        "git_head": manifest["git_head"],
        "git_tree": manifest["git_tree"],
        "database_role": manifest["database_role"],
    }.items():
        if metadata.get(key) != expected:
            raise AuditError(f"registry export metadata mismatch: {key}")
    generic = payload.get("generic_api_policies")
    if not isinstance(generic, dict) or generic.get("schema_version") != 2:
        raise AuditError("generic API policy metadata schema_version must be 2")
    records = generic.get("policy_records")
    if not isinstance(records, list) or not records:
        raise AuditError("generic API policy metadata must include policy records")
    registry_keys = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise AuditError(f"generic API policy record {index} is not a mapping")
        missing_policy_keys = sorted(REQUIRED_GENERIC_POLICY_KEYS - set(record))
        if missing_policy_keys:
            raise AuditError(
                f"generic API policy record {index} missing keys: "
                f"{missing_policy_keys}"
            )
        registry_keys.append(str(record.get("registry_key") or ""))
    if len(registry_keys) != len(set(registry_keys)):
        raise AuditError("generic API policy registry keys are not unique")
    project_models = {
        str(model or "") for model in (payload.get("project_models") or [])
    }
    decision_models = {
        str(row.get("model") or "")
        for row in (generic.get("project_model_decisions") or [])
        if isinstance(row, dict)
    }
    if project_models != decision_models:
        raise AuditError(
            "generic API project model decisions do not match project models"
        )
    project_fields = {
        (
            str(row.get("model") or ""),
            str(row.get("field") or ""),
        )
        for row in (payload.get("project_field_definitions") or [])
        if isinstance(row, dict)
    }
    decision_fields = {
        (
            str(row.get("model") or ""),
            str(row.get("field") or ""),
        )
        for row in (generic.get("project_field_decisions") or [])
        if isinstance(row, dict)
    }
    if project_fields != decision_fields:
        raise AuditError(
            "generic API project field decisions do not match project fields"
        )
    for marker in (
        "business_handlers_executed",
        "business_model_methods_executed",
        "policy_predicates_executed",
        "business_data_read",
    ):
        if generic.get(marker) is not False:
            raise AuditError(f"generic API audit safety marker must be false: {marker}")
    routes = payload.get("route_policies")
    if not isinstance(routes, dict) or routes.get("schema_version") != 4:
        raise AuditError("route policy metadata schema_version must be 4")
    route_records = routes.get("records")
    if not isinstance(route_records, list):
        raise AuditError("route policy metadata records must be a list")
    route_ids = []
    for index, record in enumerate(route_records):
        if not isinstance(record, dict):
            raise AuditError(f"route policy record {index} is not a mapping")
        missing_route_keys = sorted(REQUIRED_ROUTE_POLICY_KEYS - set(record))
        if missing_route_keys:
            raise AuditError(
                f"route policy record {index} missing keys: {missing_route_keys}"
            )
        route_ids.append(str(record.get("route_policy_id") or ""))
        if record.get("route_surface") not in ROUTE_SURFACES:
            raise AuditError(
                f"route policy record {index} has invalid route surface"
            )
        if record.get("executed_during_audit") is not False:
            raise AuditError(
                f"route policy record {index} execution marker must be false"
            )
    if len(route_ids) != len(set(route_ids)):
        raise AuditError("route policy IDs are not unique")
    framework_rules = routes.get("framework_rules")
    if not isinstance(framework_rules, list):
        raise AuditError("framework route rules must be a list")
    routing_map_ids = set()
    for index, rule in enumerate(framework_rules):
        if not isinstance(rule, dict):
            raise AuditError(f"framework route rule {index} is not a mapping")
        missing_rule_keys = sorted(REQUIRED_FRAMEWORK_RULE_KEYS - set(rule))
        if missing_rule_keys:
            raise AuditError(
                f"framework route rule {index} missing keys: {missing_rule_keys}"
            )
        if rule.get("route_surface") not in ROUTE_SURFACES:
            raise AuditError(
                f"framework route rule {index} has invalid route surface"
            )
        routing_map_ids.add(str(rule.get("routing_map_id") or ""))
        if (
            rule.get("endpoint_executed") is not False
            or rule.get("matcher_executed") is not False
        ):
            raise AuditError(
                f"framework route rule {index} safety markers must be false"
            )
    if len(routing_map_ids) != 1 or "" in routing_map_ids:
        raise AuditError("framework rules do not identify one final routing map")
    conflict_ids = []
    for index, conflict in enumerate(routes.get("collisions") or []):
        if not isinstance(conflict, dict):
            raise AuditError(f"route conflict {index} is not a mapping")
        missing_conflict_keys = sorted(
            REQUIRED_ROUTE_CONFLICT_KEYS - set(conflict)
        )
        if missing_conflict_keys:
            raise AuditError(
                f"route conflict {index} missing keys: {missing_conflict_keys}"
            )
        conflict_ids.append(str(conflict.get("route_conflict_id") or ""))
        if not set(conflict.get("route_surfaces") or []) <= ROUTE_SURFACES:
            raise AuditError(
                f"route conflict {index} has invalid route surfaces"
            )
        status = conflict.get("enumeration_status")
        if status not in {"FALSE_CONFLICT", "RESOLVED", "UNRESOLVED_DYNAMIC"}:
            raise AuditError(f"route conflict {index} has invalid status: {status}")
        classification = conflict.get("conflict_classification")
        if classification not in {
            "FALSE_CONFLICT",
            "TRUE_RUNTIME_CONFLICT",
            "UNRESOLVED_OVERLAP",
        }:
            raise AuditError(
                f"route conflict {index} has invalid classification: {classification}"
            )
        if classification == "FALSE_CONFLICT":
            if not conflict.get("false_conflict_reason"):
                raise AuditError(
                    f"route conflict {index} false positive lacks reason"
                )
            if conflict.get("winner_analysis_permitted") is not False:
                raise AuditError(
                    f"route conflict {index} false positive permits winner analysis"
                )
            if conflict.get("replaced_implementations"):
                raise AuditError(
                    f"route conflict {index} false positive calculated replacements"
                )
        elif classification == "TRUE_RUNTIME_CONFLICT":
            if conflict.get("winner_analysis_permitted") is not True:
                raise AuditError(
                    f"route conflict {index} true conflict blocks winner analysis"
                )
            if status == "RESOLVED":
                if (
                    conflict.get("winner_analysis_status")
                    != "RESOLVED_NONINVASIVE"
                    or not conflict.get("effective_endpoint")
                    or not conflict.get("effective_implementation")
                    or not conflict.get("winner_decision_rule")
                    or not conflict.get("winner_evidence")
                    or conflict.get("unresolved_reason")
                ):
                    raise AuditError(
                        f"route conflict {index} has incomplete winner proof"
                    )
            elif not conflict.get("unresolved_reason"):
                raise AuditError(
                    f"route conflict {index} true conflict lacks winner boundary"
                )
            elif (
                conflict.get("effective_endpoint")
                or conflict.get("effective_implementation")
                or conflict.get("winner_decision_rule")
                or conflict.get("winner_evidence")
                or conflict.get("replaced_implementations")
            ):
                raise AuditError(
                    f"route conflict {index} unresolved winner has result fields"
                )
        elif not conflict.get("overlap_unresolved_inputs"):
            raise AuditError(
                f"route conflict {index} unresolved overlap lacks exact inputs"
            )
        if classification != "TRUE_RUNTIME_CONFLICT" and (
            conflict.get("effective_endpoint")
            or conflict.get("effective_implementation")
            or conflict.get("winner_decision_rule")
            or conflict.get("winner_evidence")
        ):
            raise AuditError(
                f"route conflict {index} calculated winner before matcher gate"
            )
        if (
            conflict.get("request_match_executed") is not False
            or conflict.get("endpoint_executed") is not False
        ):
            raise AuditError(
                f"route conflict {index} safety markers must be false"
            )
    if len(conflict_ids) != len(set(conflict_ids)):
        raise AuditError("route conflict boundary IDs are not unique")
    matcher_proof = routes.get("matcher_order_proof") or {}
    for marker in (
        "source_executed",
        "matcher_executed",
        "request_match_executed",
    ):
        if marker not in matcher_proof and marker == "request_match_executed":
            continue
        if matcher_proof.get(marker) is not False:
            raise AuditError(f"route matcher proof marker must be false: {marker}")
    for marker in (
        "controller_methods_executed",
        "http_requests_executed",
        "request_match_executed",
        "business_model_methods_executed",
    ):
        if routes.get(marker) is not False:
            raise AuditError(f"route policy audit safety marker must be false: {marker}")
    return payload


def _wait_for_healthy_database(
    runner: Runner,
    container_name: str,
    *,
    attempts: int = 60,
    interval_seconds: float = 1.0,
) -> None:
    for _attempt in range(attempts):
        result = runner.run(
            [
                _docker_binary(),
                "inspect",
                "--format",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}",
                container_name,
            ]
        )
        status = result.stdout.strip()
        if status == "healthy":
            return
        if status in {"unhealthy", "missing"}:
            raise AuditError(
                f"ephemeral database health check failed: {status}"
            )
        time.sleep(interval_seconds)
    raise AuditError("ephemeral database did not become healthy in time")


def _assert_container_mounts_manifested(
    runner: Runner,
    manifest: dict[str, Any],
    container_name: str,
) -> None:
    result = runner.run(
        [
            _docker_binary(),
            "inspect",
            "--format",
            "{{json .Mounts}}",
            container_name,
        ]
    )
    try:
        mounts = json.loads(result.stdout.strip() or "[]")
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid container mount metadata: {container_name}") from exc
    expected_volumes = set(manifest["resources"]["volumes"])
    for mount in mounts:
        if mount.get("Type") != "volume":
            continue
        name = str(mount.get("Name") or "")
        if not name or name not in expected_volumes:
            raise AuditError(
                f"container has unmanifested volume mount: {container_name}: {name}"
            )
        _assert_labels(runner, "volumes", name, manifest["labels"])


def export(runner: Runner, run_id: str) -> dict[str, Any]:
    resolved = _validate_run_id(run_id)
    paths = _paths(resolved)
    manifest, credentials = _load(resolved)
    if manifest["lifecycle"].get("validated") is not True:
        raise AuditError("run must pass validate before export")
    _assert_resources_absent(runner, manifest)
    before = _resource_snapshot(runner)
    _atomic_json(paths["pre_snapshot"], before)
    env = _sanitized_environment(manifest, credentials)
    compose = _compose_args(manifest)
    runner.run([*compose, "up", "-d", "--no-build", "db"], env=env, capture=False)
    _record_created_resources(runner, manifest)
    created_after_database_start = {
        "containers": [manifest["resources"]["containers"][0]],
        "networks": manifest["resources"]["networks"],
        "volumes": [manifest["resources"]["volumes"][0]],
    }
    for kind, names in created_after_database_start.items():
        for name in names:
            _assert_labels(runner, kind, name, manifest["labels"])
    _wait_for_healthy_database(
        runner,
        manifest["resources"]["containers"][0],
    )
    runner.run(
        [
            *compose,
            "create",
            "--no-build",
            "registry-export",
        ],
        env=env,
        capture=False,
    )
    _record_created_resources(runner, manifest)
    for name in manifest["resources"]["containers"]:
        _assert_labels(runner, "containers", name, manifest["labels"])
        _assert_container_mounts_manifested(runner, manifest, name)
    manifest["lifecycle"]["resources_created"] = True
    _atomic_json(paths["manifest"], manifest)
    if os.environ.get("REGISTRY_AUDIT_FAIL_AFTER_CREATE") == "1":
        raise AuditError("forced failure after manifest-tracked container creation")
    runner.run(
        [
            _docker_binary(),
            "start",
            "--attach",
            manifest["resources"]["containers"][1],
        ],
        capture=False,
    )
    exit_code = runner.run(
        [
            _docker_binary(),
            "inspect",
            "--format",
            "{{.State.ExitCode}}",
            manifest["resources"]["containers"][1],
        ]
    ).stdout.strip()
    if exit_code != "0":
        raise AuditError(f"registry exporter exited with code {exit_code}")
    payload = _validate_export(
        paths["export"],
        manifest,
        (credentials["password"],),
    )
    manifest["lifecycle"]["export_created"] = True
    _atomic_json(paths["manifest"], manifest)
    print(f"REGISTRY_EXPORT={paths['export']}")
    return payload


def _remove_resource(
    runner: Runner,
    kind: str,
    name: str,
    expected_labels: dict[str, str],
    expected_id: str,
) -> bool:
    labels = _inspect_labels(runner, kind, name, allow_missing=True)
    if labels is None:
        return False
    actual_id = _inspect_resource_id(runner, kind, name)
    if not expected_id or actual_id != expected_id:
        raise AuditError(
            f"refusing to delete {kind} resource with mismatched id: "
            f"{name}: expected={expected_id!r} actual={actual_id!r}"
        )
    mismatches = {
        key: {"expected": value, "actual": labels.get(key)}
        for key, value in expected_labels.items()
        if labels.get(key) != value
    }
    if mismatches:
        raise AuditError(
            f"refusing to delete foreign {kind} resource {name}: {mismatches}"
        )
    docker = _docker_binary()
    if kind == "containers":
        runner.run([docker, "rm", "-f", name])
    elif kind == "networks":
        runner.run([docker, "network", "rm", name])
    elif kind == "volumes":
        runner.run([docker, "volume", "rm", name])
    return True


def cleanup(runner: Runner, run_id: str) -> dict[str, bool]:
    resolved = _validate_run_id(run_id)
    paths = _paths(resolved)
    manifest = _read_json(paths["manifest"])
    _validate_manifest_identity(manifest, resolved)
    # Recover exact identities for resources created between the predeclared
    # manifest write and a possible interruption.
    _record_created_resources(runner, manifest)
    removed = {"containers": False, "networks": False, "volumes": False}
    for record in reversed(manifest["resource_records"]["containers"]):
        did_remove = _remove_resource(
            runner,
            "containers",
            record["name"],
            manifest["labels"],
            record["id"],
        )
        removed["containers"] |= did_remove
        record["removed"] |= did_remove
        _atomic_json(paths["manifest"], manifest)
    for record in manifest["resource_records"]["networks"]:
        did_remove = _remove_resource(
            runner,
            "networks",
            record["name"],
            manifest["labels"],
            record["id"],
        )
        removed["networks"] |= did_remove
        record["removed"] |= did_remove
        _atomic_json(paths["manifest"], manifest)
    for record in manifest["resource_records"]["volumes"]:
        did_remove = _remove_resource(
            runner,
            "volumes",
            record["name"],
            manifest["labels"],
            record["id"],
        )
        removed["volumes"] |= did_remove
        record["removed"] |= did_remove
        _atomic_json(paths["manifest"], manifest)
    manifest["lifecycle"]["cleanup_complete"] = True
    _atomic_json(paths["manifest"], manifest)
    paths["credentials"].unlink(missing_ok=True)
    print(
        "CLEANUP_REMOVED="
        + json.dumps(removed, sort_keys=True, separators=(",", ":"))
    )
    return removed


def _snapshot_unchanged(
    before: dict[str, Any], after: dict[str, Any], manifest: dict[str, Any]
) -> bool:
    ephemeral = {
        item
        for names in manifest["resources"].values()
        for item in names
    }

    def normalize(snapshot: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
        return {
            kind: sorted(
                (str(row.get("id") or ""), str(row.get("name") or ""))
                for row in rows
                if str(row.get("name") or "") not in ephemeral
            )
            for kind, rows in snapshot.items()
        }

    return normalize(before) == normalize(after)


def audit(runner: Runner, run_id: str | None = None) -> dict[str, Any]:
    manifest: dict[str, Any] | None = None
    credentials: dict[str, str] | None = None
    failure: Exception | None = None
    result: dict[str, Any] = {}
    try:
        manifest, credentials = validate(runner, run_id)
        del credentials
        export_payload = export(runner, manifest["run_id"])
        result["export_top_level_keys"] = sorted(export_payload)
    except Exception as exc:
        failure = exc
    finally:
        if manifest is not None:
            try:
                cleanup(runner, manifest["run_id"])
            except Exception as cleanup_exc:
                if failure is None:
                    failure = cleanup_exc
                else:
                    failure = AuditError(
                        f"{failure}; cleanup also failed: {cleanup_exc}"
                    )
            paths = _paths(manifest["run_id"])
            if paths["pre_snapshot"].exists():
                before = _read_json(paths["pre_snapshot"])
                after = _resource_snapshot(runner)
                _atomic_json(paths["post_snapshot"], after)
                result["preexisting_resources_changed"] = not _snapshot_unchanged(
                    before, after, manifest
                )
            else:
                result["preexisting_resources_changed"] = False
            result.update(
                {
                    "run_id": manifest["run_id"],
                    "compose_project_name": manifest["compose_project_name"],
                    "database_name": manifest["database_name"],
                    "output_directory": manifest["output_directory"],
                    "cleanup_complete": _read_json(paths["manifest"])
                    .get("lifecycle", {})
                    .get("cleanup_complete")
                    is True,
                    "success": failure is None,
                    "failure": str(failure) if failure else "",
                }
            )
            _atomic_json(paths["result"], result)
    if failure is not None:
        raise failure
    print(
        "REGISTRY_AUDIT_RESULT="
        + json.dumps(result, sort_keys=True, separators=(",", ":"))
    )
    return result


class FakeRunner(Runner):
    """Small deterministic runner used by the exact-cleanup self-test."""

    def __init__(self) -> None:
        self.resources: dict[str, dict[str, dict[str, str]]] = {
            "containers": {},
            "networks": {},
            "volumes": {},
        }
        self.removed: list[tuple[str, str]] = []

    def add(self, kind: str, name: str, labels: dict[str, str]) -> None:
        self.resources[kind][name] = dict(labels)


def _self_test_cleanup() -> dict[str, bool]:
    run_id = _new_run_id()
    paths = _paths(run_id)
    paths["output"].mkdir(parents=True, exist_ok=False)
    paths["output"].chmod(0o700)
    manifest = _initial_manifest(run_id)
    _atomic_json(paths["manifest"], manifest)
    foreign = dict(manifest["labels"])
    foreign["com.smartconstruction.audit.run-id"] = _new_run_id()
    mismatch_detected = any(
        foreign.get(key) != value for key, value in manifest["labels"].items()
    )
    if not mismatch_detected:
        raise AuditError("foreign resource label self-test did not detect mismatch")
    invalid_manifest = dict(manifest)
    invalid_manifest["resources"] = dict(manifest["resources"])
    invalid_manifest["resources"]["volumes"] = [f"{run_id}-foreign"]
    manifest_rejected = False
    try:
        _validate_manifest_identity(invalid_manifest, run_id)
    except AuditError:
        manifest_rejected = True
    if not manifest_rejected:
        raise AuditError("manifest scope self-test did not reject foreign resource")
    shutil.rmtree(paths["output"])
    return {
        "foreign_label_rejected": mismatch_detected,
        "foreign_manifest_resource_rejected": manifest_rejected,
    }


def _integration_self_test_cleanup(runner: Runner) -> dict[str, bool]:
    owner_run_id = _new_run_id()
    foreign_run_id = _new_run_id()
    paths = _paths(owner_run_id)
    paths["output"].mkdir(parents=True, exist_ok=False)
    paths["output"].chmod(0o700)
    manifest = _initial_manifest(owner_run_id)
    _write_credentials(
        paths["credentials"],
        _resource_names(owner_run_id)["database_user"],
    )
    _atomic_json(paths["manifest"], manifest)
    docker = _docker_binary()
    labels = manifest["labels"]
    label_args = [
        item
        for key, value in sorted(labels.items())
        for item in ("--label", f"{key}={value}")
    ]
    foreign_refused = False
    first_cleanup = {}
    second_cleanup = {}
    try:
        runner.run(
            [
                docker,
                "network",
                "create",
                "--internal",
                *label_args,
                manifest["resources"]["networks"][0],
            ]
        )
        for volume in manifest["resources"]["volumes"]:
            runner.run([docker, "volume", "create", *label_args, volume])
        _record_created_resources(runner, manifest)
        owner_volume = manifest["resource_records"]["volumes"][0]
        try:
            _remove_resource(
                runner,
                "volumes",
                owner_volume["name"],
                _labels_for(foreign_run_id),
                owner_volume["id"],
            )
        except AuditError:
            foreign_refused = True
        if not foreign_refused:
            raise AuditError("actual foreign-label cleanup test did not refuse")
        # This simulates an audit failure immediately after resource creation.
        first_cleanup = cleanup(runner, owner_run_id)
        second_cleanup = cleanup(runner, owner_run_id)
        for kind, names in manifest["resources"].items():
            for name in names:
                if _inspect_labels(runner, kind, name, allow_missing=True) is not None:
                    raise AuditError(
                        f"self-test left an ephemeral {kind} resource: {name}"
                    )
    finally:
        # A failure before the assertions still receives exact manifest cleanup.
        try:
            cleanup(runner, owner_run_id)
        except AuditError:
            pass
        shutil.rmtree(paths["output"], ignore_errors=True)
    return {
        "actual_foreign_label_rejected": foreign_refused,
        "failure_path_exact_cleanup": (
            first_cleanup.get("containers") is False
            and first_cleanup.get("networks") is True
            and first_cleanup.get("volumes") is True
        ),
        "second_cleanup_noop": not any(second_cleanup.values()),
    }


def self_test(runner: Runner | None = None) -> dict[str, bool]:
    active_runner = runner or Runner()
    result = {
        **_self_test_cleanup(),
        **_integration_self_test_cleanup(active_runner),
    }
    print(
        "REGISTRY_AUDIT_SELF_TEST="
        + json.dumps(result, sort_keys=True, separators=(",", ":"))
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "audit"):
        child = subparsers.add_parser(command)
        child.add_argument("--run-id")
    for command in ("export", "cleanup"):
        child = subparsers.add_parser(command)
        child.add_argument("--run-id", required=True)
    subparsers.add_parser("self-test")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    runner = Runner()
    try:
        if args.command == "validate":
            validate(runner, args.run_id)
        elif args.command == "export":
            export(runner, args.run_id)
        elif args.command == "cleanup":
            cleanup(runner, args.run_id)
        elif args.command == "audit":
            audit(runner, args.run_id)
        elif args.command == "self-test":
            self_test(runner)
        else:  # pragma: no cover
            raise AuditError(f"unsupported command: {args.command}")
    except AuditError as exc:
        print(f"REGISTRY_AUDIT_ERROR={exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
