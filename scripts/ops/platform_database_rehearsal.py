"""Fixed, owner-authorized P4 rehearsal; invoked only by governed Make targets."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "config/platform_database_rehearsal.json"
STATE = ROOT / ".runtime/platform-database-rehearsal"
COMPOSE = ROOT / "docker-compose.platform-database-rehearsal.yml"


def declaration():
    value = json.loads(DECLARATION.read_text())
    if (value["project"] != "sc-platform-db-rehearsal"
            or value["control_database"] != "sc_platform_control_rehearsal"
            or value["target_database"] != "sc_tenant_lifecycle_rehearsal"
            or value["host_ports"] or value["customer_business_data_allowed"]):
        raise ValueError("REHEARSAL_IDENTITY_REFUSED")
    return value


def execute(args, *, capture=False, stdin=None):
    # Do not inherit caller Compose project/profiles or arbitrary interpolation.
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("COMPOSE_", "REHEARSAL_"))}
    return subprocess.run(args, cwd=ROOT, env=environment, input=stdin, text=True,
                          stdout=subprocess.PIPE if capture else None, check=True).stdout


def compose(*args, capture=False, stdin=None):
    return execute(["docker", "compose", "--project-name", declaration()["project"],
                    "--env-file", str(STATE / "authority/compose.env"), "-f", str(COMPOSE), *args],
                   capture=capture, stdin=stdin)


def volume_inventory(require_absent=False):
    declared = declaration()
    names = set(execute(["docker", "volume", "ls", "--format", "{{.Name}}"], capture=True).splitlines())
    for name in declared["volumes"]:
        if name not in names:
            continue
        if require_absent:
            raise ValueError("REHEARSAL_EXISTING_VOLUME_WITHOUT_AUTHORITY:" + name)
        inspected = json.loads(execute(["docker", "volume", "inspect", name], capture=True))[0]
        if (inspected.get("Labels") or {}).get("com.docker.compose.project") != declared["project"]:
            raise ValueError("REHEARSAL_FOREIGN_VOLUME:" + name)


def secret_file(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)


def prepare():
    declared = declaration()
    authority = STATE / "authority"
    if authority.exists():
        preflight()
        return
    volume_inventory(require_absent=True)
    postgres_image = execute(["docker", "image", "inspect", "postgres:15", "--format", "{{.Id}}"], capture=True).strip()
    odoo_image = execute(["docker", "image", "inspect", "odoo17-odoo:latest", "--format", "{{.Id}}"], capture=True).strip()
    authority.mkdir(mode=0o700)
    (STATE / "evidence").mkdir(mode=0o700, exist_ok=True)
    passwords = {key: secrets.token_hex(24) for key in ("maintenance", "control", "target")}
    secret_file(authority / "credentials.json", json.dumps(passwords))
    secret_file(authority / "maintenance.json", json.dumps({
        "host": "db", "port": 5432, "user": declared["maintenance_role"],
        "password": passwords["maintenance"], "cluster_system_identifier": None,
    }))
    secret_file(authority / "compose.env", "\n".join([
        "REHEARSAL_POSTGRES_IMAGE=" + postgres_image,
        "REHEARSAL_ODOO_IMAGE=" + odoo_image,
        "REHEARSAL_MAINTENANCE_PASSWORD=" + passwords["maintenance"], "",
    ]))
    secret_file(authority / "control.conf", "\n".join([
        "[options]", "db_host = db", "db_port = 5432",
        "db_user = " + declared["control_role"], "db_password = " + passwords["control"],
        "db_name = " + declared["control_database"],
        "dbfilter = ^" + declared["control_database"] + "$", "list_db = False",
        "data_dir = /var/lib/odoo", "addons_path = /usr/lib/python3/dist-packages/odoo/addons,/workspace/addons",
        "admin_passwd = " + secrets.token_hex(24), "workers = 0", "max_cron_threads = 0", "",
    ]))
    secret_file(authority / "identity.json", json.dumps(declared, indent=2))
    preflight()


def validate_configuration(config, declared):
    if config.get("name") != declared["project"] or set(config["services"]) != {"db", "control", "target_namespace"}:
        raise ValueError("REHEARSAL_COMPOSE_IDENTITY_MISMATCH")
    if set(v["name"] for v in config["volumes"].values()) != set(declared["volumes"]):
        raise ValueError("REHEARSAL_VOLUME_SET_MISMATCH")
    if not config["networks"]["default"].get("internal"):
        raise ValueError("REHEARSAL_NETWORK_NOT_ISOLATED")
    permitted = {str(ROOT / "scripts"), str(ROOT / "addons/smart_core"), str(ROOT / "addons/smart_scene"), str(DECLARATION),
                 str(STATE / "authority"), str(STATE / "evidence")}
    for service in config["services"].values():
        if service.get("ports") or not service["image"].startswith("sha256:"):
            raise ValueError("REHEARSAL_PORT_OR_IMAGE_UNBOUND")
        for mount in service.get("volumes", []):
            if mount["type"] == "bind" and mount["source"] not in permitted:
                raise ValueError("REHEARSAL_FOREIGN_BIND")


def preflight():
    declared = declaration()
    if json.loads((STATE / "authority/identity.json").read_text()) != declared:
        raise ValueError("REHEARSAL_AUTHORITY_DRIFT")
    for path in (STATE / "authority").iterdir():
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("REHEARSAL_SECRET_PERMISSIONS")
    config = json.loads(compose("config", "--format", "json", capture=True))
    validate_configuration(config, declared)
    volume_inventory()
    print("[platform.database.rehearsal] preflight PASS project=" + declared["project"])


def carrier(mode):
    return compose("run", "--rm", "--no-deps", "-T", "control", "python3", "-m",
                   "scripts.ops.platform_database_rehearsal_runtime", mode)


def exercise(resume=False):
    preflight()
    compose("up", "-d", "--wait", "db")
    carrier("bootstrap")
    binding = json.loads((STATE / "evidence/cluster.json").read_text())
    path = STATE / "authority/maintenance.json"
    maintenance = json.loads(path.read_text())
    if maintenance["cluster_system_identifier"] not in (None, binding["cluster_system_identifier"]):
        raise ValueError("REHEARSAL_MAINTENANCE_CLUSTER_DRIFT")
    maintenance["cluster_system_identifier"] = binding["cluster_system_identifier"]
    path.write_text(json.dumps(maintenance))
    compose("run", "--rm", "--no-deps", "-T", "target_namespace")
    carrier("install")
    try:
        compose("run", "--rm", "--no-deps", "-T", "control", "odoo", "shell",
                "-c", "/authority/control.conf", "--no-http", stdin=(
                    "from scripts.ops.platform_database_rehearsal_runtime import exercise\nexercise(env, resume=" + repr(resume) + ")\n"))
    finally:
        carrier("export_evidence")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "preflight", "exercise", "continue", "recover", "readback", "export", "cleanup"])
    action = parser.parse_args().action
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(STATE / "execution.lock", "a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action == "prepare":
            prepare()
        elif action == "preflight":
            preflight()
        elif action in ("exercise", "continue"):
            exercise(resume=action == "continue")
        elif action == "export":
            preflight()
            carrier("export_evidence")
        elif action in ("recover", "readback"):
            preflight()
            compose("run", "--rm", "--no-deps", "-T", "control", "odoo", "shell",
                    "-c", "/authority/control.conf", "--no-http", stdin=(
                        "from scripts.ops.platform_database_rehearsal_runtime import " + action + "\n" + action + "(env)\n"))
        else:
            preflight()
            carrier("cleanup_check")
            compose("down", "--volumes")
            print("[platform.database.rehearsal] isolated resources removed; evidence retained")


if __name__ == "__main__":
    main()
