#!/usr/bin/env python3
"""Governed retirement of the leftover daily development stack (P4).

Owner ruling 2026-10-15 retires the leftover ``sc-backend-odoo-prod`` pair after
a read-only review proved it is a second live writer on data volumes the live
``sc-backend-odoo-dev`` stack is still using:

* ``sc_dev_db_data`` is mounted at ``/var/lib/postgresql/data`` by *both* the dev
  and the prod database container, and the two containers were proven to be two
  separate postmasters on one cluster data directory (same ``pg_control`` inode,
  two distinct ``pg_postmaster_start_time()``, one shared ``postmaster.pid``);
* ``sc_dev_redis_data`` is mounted at ``/data`` by both redis containers, both
  started with ``--appendonly yes``.

The same ruling refuses to treat this as a routine ``docker stop``. That is a
fact about PostgreSQL, not a style preference: a container's ``StopSignal``
decides the shutdown mode. Both database containers declare ``SIGINT``, which
PostgreSQL documents as *Fast Shutdown* -- the server writes a shutdown
checkpoint. That checkpoint would land in the very WAL the surviving live
postmaster is using, which is precisely the cross-instance write this retirement
must remove. ``SIGQUIT`` is documented as *Immediate Shutdown*: the postmaster
exits without taking a checkpoint, so the orphan leaves no checkpoint record and
does not rewrite the shared control file. The redis orphan is stopped with
``SIGKILL`` because a graceful Redis shutdown performs persistence work (RDB
save / AOF flush) inside the shared volume.

This entry is fail-closed and non-destructive: it never removes a container,
a volume, a WAL file, and never runs ``pg_resetwal``. It defaults to a read-only
plan. ``--apply`` requires an exact confirmation token *and* the digest of the
plan that was reviewed, so the low-level commands that execute are exactly the
ones that were reviewed. Evidence (container configuration, logs, volume and
data-directory identity, cluster facts) is frozen on the host before the first
state change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOTE_TMP = "/tmp/sc-daily-legacy-stack-retire.py"
MARKER = "DAILY_LEGACY_RETIRE="
DEFAULT_DECLARATION = "config/ops/daily_runtime_retired_stacks.v1.json"
DEFAULT_EVIDENCE_ROOT = "/opt/projects/backups/daily-runtime-legacy-retire"
CONFIRM_ENV = "SC_CONFIRM_DAILY_RUNTIME_LEGACY_STACK_RETIRE"
CONFIRM_VALUE = "RETIRE_DAILY_RUNTIME_LEGACY_STACK"
STAMP_PLACEHOLDER = "{stamp}"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
CONTAINER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
POSTGRES_DATA_DESTINATION = "/var/lib/postgresql/data"
REMOTE_PRODUCT_REPO = "/opt/projects/repos/sce-product-odoo"

#: A leftover stack is not one shape, so the declaration has to say which one it
#: is and the plan has to prove the matching fact. A ``shared_writer`` writes
#: into a data directory a survivor is also writing: it is stopped *without* a
#: shutdown handler, and the plan must prove the sharing. A
#: ``serving_publisher`` owns no cluster data directory and only holds a
#: published port: it is stopped *with* the signal its own image declares, and
#: the plan must prove the opposite fact -- that it shares no writable volume
#: with anything still running.
SHARED_WRITER_INTENT = "shared_writer"
SERVING_PUBLISHER_INTENT = "serving_publisher"
STACK_INTENTS = (SHARED_WRITER_INTENT, SERVING_PUBLISHER_INTENT)

#: Docker's documented default for a container that declares no stop signal. The
#: plan resolves an empty ``Config.StopSignal`` to this instead of reading it as
#: "no signal", so a declaration may name the signal ``docker stop`` will really
#: send -- and a container whose image later changes it stops matching.
DEFAULT_STOP_SIGNAL = "SIGTERM"
SIGNAL_NAME = re.compile(r"^SIG[A-Z0-9]+$")
#: ``REVIEWED_STOP_METHOD[...]["signal"]`` for a method whose signal is read back
#: from the container instead of being fixed by the reviewed table.
VERIFIED_STOP_SIGNAL = "verified"

#: The reviewed stop method per container kind. ``refused`` records the command
#: that looks natural and is *not* used, with the reason, so a later reader does
#: not "simplify" this entry back into an unsafe stop.
REVIEWED_STOP_METHOD = {
    "postgres": {
        "mode": "immediate_shutdown",
        "signal": "SIGQUIT",
        "argv": ["docker", "kill", "--signal=SIGQUIT", "{container}"],
        "authority": (
            "PostgreSQL documentation, 18.5 'Shutting Down the Server': SIGQUIT is "
            "Immediate Shutdown (the postmaster exits without a checkpoint, so the next "
            "start performs crash recovery); SIGINT is Fast Shutdown and writes a "
            "shutdown checkpoint."
        ),
        "refused": {
            "docker stop (container StopSignal=SIGINT)": (
                "SIGINT is Fast Shutdown: the orphan would write a shutdown checkpoint into "
                "the cluster WAL shared with the surviving live postmaster."
            ),
            "SIGTERM": (
                "Smart Shutdown waits for clients and is not a bounded stop for an orphan "
                "that has no consumer."
            ),
        },
    },
    "redis": {
        "mode": "sigkill_no_persistence_write",
        "signal": "SIGKILL",
        "argv": ["docker", "kill", "{container}"],
        "authority": (
            "Redis performs persistence work on SIGTERM (RDB save and AOF flush) inside its "
            "data directory, which is the volume the surviving instance uses, so the orphan "
            "is stopped without running a shutdown handler."
        ),
        "refused": {
            "docker stop (SIGTERM)": (
                "the orphan would write RDB/AOF state into the volume the surviving instance "
                "is using."
            ),
        },
    },
    "idle": {
        "mode": "no_stop_required",
        "signal": None,
        "argv": None,
        "authority": (
            "the container was never started (state=created) and owns no cluster writer, so it "
            "only needs its automatic restart path removed."
        ),
        "refused": {},
    },
    "serving": {
        "mode": "graceful_stop_with_the_containers_verified_signal",
        "signal": VERIFIED_STOP_SIGNAL,
        "argv": ["docker", "stop", "--timeout", "120", "{container}"],
        "authority": (
            "this container owns no cluster data directory -- it is an application or a proxy "
            "whose own image declares the signal for its clean shutdown (the official nginx "
            "image declares SIGQUIT, fast shutdown; Odoo's image declares none, so docker's "
            "documented default SIGTERM applies). ``docker stop`` sends exactly that signal. "
            "The plan reads the signal back from the container and compares it with the "
            "declaration, so an image that changes it refuses instead of being stopped with a "
            "signal nobody reviewed."
        ),
        "refused": {
            "docker kill (SIGKILL)": (
                "no shared writer is being stopped here, so SIGKILL would skip the image's own "
                "shutdown path for no gain: nothing about this container is shared with a "
                "survivor."
            ),
            "docker kill --signal=SIGQUIT": (
                "carries the postgres Immediate Shutdown rationale onto a container that owns "
                "no cluster data directory, throwing away the image's own shutdown handler."
            ),
        },
    },
}

RESTART_ACTION = ["docker", "update", "--restart=no", "{container}"]


class RetireError(RuntimeError):
    """Any fail-closed refusal of this entry."""


PROGRAM_TEMPLATE = '''
import hashlib
import json
import os
import shlex
import subprocess
import time

MARKER = "DAILY_LEGACY_RETIRE="
PAYLOAD = __PAYLOAD__
TARGETS = PAYLOAD["targets"]
MODE = PAYLOAD["mode"]
EVIDENCE_ROOT = PAYLOAD["evidence_root"]
POSTGRES_DATA_DESTINATION = __POSTGRES_DATA_DESTINATION__
STAMP_PLACEHOLDER = __STAMP_PLACEHOLDER__
DEFAULT_STOP_SIGNAL = __DEFAULT_STOP_SIGNAL__


def run(command, cwd=None):
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)


def sh(script):
    return run(["sh", "-c", script])


def collect():
    running = [row for row in run(["docker", "ps", "--format", "{{.Names}}"]).stdout.split() if row]
    everything = [row for row in run(["docker", "ps", "-a", "--format", "{{.Names}}"]).stdout.split() if row]
    declared = {target["container"]: target for target in TARGETS}
    entries = json.loads(run(["docker", "inspect", *everything]).stdout or "[]") if everything else []
    rows = {}
    volume_owners = {}
    running_volume_owners = {}
    postgres_volume_owners = {}
    for entry in entries:
        name = (entry.get("Name") or "").lstrip("/")
        cfg = entry.get("Config") or {}
        hc = entry.get("HostConfig") or {}
        state = entry.get("State") or {}
        mounts = [
            {"type": m.get("Type"), "name": m.get("Name"), "source": m.get("Source"),
             "destination": m.get("Destination"), "rw": m.get("RW")}
            for m in (entry.get("Mounts") or [])
        ]
        for mount in mounts:
            if not mount["name"]:
                continue
            volume_owners.setdefault(mount["name"], []).append(name)
            if state.get("Running"):
                # Only a *live* co-mount is a second writer. A stopped or merely
                # created container holding the same volume name is not writing
                # into it, and reading it as one would refuse a publisher that
                # shares nothing with anything running.
                running_volume_owners.setdefault(mount["name"], []).append(name)
            if mount["destination"] == POSTGRES_DATA_DESTINATION:
                postgres_volume_owners.setdefault(mount["name"], []).append(name)
        target = declared.get(name) or {}
        row = {
            "container": name,
            "present": True,
            "declared": bool(target),
            "kind": target.get("kind") or "",
            "container_id": (entry.get("Id") or "")[:12],
            "compose_project": (cfg.get("Labels") or {}).get("com.docker.compose.project") or "",
            "config_files": (cfg.get("Labels") or {}).get("com.docker.compose.project.config_files") or "",
            "image": cfg.get("Image") or "",
            "image_id": (entry.get("Image") or "")[:19],
            "state": state.get("Status") or "",
            "running": bool(state.get("Running")),
            "started_at": state.get("StartedAt") or "",
            "restart_policy": (hc.get("RestartPolicy") or {}).get("Name") or "",
            "stop_signal": cfg.get("StopSignal") or hc.get("StopSignal") or "",
            "resolved_stop_signal": (cfg.get("StopSignal") or hc.get("StopSignal")
                                     or DEFAULT_STOP_SIGNAL),
            "mounts": mounts,
            "host_pid": state.get("Pid") or 0,
        }
        if target:
            row["shared_volume"] = target.get("shared_volume") or ""
            row["shared_mount_destination"] = target.get("mount_destination") or ""
        rows[name] = row
    for name, target in declared.items():
        if name not in rows:
            rows[name] = {"container": name, "present": False, "declared": True,
                          "kind": target["kind"], "running": False}

    cluster_writers = sorted({n for owners in postgres_volume_owners.values() for n in owners})
    for name in sorted(set(list(declared) + cluster_writers)):
        row = rows.get(name)
        if not row or not row.get("present"):
            continue
        if row.get("running"):
            pid1 = run(["docker", "exec", name, "sh", "-c",
                        "cat /proc/1/comm 2>/dev/null; ps -o args= -p 1 2>/dev/null || true"])
            if not pid1.returncode:
                row["pid1_command"] = pid1.stdout.strip()
        if row.get("running") and name in cluster_writers:
            row.setdefault("kind", "postgres")
            row["postgres_version"] = run(["docker", "exec", name, "postgres", "--version"]).stdout.strip()
            row["data_stat"] = run(["docker", "exec", name, "sh", "-c",
                "stat -c '%d %i %n' /var/lib/postgresql/data "
                "/var/lib/postgresql/data/global/pg_control "
                "/var/lib/postgresql/data/postmaster.pid 2>&1"]).stdout.strip().splitlines()
            row["postmaster_pid_file"] = run(["docker", "exec", name, "sh", "-c",
                "cat /var/lib/postgresql/data/postmaster.pid 2>&1"]).stdout.strip()
            row["cluster_facts"] = run(["docker", "exec", name, "psql", "-U", "odoo", "-d", "postgres",
                "-Atc", "SELECT pg_postmaster_start_time(), pg_is_in_recovery(), pg_current_wal_lsn(), "
                "system_identifier FROM pg_control_system()"]).stdout.strip()
        if not row.get("declared"):
            continue
        if row["kind"] == "postgres" and row.get("running"):
            clients = run(["docker", "exec", name, "psql", "-U", "odoo", "-d", "postgres", "-Atc",
                "SELECT coalesce(datname,''), coalesce(usename,''), coalesce(host(client_addr),''), "
                "coalesce(state,'') FROM pg_stat_activity WHERE pid <> pg_backend_pid()"]).stdout.strip()
            row["client_backends"] = [line.split("|") for line in clients.splitlines() if line.strip()]
            row["application_clients"] = [c for c in row["client_backends"] if c[2]]
        if row["kind"] == "redis" and row.get("running"):
            row["redis_clients"] = [line for line in
                run(["docker", "exec", name, "redis-cli", "client", "list"]).stdout.splitlines() if line.strip()]
            row["redis_consumers"] = [
                line for line in row["redis_clients"]
                if "addr=127.0.0.1:" not in line and "cmd=client|list" not in line
            ]
            row["redis_aof"] = [line for line in
                run(["docker", "exec", name, "redis-cli", "info", "persistence"]).stdout.splitlines()
                if line.startswith(("aof_enabled", "aof_current_size", "aof_last_write_status",
                                    "rdb_last_bgsave_status"))]

    volume_names = sorted({t["shared_volume"] for t in TARGETS if t.get("shared_volume")})
    volumes = json.loads(run(["docker", "volume", "inspect", *volume_names]).stdout or "[]") if volume_names else []

    compose = []
    for path in PAYLOAD["compose_files"]:
        exists = os.path.exists(path)
        compose.append({
            "path": path,
            "exists": exists,
            "sha256": (hashlib.sha256(open(path, "rb").read()).hexdigest() if exists else ""),
        })

    data_directories = []
    for volume in volumes:
        mountpoint = volume.get("Mountpoint") or ""
        if not mountpoint:
            continue
        for suffix in ("", "/global/pg_control", "/postmaster.pid", "/appendonlydir"):
            line = sh("stat -c '%d %i %n' " + shlex.quote(mountpoint + suffix) + " 2>/dev/null").stdout.strip()
            if line:
                data_directories.append(line)

    # Every declared checkout is reported, not just the first one: a declaration
    # may carry a shared-writer leftover and a serving publisher at the same
    # time, and "no systemd unit revives this path" has to be answered for each.
    checkouts = []
    systemd_units = []
    for path in PAYLOAD["legacy_checkouts"]:
        checkouts.append({
            "path": path,
            "head": sh("git -C " + shlex.quote(path) + " rev-parse HEAD").stdout.strip(),
            "status": sh("git -C " + shlex.quote(path) + " status --short").stdout.strip().splitlines(),
            "compose_diff": sh("git -C " + shlex.quote(path)
                               + " diff -- docker-compose.yml").stdout.strip()[:4000],
        })
        systemd_units.extend(
            sh("grep -rl " + shlex.quote(path)
               + " /etc/systemd/system /lib/systemd/system 2>/dev/null").stdout.strip().splitlines()
        )
    return {
        "containers": [rows[name] for name in sorted(rows)],
        "running_containers": sorted(running),
        "all_containers": sorted(everything),
        "postgres_data_volume_owners": postgres_volume_owners,
        "volume_owners": volume_owners,
        "running_volume_owners": running_volume_owners,
        "volumes": volumes,
        "data_directories": data_directories,
        "compose_files": compose,
        "legacy_checkouts": checkouts,
        "startup_sources": {
            "systemd_units": sorted(set(systemd_units)),
            "cron": [line for line in sh("crontab -l 2>/dev/null; ls /etc/cron.d 2>/dev/null")
                     .stdout.strip().splitlines() if line.strip()],
        },
        "docker_version": run(["docker", "version", "--format", "{{.Server.Version}}"]).stdout.strip(),
    }


def capture(evidence_dir, name, command, cwd=None):
    result = run(command, cwd=cwd)
    body = (result.stdout or "") + (result.stderr or "")
    with open(os.path.join(evidence_dir, name), "w", encoding="utf-8") as handle:
        handle.write(body)
    return {"file": name, "exit_code": result.returncode, "bytes": len(body.encode("utf-8"))}


def freeze_evidence(evidence_dir, before):
    evidence = [
        capture(evidence_dir, "docker.ps.all.txt",
                ["docker", "ps", "-a", "--format", "{{.Names}}\\t{{.Status}}\\t{{.Image}}"]),
    ]
    for target in TARGETS:
        name = target["container"]
        evidence.append(capture(evidence_dir, "docker.inspect.%s.json" % (name,), ["docker", "inspect", name]))
        evidence.append(capture(evidence_dir, "docker.logs.%s.txt" % (name,), ["docker", "logs", "--tail", "200", name]))
    if before["volumes"]:
        evidence.append(capture(evidence_dir, "docker.volume.inspect.json",
                                ["docker", "volume", "inspect"] + [v["Name"] for v in before["volumes"]]))
    for row in before["volumes"]:
        mountpoint = row.get("Mountpoint") or ""
        if not mountpoint:
            continue
        name = row.get("Name")
        evidence.append(capture(evidence_dir, "stat.%s.txt" % (name,),
                                ["stat", "-c", "%d %i %s %n", mountpoint]))
        evidence.append(capture(evidence_dir, "find.%s.txt" % (name,),
                                ["find", mountpoint, "-maxdepth", "2", "-printf", "%y %i %s %p\\n"]))
    for path in [row["path"] for row in before["compose_files"]]:
        if os.path.exists(path):
            evidence.append(capture(evidence_dir, "compose.content.%s.txt" % (os.path.basename(path),),
                                    ["cat", path]))
    for row in before["containers"]:
        if not row.get("running"):
            continue
        if row.get("kind") == "postgres":
            evidence.append(capture(evidence_dir, "pg.facts.%s.txt" % (row["container"],),
                                    ["docker", "exec", row["container"], "psql", "-U", "odoo", "-d", "postgres",
                                     "-Atc", "SELECT now(), pg_postmaster_start_time(), pg_current_wal_lsn(), "
                                     "pg_control_checkpoint()::text FROM pg_control_checkpoint()"]))
        if row.get("kind") == "redis":
            evidence.append(capture(evidence_dir, "redis.info.%s.txt" % (row["container"],),
                                    ["docker", "exec", row["container"], "redis-cli", "info"]))
    for probe in PAYLOAD["survivor_probes"]:
        evidence.append(capture(evidence_dir, "survivor.before.%s.txt" % (probe["name"],), probe["argv"]))
    with open(os.path.join(evidence_dir, "plan.json"), "w", encoding="utf-8") as handle:
        json.dump(PAYLOAD, handle, ensure_ascii=False, indent=2, sort_keys=True)
    digests = {}
    for entry in sorted(os.listdir(evidence_dir)):
        with open(os.path.join(evidence_dir, entry), "rb") as handle:
            digests[entry] = hashlib.sha256(handle.read()).hexdigest()
    return {
        "evidence_dir": evidence_dir,
        "files": digests,
        "items": evidence,
        "note": "container configuration, logs, mount identity and directory listings only; "
                "no data file is copied and no running file is labelled a consistent backup",
    }


def apply_actions():
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    evidence_dir = os.path.join(EVIDENCE_ROOT, stamp)
    os.makedirs(evidence_dir, exist_ok=True)
    before = collect()
    manifest = freeze_evidence(evidence_dir, before)

    results = []
    for command in PAYLOAD["commands"]:
        out = run(command)
        row = {"argv": command, "exit_code": out.returncode,
               "stdout": (out.stdout or "").strip()[-800:], "stderr": (out.stderr or "").strip()[-800:]}
        # Both stop paths are read back: ``docker kill`` returns before the
        # process is gone, and even ``docker stop`` -- which blocks until the
        # container exits -- is only *evidence* once the state is read.
        if command[:1] == ["docker"] and command[1] in ("kill", "stop"):
            name = command[-1]
            for _ in range(30):
                if run(["docker", "inspect", "-f", "{{.State.Running}}", name]).stdout.strip() == "false":
                    break
                time.sleep(1)
            row["running_after"] = run(["docker", "inspect", "-f", "{{.State.Running}}", name]).stdout.strip()
        results.append(row)

    renames = []
    for item in PAYLOAD["compose_neutralise"]:
        path = item["path"]
        target = item["to"].replace(STAMP_PLACEHOLDER, stamp)
        if os.path.exists(path):
            os.rename(path, target)
            renames.append({"from": path, "to": target, "sha256": item["sha256"], "state": "renamed"})
        else:
            renames.append({"from": path, "to": target, "sha256": item["sha256"], "state": "absent"})

    after = collect()
    survivor_probe = {}
    for probe in PAYLOAD["survivor_probes"]:
        result = run(probe["argv"])
        survivor_probe[probe["name"]] = {
            "argv": probe["argv"], "exit_code": result.returncode,
            "stdout": (result.stdout or "").strip()[-2000:], "stderr": (result.stderr or "").strip()[-400:]}
    with open(os.path.join(evidence_dir, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump({"agent": "daily_runtime_legacy_stack_retire", "stamp": stamp, "evidence": manifest,
                   "renames": renames, "command_results": results}, handle, ensure_ascii=False, indent=2,
                  sort_keys=True)
    return {
        "mode": "apply",
        "evidence_dir": evidence_dir,
        "manifest": manifest,
        "renames": renames,
        "command_results": results,
        "observed_before": before,
        "observed_after": after,
        "survivor_probe": survivor_probe,
        "writes": True,
    }


if MODE == "apply":
    payload = apply_actions()
else:
    payload = {"mode": "observe", "observed": collect(), "writes": False}
print(MARKER + json.dumps(payload, ensure_ascii=False, sort_keys=True))
'''


def run(command, *, cwd=None, input_bytes=None):
    return subprocess.run(
        command, cwd=cwd or ROOT, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def ssh(ssh_host, remote_command, *, input_bytes=None):
    return run([
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4",
        ssh_host, remote_command,
    ], input_bytes=input_bytes)


def decode(result):
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def marker_payload(output):
    for line in reversed(output.splitlines()):
        if line.startswith(MARKER):
            try:
                return json.loads(line[len(MARKER):])
            except ValueError:
                return None
    return None


def load_declaration(path):
    if not path.exists():
        raise RetireError(f"retired-stack declaration missing: {path}")
    return load_declaration_from_text(path.read_text(encoding="utf-8"))


def load_declaration_from_text(text):
    try:
        declaration = json.loads(text)
    except ValueError as error:
        raise RetireError(f"retired-stack declaration is not valid JSON: {error}")
    if declaration.get("schema") != "daily.runtime.retired_stacks.v1":
        raise RetireError("unexpected retired-stack declaration schema")
    stacks = declaration.get("stacks") or []
    if not stacks:
        raise RetireError("retired-stack declaration lists no stack")
    for stack in stacks:
        if not stack.get("legacy_checkout"):
            raise RetireError("retired-stack declaration lists a stack without a legacy checkout")
        if not (stack.get("containers") or []):
            raise RetireError("retired-stack declaration lists a stack without containers")
        intent = stack.get("intent") or SHARED_WRITER_INTENT
        if intent not in STACK_INTENTS:
            raise RetireError(f"unsupported retirement intent {intent!r}")
        if intent == SERVING_PUBLISHER_INTENT and not str(stack.get("revival_path") or "").strip():
            # A publisher is stood down so that a replacement can take its port.
            # The declaration has to say what could still bring it back, or the
            # stop reads as durable for a reason nobody wrote down.
            raise RetireError(
                "a serving_publisher stack must declare what could still revive it (revival_path)")
        for container in stack["containers"]:
            if container.get("kind") not in REVIEWED_STOP_METHOD:
                raise RetireError(f"unsupported container kind {container.get('kind')!r}")
            if intent == SERVING_PUBLISHER_INTENT and container.get("kind") in ("postgres", "redis"):
                # A publisher that owns a cluster writer *is* a shared writer, and
                # the two-writer proof is what decides that case. Letting it in
                # here would retire a writer through the graceful path.
                raise RetireError(
                    "a serving_publisher stack may not retire a %s container: that is the "
                    "shared_writer intent, where the two-writer proof applies"
                    % (container.get("kind"),))
            if container.get("kind") == "serving":
                if intent != SERVING_PUBLISHER_INTENT:
                    raise RetireError(
                        "a serving container belongs to the serving_publisher intent")
                if not SIGNAL_NAME.fullmatch(container.get("expected_stop_signal") or ""):
                    raise RetireError(
                        "serving container %s must declare the signal docker stop will send "
                        "(expected_stop_signal)" % (container.get("name"),))
            if not CONTAINER_NAME.fullmatch(container.get("name") or ""):
                raise RetireError(f"unsupported container name {container.get('name')!r}")
            if not re.fullmatch(r"[0-9a-f]{12,64}", container.get("id") or ""):
                raise RetireError(f"container {container.get('name')} has no immutable id")
            volume = container.get("shared_volume") or ""
            if volume and not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", volume):
                raise RetireError(f"unsupported shared volume name {volume!r}")
    return declaration


def declaration_targets(declaration):
    targets = []
    for stack in declaration["stacks"]:
        for container in stack["containers"]:
            targets.append({
                "container": container["name"],
                "declared_id": container["id"],
                "kind": container["kind"],
                "intent": stack.get("intent") or SHARED_WRITER_INTENT,
                "expected_stop_signal": container.get("expected_stop_signal") or "",
                "shared_volume": container.get("shared_volume") or "",
                "mount_destination": container.get("mount_destination") or "",
                "compose_project": stack["compose_project"],
            })
    return targets


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def plan_digest(actions):
    return hashlib.sha256(canonical(actions).encode("utf-8")).hexdigest()


def build_plan(declaration, facts, *, ssh_host, evidence_root):
    targets = declaration_targets(declaration)
    observed = {row.get("container"): row for row in facts.get("containers") or []}
    declared_names = {target["container"] for target in targets}
    declared_volume = {
        target["shared_volume"] for target in targets if target["shared_volume"]
    }
    shared_targets = [t for t in targets if t["intent"] == SHARED_WRITER_INTENT]
    serving_targets = [t for t in targets if t["intent"] == SERVING_PUBLISHER_INTENT]
    guards = []

    def guard(identifier, passed, detail):
        guards.append({"id": identifier, "passed": bool(passed), "detail": detail})

    missing = sorted(name for name in declared_names if not (observed.get(name) or {}).get("present"))
    guard("declared_container_present", not missing, missing)

    mismatched = []
    for target in targets:
        row = observed.get(target["container"]) or {}
        if row.get("present") and row.get("container_id") != target["declared_id"]:
            mismatched.append({"container": target["container"], "declared": target["declared_id"],
                               "observed": row.get("container_id")})
    guard("declared_container_identity_matches", not mismatched, mismatched)

    volume_owners = facts.get("volume_owners") or {}
    if shared_targets:
        shared = {
            volume: sorted(owners) for volume, owners in volume_owners.items()
            if len(set(owners)) > 1 and any(owner in declared_names for owner in owners)
        }
        guard("declared_stack_is_a_shared_writer", bool(shared), shared)

        declared_volume_covered = sorted(
            volume for volume in declared_volume
            if not any(owner in declared_names for owner in volume_owners.get(volume, []))
        )
        guard("declared_shared_volume_is_mounted_by_the_declared_stack", not declared_volume_covered,
              declared_volume_covered)

    # The retirement must take down the *older* writer on the shared cluster. If a
    # declared orphan had started last, the declaration points at the survivor and
    # the stop would take down the live stack.
    postgres_owners = facts.get("postgres_data_volume_owners") or {}
    cluster_volumes = sorted(volume for volume, owners in postgres_owners.items() if len(set(owners)) > 1)
    writer_start_times = {}
    for volume in cluster_volumes:
        for name in set(postgres_owners[volume]):
            text = (observed.get(name) or {}).get("cluster_facts") or ""
            if text:
                writer_start_times[name] = text.split("|")[0]
    declared_postgres = sorted(target["container"] for target in targets if target["kind"] == "postgres")
    running_declared_postgres = sorted(
        name for name in declared_postgres if (observed.get(name) or {}).get("running")
    )
    cluster_owner_names = {name for volume in cluster_volumes for name in set(postgres_owners[volume])}
    survivors = sorted(cluster_owner_names - declared_names)
    survivors_unreported = sorted(name for name in survivors if name not in writer_start_times)
    comparable = len(writer_start_times) >= 2 and len(set(writer_start_times.values())) >= 2
    offending = []
    if comparable:
        newest = max(writer_start_times.values())
        offending = sorted(n for n in writer_start_times
                           if n in declared_names and writer_start_times[n] == newest)
    # A declared postmaster that is not running is not a writer at all: no stop
    # command is planned for it, so it cannot be the newest writer on the shared
    # cluster. That is only a post-condition, never a shortcut around the check:
    # it requires the shared cluster to still exist, the survivor to be the sole
    # reported live writer, and every other owner to be live and reported. An
    # unreadable survivor therefore keeps blocking instead of looking "retired".
    already_retired = (
        bool(cluster_volumes)
        and not running_declared_postgres
        and bool(survivors)
        and not survivors_unreported
        and not (set(writer_start_times) & declared_names)
    )
    if shared_targets:
        guard("declared_postgres_is_not_the_newest_writer",
              (comparable and not offending) or already_retired,
              {"cluster_volumes": cluster_volumes, "writer_start_times": writer_start_times,
               "comparable": comparable, "newest_writer_is_declared": offending,
               "declared_postgres_running": running_declared_postgres,
               "declared_postgres_already_retired": already_retired,
               "survivors_unreported": survivors_unreported})

    application_clients = {
        row["container"]: row.get("application_clients")
        for row in observed.values() if row.get("application_clients")
    }
    guard("declared_container_has_no_application_consumer", not application_clients, application_clients)

    redis_consumers = {
        row["container"]: row.get("redis_consumers")
        for row in observed.values() if row.get("redis_consumers")
    }
    guard("declared_redis_has_no_application_consumer", not redis_consumers, redis_consumers)

    live_idle = sorted(row["container"] for row in observed.values()
                       if row.get("kind") == "idle" and row.get("running"))
    guard("declared_idle_container_is_not_running", not live_idle, live_idle)

    # A serving publisher owns no cluster data directory. The plan proves the
    # opposite of the shared-writer case: the only thing it holds is a published
    # port, so it must share no *writable, live* volume with anything still
    # running, and it must not mount a PostgreSQL data directory at all.
    running_volume_owners = facts.get("running_volume_owners") or {}
    serving_sharing = {}
    serving_cluster_mounts = {}
    signal_mismatch = {}
    for target in serving_targets:
        row = observed.get(target["container"]) or {}
        mounts = row.get("mounts") or []
        for mount in mounts:
            if mount.get("destination") == POSTGRES_DATA_DESTINATION:
                serving_cluster_mounts.setdefault(target["container"], []).append(
                    mount.get("destination"))
            name = mount.get("name")
            if not name or not mount.get("rw"):
                continue
            others = sorted(owner for owner in running_volume_owners.get(name, [])
                            if owner != target["container"])
            if others:
                serving_sharing.setdefault(target["container"], []).append(
                    {"volume": name, "live_owners": others})
        if not row.get("present"):
            continue
        resolved = row.get("resolved_stop_signal") or DEFAULT_STOP_SIGNAL
        if resolved != target["expected_stop_signal"]:
            signal_mismatch[target["container"]] = {
                "declared": target["expected_stop_signal"], "observed": resolved}
    if serving_targets:
        guard("declared_serving_container_does_not_share_a_live_writable_volume",
              not serving_sharing, serving_sharing)
        guard("declared_serving_container_owns_no_cluster_data_directory",
              not serving_cluster_mounts, serving_cluster_mounts)
        guard("declared_serving_stop_signal_matches_the_container",
              not signal_mismatch, signal_mismatch)

    commands = []
    for target in targets:
        row = observed.get(target["container"]) or {}
        commands.append({
            "step": "remove_automatic_restart_path",
            "container": target["container"],
            "argv": [part.format(container=target["container"]) for part in RESTART_ACTION],
        })
        method = REVIEWED_STOP_METHOD[target["kind"]]
        if method["argv"] is None or not row.get("running"):
            continue
        signal = method["signal"]
        if signal == VERIFIED_STOP_SIGNAL:
            # The reviewed table names the *source* of the signal (the container
            # itself); the plan records the value it read back, so the digest a
            # reviewer approves binds the exact signal ``docker stop`` will send.
            signal = row.get("resolved_stop_signal") or DEFAULT_STOP_SIGNAL
        commands.append({
            "step": f"stop_{target['kind']}_{method['mode']}",
            "container": target["container"],
            "signal": signal,
            "argv": [part.format(container=target["container"]) for part in method["argv"]],
            "authority": method["authority"],
            "refused": method["refused"],
        })

    compose_neutralise = []
    for row in facts.get("compose_files") or []:
        if not row.get("exists") or not row.get("sha256"):
            continue
        compose_neutralise.append({
            "path": row["path"],
            "to": row["path"] + ".retired-" + STAMP_PLACEHOLDER,
            "sha256": row["sha256"],
        })

    actions = {
        "schema": "daily.runtime.legacy_stack.retire.actions.v1",
        "ssh_host": ssh_host,
        "evidence_root": evidence_root,
        "targets": [{"container": t["container"], "id": t["declared_id"], "kind": t["kind"]} for t in targets],
        "commands": commands,
        "compose_neutralise": compose_neutralise,
    }
    return {
        "guards": guards,
        "commands": commands,
        "compose_neutralise": compose_neutralise,
        "actions": actions,
        "digest": plan_digest(actions),
        "targets": targets,
    }


def observe(*, ssh_host, declaration, evidence_root, expected_sha):
    payload = {
        "mode": "observe",
        "targets": _remote_targets(declaration),
        "evidence_root": evidence_root,
        "compose_files": _compose_files(declaration),
        "legacy_checkouts": _legacy_checkouts(declaration),
        "survivor_probes": [],
    }
    result = _execute(ssh_host, payload)
    if expected_sha:
        head = ssh(ssh_host, f"cd {shlex.quote(REMOTE_PRODUCT_REPO)} && git rev-parse HEAD")
        remote_head = head.stdout.decode().strip()
        if head.returncode or remote_head != expected_sha:
            raise RetireError(f"remote product revision {remote_head or '<unknown>'} != expected {expected_sha}")
    return result["observed"]


def apply_retirement(*, ssh_host, declaration, actions):
    payload = {
        "mode": "apply",
        "targets": _remote_targets(declaration),
        "evidence_root": actions["evidence_root"],
        "compose_files": _compose_files(declaration),
        "legacy_checkouts": _legacy_checkouts(declaration),
        "commands": [command["argv"] for command in actions["commands"]],
        "compose_neutralise": actions["compose_neutralise"],
        "survivor_probes": _survivor_probes(declaration),
    }
    return _execute(ssh_host, payload)


def _remote_targets(declaration):
    return [
        {"container": t["container"], "kind": t["kind"], "intent": t["intent"],
         "expected_stop_signal": t["expected_stop_signal"],
         "shared_volume": t["shared_volume"],
         "mount_destination": t["mount_destination"]}
        for t in declaration_targets(declaration)
    ]


def _legacy_checkouts(declaration):
    """Every declared checkout, de-duplicated and order-stable.

    A declaration may hold a shared-writer leftover and a serving publisher at
    once, and both have to answer "which revision is this, and could anything
    revive it". Reading only the first stack would silently drop the second.
    """
    seen = []
    for stack in declaration["stacks"]:
        path = stack["legacy_checkout"]
        if path not in seen:
            seen.append(path)
    return seen


def _compose_files(declaration):
    """Every declared compose file, de-duplicated and order-stable.

    A served publisher whose compose file is *shared* with a live duty leaves it
    unlisted: neutralising a file another duty still renders from would break the
    stack that is starting, not the one being retired.
    """
    paths = []
    for stack in declaration["stacks"]:
        checkout = stack["legacy_checkout"]
        for name in stack.get("compose_files") or []:
            path = f"{checkout}/{name}"
            if path not in paths:
                paths.append(path)
    return paths


def _survivor_probes(declaration):
    probes = (declaration.get("survivor") or {}).get("probes") or []
    return [{"name": probe["name"], "argv": probe["argv"]} for probe in probes]


def _execute(ssh_host, payload):
    program = (
        PROGRAM_TEMPLATE
        .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
        .replace("__POSTGRES_DATA_DESTINATION__", json.dumps(POSTGRES_DATA_DESTINATION))
        .replace("__STAMP_PLACEHOLDER__", json.dumps(STAMP_PLACEHOLDER))
        .replace("__DEFAULT_STOP_SIGNAL__", json.dumps(DEFAULT_STOP_SIGNAL))
        .encode("utf-8")
    )
    try:
        upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
        if upload.returncode:
            raise RetireError(f"remote program upload failed: {decode(upload)[:400]}")
        executed = ssh(ssh_host, f"python3 {shlex.quote(REMOTE_TMP)}")
        result = marker_payload(decode(executed))
        if result is None:
            raise RetireError(
                f"no remote payload (exit {executed.returncode}): {decode(executed)[-900:]}"
            )
        return result
    finally:
        # The probe is a temporary carrier of this entry. A failed readback must
        # not leave it on the host -- that residue is exactly what this guard
        # makes impossible to forget.
        ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--declaration", default=DEFAULT_DECLARATION)
    parser.add_argument("--evidence-root", default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expect-plan-digest", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    if not SSH_HOST.fullmatch(options.ssh_host or ""):
        print("[daily.runtime.legacy_stack.retire] BLOCKED ssh host must be a configured host alias",
              file=sys.stderr)
        return 2
    if options.expected_sha and not FULL_SHA.fullmatch(options.expected_sha):
        print("[daily.runtime.legacy_stack.retire] BLOCKED expected SHA must be a full commit identity",
              file=sys.stderr)
        return 2

    declaration_path = Path(options.declaration)
    if not declaration_path.is_absolute():
        declaration_path = ROOT / options.declaration

    try:
        declaration = load_declaration(declaration_path)
        observed = observe(
            ssh_host=options.ssh_host, declaration=declaration,
            evidence_root=options.evidence_root, expected_sha=options.expected_sha,
        )
        plan = build_plan(declaration, observed, ssh_host=options.ssh_host,
                          evidence_root=options.evidence_root)
    except RetireError as error:
        print(f"[daily.runtime.legacy_stack.retire] BLOCKED {error}", file=sys.stderr)
        return 2

    failing = [row["id"] for row in plan["guards"] if not row["passed"]]
    report = {
        "schema": "daily.runtime.legacy_stack.retire.v1",
        "ssh_host": options.ssh_host,
        "declaration": str(declaration_path.relative_to(ROOT)),
        "expected_sha": options.expected_sha,
        "observation": observed,
        "plan": {
            "guards": plan["guards"],
            "failing_guards": failing,
            "commands": plan["commands"],
            "compose_neutralise": plan["compose_neutralise"],
            "digest": plan["digest"],
        },
        "applied": None,
        "writes": False,
        "status": "PLAN" if not failing else "BLOCKED",
    }

    if options.apply:
        if failing:
            print("[daily.runtime.legacy_stack.retire] BLOCKED refusing to apply with failing guards: "
                  + ", ".join(failing), file=sys.stderr)
            _write(options.report, report)
            return 1
        if os.environ.get(CONFIRM_ENV) != CONFIRM_VALUE:
            print(f"[daily.runtime.legacy_stack.retire] BLOCKED {CONFIRM_ENV} must equal the exact "
                  "retirement confirmation", file=sys.stderr)
            return 2
        if options.expect_plan_digest != plan["digest"]:
            print("[daily.runtime.legacy_stack.retire] BLOCKED the reviewed plan digest no longer matches "
                  "the observed plan; review the current plan before applying", file=sys.stderr)
            return 2
        try:
            report["applied"] = apply_retirement(
                ssh_host=options.ssh_host, declaration=declaration, actions=plan["actions"],
            )
        except RetireError as error:
            print(f"[daily.runtime.legacy_stack.retire] BLOCKED {error}", file=sys.stderr)
            return 2
        report["writes"] = True
        report["status"] = "APPLIED"

    _write(options.report, report)
    print(json.dumps({
        "schema": report["schema"],
        "status": report["status"],
        "report": str(options.report),
        "plan_digest": plan["digest"],
        "failing_guards": failing,
        "commands": [row["step"] for row in plan["commands"]],
        "evidence_dir": (report.get("applied") or {}).get("evidence_dir", ""),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] in ("PLAN", "APPLIED") else 1


def _write(report_path, report):
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
