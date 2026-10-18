#!/usr/bin/env python3
"""Read-only verification of the daily runtime's single public entry.

It proves, against the running host, that:

* exactly one container publishes the declared public port, and it is the
  serving duty's nginx;
* every other declared face publishes only on the loopback interface;
* a request with no database hint lands on the serving duty;
* ``X-Odoo-DB`` and ``?db=`` land on the duty that owns the named database and
  never cross into a database the entry does not declare;
* both duties publish the same deployed source revision and frontend artifact;
* the platform nginx is reachable from the serving nginx on the declared
  cross-duty network, and its rendered route points back at its own Odoo.

The containers are resolved from the duty declaration, never guessed from the
port they happen to publish.  The script never writes to the host; only the
local report file is written.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_DIST = REMOTE_ROOT + "/frontend/apps/web/dist-dev"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")


REMOTE_PROGRAM = r'''
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

ENTRY = __ENTRY__
DUTIES = __DUTIES__
EXPECTED_SHA = __EXPECTED_SHA__
PRODUCT_ROOT = __PRODUCT_ROOT__
DIST = __DIST__


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def docker(*args):
    return run(["docker", *args])


def http(path, headers=None):
    request = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (int(ENTRY["public_entry"]["port"]), path),
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.getcode(), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except Exception as error:  # connection refusal is evidence too
        return 0, str(error)


def runtime_version(header=None, query=None):
    path = "/api/runtime-version"
    if query:
        path += "?db=" + urllib.parse.quote(query)
    code, body = http(path, {"X-Odoo-DB": header} if header else {})
    if code != 200:
        return code, {}
    try:
        payload = json.loads(body)
    except ValueError:
        return code, {}
    return code, payload if isinstance(payload, dict) else {}


def entry_asset(html):
    match = re.search(r'src="?/assets/(index-[^"?]+\.js)"?', html or "")
    return match.group(1) if match else ""


def env_map(container):
    if not container:
        return {}
    result = docker("inspect", container, "--format", "{{range .Config.Env}}{{println .}}{{end}}")
    values = {}
    for line in (result.stdout or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def published(container, container_port):
    if not container:
        return []
    result = docker("port", container, str(container_port))
    return sorted(line.strip() for line in (result.stdout or "").splitlines() if line.strip())


def rendered_conf(container):
    if not container:
        return ""
    result = docker("exec", container, "cat", "/etc/nginx/conf.d/default.conf")
    return result.stdout if result.returncode == 0 else ""


def container_name(duty_name, service):
    duty = DUTY_BY_NAME.get(duty_name) or {}
    project = str(((duty.get("cluster") or {}).get("compose_project") or ""))
    return "%s-%s-1" % (project, service) if project else ""


checks = []


def add(name, passed, detail=None):
    checks.append({"name": name, "passed": bool(passed), "detail": detail or {}})


DUTY_BY_NAME = {str(row.get("duty") or ""): row for row in DUTIES.get("duties") or []}
routes = {str(row.get("database") or ""): row for row in ENTRY.get("routes") or []}

serving_duty = str((ENTRY.get("public_entry") or {}).get("serving_duty") or "")
serving_route = next(
    (row for row in ENTRY.get("routes") or [] if str(row.get("duty") or "") == serving_duty),
    None,
)
platform_db = str(DUTIES.get("platform_admin_database") or "")
platform_route = routes.get(platform_db) or {}
platform_duty = str(platform_route.get("duty") or "")
serving_db = str((serving_route or {}).get("database") or "")

add("entry_declares_one_serving_duty", bool(serving_duty) and serving_route is not None,
    {"serving_duty": serving_duty, "serving_database": serving_db})
add("entry_declares_the_platform_database_route", bool(platform_duty) and platform_db in routes,
    {"platform_database": platform_db, "platform_duty": platform_duty})

serving_nginx = container_name(serving_duty, "nginx")
serving_odoo = container_name(serving_duty, "odoo")
platform_nginx = container_name(platform_duty, "nginx")
platform_odoo = container_name(platform_duty, "odoo")

head = run(["git", "-C", PRODUCT_ROOT, "rev-parse", "HEAD"]).stdout.strip()
if not EXPECTED_SHA:
    EXPECTED_SHA = head
dist_fingerprint = ""
try:
    with open(DIST + "/.build-sha256") as stream:
        dist_fingerprint = stream.read().strip()
except OSError:
    pass

add("product_root_is_at_the_deployed_revision",
    bool(EXPECTED_SHA) and head == EXPECTED_SHA,
    {"head": head, "expected": EXPECTED_SHA})
add("served_frontend_fingerprint_is_present",
    bool(re.fullmatch(r"[0-9a-f]{64}", dist_fingerprint or "")),
    {"dist": DIST, "fingerprint": dist_fingerprint})

# ---- one public face -------------------------------------------------------
public_port = int((ENTRY.get("public_entry") or {}).get("port") or 0)
publishers = set()
listing = docker("ps", "--format", "{{.ID}}\t{{.Names}}")
for line in (listing.stdout or "").splitlines():
    parts = line.split("\t")
    if len(parts) != 2:
        continue
    uid, name = parts[0].strip(), parts[1].strip()
    bindings = docker("port", uid)
    for binding in (bindings.stdout or "").splitlines():
        if binding.strip().endswith(":%d" % public_port):
            publishers.add(name)
add("exactly_one_container_publishes_the_public_port",
    publishers == {serving_nginx},
    {"port": public_port, "serving_nginx": serving_nginx, "publishers": sorted(publishers)})

for row in ENTRY.get("exposure") or []:
    duty_name = str(row.get("duty") or "")
    service = str(row.get("service") or "")
    name = container_name(duty_name, service)
    container_port = 80 if service == "nginx" else 8069
    bindings = published(name, container_port)
    expected = "%s:%s" % (row.get("bind_host"), row.get("host_port"))
    label = "exposure_%s_%s" % (duty_name, service)
    add(label + "_has_the_declared_binding", expected in bindings,
        {"container": name, "expected": expected, "bindings": bindings})
    if row.get("public") is True:
        add(label + "_is_the_public_face",
            any(binding.startswith("0.0.0.0:") for binding in bindings),
            {"bindings": bindings})
    else:
        add(label + "_is_loopback_only",
            bool(bindings)
            and all(binding.startswith("127.0.0.1:") for binding in bindings)
            and not any(binding.startswith("0.0.0.0:") or binding.startswith("[::]") for binding in bindings),
            {"bindings": bindings})

# ---- HTTP faces ------------------------------------------------------------
code, served_html = http("/")
served_entry = entry_asset(served_html)
admin_code, admin_html = http(str((ENTRY.get("public_entry") or {}).get("platform_admin_path") or "/platform-admin"))
admin_entry = entry_asset(admin_html)
asset_code, _ = http("/assets/" + served_entry) if served_entry else (0, "")

add("public_entry_root_answers", code == 200, {"code": code})
add("platform_admin_path_answers", admin_code == 200, {"code": admin_code})
add("both_paths_serve_the_same_spa_entry", bool(served_entry) and served_entry == admin_entry,
    {"root": served_entry, "platform_admin": admin_entry})
add("served_entry_asset_answers", bool(served_entry) and asset_code == 200,
    {"asset": served_entry, "code": asset_code})

default_code, default_version = runtime_version()
header_code, header_version = runtime_version(header=platform_db)
query_code, query_version = runtime_version(query=platform_db)
serving_header_code, serving_header_version = runtime_version(header=serving_db)
undeclared_code, undeclared_version = runtime_version(header="sc_undeclared_entry_probe")
undeclared_query_code, undeclared_query_version = runtime_version(query="sc_undeclared_entry_probe")

add("default_route_lands_on_the_serving_database",
    default_code == 200 and default_version.get("database") == serving_db,
    {"code": default_code, "observed": default_version.get("database"), "declared": serving_db})
add("database_header_lands_on_the_platform_database",
    header_code == 200 and header_version.get("database") == platform_db,
    {"code": header_code, "observed": header_version.get("database"), "declared": platform_db})
add("database_query_lands_on_the_platform_database",
    query_code == 200 and query_version.get("database") == platform_db,
    {"code": query_code, "observed": query_version.get("database"), "declared": platform_db})
add("platform_header_and_query_agree",
    header_version.get("database") == query_version.get("database") == platform_db,
    {"header": header_version.get("database"), "query": query_version.get("database")})
add("explicit_serving_database_hint_stays_on_the_serving_duty",
    serving_header_code == 200 and serving_header_version.get("database") == serving_db,
    {"code": serving_header_code, "observed": serving_header_version.get("database"),
     "declared": serving_db})
add("the_platform_hint_never_returns_the_serving_database",
    header_version.get("database") != serving_db and query_version.get("database") != serving_db,
    {"serving": serving_db, "header": header_version.get("database"),
     "query": query_version.get("database")})

declared_databases = {serving_db, platform_db}
add("an_undeclared_header_hint_never_reaches_an_undeclared_database",
    undeclared_code != 200 or undeclared_version.get("database") in declared_databases,
    {"code": undeclared_code, "observed": undeclared_version.get("database"),
     "declared": sorted(declared_databases)})
add("an_undeclared_query_hint_never_reaches_an_undeclared_database",
    undeclared_query_code != 200 or undeclared_query_version.get("database") in declared_databases,
    {"code": undeclared_query_code, "observed": undeclared_query_version.get("database"),
     "declared": sorted(declared_databases)})

for label, version in (("serving", default_version), ("platform", header_version)):
    add("%s_runtime_publishes_the_deployed_revision" % label,
        bool(EXPECTED_SHA) and version.get("git_sha") == EXPECTED_SHA,
        {"observed": version.get("git_sha"), "expected": EXPECTED_SHA})
    add("%s_runtime_publishes_the_served_frontend" % label,
        bool(dist_fingerprint) and version.get("frontend_build_sha256") == dist_fingerprint,
        {"observed": version.get("frontend_build_sha256"), "expected": dist_fingerprint})

# ---- containers, routes, network ------------------------------------------
for label, container, database in (
    ("serving", serving_odoo, serving_db),
    ("platform", platform_odoo, platform_db),
):
    environment = env_map(container)
    add("%s_application_reads_the_declared_database" % label,
        environment.get("DB_NAME") == database,
        {"container": container, "observed": environment.get("DB_NAME"), "declared": database})
    add("%s_application_reads_the_deployed_revision" % label,
        bool(EXPECTED_SHA) and environment.get("SC_SOURCE_REVISION") == EXPECTED_SHA,
        {"container": container, "observed": environment.get("SC_SOURCE_REVISION"),
         "expected": EXPECTED_SHA})
    add("%s_application_reads_the_served_frontend" % label,
        bool(dist_fingerprint) and environment.get("FRONTEND_BUILD_SHA256") == dist_fingerprint,
        {"container": container, "observed": environment.get("FRONTEND_BUILD_SHA256"),
         "expected": dist_fingerprint})

for label, container, expected_db, expected_upstream in (
    ("serving_nginx", serving_nginx, platform_db, str(platform_route.get("upstream") or "")),
    ("platform_nginx", platform_nginx, platform_db, "odoo:8069"),
):
    environment = env_map(container)
    add("%s_declares_the_platform_route" % label,
        environment.get("SC_PROXY_PLATFORM_DB") == expected_db
        and environment.get("SC_PROXY_PLATFORM_UPSTREAM") == expected_upstream,
        {"container": container,
         "observed_db": environment.get("SC_PROXY_PLATFORM_DB"),
         "observed_upstream": environment.get("SC_PROXY_PLATFORM_UPSTREAM"),
         "expected_db": expected_db, "expected_upstream": expected_upstream})
    conf = rendered_conf(container)
    pattern = r"%s\s+%s;" % (re.escape(expected_db), re.escape(expected_upstream))
    add("%s_rendered_config_carries_the_platform_route" % label,
        bool(conf) and re.search(pattern, conf) is not None,
        {"container": container, "expected": pattern})

network_name = str((ENTRY.get("network") or {}).get("name") or "")
network = docker("network", "inspect", network_name)
members = []
if network.returncode == 0:
    try:
        members = [
            str(row.get("Name") or "").lstrip("/")
            for row in (json.loads(network.stdout)[0].get("Containers") or {}).values()
        ]
    except (ValueError, IndexError, AttributeError):
        members = []
add("both_nginx_faces_join_the_entry_network",
    bool(serving_nginx) and serving_nginx in members and platform_nginx in members,
    {"network": network_name, "members": sorted(members)})

status = "PASS" if all(row["passed"] for row in checks) else "FAIL"
print("DAILY_ENTRY_VERIFY=" + json.dumps({
    "status": status,
    "head": head,
    "expected_sha": EXPECTED_SHA,
    "dist_fingerprint": dist_fingerprint,
    "public_port": public_port,
    "serving_database": serving_db,
    "platform_database": platform_db,
    "serving_nginx": serving_nginx,
    "platform_nginx": platform_nginx,
    "publishers": sorted(publishers),
    "network_members": sorted(members),
    "checks": checks,
}, ensure_ascii=False, sort_keys=True))
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssh-host", default="sc-root")
    parser.add_argument("--entry", default="config/ops/daily_runtime_entry.v1.json")
    parser.add_argument("--declaration", default="config/ops/daily_runtime_database_duties.v1.json")
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if not SSH_HOST.fullmatch(args.ssh_host or ""):
        raise SystemExit("[daily.runtime.entry.verify] BLOCKED invalid ssh host")
    if args.expected_sha and not FULL_SHA.fullmatch(args.expected_sha):
        raise SystemExit("[daily.runtime.entry.verify] BLOCKED invalid expected SHA")
    entry = json.loads((ROOT / args.entry).read_text(encoding="utf-8"))
    duties = json.loads((ROOT / args.declaration).read_text(encoding="utf-8"))
    program = (
        REMOTE_PROGRAM.replace("__ENTRY__", json.dumps(entry, ensure_ascii=False, sort_keys=True))
        .replace("__DUTIES__", json.dumps(duties, ensure_ascii=False, sort_keys=True))
        .replace("__EXPECTED_SHA__", json.dumps(args.expected_sha))
        .replace("__PRODUCT_ROOT__", json.dumps(REMOTE_ROOT))
        .replace("__DIST__", json.dumps(REMOTE_DIST))
    )
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.ssh_host,
         "python3 -c " + shlex.quote(program)],
        capture_output=True, text=True, check=False,
    )
    output = result.stdout.strip()
    marker = "DAILY_ENTRY_VERIFY="
    payload = None
    for line in output.splitlines():
        if line.startswith(marker):
            payload = json.loads(line[len(marker):])
    if payload is None:
        raise SystemExit(
            "[daily.runtime.entry.verify] BLOCKED "
            + (result.stderr.strip() or output or "no evidence")[:1000]
        )
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    failures = [row["name"] for row in payload.get("checks") or [] if not row.get("passed")]
    print("[daily.runtime.entry.verify] %s %s" % (payload.get("status"), report))
    if failures:
        print("[daily.runtime.entry.verify] failed: " + ", ".join(failures))
    return 0 if payload.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
