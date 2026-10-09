#!/usr/bin/env python3
"""Couple the daily runtime's code face and published product face.

The daily runtime has two artifacts that were released by two separate lanes:
the code/rendering face (``daily.runtime.*``: bundle sync, module upgrade, served
revision, built frontend) and the published product face (the active
``sc.edition.release.snapshot`` that the navigation release gate actually reads).
Only the published face decides whether an entry may be opened. Because the two
lanes were independent, a locked-contract change could reach the served runtime
while the published face still froze the previous contract, and the gated
navigation then silently served the older contract: a declared, user-visible menu
entry disappeared although the contract, the product policy and the code all
declared it, and no deploy step failed.

This entry owns both faces in one governed sequence. It binds the exact candidate
revision that the remote tree must already be at, then runs the governed
``release.daily_product_navigation.converge`` on the remote runtime - re-freezing
every published product snapshot from the locked contract, reloading the served
runtime and re-running the release-gate guard - and accepts the run only when the
guard proved the contract, the product policy, the active snapshot, the gate and
the gated navigation agree on the declared product scope.

It rewrites no contract, policy, snapshot, environment file or credential by
itself, never touches ``main``, and never lowers the released assertion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
DEFAULT_ENV_NAME = "dev"
DEFAULT_ENV_FILE = ".env.dev"
DEFAULT_DATABASE = "sc_demo"
DEFAULT_PRODUCT_KEYS = "construction.standard,construction.preview"
CONFIRMATION = "REFRESH_DAILY_RUNTIME_PUBLISHED_FACE_FROM_LOCKED_CONTRACT"
SNAPSHOT_CONFIRMATION = "RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
LOGIN = re.compile(r"^[A-Za-z0-9@._-]+$")
PRODUCT_KEY = re.compile(r"^[a-z0-9._-]+$")
MODULE_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


class ConvergeError(RuntimeError):
    pass


REMOTE_CONVERGE = r'''
import fcntl, json, os, re, shutil, subprocess, sys
from pathlib import Path

expected_sha, env_name, env_file, database, login, product_keys_arg, modules_arg, reuse_ids_arg, remote_root = sys.argv[1:10]
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
full_sha = re.compile(r"^[0-9a-f]{40}$")
product_keys = [item for item in product_keys_arg.split(",") if item]
modules = [item for item in modules_arg.split(",") if item]

def emit(payload, code):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    raise SystemExit(code)

if root != fixed_root or not root.is_dir():
    emit({"status": "BLOCKED", "reason": "INVALID_REMOTE_REPOSITORY", "remote_root": str(root)}, 1)
if not full_sha.fullmatch(expected_sha):
    emit({"status": "BLOCKED", "reason": "INVALID_CANDIDATE_REVISION", "remote_root": str(root)}, 1)
if not login or not product_keys:
    emit({"status": "BLOCKED", "reason": "MISSING_PRINCIPAL_OR_PRODUCT_SCOPE", "remote_root": str(root)}, 1)

lock_path = Path("/run/lock/sc_daily-runtime-published-face.lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)
lock = open(str(lock_path), "w")
fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

head = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
).stdout.strip()
if head != expected_sha:
    emit(
        {
            "status": "BLOCKED",
            "reason": "REMOTE_HEAD_MISMATCH",
            "head": head,
            "expected_sha": expected_sha,
            "remote_root": str(root),
        },
        1,
    )

# The declared module-tree identity is only a *hint* from the caller: the remote
# re-resolves every declared module against its own tree and reuses the previous
# upgrade only when the code is byte-identical. A hint that does not match, an
# unresolved module, or any doubt falls back to running the upgrade.
declared_tree_ids = {}
for row in reuse_ids_arg.split(","):
    if not row.strip():
        continue
    name, _, oid = row.partition("=")
    name, oid = name.strip(), oid.strip()
    if not name or not full_sha.fullmatch(oid):
        declared_tree_ids = {}
        break
    declared_tree_ids[name] = oid

def module_tree_id(module):
    for base in ("addons", "odoo/addons"):
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", "HEAD:%s/%s" % (base, module)],
            cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if probe.returncode == 0 and full_sha.fullmatch(probe.stdout.strip()):
            return probe.stdout.strip()
    return ""

deployed_tree_ids = {module: module_tree_id(module) for module in modules}
reuse_upgrade = bool(
    modules
    and declared_tree_ids
    and sorted(declared_tree_ids) == sorted(modules)
    and all(deployed_tree_ids.get(module) == declared_tree_ids[module] for module in modules)
)
reuse_reason = (
    "deployed module tree is byte-identical to the last verified upgrade"
    if reuse_upgrade
    else "no matching verified module-tree identity; upgrade stays required"
)

env = dict(os.environ)
env.update(
    {
        "ENV": env_name,
        "ENV_FILE": env_file,
        "DB_NAME": database,
        "PRODUCT_MENU_CATALOG_FULL_PRODUCT_LOGIN": login,
        "PRODUCT_MENU_CATALOG_PRODUCT_KEYS": product_keys_arg,
        "CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT": "RELEASE_EXACT_DAILY_PRODUCT_NAVIGATION",
        # ``guard.codex.fast.upgrade`` refuses a module upgrade under CODEX_MODE=fast
        # unless the intent is declared.  This entry upgrades exactly the projection
        # modules whose code must be live before the face is frozen, so it declares
        # that intent the same way the governed ``make dev.mk`` upgrade wrappers do.
        "CODEX_NEED_UPGRADE": "1",
        "CODEX_MODULES": ",".join(modules),
    }
)
make_bin = shutil.which("make") or "/usr/bin/make"

# The published face is frozen *from* the locked contract through the module code
# that projects it, so the projection code must be live before the freeze: a face
# frozen from stale projection code silently publishes the previous contract.
upgrade_returncode = 0
upgrade_tail = ""
upgrade_mode = "skipped"
if reuse_upgrade:
    upgrade_mode = "reused"
elif modules:
    upgrade_mode = "run"
    upgrade = subprocess.run(
        [make_bin, "mod.upgrade", "MODULE=" + ",".join(modules)],
        cwd=str(root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    upgrade_returncode = int(upgrade.returncode)
    upgrade_tail = (upgrade.stdout or "")[-1500:]
    if upgrade_returncode:
        emit(
            {
                "status": "FAIL",
                "reason": "MODULE_UPGRADE_FAILED",
                "head": head,
                "modules": modules,
                "module_upgrade_returncode": upgrade_returncode,
                "module_upgrade_tail": upgrade_tail,
            },
            1,
        )

proc = subprocess.run(
    [make_bin, "release.daily_product_navigation.converge"],
    cwd=str(root),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)


def records(text):
    found = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            found.append(payload)
    return found


parsed = records(proc.stdout)
refreshes = {}
for record in parsed:
    if record.get("status") != "PASS" or "snapshot_menu_count" not in record:
        continue
    key = str(record.get("product_key") or "")
    if key:
        refreshes[key] = {
            "snapshot_id": int(record.get("snapshot_id") or 0),
            "policy_menu_count": int(record.get("policy_menu_count") or 0),
            "snapshot_menu_count": int(record.get("snapshot_menu_count") or 0),
            "changed": bool(record.get("changed")),
        }
guard = None
for record in reversed(parsed):
    if isinstance(record.get("products"), list):
        guard = record
        break

products = []
if isinstance(guard, dict):
    for item in guard.get("products") or []:
        if not isinstance(item, dict):
            continue
        products.append(
            {
                "product_key": str(item.get("product_key") or ""),
                "snapshot_id": int(item.get("snapshot_id") or 0),
                "snapshot_version": str(item.get("snapshot_version") or ""),
                "policy_released_menu_count": int(item.get("policy_released_menu_count") or 0),
                "snapshot_released_page_count": int(item.get("snapshot_released_page_count") or 0),
                "gate_page_count": int(item.get("gate_page_count") or 0),
            }
        )

declared = sorted(product_keys)
observed = sorted(row["product_key"] for row in products)
agreed = bool(products) and observed == declared and all(
    row["snapshot_id"] > 0
    and row["snapshot_version"]
    and row["snapshot_released_page_count"] > 0
    and row["snapshot_released_page_count"] == row["policy_released_menu_count"] == row["gate_page_count"]
    for row in products
)
guard_passed = bool(guard) and str(guard.get("status") or "") == "PASS"
if guard_passed and not agreed:
    reason = "PUBLISHED_FACE_SCOPE_DRIFT"
elif not guard:
    reason = "RELEASE_GATE_GUARD_NOT_REACHED"
elif not guard_passed:
    reason = "RELEASE_GATE_GUARD_NOT_PASS"
elif proc.returncode:
    reason = "CONVERGE_COMMAND_FAILED"
else:
    reason = ""
ok = guard_passed and agreed and proc.returncode == 0
emit(
    {
        "status": "PASS" if ok else "FAIL",
        "reason": reason,
        "expected_sha": expected_sha,
        "head": head,
        "remote_root": str(root),
        "product_keys": declared,
        "products": products,
        "refreshes": refreshes,
        "guard_status": str((guard or {}).get("status") or ""),
        "modules": modules,
        "upgrade_mode": upgrade_mode,
        "module_tree_ids": deployed_tree_ids,
        "upgrade_reuse_reason": reuse_reason,
        "module_upgrade_returncode": upgrade_returncode,
        "converge_returncode": int(proc.returncode),
        "converge_tail": (proc.stdout or "")[-1500:],
    },
    0 if ok else 1,
)
'''


MODULE_TREE_ROOTS = ("addons", "odoo/addons")


def module_tree_ids(repository: Path, expected_sha: str, modules: list[str]) -> dict[str, str] | None:
    """Git tree oid of every declared module at the exact deployed revision.

    A tree oid is the recursive content identity of the module directory, so two
    revisions that report the same tree oid carry byte-identical module code. Any
    module that cannot be resolved, or any git failure, returns None: an unprovable
    identity must upgrade rather than silently reuse.
    """
    if not modules:
        return {}
    resolved: dict[str, str] = {}
    for module in modules:
        for base in MODULE_TREE_ROOTS:
            probe = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "--verify", "-q", f"{expected_sha}:{base}/{module}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            oid = probe.stdout.decode("utf-8", "replace").strip() if probe.returncode == 0 else ""
            if FULL_SHA.fullmatch(oid):
                resolved[module] = oid
                break
        else:
            return None
    return resolved


def reuse_hint(
    report_path: str, database: str, modules: list[str], tree_ids: dict[str, str] | None
) -> dict[str, str]:
    """Declared module-tree identity from a previous verified face convergence.

    Reuse is only a candidate: the remote re-resolves the deployed trees and runs
    the upgrade unless they match. Anything unproven returns an empty hint.
    """
    if not modules or not tree_ids:
        return {}
    try:
        payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("status") != "PASS" or payload.get("guard_status") != "PASS":
        return {}
    if payload.get("remote_root") != REMOTE_ROOT or payload.get("database") != database:
        return {}
    if sorted(payload.get("upgrade_modules") or []) != sorted(modules):
        return {}
    if payload.get("module_tree_ids") != tree_ids:
        return {}
    return dict(tree_ids)


def parse_product_keys(raw: str) -> list[str]:
    keys = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if not keys or any(not PRODUCT_KEY.fullmatch(item) for item in keys):
        raise ConvergeError("product keys must be a non-empty comma-separated product key list")
    if len(set(keys)) != len(keys):
        raise ConvergeError("product keys must be unique")
    return keys


def parse_modules(raw: str) -> list[str]:
    modules = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if any(not MODULE_KEY.fullmatch(item) for item in modules):
        raise ConvergeError("upgrade modules must be a comma-separated module name list")
    if len(set(modules)) != len(modules):
        raise ConvergeError("upgrade modules must be unique")
    return modules


def preflight(
    expected_sha: str, ssh_host: str, login: str, product_keys: list[str], modules: list[str]
) -> None:
    if os.environ.get("CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE") != CONFIRMATION:
        raise ConvergeError("exact daily runtime published-face confirmation is required")
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise ConvergeError("expected revision must be a full lowercase commit SHA")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise ConvergeError("ssh host must be a configured host alias")
    if not LOGIN.fullmatch(login or ""):
        raise ConvergeError("the daily full-product principal must be a plain login")
    if not product_keys:
        raise ConvergeError("product keys must be a non-empty comma-separated product key list")
    if any(not MODULE_KEY.fullmatch(item) for item in modules):
        raise ConvergeError("upgrade modules must be a comma-separated module name list")


def remote_command(
    expected_sha: str,
    env_name: str,
    env_file: str,
    database: str,
    login: str,
    product_keys: list[str],
    modules: list[str],
    reuse_tree_ids: dict[str, str],
) -> str:
    return " ".join(
        shlex.quote(item)
        for item in (
            "python3",
            "-c",
            REMOTE_CONVERGE,
            expected_sha,
            env_name,
            env_file,
            database,
            login,
            ",".join(product_keys),
            ",".join(modules),
            ",".join(f"{module}={reuse_tree_ids[module]}" for module in sorted(reuse_tree_ids)),
            REMOTE_ROOT,
        )
    )


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def converge(
    expected_sha: str,
    ssh_host: str,
    env_name: str,
    env_file: str,
    database: str,
    login: str,
    product_keys: list[str],
    modules: list[str],
    reuse_tree_ids: dict[str, str] | None = None,
) -> dict[str, object]:
    preflight(expected_sha, ssh_host, login, product_keys, modules)
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=4",
        ssh_host,
        remote_command(expected_sha, env_name, env_file, database, login, product_keys, modules,
                       reuse_tree_ids or {}),
    ]
    result = run(command)
    stdout = result.stdout.decode(errors="replace")
    try:
        evidence = json.loads(stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        message = result.stderr.decode(errors="replace").strip() or stdout.strip()
        raise ConvergeError(f"daily runtime published-face evidence is invalid: {message[:1000]}") from exc
    if not isinstance(evidence, dict):
        raise ConvergeError("daily runtime published-face evidence is invalid")
    if evidence.get("status") != "PASS":
        tail = str(evidence.get("module_upgrade_tail") or "").strip()
        raise ConvergeError(
            "daily runtime published face did not converge: "
            f"{evidence.get('reason') or 'unknown'} (snapshot={evidence.get('products')})"
            + (f" module_upgrade_tail={tail[-800:]}" if tail else "")
        )
    if (
        evidence.get("expected_sha") != expected_sha
        or evidence.get("head") != expected_sha
        or evidence.get("remote_root") != REMOTE_ROOT
        or sorted(evidence.get("product_keys") or []) != sorted(product_keys)
        or evidence.get("guard_status") != "PASS"
        or sorted(evidence.get("modules") or []) != sorted(modules)
        or (modules and evidence.get("upgrade_mode") not in ("run", "reused"))
    ):
        raise ConvergeError("daily runtime published-face evidence differs from the declared scope")
    if modules:
        observed = evidence.get("module_tree_ids")
        if (
            not isinstance(observed, dict)
            or sorted(observed) != sorted(modules)
            or any(not FULL_SHA.fullmatch(str(value)) for value in observed.values())
        ):
            raise ConvergeError("daily runtime published-face evidence differs from the declared scope")
        if evidence.get("upgrade_mode") == "reused" and observed != (reuse_tree_ids or {}):
            # A remote may only claim reuse for the tree identity the caller declared.
            raise ConvergeError("daily runtime published-face reuse claim is unproven")
    for row in evidence.get("products") or []:
        if (
            int(row.get("snapshot_id") or 0) <= 0
            or not str(row.get("snapshot_version") or "")
            or int(row.get("snapshot_released_page_count") or 0) <= 0
            or int(row.get("snapshot_released_page_count") or 0)
            != int(row.get("policy_released_menu_count") or 0)
            or int(row.get("snapshot_released_page_count") or 0) != int(row.get("gate_page_count") or 0)
        ):
            raise ConvergeError("daily runtime published-face evidence differs from the declared scope")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True, help="exact candidate revision the remote tree must be at")
    parser.add_argument("--ssh-host", required=True, help="governed ssh host alias of the daily runtime")
    parser.add_argument("--login", required=True, help="daily full-product release-acceptance principal")
    parser.add_argument("--product-keys", default=DEFAULT_PRODUCT_KEYS, help="declared published product scope")
    parser.add_argument(
        "--upgrade-modules",
        default="",
        help="modules whose projection code must be live before the face is frozen (empty to skip)",
    )
    parser.add_argument("--env-name", default=DEFAULT_ENV_NAME)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--report", required=True, help="report path for the governed evidence envelope")
    parser.add_argument("--repository", default=".", help="local repository holding the exact candidate revision")
    parser.add_argument(
        "--force-upgrade",
        action="store_true",
        help="run the module upgrade even when the recorded module trees still match",
    )
    args = parser.parse_args()
    product_keys = parse_product_keys(args.product_keys)
    modules = parse_modules(args.upgrade_modules)
    tree_ids = module_tree_ids(Path(args.repository), args.expected_sha, modules)
    reuse_tree_ids = {} if args.force_upgrade else reuse_hint(args.report, args.database, modules, tree_ids)
    evidence = converge(
        args.expected_sha,
        args.ssh_host,
        args.env_name,
        args.env_file,
        args.database,
        args.login,
        product_keys,
        modules,
        reuse_tree_ids,
    )
    report = {
        "schema": "daily.runtime.published_face_converge.v1",
        "producer": "scripts/ops/daily_runtime_published_face_converge.py",
        "generated_by": "daily.runtime.published_face.converge",
        "confirmation": CONFIRMATION,
        "snapshot_confirmation": SNAPSHOT_CONFIRMATION,
        "expected_sha": args.expected_sha,
        "ssh_host": args.ssh_host,
        "login": args.login,
        "database": args.database,
        "product_keys": product_keys,
        "upgrade_modules": modules,
        **evidence,
    }
    target = Path(args.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "[daily.runtime.published_face.converge] PASS "
        f"sha={args.expected_sha[:12]} products={','.join(product_keys)} report={target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
