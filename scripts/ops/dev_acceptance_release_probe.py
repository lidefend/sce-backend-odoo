#!/usr/bin/env python3
"""Read-only probe for the dev acceptance release surface."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = ROOT / "artifacts" / "backend" / "dev_acceptance_release_probe.json"
DEFAULT_CONTRACT_DECLARATION = ROOT / "config" / "acceptance" / "backend_contract_instance_v1.json"
DEFAULT_SCHEMA_ASSET = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
CONTRACT_LIFECYCLE_PATH = ROOT / "addons/smart_core/core/contract_lifecycle.py"
CONTRACT_RESOLUTION_SCHEMA = "acceptance.record_identity_resolution.v1"
CONTRACT_RECEIPT_SCHEMA = "acceptance.backend_contract_receipt.v1"
CONTRACT_PASSWORD_ENV = "ACCEPTANCE_CONTRACT_PASSWORD"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _contract_credential(contract_password: str, login_password: str) -> str:
    """Resolve the contract account credential.

    The contract section authenticates as the declared contract account, which is
    a different identity from the login/navigation account. When no dedicated
    contract credential is declared the previous single-password behaviour is
    preserved.
    """
    return contract_password or login_password


def probe_runtime_identity(base_url: str, db_name: str, expected_sha: str, requester=None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "FAIL", "expected_sha": expected_sha}
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        result["errors"] = ["expected_sha_invalid"]
        return result
    request = requester or http_request
    status, body, _headers = request(f"{base_url.rstrip('/')}/api/runtime-version")
    result["http_status"] = status
    try:
        raw = json.loads(body)
        payload = raw.get("data") or raw.get("result") or raw
    except (json.JSONDecodeError, AttributeError):
        payload = {}
    served_sha = str(payload.get("git_sha") or payload.get("source_sha") or payload.get("source_revision") or "").strip()
    served_db = str(payload.get("database") or payload.get("db_name") or payload.get("db") or "").strip()
    result.update({"served_sha": served_sha, "served_database": served_db, "frontend_build_sha256": payload.get("frontend_build_sha256")})
    errors = []
    if status != 200:
        errors.append("runtime_identity_http_failed")
    if served_sha != expected_sha:
        errors.append("runtime_identity_sha_mismatch")
    if served_db and served_db != db_name:
        errors.append("runtime_identity_database_mismatch")
    result["errors"] = errors
    result["status"] = "PASS" if not errors else "FAIL"
    return result


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


def http_request(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    cookie_jar: CookieJar | None = None,
    timeout: int = 20,
) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar)) if cookie_jar else None
    try:
        with (opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers)


def find_one(directory: Path, patterns: list[str]) -> Path | None:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(directory.glob(pattern))
    matches = [p for p in matches if p.is_file()]
    return max(matches, key=lambda p: p.stat().st_mtime) if matches else None


def probe_backup(directory: Path | None, db_name: str) -> dict[str, Any]:
    if not directory:
        return {"enabled": False}
    result: dict[str, Any] = {"enabled": True, "dir": str(directory), "status": "PASS", "checks": {}}
    errors: list[str] = []
    if not directory.is_dir():
        return {"enabled": True, "dir": str(directory), "status": "FAIL", "errors": ["backup_dir_missing"]}

    checksum = directory / "SHA256SUMS"
    if checksum.exists():
        rc, out = run_cmd(["sha256sum", "-c", str(checksum.name)], cwd=directory)
        result["checks"]["sha256"] = {"rc": rc, "output": out.strip()}
        if rc != 0:
            errors.append("sha256_check_failed")
    else:
        errors.append("sha256sums_missing")

    dump = find_one(directory, [f"{db_name}_*.dump", "*.dump"])
    filestore = find_one(directory, [f"{db_name}_filestore_*.tgz", "*filestore*.tgz", "*.tar.gz"])
    result["dump"] = str(dump) if dump else None
    result["filestore"] = str(filestore) if filestore else None
    if not dump:
        errors.append("dump_missing")
    if not filestore:
        errors.append("filestore_archive_missing")

    if dump:
        rc, out = run_cmd(["pg_restore", "-l", str(dump)])
        db_match = re.search(r"dbname:\s*(\S+)", out)
        result["checks"]["pg_restore_list"] = {
            "rc": rc,
            "dbname": db_match.group(1) if db_match else None,
            "toc_entries": len(out.splitlines()),
        }
        if rc != 0:
            errors.append("pg_restore_list_failed")
        if db_match and db_match.group(1) != db_name:
            errors.append("dump_db_mismatch")

        rc, out = run_cmd(["pg_restore", "-f", "-", "--data-only", "-t", "ir_config_parameter", str(dump)])
        uuid_match = re.search(r"\tdatabase\.uuid\t([^\t\n]+)", out)
        result["checks"]["dump_database_uuid"] = uuid_match.group(1) if uuid_match else None
        if rc != 0:
            errors.append("dump_config_extract_failed")

    if filestore:
        try:
            with tarfile.open(filestore, "r:*") as archive:
                names = archive.getnames()[:2000]
            result["checks"]["filestore_prefix_present"] = any(name == db_name or name.startswith(f"{db_name}/") for name in names)
            result["checks"]["filestore_sample_entries"] = len(names)
            if not result["checks"]["filestore_prefix_present"]:
                errors.append("filestore_db_prefix_missing")
        except tarfile.TarError as exc:
            result["checks"]["filestore_error"] = str(exc)
            errors.append("filestore_archive_invalid")

    if errors:
        result["status"] = "FAIL"
        result["errors"] = errors
    return result


def probe_frontend(base_url: str, db_name: str, app_env: str, forbidden_db: str) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "PASS", "base_url": base_url, "checks": {}}
    errors: list[str] = []
    status, body, headers = http_request(base_url.rstrip("/") + "/")
    result["checks"]["root_status"] = status
    result["checks"]["root_content_type"] = headers.get("Content-Type")
    if status != 200:
        errors.append("root_not_200")
    asset_match = re.search(r'<script[^>]+src="([^"]+index-[^"]+\.js)"', body)
    asset_path = asset_match.group(1) if asset_match else None
    result["checks"]["asset_path"] = asset_path
    if not asset_path:
        errors.append("frontend_asset_missing")
    else:
        asset_url = base_url.rstrip("/") + asset_path
        asset_status, asset_body, _asset_headers = http_request(asset_url)
        default_env_match = re.search(r'const\s+\w+="([^"]+)"\.trim\(\)\|\|"default"', asset_body)
        forbidden_default_db = (
            re.search(rf'const\s+\w+="{re.escape(forbidden_db)}"', asset_body) is not None if forbidden_db else False
        )
        result["checks"]["asset_status"] = asset_status
        result["checks"]["asset_has_db"] = db_name in asset_body
        result["checks"]["asset_has_app_env"] = f'"{app_env}"' in asset_body or app_env in asset_body
        result["checks"]["asset_default_app_env"] = default_env_match.group(1) if default_env_match else None
        result["checks"]["asset_has_forbidden_db_token"] = forbidden_db in asset_body if forbidden_db else False
        result["checks"]["asset_forbidden_db_is_default"] = forbidden_default_db
        if asset_status != 200:
            errors.append("frontend_asset_not_200")
        if db_name not in asset_body:
            errors.append("frontend_db_token_missing")
        if default_env_match and default_env_match.group(1) != app_env:
            errors.append("frontend_default_app_env_mismatch")
        if forbidden_default_db:
            errors.append("frontend_forbidden_db_is_default")

    options_status, _options_body, _options_headers = http_request(
        base_url.rstrip("/") + f"/api/v1/intent?db={db_name}",
        method="OPTIONS",
        headers={"X-Odoo-DB": db_name, "X-DB": db_name},
    )
    get_status, _get_body, _get_headers = http_request(
        base_url.rstrip("/") + f"/api/v1/intent?db={db_name}",
        headers={"X-Odoo-DB": db_name, "X-DB": db_name},
    )
    result["checks"]["intent_options_status"] = options_status
    result["checks"]["intent_get_status"] = get_status
    if options_status != 204:
        errors.append("intent_options_not_204")
    if get_status != 405:
        errors.append("intent_get_not_405")

    if errors:
        result["status"] = "FAIL"
        result["errors"] = errors
    return result


def _node_label(node: dict[str, Any]) -> str:
    return str(node.get("label") or node.get("title") or node.get("name") or node.get("display_name") or "").strip()


def _node_action_id(node: dict[str, Any]) -> Any:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    target = node.get("target") if isinstance(node.get("target"), dict) else {}
    action = node.get("action") if isinstance(node.get("action"), dict) else {}
    return node.get("action_id") or meta.get("action_id") or target.get("action_id") or action.get("id") or action.get("action_id")


def _walk_nav(nodes: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(nodes, list):
        return rows
    for node in nodes:
        if not isinstance(node, dict):
            continue
        label = _node_label(node)
        current = path + ((label,) if label else ())
        children = node.get("children") if isinstance(node.get("children"), list) else []
        rows.append(
            {
                "path": " / ".join(current),
                "label": label,
                "action_id": _node_action_id(node),
                "child_count": len(children),
            }
        )
        rows.extend(_walk_nav(children, current))
    return rows


def _int_env(value: str) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _parse_required_actions(value: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in str(value or "").split("|"):
        raw = item.strip()
        if not raw:
            continue
        if "=>" not in raw:
            continue
        path, action_id = raw.rsplit("=>", 1)
        path = path.strip()
        try:
            out[path] = int(action_id.strip())
        except ValueError:
            continue
    return out


def probe_login(
    base_url: str,
    db_name: str,
    login: str,
    password: str,
    nav_min_actions: int | None = None,
    nav_max_actions: int | None = None,
    nav_forbidden_labels: list[str] | None = None,
    nav_required_paths: list[str] | None = None,
    nav_required_actions: dict[str, int] | None = None,
    expected_role_code: str | None = None,
) -> dict[str, Any]:
    if not login or not password:
        return {"enabled": False}
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    headers = {"Content-Type": "application/json", "X-Odoo-DB": db_name, "X-DB": db_name}
    payload = json.dumps(
        {"jsonrpc": "2.0", "params": {"db": db_name, "login": login, "password": password}}
    ).encode("utf-8")
    auth_req = urllib.request.Request(
        base_url.rstrip("/") + "/web/session/authenticate",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with opener.open(auth_req, timeout=20) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    result: dict[str, Any] = {"enabled": True, "status": "PASS", "login": login, "checks": {"auth_status": status}}
    errors: list[str] = []
    try:
        auth = json.loads(body)
    except json.JSONDecodeError:
        auth = {"error": "invalid_json", "raw": body[:300]}
    auth_result = auth.get("result") if isinstance(auth, dict) else None
    result["checks"]["auth_uid"] = auth_result.get("uid") if isinstance(auth_result, dict) else None
    result["checks"]["auth_name"] = auth_result.get("name") if isinstance(auth_result, dict) else None
    if status != 200 or not result["checks"]["auth_uid"]:
        errors.append("auth_failed")

    init_payload = json.dumps({"intent": "system.init", "params": {}}).encode("utf-8")
    init_req = urllib.request.Request(
        base_url.rstrip("/") + f"/api/v1/intent?db={db_name}",
        data=init_payload,
        headers=headers,
        method="POST",
    )
    try:
        with opener.open(init_req, timeout=20) as resp:
            init_status = resp.status
            init_body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        init_status = exc.code
        init_body = exc.read().decode("utf-8", errors="replace")
    result["checks"]["system_init_status"] = init_status
    try:
        init = json.loads(init_body)
    except json.JSONDecodeError:
        init = {"error": "invalid_json", "raw": init_body[:300]}
    result["checks"]["system_init_ok"] = bool(init.get("ok")) if isinstance(init, dict) else False
    data = init.get("data") if isinstance(init, dict) else None
    if isinstance(data, dict):
        role = data.get("role_surface") or {}
        result["checks"]["role_code"] = role.get("role_code") if isinstance(role, dict) else data.get("role_code")
        navigation = data.get("navigation")
        nav = navigation.get("nav") if isinstance(navigation, dict) else None
        if not isinstance(nav, list):
            errors.append("canonical_navigation_nav_missing_or_invalid")
            nav = []
        result["checks"]["nav_count"] = len(nav) if isinstance(nav, list) else None
        nav_rows = _walk_nav(nav)
        forbidden_labels = nav_forbidden_labels or []
        required_paths = nav_required_paths or []
        required_actions = nav_required_actions or {}
        nav_path_set = {row["path"] for row in nav_rows}
        nav_action_by_path = {row["path"]: row.get("action_id") for row in nav_rows}
        forbidden_hits = [
            row["path"]
            for row in nav_rows
            if any(token in row["path"] for token in forbidden_labels)
        ]
        required_path_misses = [path for path in required_paths if path not in nav_path_set]
        required_action_mismatches = [
            {
                "path": path,
                "expected_action_id": expected,
                "actual_action_id": nav_action_by_path.get(path),
            }
            for path, expected in required_actions.items()
            if nav_action_by_path.get(path) != expected
        ]
        result["checks"]["nav_node_count"] = len(nav_rows)
        result["checks"]["nav_action_count"] = sum(1 for row in nav_rows if row.get("action_id"))
        result["checks"]["nav_leaf_count"] = sum(1 for row in nav_rows if row.get("child_count") == 0)
        result["checks"]["nav_forbidden_label_hits"] = forbidden_hits[:50]
        result["checks"]["nav_required_path_misses"] = required_path_misses
        result["checks"]["nav_required_action_mismatches"] = required_action_mismatches
        result["checks"]["nav_paths_sample"] = [row["path"] for row in nav_rows[:80]]
        if not result["checks"]["role_code"]:
            errors.append("role_code_missing")
        # Contract-driven acceptance: the menu count is only determinate for a
        # locked role, so a runtime identity that drifts away from the declared
        # principal role must fail rather than be silently measured against the
        # wrong locked surface.
        if expected_role_code:
            result["checks"]["role_code_expected"] = expected_role_code
            if result["checks"]["role_code"] != expected_role_code:
                errors.append("role_code_unexpected")
        if result["checks"]["nav_node_count"] <= 0:
            errors.append("nav_empty")
        if result["checks"]["nav_action_count"] <= 0:
            errors.append("nav_action_empty")
        if nav_min_actions is not None and result["checks"]["nav_action_count"] < nav_min_actions:
            errors.append("nav_action_count_below_min")
        if nav_max_actions is not None and result["checks"]["nav_action_count"] > nav_max_actions:
            errors.append("nav_action_count_above_max")
        if forbidden_hits:
            errors.append("nav_forbidden_label_hits")
        if required_path_misses:
            errors.append("nav_required_path_misses")
        if required_action_mismatches:
            errors.append("nav_required_action_mismatches")
    if not isinstance(data, dict):
        errors.append("canonical_navigation_nav_missing_or_invalid")
    if init_status != 200 or not result["checks"]["system_init_ok"]:
        errors.append("system_init_failed")

    if errors:
        result["status"] = "FAIL"
        result["errors"] = errors
    return result


def load_contract_lifecycle(path: Path | None = None):
    """Reuse the producer integrity protocol; never re-implement its hashing."""
    target = Path(path) if path else CONTRACT_LIFECYCLE_PATH
    spec = importlib.util.spec_from_file_location("acceptance_contract_lifecycle", target)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load contract lifecycle module: {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_acceptance_declaration(declaration: Any) -> list[str]:
    """Shape-check the declared exact-instance acceptance scope."""
    errors: list[str] = []
    if not isinstance(declaration, dict):
        return ["contract_declaration_not_object"]
    if declaration.get("schema") != "acceptance.backend_contract_instance.v1":
        errors.append("contract_declaration_schema_unknown")
    account = declaration.get("account")
    if not isinstance(account, dict) or not all(
        isinstance(account.get(key), str) and account.get(key) for key in ("login", "role_code", "company_name")
    ):
        errors.append("contract_declaration_account_incomplete")
    resolution = declaration.get("resolution")
    if not isinstance(resolution, dict) or not all(
        isinstance(resolution.get(key), str) and resolution.get(key)
        for key in ("governed_producer", "producer_output_key", "target_key", "company_key", "stable_identifier_field")
    ):
        errors.append("contract_declaration_resolution_incomplete")
    request_decl = declaration.get("request")
    if not isinstance(request_decl, dict) or not all(
        isinstance(request_decl.get(key), str) and request_decl.get(key)
        for key in ("intent", "view_type", "delivery_profile", "client_type")
    ):
        errors.append("contract_declaration_request_incomplete")
    elif not isinstance(request_decl.get("accepted_contract_versions"), list) or not isinstance(
        request_decl.get("client_contract_capabilities"), list
    ):
        errors.append("contract_declaration_request_capabilities_invalid")
    elif not isinstance(request_decl.get("context"), dict) or not all(
        isinstance(request_decl["context"].get(key), str) and request_decl["context"].get(key)
        for key in ("lang", "tz")
    ):
        # The sealed contract echoes the localized projection, so the declared
        # request must state the context that produced the approved digest;
        # otherwise the recorded request could not be replayed verbatim.
        errors.append("contract_declaration_request_context_invalid")
    required = declaration.get("required_checks")
    if not isinstance(required, list) or not required or not all(isinstance(item, str) and item for item in required):
        errors.append("contract_declaration_required_checks_invalid")
    if not isinstance(declaration.get("schema_asset"), str) or not declaration.get("schema_asset"):
        errors.append("contract_declaration_schema_asset_missing")
    return errors


def load_acceptance_declaration(path: Path | None) -> tuple[dict[str, Any] | None, list[str]]:
    """Load the declared scope and refuse an unusable declaration."""
    if not path:
        return None, ["contract_declaration_path_missing"]
    source = Path(path)
    if not source.is_file():
        return None, ["contract_declaration_missing"]
    try:
        declaration = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, ["contract_declaration_invalid_json"]
    errors = validate_acceptance_declaration(declaration)
    return (declaration if not errors else None), errors


def load_record_resolution(path: Path | None, declaration: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Consume the governed fixture resolution; never send a record id of our own."""
    errors: list[str] = []
    if not path:
        return None, ["record_resolution_path_missing"]
    source = Path(path)
    if not source.is_file():
        return None, ["record_resolution_missing"]
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, ["record_resolution_invalid_json"]
    if not isinstance(payload, dict):
        return None, ["record_resolution_not_object"]
    if payload.get("schema") != CONTRACT_RESOLUTION_SCHEMA:
        errors.append("record_resolution_schema_unknown")
    declared_producer = (declaration.get("resolution") or {}).get("governed_producer")
    if payload.get("producer") != declared_producer:
        errors.append("record_resolution_producer_mismatch")
    targets = payload.get("targets")
    if not isinstance(targets, dict):
        errors.append("record_resolution_targets_missing")
    else:
        resolution_decl = declaration.get("resolution") or {}
        target = targets.get(resolution_decl.get("target_key"))
        companies = targets.get("companies")
        if not isinstance(target, dict):
            errors.append("record_resolution_target_key_missing")
        else:
            if not isinstance(target.get("model"), str) or not target.get("model"):
                errors.append("record_resolution_target_model_invalid")
            for key in ("action_id", "menu_id", "record_id"):
                if not isinstance(target.get(key), int) or isinstance(target.get(key), bool) or target.get(key) <= 0:
                    errors.append(f"record_resolution_target_{key}_invalid")
            stable_field = resolution_decl.get("stable_identifier_field")
            if not isinstance(target.get(stable_field), str) or not target.get(stable_field):
                errors.append("record_resolution_stable_identifier_missing")
        if not isinstance(companies, dict) or not isinstance(companies.get(resolution_decl.get("company_key")), int):
            errors.append("record_resolution_company_missing")
    return (payload if not errors else None), errors


