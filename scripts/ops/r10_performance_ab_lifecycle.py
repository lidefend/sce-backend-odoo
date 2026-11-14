#!/usr/bin/env python3
"""Governed lifecycle for the isolated R10 A/B performance twins."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r10_performance_ab_profile import evaluate_preflight, remote_probe


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config/ops/r10_performance_ab_profile.v1.json"
STACK_TEMPLATE = ROOT / "config/ops/r10_performance_ab_stack.yml"
CONFIRM = "CREATE_R10_ISOLATED_PERFORMANCE_TWINS"
DESTROY_CONFIRM = "DESTROY_R10_ISOLATED_PERFORMANCE_TWINS"
SOURCE_ENV = "/opt/projects/secure/daily-runtime-duties/sc-demo-dev.env"
CURRENT_PRODUCT_ROOT = "/opt/projects/repos/sce-product-odoo"
CURRENT_DIST = f"{CURRENT_PRODUCT_ROOT}/frontend/apps/web/dist-dev"
SAFE_SHA = re.compile(r"^[0-9a-f]{40}$")
SAFE_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class LifecycleError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LifecycleError(f"unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise LifecycleError(f"JSON object required: {path}")
    return payload


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LifecycleError(message)


def _git(*args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise LifecycleError(
            f"git {args[0]} failed: {result.stderr.decode(errors='replace')[:500]}"
        )
    return result.stdout


def _ssh(host: str, script: str, *, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, script],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = (
            result.stderr.decode(errors="replace")
            + "\n"
            + result.stdout.decode(errors="replace")
        ).strip()
        raise LifecycleError(
            f"remote command failed: {detail[-1800:]}"
        )
    return result.stdout


def _run(args: list[str], *, env: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise LifecycleError(
            f"command failed ({' '.join(args[:3])}): "
            f"{result.stderr.decode(errors='replace')[-1000:]}"
        )
    return result.stdout


def _write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha(value: str) -> str:
    sha = str(value or "").strip()
    _require(bool(SAFE_SHA.fullmatch(sha)), "source SHA must be a full commit")
    return _git("rev-parse", f"{sha}^{{tree}}").decode().strip()


def _profile(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    _require(payload.get("status") == "design_only", "profile status changed")
    _require(set((payload.get("arms") or {}).keys()) == {"a", "b"}, "invalid arms")
    return payload


def _remote_snapshot(host: str, snapshot: str) -> dict[str, Any]:
    _require(snapshot.startswith("/data/backups/daily-demo-dev/sc_demo-"), "invalid snapshot")
    _require(
        bool(re.fullmatch(r"/data/backups/daily-demo-dev/sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}", snapshot)),
        "invalid snapshot identity",
    )
    raw = _ssh(host, f"cat {shlex.quote(snapshot + '/manifest.json')}")
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise LifecycleError("snapshot manifest is invalid") from exc
    _require(isinstance(payload, dict), "snapshot manifest must be an object")
    return payload


def _wait_remote_health(host: str, env_file: str, compose_file: str, project: str, service: str) -> str:
    script = f"""
set -eu
set -a
. {shlex.quote(env_file)}
set +a
for _ in $(seq 1 120); do
  state="$(docker inspect -f '{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{else}}}}{{{{.State.Status}}}}{{{{end}}}}' "$(docker compose --project-name {shlex.quote(project)} --env-file {shlex.quote(env_file)} -f {shlex.quote(compose_file)} ps -q {shlex.quote(service)})" 2>/dev/null || true)"
  if test "$state" = healthy -o "$state" = running; then
    printf '%s\\n' "$state"
    exit 0
  fi
  sleep 2
done
docker compose --project-name {shlex.quote(project)} --env-file {shlex.quote(env_file)} -f {shlex.quote(compose_file)} logs --no-color {shlex.quote(service)} >&2 || true
exit 1
"""
    return _ssh(host, script).decode().strip()


def _stage_arm(host: str, arm: dict[str, Any], sha: str) -> dict[str, Any]:
    root = arm["source_root"]
    _require(arm["compose_project"] in root or root.startswith("/opt/projects/perf-r10/"), "invalid source root")
    script = f"""
