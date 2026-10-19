#!/usr/bin/env python3
"""Reproducible acceptance probes for the batch-C path namespace entry.

The script exercises the five behaviour groups that batch C froze and writes a
JSON report with an explicit expected/actual/status triple for every check:

1. entry mapping and refusal codes (400 / 409 / 404 and DB binding);
2. same-name ``admin`` authentication isolation across the two entries;
3. bidirectional token replay between the tenant and platform entries;
4. independent sessions and logout scope;
5. company-switch boundary (``company_id`` outside the allowed set).

It is read-only with respect to business data.  Login and logout do create and
invalidate authentication state (session rows and ``token_version``); that is
inherent to group 2-5 and is the only mutation the script performs.

Run it locally against a reachable entry::

    python3 scripts/ops/path_ns_c_acceptance.py --report /tmp/acceptance.json

or against a remote host, where the probe runs on that host so that
``127.0.0.1`` means the host's own entry, and provenance is read from the
host's checkout::

    python3 scripts/ops/path_ns_c_acceptance.py --ssh-host sc-root \
        --repo /opt/projects/repos/sce-product-odoo \
        --expected-sha <40-hex> --report /tmp/acceptance.json

Exit status is 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCHEMA = "path-ns-c.acceptance.v1"
TASK_ID = "PATH-NS-C-EVIDENCE-CLOSURE-20261018"
DEFAULT_BASE_URL = "http://127.0.0.1:18081"
TENANT_NAMESPACE = "demo"
PLATFORM_PATH = "platform-admin"
SERVER_APPLIED_COMMIT = "b81166475"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects are part of the contract; never follow them silently."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener():
    return urllib.request.build_opener(NoRedirect)


def _call(opener, url, *, method="GET", headers=None, body=None, timeout=30):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        resp = opener.open(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except Exception as exc:  # connection refused, DNS, timeouts
        return -1, {}, str(exc).encode("utf-8")


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _content_type(headers):
    return (headers.get("Content-Type") or "").split(";")[0].strip()


CREDENTIAL_ENV_KEYS = ("SC_PATH_NS_TENANT_PASSWORD", "SC_PATH_NS_PLATFORM_PASSWORD")


def _credentials():
    values = {key: os.environ.get(key, "") for key in CREDENTIAL_ENV_KEYS}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ValueError("managed namespace acceptance credentials required: " + ", ".join(missing))
    return values


def _root_requires_namespace(status, headers, raw):
    return (status == 400 and _json(raw).get("error") == "NS_NAMESPACE_REQUIRED"
            and _content_type(headers) == "application/json")


def _login(opener, base, path, password):
    status, headers, raw = _call(
        opener,
        base + path + "/api/v1/intent",
        method="POST",
        headers={"X-Anonymous-Intent": "1"},
        body={"intent": "login", "params": {"login": "admin", "password": password}},
    )
    doc = _json(raw)
    token = ""
    try:
        token = str(doc["data"]["session"]["token"])
    except Exception:
        token = ""
    return status, token, doc


def _intent(opener, base, path, intent, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    return _call(
        opener,
        base + path + "/api/v1/intent",
        method="POST",
        headers=headers,
        body={"intent": intent, "params": params or {}},
    )


def _git(repo, *args):
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _provenance(repo, expected_sha):
    info = {"repo": repo}
    if not repo:
        return info
    for key, args in (
        ("head", ("rev-parse", "HEAD")),
        ("branch", ("rev-parse", "--abbrev-ref", "HEAD")),
        ("subject", ("log", "-1", "--format=%s")),
    ):
        code, out, err = _git(repo, *args)
        info[key] = out if code == 0 else ""
        if code != 0:
            info[key + "_error"] = err
    code, out, _ = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    info["dirty"] = len([line for line in out.splitlines() if line.strip()]) if code == 0 else -1
    info["expected_sha"] = expected_sha
    code, out, _ = _git(repo, "cat-file", "-t", SERVER_APPLIED_COMMIT)
    info["server_applied_commit"] = {
        "sha": SERVER_APPLIED_COMMIT,
        "present": code == 0 and out.strip() == "commit",
    }
    if info["server_applied_commit"]["present"]:
        code, out, _ = _git(repo, "merge-base", "--is-ancestor", SERVER_APPLIED_COMMIT, "HEAD")
        info["server_applied_commit"]["ancestor_of_head"] = code == 0
        code, out, _ = _git(repo, "log", "-1", "--format=%s", SERVER_APPLIED_COMMIT)
        info["server_applied_commit"]["subject"] = out
    return info


def run_checks(base_url, expected_sha, repo):
    credentials = _credentials()
    opener = _opener()
    checks = []
    started = time.time()

    def add(group, name, expected, actual, ok):
        checks.append(
            {
                "group": group,
                "name": name,
                "expected": expected,
                "actual": actual,
                "status": "pass" if ok else "fail",
            }
        )

    provenance = _provenance(repo, expected_sha)
    if repo:
        head = provenance.get("head") or ""
        add(
            "provenance",
            "server_head_matches_expected",
            expected_sha,
            head,
            bool(expected_sha) and head == expected_sha,
        )
        add(
            "provenance",
            "server_worktree_clean",
            0,
            provenance.get("dirty"),
            provenance.get("dirty") == 0,
        )
        applied = provenance.get("server_applied_commit") or {}
        add(
            "provenance",
            "server_applied_commit_in_history",
            True,
            {
                "present": applied.get("present"),
                "ancestor_of_head": applied.get("ancestor_of_head"),
                "subject": applied.get("subject"),
            },
            bool(applied.get("present")) and bool(applied.get("ancestor_of_head")),
        )

    tenant = "/t/" + TENANT_NAMESPACE
    platform = "/" + PLATFORM_PATH

    # ---- group 1: entry mapping and refusal codes -------------------------
    status, headers, raw = _call(opener, base_url + "/")
    add(
        "entry_contract",
        "bare_root_requires_a_namespace",
        {"status": 400, "error": "NS_NAMESPACE_REQUIRED"},
        {"status": status, "error": _json(raw).get("error")},
        _root_requires_namespace(status, headers, raw),
    )

    status, headers, raw = _call(opener, base_url + "/api/runtime-version")
    code = (_json(raw).get("error") or "")
    add(
        "entry_contract",
        "bare_api_requires_namespace",
        {"status": 400, "error": "NS_NAMESPACE_REQUIRED", "content_type": "application/json"},
        {"status": status, "error": code, "content_type": _content_type(headers)},
        status == 400 and code == "NS_NAMESPACE_REQUIRED" and _content_type(headers) == "application/json",
    )

    status, headers, raw = _call(
        opener, base_url + tenant + "/api/runtime-version", headers={"X-Odoo-DB": "sc_demo"}
    )
    code = (_json(raw).get("error") or "")
    add(
        "entry_contract",
        "database_header_hint_refused",
        {"status": 409, "error": "NS_DATABASE_HINT_CONFLICT"},
        {"status": status, "error": code},
        status == 409 and code == "NS_DATABASE_HINT_CONFLICT",
    )

    status, headers, raw = _call(opener, base_url + tenant + "/api/runtime-version?db=sc_demo")
    code = (_json(raw).get("error") or "")
    add(
        "entry_contract",
        "database_query_hint_refused",
        {"status": 409, "error": "NS_DATABASE_HINT_CONFLICT"},
        {"status": status, "error": code},
        status == 409 and code == "NS_DATABASE_HINT_CONFLICT",
    )

    status, headers, raw = _call(opener, base_url + "/t/nope/api/runtime-version")
    doc = _json(raw)
    add(
        "entry_contract",
        "unknown_namespace_refused",
        {"status": 404, "error": "NS_UNKNOWN_NAMESPACE"},
        {"status": status, "error": doc.get("error"), "content_type": _content_type(headers)},
        status == 404 and doc.get("error") == "NS_UNKNOWN_NAMESPACE",
    )

    tenant_version = {}
    status, headers, raw = _call(opener, base_url + tenant + "/api/runtime-version")
    tenant_version = _json(raw)
    add(
        "entry_contract",
        "tenant_entry_binds_tenant_database",
        "sc_demo",
        tenant_version.get("database"),
        status == 200 and tenant_version.get("database") == "sc_demo",
    )

    platform_version = {}
    status, headers, raw = _call(opener, base_url + platform + "/api/runtime-version")
    platform_version = _json(raw)
    add(
        "entry_contract",
        "platform_entry_binds_platform_database",
        "sc_platform_control",
        platform_version.get("database"),
        status == 200 and platform_version.get("database") == "sc_platform_control",
    )

    if expected_sha:
        add(
            "provenance",
            "tenant_runtime_reports_deployed_revision",
            expected_sha,
            tenant_version.get("source_revision"),
            tenant_version.get("source_revision") == expected_sha,
        )
        add(
            "provenance",
            "platform_runtime_reports_deployed_revision",
            expected_sha,
            platform_version.get("source_revision"),
            platform_version.get("source_revision") == expected_sha,
        )

    # ---- group 2: same-name admin isolation ------------------------------
    demo_status, demo_token, _ = _login(opener, base_url, tenant, credentials["SC_PATH_NS_TENANT_PASSWORD"])
    add(
        "dual_entry_auth",
        "demo_entry_admin_login_succeeds",
        {"status": 200, "token_present": True},
        {"status": demo_status, "token_length": len(demo_token)},
        demo_status == 200 and bool(demo_token),
    )

    plat_status, plat_token, _ = _login(opener, base_url, platform, credentials["SC_PATH_NS_PLATFORM_PASSWORD"])
    add(
        "dual_entry_auth",
        "platform_entry_admin_login_succeeds",
        {"status": 200, "token_present": True},
        {"status": plat_status, "token_length": len(plat_token)},
        plat_status == 200 and bool(plat_token),
    )

    add(
        "dual_entry_auth",
        "tokens_are_independent",
        True,
        {"distinct": bool(demo_token) and bool(plat_token) and demo_token != plat_token},
        bool(demo_token) and bool(plat_token) and demo_token != plat_token,
    )

    status, _, _ = _intent(opener, base_url, tenant, "app.nav", demo_token)
    add(
        "dual_entry_auth",
        "demo_token_accepted_on_demo_entry",
        200,
        status,
        status == 200,
    )

    status, _, _ = _intent(opener, base_url, platform, "app.nav", plat_token)
    add(
        "dual_entry_auth",
        "platform_token_accepted_on_platform_entry",
        200,
        status,
        status == 200,
    )

    # ---- group 3: bidirectional replay -----------------------------------
    status, _, raw = _intent(opener, base_url, platform, "app.nav", demo_token)
    add(
        "cross_namespace_replay",
        "demo_token_rejected_on_platform_entry",
        401,
        status,
        status == 401,
    )

    status, _, raw = _intent(opener, base_url, tenant, "app.nav", plat_token)
    add(
        "cross_namespace_replay",
        "platform_token_rejected_on_demo_entry",
        401,
        status,
        status == 401,
    )

    # ---- group 4: independent sessions and logout scope ------------------
    status, _, _ = _intent(opener, base_url, tenant, "auth.logout", demo_token)
    add(
        "session_logout",
        "demo_logout_succeeds",
        200,
        status,
        status == 200,
    )

    status, _, _ = _intent(opener, base_url, tenant, "app.nav", demo_token)
    add(
        "session_logout",
        "demo_token_invalid_after_demo_logout",
        401,
        status,
        status == 401,
    )

    status, _, _ = _intent(opener, base_url, platform, "app.nav", plat_token)
    add(
        "session_logout",
        "platform_token_survives_demo_logout",
        200,
        status,
        status == 200,
    )

    # ---- group 5: company boundary ---------------------------------------
    status, _, raw = _call(
        opener,
        base_url + tenant + "/api/v1/intent",
        method="POST",
        headers={"X-Anonymous-Intent": "1"},
        body={
            "intent": "login",
            "params": {"login": "admin", "password": credentials["SC_PATH_NS_TENANT_PASSWORD"], "company_id": 999},
        },
    )
    doc = _json(raw)
    error_code = (doc.get("error") or {}).get("code") if isinstance(doc.get("error"), dict) else doc.get("error")
    add(
        "company_boundary",
        "unauthorized_company_is_refused",
        {"status": 403, "error": "PERMISSION_DENIED"},
        {"status": status, "error": error_code},
        status == 403 and error_code == "PERMISSION_DENIED",
    )

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = len(checks) - passed
    return {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - started, 3),
        "target": {"base_url": base_url, "repo": repo, "expected_sha": expected_sha},
        "provenance": provenance,
        "summary": {
            "total": len(checks),
            "passed": passed,
            "failed": failed,
            "status": "PASS" if failed == 0 else "FAIL",
        },
        "checks": checks,
    }


def _run_remote(args):
    # Secrets travel only through SSH stdin, never command arguments or reports.
    values = _credentials()
    source = ("import os\nos.environ.update(" + repr(values) + ")\n"
              + "exec(compile(" + repr(Path(__file__).read_bytes()) + ", 'path_ns_c_acceptance.py', 'exec'))\n").encode()
    remote = [
        "python3",
        "-",
        "--base-url",
        args.base_url,
        "--emit-json",
    ]
    if args.repo:
        remote += ["--repo", args.repo]
    if args.expected_sha:
        remote += ["--expected-sha", args.expected_sha]
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPath=none",
            "-o",
            "BatchMode=yes",
            args.ssh_host,
            shlex.join(remote),
        ],
        input=source,
        capture_output=True,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        raise SystemExit(proc.returncode or 1)
    return proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace"), proc.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--ssh-host", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--json-out", default="")
    parser.add_argument("--emit-json", action="store_true")
    args = parser.parse_args()

    if args.ssh_host:
        text, err, code = _run_remote(args)
        report = json.loads(text)
        if code != 0:
            report["checks"].append({"group": "transport", "name": "remote_execution_succeeded",
                                     "expected": 0, "actual": code, "status": "fail"})
            report["summary"]["total"] += 1
            report["summary"]["failed"] += 1
            report["summary"]["status"] = "FAIL"
    else:
        report = run_checks(args.base_url, args.expected_sha, args.repo)
        code = 0 if report["summary"]["failed"] == 0 else 1

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(payload + "\n", encoding="utf-8")
    if args.emit_json:
        sys.stdout.write(payload + "\n")
    else:
        summary = report["summary"]
        sys.stdout.write(
            "[path-ns-c] %s total=%d passed=%d failed=%d\n"
            % (summary["status"], summary["total"], summary["passed"], summary["failed"])
        )
        for item in report["checks"]:
            if item["status"] != "pass":
                sys.stdout.write(
                    "  FAIL %s/%s expected=%s actual=%s\n"
                    % (item["group"], item["name"], item["expected"], item["actual"])
                )
    return 0 if code == 0 and report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