class _HttpSession:
    """Minimal authenticated JSON session against the governed acceptance backend."""

    def __init__(self, base_url: str, db_name: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.db_name = db_name
        self.timeout = timeout
        self._jar = CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))

    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, str]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Odoo-DB": self.db_name, "X-DB": self.db_name},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return response.status, response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            return 0, json.dumps({"transport_error": str(exc)})


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _relative_to_root(path: Path) -> str:
    """Report an evidence path relative to the repo when it lives inside it."""
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return resolved.relative_to(root).as_posix()
    return str(resolved)


_STABLE_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*\Z")


def _resolution_target_is_unique(
    resolution: dict[str, Any],
    declaration_resolution: dict[str, Any],
    target: dict[str, Any],
    company_id: Any,
) -> tuple[bool, dict[str, Any]]:
    """Prove the resolved target is the declaration's unique stable identifier.

    The declaration requires a unique match, so the receipt must carry evidence,
    not just the resolved id: the identifier must be a governed fixture external
    id (unique by construction through env.ref) and the target keys must be
    complete.

    Uniqueness is a property of the resolved identity, not of the alias count.
    The governed resolver exposes the same record under several target keys (a
    business alias plus its journey alias), so several aliases may claim one
    (model, record_id) pair only while every alias carries the same stable
    identifier, and one stable identifier must resolve to exactly that one pair.
    Ambiguity is a pair claimed by two distinct identifiers, or an identifier
    spread across two pairs.
    """
    field = str(declaration_resolution.get("stable_identifier_field") or "")
    stable_identifier = target.get(field)
    targets = resolution.get("targets") if isinstance(resolution.get("targets"), dict) else {}
    target_pair = (target.get("model"), target.get("record_id"))
    identifiers_by_pair: dict[tuple[Any, Any], set[str]] = {}
    pairs_by_identifier: dict[str, set[tuple[Any, Any]]] = {}
    claiming_targets: list[dict[str, Any]] = []
    for item in targets.values():
        if not isinstance(item, dict) or not item.get(field):
            continue
        identifier = str(item.get(field))
        pair = (item.get("model"), item.get("record_id"))
        identifiers_by_pair.setdefault(pair, set()).add(identifier)
        pairs_by_identifier.setdefault(identifier, set()).add(pair)
        if pair == target_pair:
            claiming_targets.append(item)
    identifier = str(stable_identifier) if isinstance(stable_identifier, str) else ""
    competing_identifiers = sorted(identifiers_by_pair.get(target_pair, set()) - {identifier})
    identifier_pairs = pairs_by_identifier.get(identifier, set())
    producer_matches = str(resolution.get("producer") or "") == str(
        declaration_resolution.get("governed_producer") or ""
    )
    unique = bool(
        isinstance(stable_identifier, str)
        and _STABLE_IDENTIFIER_RE.fullmatch(stable_identifier)
        and isinstance(target.get("record_id"), int)
        and target.get("record_id") > 0
        and isinstance(target.get("action_id"), int)
        and target.get("action_id") > 0
        and isinstance(target.get("menu_id"), int)
        and target.get("menu_id") > 0
        and isinstance(company_id, int)
        and bool(declaration_resolution.get("requires_unique_match"))
        and producer_matches
        and len(claiming_targets) >= 1
        and not competing_identifiers
        and identifier_pairs == {target_pair}
    )
    return unique, {
        "stable_identifier": stable_identifier,
        "record_xmlid": target.get("record_xmlid"),
        "record_id": target.get("record_id"),
        "model": target.get("model"),
        "action_id": target.get("action_id"),
        "menu_id": target.get("menu_id"),
        "company_id": company_id,
        "company_key": declaration_resolution.get("company_key"),
        "governed_producer": declaration_resolution.get("governed_producer"),
        "resolved_producer": resolution.get("producer"),
        "requires_unique_match": bool(declaration_resolution.get("requires_unique_match")),
        "matching_resolved_targets": len(claiming_targets),
        "distinct_claiming_identifiers": len(identifiers_by_pair.get(target_pair, set())),
        "competing_identifiers": competing_identifiers,
        "identifier_resolved_pairs": len(identifier_pairs),
    }


