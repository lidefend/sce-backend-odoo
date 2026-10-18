#!/usr/bin/env python3
"""Read-only verification of the daily runtime's single public entry.

It proves, against the running host, that:

* exactly one container publishes the declared public port, and it is the
  serving duty's nginx;
* every other declared face publishes only on the loopback interface;
* a path namespace selects the immutable database binding;
* a client database hint (``X-Odoo-DB`` / ``?db=``) is refused with 409;
* an unknown namespace is refused with 404 and a missing one with 400;
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

ENTRY = json.loads(__ENTRY__)
DUTIES = json.loads(__DUTIES__)
EXPECTED_SHA = __EXPECTED_SHA__
PRODUCT_ROOT = __PRODUCT_ROOT__
DIST = __DIST__


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def docker(*args):
    return run(["docker", *args])


def http_full(path, headers=None):
    request = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (int(ENTRY["public_entry"]["port"]), path),
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return (
                response.getcode(),
                response.read().decode("utf-8", "replace"),
                response.headers.get("Content-Type", ""),
            )
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), error.headers.get("Content-Type", "")
    except Exception as error:  # connection refusal is evidence too
        return 0, str(error), ""


def http(path, headers=None):
    code, body, _ = http_full(path, headers)
    return code, body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_no_redirect(path):
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (int(ENTRY["public_entry"]["port"]), path))
    try:
        with opener.open(request, timeout=20) as response:
            return (
                response.getcode(),
                response.headers.get("Location", ""),
                response.read().decode("utf-8", "replace"),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.headers.get("Location", ""),
            error.read().decode("utf-8", "replace"),
        )
    except Exception as error:
        return 0, "", str(error)


def probe(path, header=None, query=None):
    if query:
        separator = "&" if "?" in path else "?"
        path += separator + "db=" + urllib.parse.quote(query)
    code, body, content_type = http_full(path, {"X-Odoo-DB": header} if header else {})
    try:
        payload = json.loads(body)
    except ValueError:
        payload = {}
    return code, payload if isinstance(payload, dict) else {}, content_type


def runtime_version(path, header=None, query=None):
    code, payload, _ = probe(path, header=header, query=query)
    return code, payload


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
namespace_routes = ENTRY.get("namespace_routes") or {}
tenant_prefix = str(namespace_routes.get("tenant_prefix") or "/t")
platform_prefix = str(namespace_routes.get("platform_prefix") or "/platform-admin")
namespace_rows = {
    str(row.get("alias") or ""): row for row in namespace_routes.get("namespaces") or []
}
demo_ns = namespace_rows.get("demo") or next(
    (row for row in namespace_rows.values() if str(row.get("database") or "") == serving_db), {})
platform_ns = namespace_rows.get("platform") or next(
    (row for row in namespace_rows.values() if str(row.get("database") or "") == platform_db), {})
tenant_base = "%s/%s" % (tenant_prefix, str(demo_ns.get("alias") or "demo"))
platform_base = platform_prefix

public = ENTRY.get("public_entry") or {}
code, served_html = http(str(public.get("demo_path") or "/"))
root_path = str(public.get("root_path") or "/")
root_redirect_status = int(public.get("root_path_redirect_status") or 308)
root_redirect_location = str(public.get("root_path_redirect_location") or "/t/demo/")
root_redirect_code, root_redirect_header, root_redirect_body = http_no_redirect(root_path)
served_entry = entry_asset(served_html)
admin_code, admin_html = http(str(public.get("platform_admin_path") or platform_base))
admin_entry = entry_asset(admin_html)
asset_code, _ = http("/assets/" + served_entry) if served_entry else (0, "")

add("public_entry_root_answers", code == 200, {"code": code})
add("bare_root_requires_a_namespace",
    root_redirect_code == root_redirect_status
    and root_redirect_header.rstrip("/") == root_redirect_location.rstrip("/")
    and entry_asset(root_redirect_body) == "",
    {"path": root_path, "code": root_redirect_code,
     "location": root_redirect_header, "expected_status": root_redirect_status,
     "expected_location": root_redirect_location,
     "served_spa": bool(entry_asset(root_redirect_body))})
add("platform_admin_path_answers", admin_code == 200, {"code": admin_code})
add("both_paths_serve_the_same_spa_entry", bool(served_entry) and served_entry == admin_entry,
    {"root": served_entry, "platform_admin": admin_entry})
add("served_entry_asset_answers", bool(served_entry) and asset_code == 200,
    {"asset": served_entry, "code": asset_code})

hint_contract = namespace_routes.get("client_database_hint") or {}
hint_status = int(hint_contract.get("status") or 0)
hint_code = str(hint_contract.get("code") or "")
missing_contract = namespace_routes.get("missing_namespace") or {}
missing_status = int(missing_contract.get("status") or 0)
missing_code = str(missing_contract.get("code") or "")
missing_type = str(missing_contract.get("content_type") or "")
unknown_contract = namespace_routes.get("unknown_namespace") or {}
unknown_status = int(unknown_contract.get("status") or 0)
unknown_code = str(unknown_contract.get("code") or "")
unknown_type_expected = str(unknown_contract.get("content_type") or "")

tenant_code, tenant_version, tenant_type = probe("%s/api/runtime-version" % tenant_base)
platform_code, platform_version, platform_type = probe("%s/api/runtime-version" % platform_base)
root_code, root_payload, root_type = probe("/api/runtime-version")
root_login_code, root_login_payload, root_login_type = probe("/api/v1/auth/page-contracts")
header_hint_code, header_hint_payload, header_hint_type = probe(
    "%s/api/runtime-version" % tenant_base, header=platform_db)
query_hint_code, query_hint_payload, query_hint_type = probe(
    "%s/api/runtime-version" % tenant_base, query=platform_db)
unknown_path = "%s/%s/api/runtime-version" % (tenant_prefix, "sc_undeclared_entry_probe")
unknown_status_observed, unknown_payload, unknown_type = probe(unknown_path)

add("tenant_namespace_lands_on_the_serving_database",
    tenant_code == 200 and tenant_version.get("database") == serving_db,
    {"path": "%s/api/runtime-version" % tenant_base, "code": tenant_code,
     "observed": tenant_version.get("database"), "declared": serving_db})
add("platform_namespace_lands_on_the_platform_database",
    platform_code == 200 and platform_version.get("database") == platform_db,
    {"path": "%s/api/runtime-version" % platform_base, "code": platform_code,
     "observed": platform_version.get("database"), "declared": platform_db})
add("root_api_requires_a_namespace",
    root_code == missing_status and root_payload.get("error") == missing_code
    and (not missing_type or missing_type in root_type),
    {"path": "/api/runtime-version", "code": root_code, "body": root_payload,
     "content_type": root_type, "expected_status": missing_status, "expected_code": missing_code})
add("root_login_contract_requires_a_namespace",
    root_login_code == missing_status and root_login_payload.get("error") == missing_code
    and (not missing_type or missing_type in root_login_type),
    {"path": "/api/v1/auth/page-contracts", "code": root_login_code,
     "body": root_login_payload, "content_type": root_login_type,
     "expected_status": missing_status, "expected_code": missing_code})
add("client_database_header_is_refused",
    header_hint_code == hint_status and header_hint_payload.get("error") == hint_code
    and "application/json" in header_hint_type,
    {"path": "%s/api/runtime-version" % tenant_base, "header": platform_db,
     "code": header_hint_code, "body": header_hint_payload,
     "content_type": header_hint_type, "expected_status": hint_status, "expected_code": hint_code})
add("client_database_query_is_refused",
    query_hint_code == hint_status and query_hint_payload.get("error") == hint_code
    and "application/json" in query_hint_type,
    {"path": "%s/api/runtime-version" % tenant_base, "query": platform_db,
     "code": query_hint_code, "body": query_hint_payload,
     "content_type": query_hint_type, "expected_status": hint_status, "expected_code": hint_code})
add("unknown_namespace_is_refused",
    unknown_status_observed == unknown_status and unknown_payload.get("error") == unknown_code
    and (not unknown_type_expected or unknown_type_expected in unknown_type),
    {"path": unknown_path, "code": unknown_status_observed, "body": unknown_payload,
     "content_type": unknown_type, "expected_status": unknown_status,
     "expected_code": unknown_code})

for label, version in (("tenant", tenant_version), ("platform", platform_version)):
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

for label, container, expected_strip in (
    ("serving_nginx", serving_nginx, "0"),
    ("platform_nginx", platform_nginx, "1"),
):
    environment = env_map(container)
    add("%s_declares_the_entry_upstreams" % label,
        bool(environment.get("SC_PROXY_DEFAULT_UPSTREAM"))
        and bool(environment.get("SC_PROXY_PLATFORM_UPSTREAM")),
        {"container": container,
         "default_upstream_present": bool(environment.get("SC_PROXY_DEFAULT_UPSTREAM")),
         "platform_upstream_present": bool(environment.get("SC_PROXY_PLATFORM_UPSTREAM"))})
    add("%s_retires_the_database_selector" % label,
        "SC_PROXY_DEFAULT_DB" not in environment
        and "SC_PROXY_ALLOWED_DB_PATTERN" not in environment,
        {"container": container,
         "default_db_present": "SC_PROXY_DEFAULT_DB" in environment,
         "allowed_pattern_present": "SC_PROXY_ALLOWED_DB_PATTERN" in environment})
    add("%s_entry_secret_is_injected" % label,
        "SC_ENTRY_SHARED_SECRET" in environment,
        {"container": container, "present": "SC_ENTRY_SHARED_SECRET" in environment})
    add("%s_declares_the_route_version" % label,
        bool(environment.get("SC_ENTRY_ROUTE_VERSION")),
        {"container": container,
         "present": bool(environment.get("SC_ENTRY_ROUTE_VERSION"))})
    add("%s_platform_strip_matches_its_hop" % label,
        environment.get("SC_ENTRY_PLATFORM_STRIP") == expected_strip,
        {"container": container, "observed": environment.get("SC_ENTRY_PLATFORM_STRIP"),
         "expected": expected_strip})
    conf = rendered_conf(container)
    add("%s_rendered_config_uses_the_path_namespace" % label,
        bool(conf)
        and "X-SC-Namespace" in conf
        and "NS_NAMESPACE_REQUIRED" in conf
        and "$sc_path_ns" in conf,
        {"container": container})
    add("%s_rendered_config_has_no_database_selector" % label,
        bool(conf)
        and "$sc_proxy_db" not in conf
        and "unknown_database" not in conf
        and "$http_x_odoo_db" not in conf
        and "$arg_db" not in conf,
        {"container": container})
    add("%s_rendered_config_gates_the_platform_prefix_rewrite" % label,
        bool(conf)
        and "$sc_entry_platform_strip" in conf
        and "rewrite ^/platform-admin" in conf,
        {"container": container, "strip_guard_present": "$sc_entry_platform_strip" in conf})

expected_platform_upstream = str(platform_route.get("upstream") or "")
add("serving_nginx_forwards_the_platform_path_to_the_platform_face",
    bool(expected_platform_upstream)
    and env_map(serving_nginx).get("SC_PROXY_PLATFORM_UPSTREAM") == expected_platform_upstream,
    {"container": serving_nginx,
     "observed": env_map(serving_nginx).get("SC_PROXY_PLATFORM_UPSTREAM"),
     "declared": expected_platform_upstream})

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
        REMOTE_PROGRAM.replace(
            "__ENTRY__", json.dumps(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        )
        .replace(
            "__DUTIES__", json.dumps(json.dumps(duties, ensure_ascii=False, sort_keys=True))
        )
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
