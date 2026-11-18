#!/usr/bin/env python3
"""Capture BE-CLOSE-01 workflow contracts through the authenticated final API."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
REQUEST_DECLARATION_PATH = ROOT / "config/acceptance/backend_contract_instance_v1.json"
ENTRY_IDENTITY_PATH = ROOT / "config/acceptance/isolated_entry_identity.v1.env"
DEFAULT_IDS_PATH = ROOT / "artifacts/backend/be_close_01_workflow_contract_runtime_ids_v1.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts/backend/be_close_01_workflow_contract_samples_v1.json"


class FinalApiSession:
    def __init__(self, base_url: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token = ""
        self.jar = CookieJar()
        self.entry_headers = _entry_headers()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def get_json(self, path: str) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(
            self.base_url + path,
            headers=self._headers(anonymous=True),
            method="GET",
        )
        return self._open(request)

    def post_intent(self, intent: str, params: dict[str, Any], **kwargs: Any) -> tuple[int, dict[str, Any]]:
        payload = {"intent": intent, "params": params}
        payload.update(kwargs)
        request = urllib.request.Request(
            self.base_url + "/api/v1/intent",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(anonymous=intent == "login"),
            method="POST",
        )
        return self._open(request)

    def login(self, login: str, password: str) -> tuple[int, dict[str, Any]]:
        status, envelope = self.post_intent(
            "login",
            {"login": login, "password": password, "contract_mode": "default"},
        )
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        session = data.get("session") if isinstance(data.get("session"), dict) else {}
        self.token = str(session.get("token") or "").strip()
        return status, envelope

    def _headers(self, *, anonymous: bool = False) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.entry_headers}
        if anonymous:
            headers["X-Anonymous-Intent"] = "1"
        elif self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    def _open(self, request: urllib.request.Request) -> tuple[int, dict[str, Any]]:
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.status, _loads(body)
        except urllib.error.HTTPError as exc:
            return exc.code, _loads(exc.read().decode("utf-8", errors="replace"))
        except urllib.error.URLError as exc:
            raise RuntimeError("final API transport failed: %s" % exc) from exc


def _loads(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("final API returned non-JSON response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("final API response must be an object")
    return payload


def _entry_headers() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENTRY_IDENTITY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    required = {
        "SC_ENTRY_NAMESPACE": "X-SC-Namespace",
        "SC_ENTRY_AUDIENCE": "X-SC-Audience",
        "SC_ENTRY_SHARED_SECRET": "X-SC-Entry-Secret",
        "SC_ENTRY_ROUTE_VERSION": "X-SC-Route-Version",
    }
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise RuntimeError("acceptance entry identity missing: %s" % ", ".join(missing))
    return {header: values[key] for key, header in required.items()}


def _require_ok(status: int, envelope: dict[str, Any], operation: str) -> dict[str, Any]:
    if status != 200 or envelope.get("ok") is not True:
        raise RuntimeError("%s failed: status=%s response=%s" % (
            operation,
            status,
            json.dumps(envelope, ensure_ascii=False, sort_keys=True),
        ))
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("%s response has no data object" % operation)
    return data


def _request_identity(entry: dict[str, Any], record_id: int, *, render_profile: str) -> dict[str, Any]:
    declaration = json.loads(REQUEST_DECLARATION_PATH.read_text(encoding="utf-8"))
    request_decl = declaration["request"]
    return {
        "op": "action_open",
        "model": entry["model"],
        "action_id": entry["action_id"],
        "menu_id": entry["menu_id"],
        "record_id": record_id,
        "view_type": request_decl["view_type"],
        "render_profile": render_profile,
        "contract_surface": request_decl["contract_surface"],
        "source_mode": request_decl["source_mode"],
        "delivery_profile": request_decl["delivery_profile"],
        "client_type": request_decl["client_type"],
        "accepted_contract_versions": list(request_decl["accepted_contract_versions"]),
        "client_contract_capabilities": list(request_decl["client_contract_capabilities"]),
    }


def _create_request(entry: dict[str, Any]) -> dict[str, Any]:
    payload = _request_identity(entry, 0, render_profile="create")
    payload.pop("record_id")
    payload["op"] = "model"
    return payload


def _contract_response(
    session: FinalApiSession,
    params: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs = {"context": context} if context else {}
    status, envelope = session.post_intent("ui.contract.v2", params, **kwargs)
    data = _require_ok(status, envelope, "ui.contract.v2")
    workflow = data.get("workflowContract")
    if not isinstance(workflow, dict):
        raise RuntimeError("ui.contract.v2 response has no workflowContract")
    return envelope, data


def _record_contract(
    session: FinalApiSession,
    entry: dict[str, Any],
    record_id: int,
    *,
    render_profile: str = "edit",
    context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return _contract_response(
        session,
        _request_identity(entry, record_id, render_profile=render_profile),
        context=context,
    )


def _action_summary(contract: dict[str, Any]) -> dict[str, Any]:
    available = contract.get("availableActions") or []
    return {
        "allowed_action_keys": sorted(
            str(row.get("key") or "") for row in available if row.get("enabled") is True
        ),
        "disabled_action_keys": sorted(
            str(row.get("key") or "") for row in available if row.get("enabled") is False
        ),
        "denial_reasons": {
            str(row.get("key") or ""): {
                "reasonCode": str(row.get("reason_code") or ""),
                "message": str(row.get("blocked_message") or ""),
            }
            for row in available
            if row.get("enabled") is False
        },
    }


def _workflow_action(contract: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [
        row for row in contract.get("availableActions") or []
        if isinstance(row, dict) and row.get("key") == key
    ]
    if len(matches) > 1:
        raise RuntimeError("workflow action identity is ambiguous: %s" % key)
    return matches[0] if matches else None


def _action_rule(data: dict[str, Any], method: str) -> dict[str, Any]:
    action_contract = data.get("actionContract")
    action_contract = action_contract if isinstance(action_contract, dict) else {}
    rules = action_contract.get("actionRuleList")
    rules = rules if isinstance(rules, list) else []
    matches = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        button = rule.get("button") if isinstance(rule.get("button"), dict) else {}
        if str(button.get("name") or "").strip() == method:
            matches.append(rule)
    if len(matches) != 1:
        raise RuntimeError("action contract identity is not unique for method %s: %s" % (
            method,
            len(matches),
        ))
    rule = matches[0]
    if (
        rule.get("allowed") is not True
        or rule.get("enabled") is not True
        or rule.get("disabled") is not False
        or rule.get("entitlementEvaluated") is not True
    ):
        raise RuntimeError("workflow action availability disagrees with action contract: %s" % method)
    return rule


def _execute_declared_action(
    session: FinalApiSession,
    *,
    entry: dict[str, Any],
    record_id: int,
    data: dict[str, Any],
    action_key: str,
) -> dict[str, Any]:
    workflow = data["workflowContract"]
    action = _workflow_action(workflow, action_key)
    if not action or action.get("enabled") is not True:
        raise RuntimeError("declared action is not executable: %s" % action_key)
    method = str(action.get("method") or "").strip()
    if not method:
        raise RuntimeError("declared object action has no method: %s" % action_key)
    rule = _action_rule(data, method)
    button = rule["button"]
    status, envelope = session.post_intent(
        "execute_button",
        {
            "model": entry["model"],
            "res_id": record_id,
            "button": {
                "name": method,
                "type": str(button.get("type") or "object"),
                "action_id": rule["actionId"],
                "backend_identity": rule["backendIdentity"],
                "source_widget_id": rule["sourceWidgetId"],
            },
            "action_params": {},
        },
        context={},
        meta={"menu_id": entry["menu_id"], "action_id": entry["action_id"]},
    )
    result = _require_ok(status, envelope, "execute_button:%s" % action_key)
    return {
        "action_key": action_key,
        "method": method,
        "backendIdentity": rule["backendIdentity"],
        "sourceWidgetId": rule["sourceWidgetId"],
        "request": {
            "model": entry["model"],
            "record_id": record_id,
            "menu_id": entry["menu_id"],
            "action_id": entry["action_id"],
            "method": method,
        },
        "response": envelope,
        "result": result,
    }


def _sample(
    *,
    kind: str,
    entry_name: str,
    entry: dict[str, Any],
    envelope: dict[str, Any],
    data: dict[str, Any],
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow = data["workflowContract"]
    validator.validate(workflow)
    return {
        "kind": kind,
        "entry_name": entry_name,
        "entry": entry,
        "record": record or {},
        "http_response": envelope,
        "contract": workflow,
        "summary": _action_summary(workflow),
    }


def _find_project_blocked(session: FinalApiSession, ids: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    entry = ids["entries"]["project_lifecycle"]
    context = _record_context(session)
    observed = []
    for record in ids["records"]["project_blocked_candidates"]:
        envelope, data = _record_contract(
            session,
            entry,
            record["id"],
            render_profile="readonly",
            context=context,
        )
        close = _workflow_action(data["workflowContract"], "close")
        observed.append({
            "record": record,
            "close": close,
        })
        if close and close.get("enabled") is False:
            return record, envelope, data
    raise RuntimeError("no project candidate exposes a business-blocked close action: %s" % json.dumps(
        observed,
        ensure_ascii=False,
        sort_keys=True,
    ))


def _record_context(session: FinalApiSession) -> dict[str, Any]:
    status, envelope = session.post_intent("system.init", {})
    data = _require_ok(status, envelope, "system.init")
    record_context = data.get("record_context")
    record_context = record_context if isinstance(record_context, dict) else {}
    context = record_context.get("request_context")
    if not isinstance(context, dict) or not context:
        raise RuntimeError("system.init did not expose record request context")
    return {str(key): value for key, value in context.items() if isinstance(value, str) and value}


def emit_samples() -> None:
    base_url = os.environ.get("SC_ACCEPTANCE_BE_CLOSE01_BASE_URL", "http://127.0.0.1:18082")
    expected_sha = os.environ.get("SC_ACCEPTANCE_BE_CLOSE01_EXPECTED_SHA", "").strip()
    login = os.environ.get("SC_ACCEPTANCE_BE_CLOSE01_LOGIN", "fixture_role_config_admin")
    password = os.environ.get("SC_ACCEPTANCE_FIXTURE_PASSWORD", "")
    ids_path = Path(os.environ.get("SC_ACCEPTANCE_BE_CLOSE01_IDS", str(DEFAULT_IDS_PATH)))
    output_path = Path(os.environ.get("SC_ACCEPTANCE_BE_CLOSE01_OUTPUT", str(DEFAULT_OUTPUT_PATH)))
    if not password:
        raise RuntimeError("SC_ACCEPTANCE_FIXTURE_PASSWORD is required")
    ids = json.loads(ids_path.read_text(encoding="utf-8"))

    session = FinalApiSession(base_url)
    runtime_status, runtime_envelope = session.get_json("/api/runtime-version")
    if runtime_status != 200:
        raise RuntimeError("runtime-version failed: status=%s response=%s" % (
            runtime_status,
            json.dumps(runtime_envelope, ensure_ascii=False, sort_keys=True),
        ))
    runtime_data = (
        runtime_envelope.get("data")
        if isinstance(runtime_envelope.get("data"), dict)
        else runtime_envelope
    )
    served_sha = str(
        runtime_data.get("git_sha")
        or runtime_data.get("source_sha")
        or runtime_data.get("source_revision")
        or ""
    )
    if expected_sha and served_sha != expected_sha:
        raise RuntimeError("served backend SHA differs: %s != %s" % (served_sha, expected_sha))
    runtime_database = str(
        runtime_data.get("database")
        or runtime_data.get("db_name")
        or runtime_data.get("db")
        or ""
    )
    if runtime_database and runtime_database != ids["runtime"]["database"]:
        raise RuntimeError("served database differs: %s" % runtime_database)

    auth_status, auth_envelope = session.login(
        str(ids["actor"]["login"] or login),
        password,
    )
    _require_ok(auth_status, auth_envelope, "login")
    if not session.token:
        raise RuntimeError("login did not issue a session token")
    context = _record_context(session)

    payment_entry = ids["entries"]["payment_request"]
    project_entry = ids["entries"]["project_lifecycle"]

    payment_create_envelope, payment_create_data = _contract_response(
        session,
        _create_request(payment_entry),
        context=context,
    )
    project_create_envelope, project_create_data = _contract_response(
        session,
        _create_request(project_entry),
        context=context,
    )

    payment_record = ids["records"]["payment_actionable"]
    payment_blocked = ids["records"]["payment_blocked"]
    project_record = ids["records"]["project_actionable"]

    payment_envelope, payment_data = _record_contract(
        session,
        payment_entry,
        payment_record["id"],
        context=context,
    )
    payment_blocked_envelope, payment_blocked_data = _record_contract(
        session,
        payment_entry,
        payment_blocked["id"],
        render_profile="readonly",
        context=context,
    )
    project_envelope, project_data = _record_contract(
        session,
        project_entry,
        project_record["id"],
        context=context,
    )
    project_blocked_record, project_blocked_envelope, project_blocked_data = _find_project_blocked(
        session,
        ids,
    )

    payment_submit = _execute_declared_action(
        session,
        entry=payment_entry,
        record_id=payment_record["id"],
        data=payment_data,
        action_key="submit",
    )
    payment_after_envelope, payment_after_data = _record_contract(
        session,
        payment_entry,
        payment_record["id"],
        render_profile="readonly",
        context=context,
    )

    project_executions = []
    current_project_data = project_data
    for action_key in ("submit", "approve", "activate"):
        action = _workflow_action(current_project_data["workflowContract"], action_key)
        if not action:
            continue
        if action.get("enabled") is not True:
            if action_key == "approve":
                continue
            raise RuntimeError("project action is disabled before readback: %s" % action_key)
        project_executions.append(_execute_declared_action(
            session,
            entry=project_entry,
            record_id=project_record["id"],
            data=current_project_data,
            action_key=action_key,
        ))
        project_after_envelope, current_project_data = _record_contract(
            session,
            project_entry,
            project_record["id"],
            context=context,
        )
        if action_key == "activate":
            break
    if not project_executions or project_executions[-1]["action_key"] != "activate":
        raise RuntimeError("project lifecycle did not read back an executable start action")
    project_after_envelope, project_after_data = _record_contract(
        session,
        project_entry,
        project_record["id"],
        render_profile="readonly",
        context=context,
    )

    payload = {
        "schema": "be_close_01.workflow_contract_final_api_samples.v1",
        "base_url": base_url,
        "served_sha": served_sha,
        "expected_sha": expected_sha,
        "database": runtime_database or ids["runtime"]["database"],
        "actor": {
            **ids["actor"],
            "authenticated": True,
        },
        "record_context": context,
        "create_catalog_samples": [
            _sample(
                kind="payment_create_catalog",
                entry_name="payment_request",
                entry=payment_entry,
                envelope=payment_create_envelope,
                data=payment_create_data,
            ),
            _sample(
                kind="project_lifecycle_create_catalog",
                entry_name="project_lifecycle",
                entry=project_entry,
                envelope=project_create_envelope,
                data=project_create_data,
            ),
        ],
        "persisted_record_samples": [
            _sample(
                kind="payment_actionable",
                entry_name="payment_request",
                entry=payment_entry,
                envelope=payment_envelope,
                data=payment_data,
                record=payment_record,
            ),
            _sample(
                kind="payment_business_blocked",
                entry_name="payment_request",
                entry=payment_entry,
                envelope=payment_blocked_envelope,
                data=payment_blocked_data,
                record=payment_blocked,
            ),
            _sample(
                kind="project_lifecycle_actionable",
                entry_name="project_lifecycle",
                entry=project_entry,
                envelope=project_envelope,
                data=project_data,
                record=project_record,
            ),
            _sample(
                kind="project_lifecycle_business_blocked",
                entry_name="project_lifecycle",
                entry=project_entry,
                envelope=project_blocked_envelope,
                data=project_blocked_data,
                record=project_blocked_record,
            ),
        ],
        "action_execution_readbacks": [
            {
                "entry_name": "payment_request",
                "record": payment_record,
                "executions": [payment_submit],
                "after": _sample(
                    kind="payment_after_submit",
                    entry_name="payment_request",
                    entry=payment_entry,
                    envelope=payment_after_envelope,
                    data=payment_after_data,
                    record=payment_record,
                ),
            },
            {
                "entry_name": "project_lifecycle",
                "record": project_record,
                "executions": project_executions,
                "after": _sample(
                    kind="project_after_start",
                    entry_name="project_lifecycle",
                    entry=project_entry,
                    envelope=project_after_envelope,
                    data=project_after_data,
                    record=project_record,
                ),
            },
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("BE_CLOSE_01_WORKFLOW_SAMPLES=" + json.dumps({
        "output": str(output_path),
        "database": payload["database"],
        "create_samples": len(payload["create_catalog_samples"]),
        "record_samples": len(payload["persisted_record_samples"]),
        "post_action_readbacks": len(payload["action_execution_readbacks"]),
    }, sort_keys=True))


def validate_samples(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "be_close_01.workflow_contract_final_api_samples.v1":
        raise RuntimeError("unexpected BE-CLOSE-01 sample schema")
    if payload.get("served_sha") != payload.get("expected_sha"):
        raise RuntimeError("sample backend SHA is not self-bound")
    if payload.get("database") != "sc_frontend_acceptance":
        raise RuntimeError("sample database is not the managed acceptance database")
    if not payload.get("actor", {}).get("authenticated"):
        raise RuntimeError("sample actor is not authenticated")

    creates = payload.get("create_catalog_samples") or []
    records = payload.get("persisted_record_samples") or []
    readbacks = payload.get("action_execution_readbacks") or []
    if len(creates) != 2 or len(records) != 4 or len(readbacks) != 2:
        raise RuntimeError("BE-CLOSE-01 sample population is incomplete")
    contracts = [
        *(sample["contract"] for sample in creates),
        *(sample["contract"] for sample in records),
        *(readback["after"]["contract"] for readback in readbacks),
    ]
    for contract in contracts:
        validator.validate(contract)
    for sample in creates:
        contract = sample["contract"]
        if contract.get("availabilityScope") != "declaration_only":
            raise RuntimeError("create sample claims record scope")
        if "record_id" in contract or "availableActions" in contract:
            raise RuntimeError("create sample leaks record execution authority")

    record_by_kind = {sample["kind"]: sample for sample in records}
    for kind in (
        "payment_actionable",
        "payment_business_blocked",
        "project_lifecycle_actionable",
        "project_lifecycle_business_blocked",
    ):
        if kind not in record_by_kind:
            raise RuntimeError("missing persisted sample: " + kind)
    payment_blocked = record_by_kind["payment_business_blocked"]["contract"]
    payment_done = _workflow_action(payment_blocked, "done")
    if (
        not payment_done
        or payment_done.get("enabled") is not False
        or payment_done.get("reason_code") != "PAYMENT_EXECUTION_REQUIRED"
        or not payment_done.get("blocked_message")
    ):
        raise RuntimeError("payment business-blocked sample is not explicit")
    project_blocked = record_by_kind["project_lifecycle_business_blocked"]["contract"]
    project_close = _workflow_action(project_blocked, "close")
    if (
        not project_close
        or project_close.get("enabled") is not False
        or project_close.get("reason_code") != "P0_PROJECT_TERMINAL_BLOCKED"
        or not project_close.get("blocked_message")
    ):
        raise RuntimeError("project business-blocked sample is not explicit")

    by_entry = {readback["entry_name"]: readback for readback in readbacks}
    payment_after = by_entry["payment_request"]["after"]["contract"]
    if payment_after.get("rawState") != "submit":
        raise RuntimeError("payment submit did not read back as submitted")
    project_after = by_entry["project_lifecycle"]["after"]["contract"]
    if project_after.get("rawState") != "in_progress":
        raise RuntimeError("project start did not read back as in progress")
    executed_project_actions = {
        row.get("action_key") for row in by_entry["project_lifecycle"]["executions"]
    }
    if "activate" not in executed_project_actions:
        raise RuntimeError("project start action was not executed")
    print("BE_CLOSE_01_WORKFLOW_SAMPLES_VALIDATED=" + json.dumps({
        "contracts": len(contracts),
        "create_samples": len(creates),
        "record_samples": len(records),
        "post_action_readbacks": len(readbacks),
        "payment_state": payment_after["rawState"],
        "project_state": project_after["rawState"],
    }, sort_keys=True))


def _load_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator({
        "$ref": "#/properties/workflowContract",
        "properties": schema["properties"],
        "$defs": schema["$defs"],
    })


validator = _load_validator()


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--validate-only":
            validate_samples(Path(sys.argv[2]))
        else:
            emit_samples()
    except Exception as exc:
        print("BE_CLOSE_01_WORKFLOW_SAMPLES_FAILED=" + json.dumps({
            "error": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        raise
