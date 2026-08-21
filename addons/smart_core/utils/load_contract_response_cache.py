# -*- coding: utf-8 -*-
"""Small, process-local cache for fully assembled ``load_contract`` responses.

The cache is deliberately not an authority. Callers must provide a source token
derived from the current Odoo authorities on every lookup. A token change makes
an entry unreachable immediately; the short TTL is a second safety boundary for
runtime inputs which are not represented by ``write_date``.
"""

import copy
import hashlib
import json
import os
import time
from collections import OrderedDict
from threading import RLock


class LoadContractResponseCache:
    def __init__(self, *, max_entries=256, ttl_seconds=30.0, clock=None):
        self.max_entries = max(1, int(max_entries))
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self._clock = clock or time.monotonic
        self._entries = OrderedDict()
        self._lock = RLock()

    def get(self, cache_key, source_token):
        if not cache_key or not source_token or self.ttl_seconds <= 0:
            return None
        now = self._clock()
        with self._lock:
            entry = self._entries.get(cache_key)
            if entry is None:
                return None
            created_at, stored_token, response = entry
            if stored_token != source_token or now - created_at > self.ttl_seconds:
                self._entries.pop(cache_key, None)
                return None
            self._entries.move_to_end(cache_key)
            return copy.deepcopy(response)

    def put(self, cache_key, source_token, response):
        if not cache_key or not source_token or not isinstance(response, dict):
            return
        with self._lock:
            self._entries[cache_key] = (
                self._clock(),
                source_token,
                copy.deepcopy(response),
            )
            self._entries.move_to_end(cache_key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self):
        with self._lock:
            self._entries.clear()


CONTRACT_PROJECTION_HOT_CACHE = LoadContractResponseCache(
    max_entries=256,
    ttl_seconds=30.0,
)


def projection_role_code(env):
    group_ids = sorted(int(group_id) for group_id in env.user.groups_id.ids)
    digest = hashlib.sha256(
        json.dumps(group_ids, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"uid:{int(env.user.id)}:groups:{digest}"


def build_projection_cache_key(env, *, namespace, params, model_name, view_types, context):
    allowed_company_ids = context.get("allowed_company_ids") or [env.company.id]
    if not isinstance(allowed_company_ids, (list, tuple, set)):
        return ""
    transport_only_keys = {
        "request_id",
        "requestId",
        "trace_id",
        "traceId",
        "timestamp",
        "request_timestamp",
        "requestTimestamp",
    }

    def semantic_request_value(value):
        if isinstance(value, dict):
            return {
                key: semantic_request_value(child)
                for key, child in value.items()
                if key not in transport_only_keys
            }
        if isinstance(value, list):
            return [semantic_request_value(child) for child in value]
        return value

    identity = {
        "namespace": str(namespace or ""),
        "db": env.cr.dbname,
        "uid": int(env.user.id),
        "role": projection_role_code(env),
        "company_id": int(env.company.id),
        "allowed_company_ids": sorted(int(item) for item in allowed_company_ids),
        "lang": str(context.get("lang") or ""),
        "tz": str(context.get("tz") or ""),
        "model": str(model_name or ""),
        "view_types": view_types if isinstance(view_types, list) else [view_types],
        "params": semantic_request_value(params),
    }
    raw = json.dumps(identity, ensure_ascii=False, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_projection_source_token(env, *, model_name, menu_id=None, action_id=None):
    specifications = [
        ("ir.ui.view", [("model", "=", model_name)]),
        ("ir.model.fields", [("model", "=", model_name)]),
        (
            "ir.actions.act_window",
            [("id", "=", action_id)] if action_id else [("res_model", "=", model_name)],
        ),
        ("ir.ui.menu", [("id", "=", menu_id)] if menu_id else []),
        ("ir.model.access", [("model_id.model", "=", model_name)]),
        ("ir.rule", [("model_id.model", "=", model_name)]),
        ("res.users", [("id", "=", env.user.id)]),
        ("ir.module.module", [("name", "=", "smart_core")]),
    ]
    optional_models = (
        "app.model.config",
        "app.view.config",
        "app.search.config",
        "app.permission.config",
        "app.action.config",
        "ui.business.config.contract",
        "ui.form.field.policy",
        "ui.menu.config.policy",
        "sc.approval.policy",
        "sc.scene",
    )
    try:
        versions = [[
            "runtime_source",
            str(os.getenv("SC_SOURCE_REVISION") or "").strip().lower(),
            str(os.getenv("SC_SOURCE_FINGERPRINT") or "").strip().lower(),
        ]]
        for model_code, domain in specifications:
            if model_code not in env:
                return ""
            model = env[model_code]
            if "write_date" not in model._fields:
                return ""
            latest = model.sudo().with_context(active_test=False).search(
                domain, order="write_date desc, id desc", limit=1
            )
            versions.append([
                model_code,
                latest.id if latest else 0,
                str(latest.write_date or "") if latest else "",
                str(getattr(latest, "latest_version", "") or "") if latest else "",
            ])
        for model_code in optional_models:
            if model_code not in env:
                continue
            model = env[model_code]
            if "write_date" not in model._fields:
                return ""
            latest = model.sudo().with_context(active_test=False).search(
                [], order="write_date desc, id desc", limit=1
            )
            versions.append([
                model_code,
                latest.id if latest else 0,
                str(latest.write_date or "") if latest else "",
            ])
        raw = json.dumps(versions, ensure_ascii=False, default=str, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def static_projection_request(params):
    dynamic_keys = {
        "active_id",
        "active_ids",
        "active_model",
        "current_project_id",
        "default_project_id",
        "record_id",
        "recordId",
        "res_id",
        "preview_token",
        "previewToken",
        "preview_role_key",
        "previewRoleKey",
    }
    if any(params.get(key) not in (None, "", [], False) for key in dynamic_keys):
        return False
    request_context = params.get("context") if isinstance(params.get("context"), dict) else {}
    return not any(
        request_context.get(key) not in (None, "", [], False)
        for key in dynamic_keys
    )


def projection_base_params(params):
    """Return the record-independent request used to build a reusable base."""
    source = dict(params or {})
    hard_dynamic_keys = {
        "current_project_id",
        "default_project_id",
        "preview_token",
        "previewToken",
        "preview_role_key",
        "previewRoleKey",
    }
    if any(source.get(key) not in (None, "", [], False) for key in hard_dynamic_keys):
        return None
    for key in (
        "record_id",
        "recordId",
        "res_id",
        "resId",
        "active_id",
        "active_ids",
        "active_model",
    ):
        source.pop(key, None)
    request_context = source.get("context")
    if isinstance(request_context, dict):
        context = dict(request_context)
        if any(context.get(key) not in (None, "", [], False) for key in hard_dynamic_keys):
            return None
        for key in ("record_id", "res_id", "active_id", "active_ids", "active_model"):
            context.pop(key, None)
        source["context"] = context
    return source
