#!/usr/bin/env python3
"""Atomic installer for the governed production backup/rehearsal tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PROJECT = "sc_production"
DATABASE = "sc_production"
SSH_TARGET = "sc-prod"
INSTALL_ROOT = Path("/opt/ops")
SYSTEMD_ROOT = Path("/etc/systemd/system")
HISTORY_ROOT = Path("/opt/ops/backup-install-history")
ENVIRONMENT_FILE = Path("/etc/scems/production-backup.env")
RUNTIME_ENVIRONMENT_FILE = Path("/etc/scems/production-backup-runtime.env")
FILES = {
    ROOT / "scripts/release/production_backup_restore.py":
        INSTALL_ROOT / "production_backup_restore.py",
    ROOT / "scripts/ops/production_backup_install.py":
        INSTALL_ROOT / "production_backup_install.py",
    ROOT / "deploy/production-backup/scems-production-backup.service":
        SYSTEMD_ROOT / "scems-production-backup.service",
    ROOT / "deploy/production-backup/scems-production-backup.timer":
        SYSTEMD_ROOT / "scems-production-backup.timer",
}
STALE_TOKENS = ("sc-backend-odoo-prod-db-1", "sc_prod")
IDENTITY_CHARACTER_CLASS = "A-Za-z0-9_"


class InstallError(RuntimeError):
    pass


Runner = Callable[[list[str]], bytes]


def contains_stale_identity(text: str) -> bool:
    return any(
        re.search(
            rf"(?<![{IDENTITY_CHARACTER_CLASS}])"
            rf"{re.escape(token)}"
            rf"(?![{IDENTITY_CHARACTER_CLASS}])",
            text,
        )
        is not None
        for token in STALE_TOKENS
    )


def run(args: list[str]) -> bytes:
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise InstallError(
            f"command failed ({args[0]}): "
            f"{result.stderr.decode(errors='replace').strip()[:500]}"
        )
    return result.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(0o600)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class Identity:
    expected_tool_source_sha: str
    expected_live_main_sha: str
    project: str
    database: str
    db_container: str
    odoo_container: str
    filestore_root: str
    install_root: Path
    backup_root: Path
    encryption_status: str
    retention_days: int

    @classmethod
    def from_env(cls) -> "Identity":
        required = (
            "EXPECTED_BACKUP_TOOL_SOURCE_SHA",
            "EXPECTED_LIVE_MAIN_SHA",
            "PRODUCTION_COMPOSE_PROJECT",
            "BACKUP_TARGET_DB",
            "BACKUP_DB_CONTAINER",
            "BACKUP_ODOO_CONTAINER",
            "BACKUP_FILESTORE_ROOT",
            "BACKUP_INSTALL_ROOT",
            "BACKUP_ROOT",
            "BACKUP_ENCRYPTION_STATUS",
            "BACKUP_RETENTION_DAYS",
        )
        values = {}
        for key in required:
            value = str(os.environ.get(key) or "").strip()
            if not value:
                raise InstallError(f"{key} is required")
            values[key] = value
        try:
            identity = cls(
                expected_tool_source_sha=values["EXPECTED_BACKUP_TOOL_SOURCE_SHA"],
                expected_live_main_sha=values["EXPECTED_LIVE_MAIN_SHA"],
                project=values["PRODUCTION_COMPOSE_PROJECT"],
                database=values["BACKUP_TARGET_DB"],
                db_container=values["BACKUP_DB_CONTAINER"],
                odoo_container=values["BACKUP_ODOO_CONTAINER"],
                filestore_root=values["BACKUP_FILESTORE_ROOT"].rstrip("/"),
                install_root=Path(values["BACKUP_INSTALL_ROOT"]),
                backup_root=Path(values["BACKUP_ROOT"]),
                encryption_status=values["BACKUP_ENCRYPTION_STATUS"],
                retention_days=int(values["BACKUP_RETENTION_DAYS"]),
            )
        except ValueError as exc:
            raise InstallError("backup retention days must be an integer") from exc
        identity.validate()
        return identity

    def validate(self) -> None:
        if not FULL_SHA.fullmatch(self.expected_tool_source_sha):
            raise InstallError("expected tool source SHA must be a full SHA")
        if not FULL_SHA.fullmatch(self.expected_live_main_sha):
            raise InstallError("expected live main SHA must be a full SHA")
        if self.expected_tool_source_sha != self.expected_live_main_sha:
            raise InstallError("tool source and live main must match for installation")
        if (
            self.project != PROJECT
            or self.database != DATABASE
            or self.db_container != "sc_production-db-1"
            or self.odoo_container != "sc_production-odoo-1"
            or self.filestore_root != "/opt/sce-runtime/filestore"
            or self.install_root != INSTALL_ROOT
            or self.backup_root != Path("/data/backups/sc_production")
        ):
            raise InstallError("production backup installation identity mismatch")
        if self.encryption_status not in {
            "encrypted_at_rest",
            "external_encryption_verified",
            "not_encrypted",
        } or not 1 <= self.retention_days <= 3650:
            raise InstallError("backup retention/encryption policy is invalid")
        if any(
            path.is_symlink()
            for path in (self.install_root, self.backup_root)
            if path.exists()
        ):
            raise InstallError("installation paths must not use symlink indirection")


def _git(args: list[str], runner: Runner) -> str:
    return runner(["git", *args]).decode().strip()


def _live_main(remote: str, runner: Runner) -> str:
    lines = _git(["ls-remote", "--heads", remote, "refs/heads/main"], runner).splitlines()
    if len(lines) != 1:
        raise InstallError(f"cannot resolve {remote}/main")
    value = lines[0].split()[0]
    if not FULL_SHA.fullmatch(value):
        raise InstallError(f"{remote}/main returned an invalid SHA")
    return value


def preflight(identity: Identity, runner: Runner = run) -> dict:
    head = _git(["rev-parse", "HEAD"], runner)
    tree = _git(["rev-parse", "HEAD^{tree}"], runner)
    github = _live_main("origin", runner)
    gitee = _live_main("gitee-mirror", runner)
    if (
        head != identity.expected_tool_source_sha
        or github != identity.expected_live_main_sha
        or gitee != identity.expected_live_main_sha
    ):
        raise InstallError("local or dual-remote main identity drift")
    if _git(["status", "--short"], runner):
        raise InstallError("tool source worktree is not clean")
    for source, target in FILES.items():
        if not source.is_file() or source.is_symlink():
            raise InstallError(f"versioned installation source missing: {source}")
        if target.parent not in {INSTALL_ROOT, SYSTEMD_ROOT}:
            raise InstallError("installation target escaped approved roots")
        text = source.read_text(encoding="utf-8")
        if (
            source.suffix in {".service", ".timer"}
            and contains_stale_identity(text)
        ):
            raise InstallError(f"stale production identity in installation source: {source}")
    if not ENVIRONMENT_FILE.is_file() or ENVIRONMENT_FILE.is_symlink():
        raise InstallError("approved backup environment file is unavailable")
    metadata = ENVIRONMENT_FILE.stat()
    if metadata.st_uid != 0 or metadata.st_gid != 0 or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise InstallError("backup environment file must be root-owned 0600")
    return {
        "status": "PASS",
        "tool_source_sha": head,
        "tool_source_tree": tree,
        "github_main_sha": github,
        "gitee_main_sha": gitee,
        "project": identity.project,
        "database": identity.database,
        "files": {
            str(target): {"source": str(source.relative_to(ROOT)), "sha256": sha256(source)}
            for source, target in FILES.items()
        },
        "writes": 0,
    }


def _file_snapshot(path: Path, history: Path) -> dict:
    record = {"path": str(path), "present": path.exists() or path.is_symlink()}
    if not record["present"]:
        return record
    if path.is_symlink() or not path.is_file():
        raise InstallError(f"existing installation target is unsafe: {path}")
    metadata = path.stat()
    destination = history / "previous" / path.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copy2(path, destination)
    record.update(
        {
            "sha256": sha256(path),
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "mode": stat.S_IMODE(metadata.st_mode),
            "backup_path": str(destination),
        }
    )
    return record


def _systemd_state(runner: Runner) -> dict:
    state = {}
    for unit in ("scems-production-backup.service", "scems-production-backup.timer"):
        output = runner(
            [
                "systemctl",
                "show",
                unit,
                "--property=Id,LoadState,ActiveState,UnitFileState,"
                "NextElapseUSecRealtime,LastTriggerUSec",
                "--no-pager",
            ]
        ).decode()
        state[unit] = dict(
            line.split("=", 1) for line in output.splitlines() if "=" in line
        )
    return state


def _assert_no_duplicate_backup_entry(runner: Runner, *, require_governed: bool) -> None:
    output = runner(
        [
            "systemctl",
            "list-unit-files",
            "--type=timer",
            "--state=enabled",
            "--no-legend",
        ]
    ).decode()
    governed = []
    for line in output.splitlines():
        unit = line.split(None, 1)[0] if line.split() else ""
        if unit == "scems-production-backup.timer":
            governed.append(unit)
        elif "scems" in unit and "backup" in unit:
            raise InstallError(f"duplicate production backup timer found: {unit}")
    expected = ["scems-production-backup.timer"] if require_governed else []
    if governed != expected:
        raise InstallError("governed production backup timer is not uniquely enabled")


def _install_one(source: Path, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(temporary)
    try:
        with source.open("rb") as incoming, os.fdopen(descriptor, "wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        os.chown(temp, 0, 0)
        temp.chmod(mode)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _install_bytes(payload: bytes, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as outgoing:
            outgoing.write(payload)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        os.chown(temp, 0, 0)
        temp.chmod(mode)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _validate_environment(identity: Identity) -> None:
    allowed = {
        "BACKUP_TARGET_DB",
        "BACKUP_DB_CONTAINER",
        "BACKUP_ODOO_CONTAINER",
        "BACKUP_DB_USER",
        "BACKUP_FILESTORE_ROOT",
        "BACKUP_ROOT",
    }
    values: dict[str, str] = {}
    for line in ENVIRONMENT_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise InstallError("backup environment format is invalid")
        key, value = line.split("=", 1)
        if key not in allowed or key in values or "\n" in value or "\r" in value:
            raise InstallError("backup environment contains an unapproved key")
        values[key] = value
    expected = {
        "BACKUP_TARGET_DB": identity.database,
        "BACKUP_DB_CONTAINER": identity.db_container,
        "BACKUP_ODOO_CONTAINER": identity.odoo_container,
        "BACKUP_FILESTORE_ROOT": identity.filestore_root,
        "BACKUP_ROOT": str(identity.backup_root),
    }
    if not allowed.issubset(values) or any(values[key] != value for key, value in expected.items()):
        raise InstallError("backup environment identity differs from approved production")
    return None


def _render_runtime_environment(identity: Identity) -> bytes:
    return (
        f"BACKUP_COMPOSE_PROJECT={identity.project}\n"
        f"BACKUP_TOOL_SOURCE_SHA={identity.expected_tool_source_sha}\n"
        f"BACKUP_ENCRYPTION_STATUS={identity.encryption_status}\n"
        f"BACKUP_RETENTION_DAYS={identity.retention_days}\n"
    ).encode()


def _restore(snapshot: list[dict], runner: Runner) -> None:
    for record in reversed(snapshot):
        path = Path(record["path"])
        if record["present"]:
            backup = Path(record["backup_path"])
            _install_one(backup, path, int(record["mode"]))
            os.chown(path, int(record["uid"]), int(record["gid"]))
        elif path.exists():
            path.unlink()
    runner(["systemctl", "daemon-reload"])


def _restore_timer_state(systemd_before: dict, runner: Runner) -> None:
    timer = systemd_before.get("scems-production-backup.timer") or {}
    if timer.get("UnitFileState") == "enabled":
        runner(["systemctl", "enable", "scems-production-backup.timer"])
    if timer.get("ActiveState") == "active":
        runner(["systemctl", "start", "scems-production-backup.timer"])


def install(identity: Identity, runner: Runner = run) -> dict:
    if os.geteuid() != 0:
        raise InstallError("installation must run as root")
    if os.environ.get("CONFIRM_BACKUP_TOOL_INSTALL") != "YES_INSTALL_GOVERNED_BACKUP_TOOL":
        raise InstallError("exact installation acknowledgement is required")
    preflight_result = preflight(identity, runner)
    # Close the preflight-to-write race immediately before the first
    # filesystem or systemd mutation.
    if (
        _git(["rev-parse", "HEAD"], runner) != identity.expected_tool_source_sha
        or _live_main("origin", runner) != identity.expected_live_main_sha
        or _live_main("gitee-mirror", runner) != identity.expected_live_main_sha
    ):
        raise InstallError("live main drifted before installation write")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    history = HISTORY_ROOT / f"{stamp}-{identity.expected_tool_source_sha[:12]}"
    if history.exists() or history.is_symlink():
        raise InstallError("installation history identity already exists")
    history.mkdir(parents=True, mode=0o700)
    before_systemd = _systemd_state(runner)
    snapshots = [
        *[_file_snapshot(target, history) for target in FILES.values()],
        _file_snapshot(RUNTIME_ENVIRONMENT_FILE, history),
    ]
    rollback_manifest = {
        "schema_version": 1,
        "status": "prepared",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool_source_sha": identity.expected_tool_source_sha,
        "files": snapshots,
        "systemd_before": before_systemd,
    }
    atomic_json(history / "rollback-manifest.json", rollback_manifest)
    try:
        if (
            before_systemd["scems-production-backup.timer"].get("UnitFileState")
            == "enabled"
        ):
            runner(["systemctl", "disable", "--now", "scems-production-backup.timer"])
        elif (
            before_systemd["scems-production-backup.timer"].get("ActiveState")
            == "active"
        ):
            runner(["systemctl", "stop", "scems-production-backup.timer"])
        for source, target in FILES.items():
            mode = 0o755 if target.suffix == ".py" else 0o644
            _install_one(source, target, mode)
        _validate_environment(identity)
        _install_bytes(
            _render_runtime_environment(identity),
            RUNTIME_ENVIRONMENT_FILE,
            0o600,
        )
        runner(
            [
                "systemd-analyze",
                "verify",
                str(SYSTEMD_ROOT / "scems-production-backup.service"),
                str(SYSTEMD_ROOT / "scems-production-backup.timer"),
            ]
        )
        for source, target in FILES.items():
            if sha256(source) != sha256(target):
                raise InstallError(f"installed file digest mismatch: {target}")
        runner(["systemctl", "daemon-reload"])
        rollback_manifest["status"] = "installed"
        rollback_manifest["installed_at"] = datetime.now(timezone.utc).isoformat()
        rollback_manifest["installed_hashes"] = {
            str(target): sha256(target) for target in FILES.values()
        }
        atomic_json(history / "rollback-manifest.json", rollback_manifest)
        return {
            **preflight_result,
            "status": "PASS",
            "history": str(history),
            "rollback_manifest": str(history / "rollback-manifest.json"),
            "systemd_daemon_reloaded": True,
            "application_services_restarted": False,
        }
    except Exception:
        _restore(snapshots, runner)
        _restore_timer_state(before_systemd, runner)
        rollback_manifest["status"] = "rolled_back"
        rollback_manifest["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(history / "rollback-manifest.json", rollback_manifest)
        raise


def restore_timer(
    *,
    rollback_manifest: Path,
    backup_dir: Path,
    restore_report: Path,
    runner: Runner = run,
) -> dict:
    if os.geteuid() != 0:
        raise InstallError("timer restoration must run as root")
    if os.environ.get("CONFIRM_BACKUP_TIMER_RESTORE") != "YES_RESTORE_VERIFIED_BACKUP_TIMER":
        raise InstallError("exact timer restoration acknowledgement is required")
    try:
        installation = json.loads(rollback_manifest.read_text())
        backup = json.loads((backup_dir / "manifest.json").read_text())
        rehearsal = json.loads(restore_report.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstallError("timer evidence is missing or invalid") from exc
    if installation.get("status") != "installed":
        raise InstallError("backup installation is not verified")
    previous = (
        installation.get("systemd_before", {})
        .get("scems-production-backup.timer", {})
    )
    if previous.get("UnitFileState") != "enabled":
        raise InstallError("previous timer was not enabled; scheduling decision required")
    if (
        backup.get("status") != "complete"
        or backup.get("backup_pair_verified") is not True
        or rehearsal.get("status") != "PASS"
        or rehearsal.get("external_write_side_effects") != 0
        or rehearsal.get("backup_set_id") != backup.get("backup_set_id")
    ):
        raise InstallError("backup and restore evidence is not complete")
    runner(
        [
            "systemd-analyze",
            "verify",
            str(SYSTEMD_ROOT / "scems-production-backup.service"),
            str(SYSTEMD_ROOT / "scems-production-backup.timer"),
        ]
    )
    _assert_no_duplicate_backup_entry(runner, require_governed=False)
    runner(["systemctl", "enable", "--now", "scems-production-backup.timer"])
    _assert_no_duplicate_backup_entry(runner, require_governed=True)
    state = _systemd_state(runner)
    timer = state["scems-production-backup.timer"]
    if timer.get("UnitFileState") != "enabled" or timer.get("ActiveState") != "active":
        raise InstallError("timer did not return to enabled/active state")
    return {
        "status": "PASS",
        "timer_previous_state": previous,
        "timer_final_state": timer,
        "backup_set_id": backup["backup_set_id"],
        "restore_id": rehearsal["restore_id"],
        "duplicate_backup_entry_absent": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preflight", "install", "timer-restore"))
    parser.add_argument("--rollback-manifest", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--restore-report", type=Path)
    args = parser.parse_args()
    if args.action == "timer-restore":
        if not args.rollback_manifest or not args.backup_dir or not args.restore_report:
            raise InstallError("timer restoration evidence paths are required")
        result = restore_timer(
            rollback_manifest=args.rollback_manifest,
            backup_dir=args.backup_dir,
            restore_report=args.restore_report,
        )
    else:
        identity = Identity.from_env()
        result = preflight(identity) if args.action == "preflight" else install(identity)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
