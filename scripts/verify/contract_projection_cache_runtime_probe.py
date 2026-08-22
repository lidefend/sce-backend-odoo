#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib import request as urlrequest


def env_file_value(path, key):
    if not path or not os.path.isfile(path):
        return ""
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def post_json(url, payload, headers=None):
    req = urlrequest.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    started = time.monotonic()
    with urlrequest.urlopen(req, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8") or "{}")
    return body, int((time.monotonic() - started) * 1000)


def find_projection_meta(value):
    if isinstance(value, dict):
        cache = value.get("projection_cache")
        if isinstance(cache, dict) and cache.get("status"):
            return {
                "projection_cache": cache,
                "elapsed_ms": value.get("elapsed_ms"),
            }
        for child in value.values():
            found = find_projection_meta(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_projection_meta(child)
            if found:
                return found
    return {}


def stable_value(value):
    volatile = {
        "trace_id",
        "traceId",
        "request_id",
        "requestId",
        "elapsed_ms",
        "projection_cache",
        "runtimeHash",
        "etag",
        "sourceSha256",
        "contractSha256",
        "snapshotId",
        "generatedAt",
        "generated_at",
    }

    def normalize(item):
        if isinstance(item, dict):
            return {
                key: normalize(child)
                for key, child in sorted(item.items())
                if key not in volatile
            }
        if isinstance(item, list):
            return [normalize(child) for child in item]
        return item

    return normalize(value)


def stable_signature(value):
    raw = json.dumps(stable_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scalar_paths(value, prefix="$"):
    if isinstance(value, dict):
        out = {}
        for key, child in value.items():
            out.update(scalar_paths(child, f"{prefix}.{key}"))
        return out
    if isinstance(value, list):
        out = {}
        for index, child in enumerate(value):
            out.update(scalar_paths(child, f"{prefix}[{index}]"))
        return out
    return {prefix: value}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("initial", "persisted", "record_initial", "record_persisted"),
        required=True,
    )
    parser.add_argument(
        "--output",
        default="artifacts/backend/contract_projection_cache_runtime_probe.json",
    )
    args = parser.parse_args()

    env_file = os.getenv("ENV_FILE") or ".env"
    port = os.getenv("ODOO_PORT") or env_file_value(env_file, "ODOO_PORT") or "8070"
    base_url = (os.getenv("E2E_BASE_URL") or f"http://localhost:{port}").rstrip("/")
    db_name = os.getenv("E2E_DB") or os.getenv("DB_NAME") or os.getenv("DB") or ""
    login = os.getenv("E2E_LOGIN") or "admin"
    password = os.getenv("E2E_PASSWORD") or os.getenv("ADMIN_PASSWD") or "admin"
    intent_url = f"{base_url}/api/v1/intent"

    login_response, _ = post_json(
        intent_url,
        {"intent": "login", "params": {"db": db_name, "login": login, "password": password}},
        {"X-Anonymous-Intent": "1"},
    )
    token = (login_response.get("data") or {}).get("token")
    if not login_response.get("ok") or not token:
        raise RuntimeError(f"login failed: {login_response}")

    headers = {"Authorization": f"Bearer {token}"}
    login_data = login_response.get("data") if isinstance(login_response.get("data"), dict) else {}
    login_user = login_data.get("user") if isinstance(login_data.get("user"), dict) else {}
    user_record_id = int(
        login_data.get("uid")
        or login_data.get("user_id")
        or login_user.get("id")
        or 2
    )
    record_mode = args.phase.startswith("record_")
    probe_model = str(os.getenv("CACHE_PROBE_MODEL") or "res.users").strip()
    probe_view_type = str(os.getenv("CACHE_PROBE_VIEW_TYPE") or "form").strip().lower()
    probe_record_id = int(os.getenv("CACHE_PROBE_RECORD_ID") or user_record_id)
    payload = {
        "intent": "ui.contract.v2",
        "params": {
            "db": db_name,
            "op": "model",
            "model": probe_model,
            "view_type": probe_view_type,
            "render_profile": "create",
            "client_type": "web_pc",
            "delivery_profile": "full",
        },
    }
    if record_mode:
        payload["params"]["record_id"] = probe_record_id
        payload["params"]["render_profile"] = "edit"
    persisted_phase = args.phase in {"persisted", "record_persisted"}
    attempts = 1 if persisted_phase else 3
    observations = []
    signatures = []
    stable_payloads = []
    product_facts = {}
    for _index in range(attempts):
        response, wall_ms = post_json(intent_url, payload, headers)
        if not response.get("ok"):
            raise RuntimeError(f"ui.contract.v2 failed: {response}")
        meta = find_projection_meta(response)
        status = str((meta.get("projection_cache") or {}).get("status") or "")
        if not status:
            raise RuntimeError("ui.contract.v2 response missing projection_cache status")
        record_overlay = bool((meta.get("projection_cache") or {}).get("record_overlay"))
        if record_overlay != record_mode:
            raise RuntimeError(
                f"record overlay mismatch: expected={record_mode} actual={record_overlay}"
            )
        observations.append({
            "status": status,
            "cache": meta.get("projection_cache"),
            "handler_elapsed_ms": meta.get("elapsed_ms"),
            "wall_ms": wall_ms,
        })
        signatures.append(stable_signature(response.get("data")))
        stable_payloads.append(stable_value(response.get("data")))
        contract_data = response.get("data") if isinstance(response.get("data"), dict) else {}
        action_contract = contract_data.get("actionContract") if isinstance(contract_data.get("actionContract"), dict) else {}
        action_rules = action_contract.get("actionRuleList") if isinstance(action_contract.get("actionRuleList"), list) else []
        native_action_rules = [
            rule for rule in action_rules
            if isinstance(rule, dict)
            and isinstance(rule.get("nativeIdentity"), dict)
            and str(rule.get("nativeIdentity", {}).get("native_locator") or "").strip()
        ]
        layout_contract = contract_data.get("layoutContract") if isinstance(contract_data.get("layoutContract"), dict) else {}
        layout_nodes = []
        pending_nodes = list(layout_contract.get("containerTree") or [])
        while pending_nodes:
            node = pending_nodes.pop()
            if not isinstance(node, dict):
                continue
            layout_nodes.append(node)
            for child_key in ("children", "pages", "tabs", "nodes", "items"):
                children = node.get(child_key)
                if isinstance(children, list):
                    pending_nodes.extend(children)
        product_facts = {
            "action_rule_count": len(action_rules),
            "native_action_rule_count": len(native_action_rules),
            "unique_native_backend_identity_count": len({
                str(rule.get("backendIdentity") or "").strip()
                for rule in native_action_rules
                if str(rule.get("backendIdentity") or "").strip()
            }),
            "native_action_locators": sorted({
                str(rule.get("nativeIdentity", {}).get("native_locator") or "").strip()
                for rule in native_action_rules
            }),
            "native_occurrence_node_count": sum(
                1 for node in layout_nodes
                if str(node.get("native_locator") or "").strip()
            ),
            "native_modifier_node_count": sum(
                1 for node in layout_nodes
                if isinstance(node.get("modifiers"), dict) and node.get("modifiers")
            ),
            "native_relation_action_node_count": sum(
                1 for node in layout_nodes
                if isinstance(node.get("relation_active_actions"), dict)
                and node.get("relation_active_actions")
            ),
        }

    if len(set(signatures)) != 1:
        first = scalar_paths(stable_payloads[0])
        differences = []
        for index, payload_value in enumerate(stable_payloads[1:], start=2):
            candidate = scalar_paths(payload_value)
            for key in sorted(set(first) | set(candidate)):
                if first.get(key) != candidate.get(key):
                    differences.append({
                        "attempt": index,
                        "path": key,
                        "first": first.get(key),
                        "candidate": candidate.get(key),
                    })
                    if len(differences) >= 30:
                        break
            if len(differences) >= 30:
                break
        raise RuntimeError(
            "contract semantics changed across cache layers: "
            + json.dumps({"signatures": signatures, "differences": differences}, ensure_ascii=False)
        )
    statuses = [item["status"] for item in observations]
    if not persisted_phase:
        if statuses[0] not in {"miss", "persisted"}:
            raise RuntimeError(f"initial request must resolve miss/persisted, got {statuses}")
        if not any(status in {"hot", "persisted"} for status in statuses[1:]):
            raise RuntimeError(f"repeated requests did not bypass parser: {observations}")
    elif statuses != ["persisted"]:
        raise RuntimeError(f"post-restart request must use persisted source, got {statuses}")

    output = {
        "schema_version": "1.0",
        "phase": args.phase,
        "model": probe_model,
        "view_type": probe_view_type,
        "record_id": probe_record_id if record_mode else None,
        "observations": observations,
        "stable_signature": signatures[0],
        "product_facts": product_facts,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