set -eu
test ! -e {shlex.quote(root)}
install -d -m 0750 {shlex.quote(root)}
install -d -m 0750 {shlex.quote(arm["frontend_dist"])}
install -d -m 0750 {shlex.quote(arm["log_root"])}
install -d -m 0750 {shlex.quote(root + "/artifacts")}
"""
    _ssh(host, script)
    archive = _git("archive", "--format=tar", sha)
    _ssh(host, f"tar -xf - -C {shlex.quote(root)}", input_bytes=archive)
    _ssh(
        host,
        " && ".join(
            [
                f"printf '%s\\n' {shlex.quote(sha)} > {shlex.quote(root + '/SOURCE_SHA')}",
                f"printf '%s\\n' {shlex.quote(_tree_sha(sha))} > {shlex.quote(root + '/SOURCE_TREE')}",
            ]
        ),
    )
    return {"source_root": root, "source_revision": sha, "source_tree": _tree_sha(sha)}


def _build_candidate_bundle(sha: str, evidence_root: Path) -> tuple[Path, str]:
    output = evidence_root / "bundle" / sha
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "make",
            "--no-print-directory",
            "verify.frontend.build",
            "ENV=dev",
            f"ENV_FILE={ROOT / '.env.dev'}",
            f"FRONTEND_DIST_DIR={output}",
            f"SC_SOURCE_REVISION={sha}",
            "SC_DEPLOY_ENV=perf-r10",
        ]
    )
    _run(["bash", "scripts/verify/frontend_build_fingerprint.sh", str(output)])
    marker = output / ".build-sha256"
    _require(marker.is_file(), "candidate bundle identity is missing")
    digest = marker.read_text(encoding="utf-8").strip()
    _require(bool(SAFE_DIGEST.fullmatch(digest)), "candidate bundle identity is invalid")
    return output, digest


def _copy_bundle(host: str, source: Path, target: str, expected: str) -> None:
    archive = _run(["tar", "-C", str(source), "-cf", "-", "."])
    _ssh(host, f"tar -xf - -C {shlex.quote(target)}", input_bytes=archive)
    actual = _ssh(host, f"cat {shlex.quote(target + '/.build-sha256')}").decode().strip()
    _require(actual == expected, "uploaded bundle identity mismatch")


def prepare(
    profile_path: Path,
    *,
    candidate_sha: str,
    snapshot: str,
    evidence: Path,
    a_sha: str,
) -> dict[str, Any]:
    _require(
        os.environ.get("CONFIRM_R10_PERFORMANCE_TWIN_RESOURCES") == CONFIRM,
        f"confirmation {CONFIRM} is required",
    )
    _require(not _git("status", "--porcelain"), "lifecycle preparation requires a clean worktree")
    head = _git("rev-parse", "HEAD").decode().strip()
    _require(head == candidate_sha, "candidate SHA differs from local HEAD")
    _require(bool(SAFE_SHA.fullmatch(a_sha)), "A SHA must be a full commit")
    profile = _profile(profile_path)
    host = profile["source"]["ssh_host"]
    _remote_snapshot(host, snapshot)
    paths = [
        values[key]
        for values in profile["arms"].values()
        for key in ("source_root", "frontend_dist", "log_root")
    ]
    preflight = evaluate_preflight(profile, remote_probe(host, paths))
    _require(preflight["status"] == "PASS", "R10 resource preflight is blocked")

    evidence_root = evidence.parent / f"{candidate_sha}-{snapshot.rsplit('-', 1)[-1]}"
    b_dist, b_bundle = _build_candidate_bundle(candidate_sha, evidence_root)
    staged = {
        "a": _stage_arm(host, profile["arms"]["a"], a_sha),
        "b": _stage_arm(host, profile["arms"]["b"], candidate_sha),
    }
    a_bundle = (
        _ssh(host, f"cat {shlex.quote(CURRENT_DIST + '/.build-sha256')}")
        .decode()
        .strip()
    )
    _require(bool(SAFE_DIGEST.fullmatch(a_bundle)), "A bundle identity is invalid")
    _ssh(
        host,
        f"cp -a {shlex.quote(CURRENT_DIST + '/.')} {shlex.quote(profile['arms']['a']['frontend_dist'] + '/')}",
    )
    _copy_bundle(host, b_dist, profile["arms"]["b"]["frontend_dist"], b_bundle)
    stack_target = "/opt/projects/perf-r10/runtime/stack.yml"
    _ssh(host, f"install -d -m 0750 {shlex.quote(str(Path(stack_target).parent))}")
    _ssh(host, f"cat > {shlex.quote(stack_target)}", input_bytes=STACK_TEMPLATE.read_bytes())
    result = {
        "schema": "r10.performance_ab.prepare.v1",
        "status": "PASS",
        "host": host,
        "snapshot": snapshot,
        "stack": stack_target,
        "arms": {
            "a": {
                **staged["a"],
                "frontend_dist": profile["arms"]["a"]["frontend_dist"],
                "frontend_build_sha256": a_bundle,
            },
            "b": {
                **staged["b"],
                "frontend_dist": profile["arms"]["b"]["frontend_dist"],
                "frontend_build_sha256": b_bundle,
            },
        },
    }
    _write_evidence(evidence, result)
    return result


REMOTE_RENDER_ENV = r'''
import json
import os
from pathlib import Path

source, target = Path(os.environ["SOURCE_ENV"]), Path(os.environ["TARGET_ENV"])
arm = json.loads(os.environ["ARM"])
current = {}
for raw in source.read_text(encoding="utf-8").splitlines():
    if not raw or raw.lstrip().startswith("#") or "=" not in raw:
        continue
    key, value = raw.split("=", 1)
    current[key.strip()] = value
overrides = {
    "COMPOSE_PROJECT_NAME": arm["compose_project"],
    "DB_NAME": arm["database"],
    "ODOO_DBFILTER": arm["database_filter"],
    "DB_DATA": arm["database_volume"],
    "REDIS_DATA": arm["redis_volume"],
    "ODOO_DATA": arm["odoo_volume"],
    "INTERNAL_NETWORK": arm["internal_network"],
    "NGINX_PORT": str(arm["public_port"]),
    "SC_PRODUCT_ROOT": arm["source_root"],
    "DEMO_ADDONS_ROOT": arm["source_root"] + "/demo_addons",
    "FRONTEND_DIST_DIR": arm["frontend_dist"],
    "SC_SOURCE_REVISION": arm["source_revision"],
    "FRONTEND_BUILD_SHA256": arm["frontend_build_sha256"],
    "SC_DEPLOY_ENV": "perf-r10",
    "NGINX_BIND_HOST": "0.0.0.0",
    "SC_PROXY_DEFAULT_UPSTREAM": "odoo:8069",
    "SC_PROXY_PLATFORM_UPSTREAM": "odoo:8069",
}
current.update(overrides)
target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
target.write_text("".join(f"{key}={value}\n" for key, value in sorted(current.items())), encoding="utf-8")
target.chmod(0o600)
'''


def _render_arm_env(host: str, arm: dict[str, Any], stack: str) -> str:
    env_file = f"/opt/projects/secure/r10-performance-ab/{arm['compose_project']}.env"
    values = {
        "SOURCE_ENV": SOURCE_ENV,
        "TARGET_ENV": env_file,
        "ARM": json.dumps(arm, separators=(",", ":")),
    }
    remote = " ".join(
        f"{key}={shlex.quote(value)}" for key, value in values.items()
    ) + f" python3 - <<'PY'\n{REMOTE_RENDER_ENV}\nPY\n"
    _ssh(host, remote)
    return env_file


def _compose(env_file: str, stack: str, project: str, action: str) -> str:
    return (
        "set -eu; set -a; "
        f". {shlex.quote(env_file)}; set +a; "
        f"docker compose --project-name {shlex.quote(project)} "
        f"--env-file {shlex.quote(env_file)} -f {shlex.quote(stack)} {action}"
    )


def restore(
    profile_path: Path,
    *,
    candidate_sha: str,
    snapshot: str,
    evidence: Path,
    a_sha: str,
) -> dict[str, Any]:
    _require(
        os.environ.get("CONFIRM_R10_PERFORMANCE_TWIN_RESOURCES") == CONFIRM,
        f"confirmation {CONFIRM} is required",
    )
    profile = _profile(profile_path)
    host = profile["source"]["ssh_host"]
    stack = "/opt/projects/perf-r10/runtime/stack.yml"
    snapshot_manifest = _remote_snapshot(host, snapshot)
    arm_identity = {
        "a": {"source_revision": a_sha},
        "b": {"source_revision": candidate_sha},
    }
    restore_rows: dict[str, Any] = {}
    for name, arm in profile["arms"].items():
        enriched = {
            **arm,
            **arm_identity[name],
            "frontend_build_sha256": (
                profile["source"]["frontend_build_sha256"]
                if name == "a"
                else _ssh(host, f"cat {shlex.quote(arm['frontend_dist'] + '/.build-sha256')}")
                .decode()
                .strip()
            ),
        }
        env_file = _render_arm_env(host, enriched, stack)
        _ssh(host, _compose(env_file, stack, arm["compose_project"], "up -d db redis"))
        _wait_remote_health(host, env_file, stack, arm["compose_project"], "db")
        restore_cmd = (
            f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
            f"docker compose --project-name {shlex.quote(arm['compose_project'])} "
            f"--env-file {shlex.quote(env_file)} -f {shlex.quote(stack)} "
            'exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" '
            "--clean --if-exists --no-owner --no-privileges"
        )
        dump = _ssh(host, f"cat {shlex.quote(snapshot + '/database.dump')}")
        _ssh(host, restore_cmd, input_bytes=dump)
        filestore_cmd = (
            f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
            f"docker run --rm -i -v \"$ODOO_DATA\":/target alpine:3.20 "
            "sh -c 'mkdir -p /target/filestore && tar -xzf - -C /target/filestore'"
        )
        filestore = _ssh(host, f"cat {shlex.quote(snapshot + '/filestore.tar.gz')}")
        _ssh(host, filestore_cmd, input_bytes=filestore)
        facts = _ssh(
            host,
            f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
            f"docker compose --project-name {shlex.quote(arm['compose_project'])} "
            f"--env-file {shlex.quote(env_file)} -f {shlex.quote(stack)} "
            'exec -T db psql -U "$DB_USER" -d "$DB_NAME" -Atc '
            + shlex.quote(
                "select current_database(), "
                "(select count(*) from project_project), "
                "(select name from project_project where id=2)"
            ),
        ).decode().strip()
        restore_rows[name] = {
            "env_file": env_file,
            "database_fact": facts,
            "snapshot_database_uuid": snapshot_manifest["recovery_expectations"]["database_uuid"],
        }
    result = {
        "schema": "r10.performance_ab.restore.v1",
        "status": "PASS",
        "snapshot": snapshot,
        "arms": restore_rows,
    }
    _write_evidence(evidence, result)
    return result


def deploy(
    profile_path: Path,
    *,
    candidate_sha: str,
    evidence: Path,
    a_sha: str,
) -> dict[str, Any]:
    profile = _profile(profile_path)
    host = profile["source"]["ssh_host"]
    stack = "/opt/projects/perf-r10/runtime/stack.yml"
    result: dict[str, Any] = {
        "schema": "r10.performance_ab.deploy.v1",
        "status": "PASS",
        "arms": {},
    }
    for name, arm in profile["arms"].items():
        env_file = f"/opt/projects/secure/r10-performance-ab/{arm['compose_project']}.env"
        _ssh(
            host,
            f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
            'docker run --rm -v "$ODOO_DATA":/target alpine:3.20 '
            "chown -R 101:101 /target",
        )
        if name == "b":
            upgrade_log = arm["log_root"] + "/b-module-upgrade.log"
            upgrade = (
                f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
                f"log={shlex.quote(upgrade_log)}; "
                f"if ! docker compose --project-name {shlex.quote(arm['compose_project'])} "
                f"--env-file {shlex.quote(env_file)} -f {shlex.quote(stack)} "
                "run --rm --no-deps --entrypoint /bin/sh odoo -ec "
                + shlex.quote(
                    'python3 /usr/local/bin/render_odoo_conf.py '
                    '/etc/odoo/odoo.conf.template /var/lib/odoo/odoo.conf && '
                    'odoo -c /var/lib/odoo/odoo.conf -d "$DB_NAME" '
                    '-u smart_core,smart_construction_core,smart_construction_scene '
                    '--without-demo=all --no-http --workers=0 --max-cron-threads=0 '
                    '--stop-after-init'
                )
                + f" >\"$log\" 2>&1; then tail -n 180 \"$log\" >&2; exit 1; fi"
            )
            _ssh(host, upgrade)
        _ssh(host, _compose(env_file, stack, arm["compose_project"], "up -d odoo nginx"))
        _wait_remote_health(host, env_file, stack, arm["compose_project"], "odoo")
        _wait_remote_health(host, env_file, stack, arm["compose_project"], "nginx")
        _ssh(
            host,
            _compose(env_file, stack, arm["compose_project"], "logs --no-color")
            + f" > {shlex.quote(arm['log_root'] + '/runtime.log')}",
        )
        result["arms"][name] = {
            "compose_project": arm["compose_project"],
            "endpoint": f"http://127.0.0.1:{arm['public_port']}",
            "source_revision": a_sha if name == "a" else candidate_sha,
        }
    _write_evidence(evidence, result)
    return result


def readback(profile_path: Path, *, evidence: Path) -> dict[str, Any]:
    profile = _profile(profile_path)
    host = profile["source"]["ssh_host"]
    stack = "/opt/projects/perf-r10/runtime/stack.yml"
    arms: dict[str, Any] = {}
    for name, arm in profile["arms"].items():
        env_file = f"/opt/projects/secure/r10-performance-ab/{arm['compose_project']}.env"
        script = (
            f"set -eu; set -a; . {shlex.quote(env_file)}; set +a; "
            f"project={shlex.quote(arm['compose_project'])}; "
            f"stack={shlex.quote(stack)}; "
            'printf "CONTAINERS=%s\\n" "$(docker ps --filter label=com.docker.compose.project=$project --format "{{.Names}}" | paste -sd, -)"; '
            'printf "NETWORKS=%s\\n" "$(docker network ls --filter label=com.docker.compose.project=$project --format "{{.Name}}" | paste -sd, -)"; '
            'printf "VOLUMES=%s\\n" "$(docker volume ls --filter label=com.docker.compose.project=$project --format "{{.Name}}" | paste -sd, -)"; '
            'printf "DATABASE=%s\\n" "$(docker compose --project-name "$project" --env-file "$env_file" -f "$stack" exec -T db psql -U "$DB_USER" -d "$DB_NAME" -Atc "select current_database(), (select value from ir_config_parameter where key=\'database.uuid\'), (select name from project_project where id=2)")"; '
            f'printf "HTTP=%s\\n" "$(curl -fsS --max-time 20 http://127.0.0.1:{arm["public_port"]}/web/login >/dev/null && echo PASS || echo FAIL)"'
        )
        lines = _ssh(host, script).decode().splitlines()
        facts = dict(line.split("=", 1) for line in lines if "=" in line)
        _require(
            {"CONTAINERS", "NETWORKS", "VOLUMES", "DATABASE", "HTTP"} <= set(facts),
            f"{name} readback is incomplete",
        )
        arms[name] = {
            "containers": sorted(filter(None, facts["CONTAINERS"].split(","))),
            "networks": sorted(filter(None, facts["NETWORKS"].split(","))),
            "volumes": sorted(filter(None, facts["VOLUMES"].split(","))),
            "database": facts["DATABASE"],
            "http_login": facts["HTTP"],
            "port": arm["public_port"],
        }
    result = {
        "schema": "r10.performance_ab.readback.v1",
        "status": "PASS"
        if all(row["http_login"] == "PASS" for row in arms.values())
        else "FAIL",
        "arms": arms,
    }
    _write_evidence(evidence, result)
    _require(result["status"] == "PASS", "R10 readback failed")
    return result


def destroy(profile_path: Path, *, evidence: Path) -> dict[str, Any]:
    _require(
        os.environ.get("CONFIRM_R10_PERFORMANCE_TWIN_DESTROY") == DESTROY_CONFIRM,
        f"confirmation {DESTROY_CONFIRM} is required",
    )
    profile = _profile(profile_path)
    host = profile["source"]["ssh_host"]
    stack = "/opt/projects/perf-r10/runtime/stack.yml"
    removed = {}
    for name, arm in profile["arms"].items():
        env_file = f"/opt/projects/secure/r10-performance-ab/{arm['compose_project']}.env"
        _ssh(
            host,
            _compose(env_file, stack, arm["compose_project"], "down -v --remove-orphans"),
        )
        remaining = _ssh(
            host,
            f"docker ps -a --filter label=com.docker.compose.project={shlex.quote(arm['compose_project'])} --format '{{{{.Names}}}}'",
        ).decode().split()
        _require(not remaining, f"{name} containers remain")
        removed[name] = {"containers_remaining": 0}
    result = {
        "schema": "r10.performance_ab.destroy.v1",
        "status": "PASS",
        "arms": removed,
        "snapshot_preserved": True,
    }
    _write_evidence(evidence, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "restore", "deploy", "readback", "destroy"))
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--candidate-sha", default="")
    parser.add_argument("--a-sha", default="5d631f6dd304a003f09c72e7de22fde45b8c3dbc")
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action in {"prepare", "restore", "deploy"}:
            _require(bool(SAFE_SHA.fullmatch(args.candidate_sha)), "candidate SHA is required")
        if args.action in {"prepare", "restore"}:
            _require(bool(args.snapshot), "snapshot directory is required")
        if args.action == "prepare":
            result = prepare(
                args.profile,
                candidate_sha=args.candidate_sha,
                snapshot=args.snapshot,
                evidence=args.evidence,
                a_sha=args.a_sha,
            )
        elif args.action == "restore":
            result = restore(
                args.profile,
                candidate_sha=args.candidate_sha,
                snapshot=args.snapshot,
                evidence=args.evidence,
                a_sha=args.a_sha,
            )
        elif args.action == "deploy":
            result = deploy(
                args.profile,
                candidate_sha=args.candidate_sha,
                evidence=args.evidence,
                a_sha=args.a_sha,
            )
        elif args.action == "readback":
            result = readback(args.profile, evidence=args.evidence)
        else:
            result = destroy(args.profile, evidence=args.evidence)
    except (LifecycleError, OSError) as exc:
        print(f"[r10.performance_ab.lifecycle] BLOCKED {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