def probe_contract_acceptance(
    base_url: str,
    db_name: str,
    declaration: dict[str, Any] | None,
    resolution: dict[str, Any] | None,
    *,
    served_sha: str = "",
    expected_sha: str = "",
    declaration_errors: list[str] | None = None,
    resolution_errors: list[str] | None = None,
    schema_path: Path | None = None,
    lifecycle: Any = None,
    session: Any = None,
    password: str = "",
    contract_output: Path | None = None,
) -> dict[str, Any]:
    """Produce the exact-instance backend contract receipt, fail-closed on any gap."""
    receipt: dict[str, Any] = {"schema": CONTRACT_RECEIPT_SCHEMA, "enabled": True, "status": "FAIL", "errors": []}
    if declaration is None:
        receipt["status"] = "FAIL"
        receipt["errors"] = declaration_errors or ["contract_declaration_unavailable"]
        return receipt

    required_checks = list(declaration.get("required_checks") or [])
    # A check is present only once it was actually evaluated; an absent key is
    # "not evaluated", never a silent False, so executed/not_run stay truthful.
    checks: dict[str, bool] = {}
    detail: dict[str, Any] = {}
    shape_errors = validate_acceptance_declaration(declaration)
    errors: list[str] = list(declaration_errors or []) + shape_errors + list(resolution_errors or [])
    if resolution is None and not resolution_errors:
        errors.append("record_resolution_unavailable")
    errors = list(dict.fromkeys(errors))
    if shape_errors or resolution is None:
        receipt.update(
            {
                "required_checks": required_checks,
                "executed_checks": [],
                "not_run_checks": list(required_checks),
                "checks": checks,
                "check_detail": detail,
                "errors": errors,
            }
        )
        return receipt

    account = declaration.get("account") or {}
    declaration_resolution = declaration.get("resolution") or {}
    request_decl = declaration.get("request") or {}
    declared_asset = Path(declaration["schema_asset"])
    asset = Path(schema_path) if schema_path else (declared_asset if declared_asset.is_absolute() else ROOT / declared_asset)

    target: dict[str, Any] = {}
    if isinstance(resolution, dict):
        targets = resolution.get("targets") or {}
        candidate = targets.get(declaration_resolution.get("target_key"))
        target = candidate if isinstance(candidate, dict) else {}
        companies = targets.get("companies") or {}
        company_id = companies.get(declaration_resolution.get("company_key"))
    else:
        company_id = None

    # --- provenance and custody-bound identity ---------------------------------
    checks["identity_deployed_sha"] = bool(
        re.fullmatch(r"[0-9a-f]{40}", served_sha or "") and served_sha == expected_sha
    )
    detail["identity_deployed_sha"] = {"served_sha": served_sha, "expected_sha": expected_sha}
    if not checks["identity_deployed_sha"]:
        errors.append("identity_deployed_sha_mismatch")

    if isinstance(resolution, dict):
        resolution_sha = str(resolution.get("expected_sha") or "")
        unique, unique_detail = _resolution_target_is_unique(
            resolution, declaration_resolution, target, company_id
        )
        checks["resolution_unique_target"] = bool(resolution_sha == served_sha and unique)
        if resolution_sha != served_sha:
            errors.append("record_resolution_served_sha_mismatch")
        if not unique:
            errors.append("record_resolution_not_unique")
        detail["resolution_unique_target"] = {
            **unique_detail,
            "resolved_sha": resolution_sha,
            "expected_sha": served_sha,
        }

    # --- schema digest binding --------------------------------------------------
    if not asset.is_file():
        errors.append("contract_schema_asset_missing")
        checks["contract_schema_digest_bound"] = False
        declared_schema_sha = ""
    else:
        declared_schema_sha = _hash_bytes(asset.read_bytes())

    # --- live instance ----------------------------------------------------------
    session = session or _HttpSession(base_url, db_name)
    status, body = session.post(
        "/web/session/authenticate",
        {"jsonrpc": "2.0", "params": {"db": db_name, "login": account.get("login"), "password": password}},
    )
    try:
        auth = json.loads(body)
    except json.JSONDecodeError:
        auth = {}
    auth_result = auth.get("result") if isinstance(auth, dict) else None
    uid = auth_result.get("uid") if isinstance(auth_result, dict) else None
    if status != 200 or not isinstance(uid, int):
        errors.append("contract_probe_auth_failed")
        receipt.update(
            {
                "required_checks": required_checks,
                "executed_checks": [name for name in required_checks if name in checks],
                "not_run_checks": [name for name in required_checks if name not in checks],
                "checks": checks,
                "check_detail": detail,
                "errors": errors,
                "identity": {"served_sha": served_sha, "expected_sha": expected_sha},
            }
        )
        return receipt

    init_status, init_body = session.post("/api/v1/intent?db=" + db_name, {"intent": "system.init", "params": {}})
    try:
        init = json.loads(init_body)
    except json.JSONDecodeError:
        init = {}
    init_data = init.get("data") if isinstance(init, dict) else None
    init_data = init_data if isinstance(init_data, dict) else {}
    user = init_data.get("user") if isinstance(init_data.get("user"), dict) else {}
    role_surface = init_data.get("role_surface") if isinstance(init_data.get("role_surface"), dict) else {}

    checks["identity_actor_uid"] = bool(isinstance(user.get("id"), int) and user.get("id") == uid)
    checks["identity_role_code"] = bool(
        isinstance(role_surface.get("role_code"), str) and role_surface.get("role_code") == account.get("role_code")
    )
    checks["identity_company"] = bool(
        isinstance(user.get("company_name"), str) and user.get("company_name") == account.get("company_name")
    )
    for check, code in (
        ("identity_actor_uid", "identity_actor_uid_mismatch"),
        ("identity_role_code", "identity_role_code_mismatch"),
        ("identity_company", "identity_company_mismatch"),
    ):
        if not checks[check]:
            errors.append(code)
    detail["identity"] = {
        "uid": uid,
        "user_id": user.get("id"),
        "login": account.get("login"),
        "role_code": role_surface.get("role_code"),
        "company_id": user.get("company_id"),
        "company_name": user.get("company_name"),
        "allowed_company_ids": user.get("allowed_company_ids"),
        "init_status": init_status,
    }

    params: dict[str, Any] = {
        "op": "model",
        "model": target.get("model"),
        "view_type": request_decl.get("view_type"),
        "record_id": target.get("record_id"),
        "action_id": target.get("action_id"),
        "menu_id": target.get("menu_id"),
        "delivery_profile": request_decl.get("delivery_profile"),
        "client_type": request_decl.get("client_type"),
        "accepted_contract_versions": list(request_decl.get("accepted_contract_versions") or []),
        "client_contract_capabilities": list(request_decl.get("client_contract_capabilities") or []),
    }
    request_context = {
        str(key): value
        for key, value in (request_decl.get("context") or {}).items()
        if isinstance(value, str) and value
    }
    request_payload: dict[str, Any] = {"intent": request_decl.get("intent"), "params": params}
    if request_context:
        request_payload["context"] = request_context
    contract_status, contract_body = session.post(
        "/api/v1/intent?db=" + db_name,
        request_payload,
    )
    try:
        envelope = json.loads(contract_body)
    except json.JSONDecodeError:
        envelope = {}
    contract = envelope.get("data") if isinstance(envelope, dict) else None
    contract = contract if isinstance(contract, dict) else {}
    page_info = contract.get("pageInfo") if isinstance(contract.get("pageInfo"), dict) else {}

    checks["request_target_binding"] = bool(
        contract_status == 200
        and isinstance(envelope, dict)
        and envelope.get("ok") is True
        and page_info.get("model") == target.get("model")
        and page_info.get("viewType") == request_decl.get("view_type")
        and page_info.get("pageId")
        and isinstance(target.get("record_id"), int)
    )
    if not checks["request_target_binding"]:
        errors.append("request_target_binding_mismatch")

    checks["contract_custody_captured"] = bool(contract_body) and bool(contract)
    if not checks["contract_custody_captured"]:
        errors.append("contract_custody_not_captured")

    # Offline custody: persist the exact live response bytes and read them back, so
    # an independent verifier can reproduce response_sha256 without the runtime and
    # re-derive the whole contract from the bytes rather than from a re-serialization.
    contract_bytes = contract_body.encode("utf-8")
    custody_path = ""
    if contract_output is not None and checks["contract_custody_captured"]:
        target_output = Path(contract_output)
        target_output.parent.mkdir(parents=True, exist_ok=True)
        target_output.write_bytes(contract_bytes)
        checks["contract_custody_bytes_persisted"] = target_output.read_bytes() == contract_bytes
        custody_path = _relative_to_root(target_output)
    else:
        checks["contract_custody_bytes_persisted"] = False
    if checks["contract_custody_captured"] and not checks["contract_custody_bytes_persisted"]:
        errors.append("contract_custody_bytes_not_persisted")

    lifecycle = lifecycle or load_contract_lifecycle()
    meta = contract.get("meta") if isinstance(contract.get("meta"), dict) else {}
    lifecycle_evidence = meta.get("lifecycle") if isinstance(meta.get("lifecycle"), dict) else {}
    definition = lifecycle_evidence.get("definition") if isinstance(lifecycle_evidence.get("definition"), dict) else {}
    integrity = lifecycle_evidence.get("integrity") if isinstance(lifecycle_evidence.get("integrity"), dict) else {}
    approved_semantic_sha = str(integrity.get("contractSha256") or "")
    recomputed_semantic_sha = (
        lifecycle.payload_sha256(lifecycle.contract_semantic_payload(contract)) if contract else ""
    )
    valid, reason = (
        lifecycle.verify_unified_page_contract_integrity(contract) if contract else (False, "contract_absent")
    )
    checks["contract_integrity_self_consistent"] = bool(valid) and approved_semantic_sha == recomputed_semantic_sha
    if not checks["contract_integrity_self_consistent"]:
        errors.append("contract_integrity_self_inconsistent")

    checks["contract_schema_digest_bound"] = bool(
        declared_schema_sha and str(definition.get("schemaSha256") or "") == declared_schema_sha
    )
    if not checks["contract_schema_digest_bound"]:
        errors.append("contract_schema_digest_not_bound")

    schema_errors: list[str] = []
    if contract:
        try:
            from jsonschema import Draft202012Validator

            validator = Draft202012Validator(json.loads(asset.read_text(encoding="utf-8")))
            schema_errors = [
                "$." + ".".join(str(item) for item in issue.absolute_path)
                for issue in sorted(validator.iter_errors(contract), key=lambda item: list(item.absolute_path))
            ]
        except Exception as exc:  # noqa: BLE001 - report the failure, never mask it
            schema_errors = [f"validator_error:{exc}"]
    else:
        schema_errors = ["contract_absent"]
    checks["contract_formal_schema_valid"] = bool(contract) and not schema_errors
    if not checks["contract_formal_schema_valid"]:
        errors.append("contract_formal_schema_invalid")

    executed = [name for name in required_checks if name in checks]
    not_run = [name for name in required_checks if name not in checks]
    # PASS requires every declared check to have been evaluated True; an
    # unevaluated required check is a failure, never an implicit pass.
    all_passed = bool(required_checks) and all(name in checks and checks[name] is True for name in required_checks)

    receipt.update(
        {
            "status": "PASS" if (all_passed and not errors) else "FAIL",
            "required_checks": required_checks,
            "executed_checks": executed,
            "not_run_checks": not_run,
            "checks": checks,
            "check_detail": detail,
            "identity": {
                "served_sha": served_sha,
                "expected_sha": expected_sha,
                "uid": uid,
                "login": account.get("login"),
                "role_code": role_surface.get("role_code"),
                "company_id": user.get("company_id"),
                "company_name": user.get("company_name"),
                "allowed_company_ids": user.get("allowed_company_ids"),
            },
            "resolution": {
                "governed_producer": resolution.get("producer") if isinstance(resolution, dict) else None,
                "target_key": declaration_resolution.get("target_key"),
                "company_key": declaration_resolution.get("company_key"),
                "company_id": company_id,
                "stable_identifier": target.get(declaration_resolution.get("stable_identifier_field")),
                "model": target.get("model"),
                "action_id": target.get("action_id"),
                "menu_id": target.get("menu_id"),
                "record_id": target.get("record_id"),
            },
            "request": {
                "url_path": "/api/v1/intent",
                "database": db_name,
                "intent": request_decl.get("intent"),
                "params": params,
                "context": request_context,
                "fingerprint_sha256": _hash_bytes(
                    json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ),
                "http_status": contract_status,
            },
            "approved_semantic_sha256": approved_semantic_sha,
            "recomputed_semantic_sha256": recomputed_semantic_sha,
            "schema_asset": {
                "path": str(asset.relative_to(ROOT)) if str(asset).startswith(str(ROOT)) else str(asset),
                "sha256": declared_schema_sha,
                "declared_schema_sha256": str(definition.get("schemaSha256") or ""),
                "declared_schema_version": str(definition.get("schemaVersion") or ""),
                "formal_schema_errors": schema_errors,
            },
            "custody": {
                "response_sha256": _hash_bytes(contract_bytes),
                "response_bytes": len(contract_bytes),
                "response_path": custody_path,
                "response_encoding": "utf-8",
            },
            "integrity_reason": reason,
            "snapshot": contract,
            "errors": errors,
        }
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-dir", default=os.getenv("ACCEPTANCE_BACKUP_DIR", ""))
    parser.add_argument("--base-url", default=os.getenv("ACCEPTANCE_BASE_URL", ""), required=not bool(os.getenv("ACCEPTANCE_BASE_URL")))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", ""), required=not bool(os.getenv("DB_NAME")))
    parser.add_argument("--expected-sha", default=os.getenv("SC_ACCEPTANCE_EXPECTED_SHA", ""), required=not bool(os.getenv("SC_ACCEPTANCE_EXPECTED_SHA")))
    parser.add_argument("--app-env", default=os.getenv("VITE_APP_ENV", os.getenv("ENV", "dev")))
    parser.add_argument("--forbidden-db", default=os.getenv("ACCEPTANCE_FORBIDDEN_DB", "sc_prod_sim"))
    parser.add_argument("--login", default=os.getenv("ACCEPTANCE_LOGIN", ""))
    parser.add_argument("--password", default=os.getenv("ACCEPTANCE_PASSWORD", ""))
    # The contract section authenticates as the declared contract account, which
    # is a different identity from the login/navigation account. Keep the two
    # credentials independent; when no contract credential is declared the
    # previous single-password behaviour is preserved.
    parser.add_argument("--contract-password", default=os.getenv(CONTRACT_PASSWORD_ENV, ""))
    parser.add_argument("--nav-min-actions", default=os.getenv("ACCEPTANCE_NAV_MIN_ACTIONS", ""))
    parser.add_argument("--nav-max-actions", default=os.getenv("ACCEPTANCE_NAV_MAX_ACTIONS", ""))
    parser.add_argument("--nav-forbidden-labels", default=os.getenv("ACCEPTANCE_NAV_FORBIDDEN_LABELS", ""))
    parser.add_argument("--nav-required-paths", default=os.getenv("ACCEPTANCE_NAV_REQUIRED_PATHS", ""))
    parser.add_argument("--nav-required-actions", default=os.getenv("ACCEPTANCE_NAV_REQUIRED_ACTIONS", ""))
    parser.add_argument("--nav-principal-role", default=os.getenv("ACCEPTANCE_NAV_PRINCIPAL_ROLE", ""))
    parser.add_argument("--contract-declaration", default=os.getenv("ACCEPTANCE_CONTRACT_DECLARATION", ""))
    parser.add_argument("--record-resolution", default=os.getenv("ACCEPTANCE_RECORD_RESOLUTION", ""))
    parser.add_argument("--schema-asset", default=os.getenv("ACCEPTANCE_SCHEMA_ASSET", ""))
    parser.add_argument("--require-contract", action="store_true", default=os.getenv("ACCEPTANCE_REQUIRE_CONTRACT", "") not in ("", "0", "false"))
    parser.add_argument("--output", default=os.getenv("ACCEPTANCE_PROBE_OUTPUT", str(DEFAULT_ARTIFACT)))
    parser.add_argument("--contract-output", default=os.getenv("ACCEPTANCE_PROBE_CONTRACT_OUTPUT", ""))
    args = parser.parse_args()

    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else None
    runtime_identity = probe_runtime_identity(args.base_url, args.db_name, args.expected_sha)
    declaration, declaration_errors = (
        load_acceptance_declaration(Path(args.contract_declaration)) if args.contract_declaration else (None, [])
    )
    resolution, resolution_errors = (
        load_record_resolution(Path(args.record_resolution), declaration)
        if (declaration is not None and args.record_resolution)
        else (None, ["record_resolution_path_missing"] if declaration is not None else [])
    )
    report = {
        "mode": "dev_acceptance_release_probe",
        "db_name": args.db_name,
        "base_url": args.base_url,
        "app_env": args.app_env,
        "runtime_identity": runtime_identity,
        "backup": probe_backup(backup_dir, args.db_name),
        "frontend": probe_frontend(args.base_url, args.db_name, args.app_env, args.forbidden_db),
        "login": probe_login(
            args.base_url,
            args.db_name,
            args.login,
            args.password,
            nav_min_actions=_int_env(args.nav_min_actions),
            nav_max_actions=_int_env(args.nav_max_actions),
            nav_forbidden_labels=_split_csv(args.nav_forbidden_labels),
            nav_required_paths=_split_csv(args.nav_required_paths),
            nav_required_actions=_parse_required_actions(args.nav_required_actions),
            expected_role_code=args.nav_principal_role.strip() or None,
        ) if runtime_identity.get("status") == "PASS" else {"enabled": bool(args.login), "status": "NOT_RUN", "reason": "runtime_identity_not_verified"},
    }
    if not args.contract_declaration:
        if args.require_contract:
            # An explicitly required contract without a declaration can never be
            # satisfied; report it as a failure instead of a silent NOT_RUN.
            report["contract"] = {
                "enabled": True,
                "status": "FAIL",
                "reason": "contract_required_but_undeclared",
                "errors": ["contract_required_but_undeclared"],
                "required_checks": [],
                "executed_checks": [],
                "not_run_checks": [],
                "checks": {},
            }
        else:
            report["contract"] = {"enabled": False, "status": "NOT_RUN", "reason": "no_contract_declaration"}
    elif runtime_identity.get("status") != "PASS":
        report["contract"] = {"enabled": True, "status": "NOT_RUN", "reason": "runtime_identity_not_verified"}
    else:
        # The persisted raw contract is the offline custody artifact; keep it as a
        # lane-specific sibling of the receipt so distinct lanes never overwrite.
        receipt_output = Path(args.output)
        contract_output = (
            Path(args.contract_output)
            if args.contract_output
            else receipt_output.with_name(receipt_output.stem + ".contract.json")
        )
        report["contract"] = probe_contract_acceptance(
            args.base_url,
            args.db_name,
            declaration,
            resolution,
            served_sha=str(runtime_identity.get("served_sha") or ""),
            expected_sha=args.expected_sha,
            declaration_errors=declaration_errors,
            resolution_errors=resolution_errors,
            schema_path=Path(args.schema_asset) if args.schema_asset else None,
            password=_contract_credential(args.contract_password, args.password),
            contract_output=contract_output,
        )
    statuses = [
        report["backup"].get("status", "PASS"),
        report["runtime_identity"].get("status", "FAIL"),
        report["frontend"].get("status", "PASS"),
        report["login"].get("status", "PASS"),
    ]
    if report["contract"].get("enabled") is not False:
        statuses.append(report["contract"].get("status", "FAIL"))
    report["status"] = "PASS" if all(status == "PASS" for status in statuses) else "FAIL"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("DEV_ACCEPTANCE_RELEASE_PROBE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
