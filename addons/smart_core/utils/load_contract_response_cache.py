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
from typing import Any
from threading import RLock


_DEEPCOPY = copy.deepcopy


def _isolated_clone(value, memo):
    value_type = type(value)
    if value_type is dict:
        known = memo.get(id(value))
        if known is not None:
            return known
        clone = {}
        memo[id(value)] = clone
        for key, item in value.items():
            clone[_isolated_clone(key, memo)] = _isolated_clone(item, memo)
        return clone
    if value_type is list:
        known = memo.get(id(value))
        if known is not None:
            return known
        clone = []
        memo[id(value)] = clone
        append = clone.append
        for item in value:
            append(_isolated_clone(item, memo))
        return clone
    if value is None or value_type is str or value_type is bool or value_type is int or value_type is float:
        # ``copy.deepcopy`` returns atomic values unchanged and never memoises
        # them; subclasses (int/str enums, numpy scalars ...) fall through to it.
        return value
    return _DEEPCOPY(value, memo)


def isolated_clone(value):
    """Return a graph disjoint from ``value``, exactly as ``copy.deepcopy`` does.

    Assembled contract payloads are JSON-shaped, so the two dominant container
    types are cloned directly. That skips ``copy.deepcopy``'s per-object
    dispatch (``_deepcopy_dispatch`` lookup, ``__deepcopy__``/``__reduce_ex__``
    probing) while keeping the same memo bookkeeping, so shared sub-objects stay
    shared in the copy exactly like ``deepcopy``. Every other type is delegated
    to ``copy.deepcopy`` with the same memo, which keeps tuple, set, subclass
    and custom-object semantics unchanged.
    """
    return _isolated_clone(value, {})


def assembled_snapshot_gate_matches(
    response: Any,
    *,
    cache_version: Any,
    client_type: Any,
    delivery_profile: Any,
    limit_params: Any,
) -> bool:
    """True only for an entry whose assembled slice is the one this request wants.

    The gate tuple is read in two places - the shared read and the handler that
    consumes it - so it lives here once: a drift between the accessor and its
    consumer must degrade to the fully isolated read, never to a shared graph
    handed to a path that writes in place. An entry without a matching
    ``_assembled_v2`` (or without dict ``contract``/``source_contract``) is not
    a consumable assembled hit.
    """
    assembled = response.get("_assembled_v2") if isinstance(response, dict) else None
    if not isinstance(assembled, dict):
        return False
    return bool(
        assembled.get("cache_version") == cache_version
        and assembled.get("client_type") == client_type
        and assembled.get("delivery_profile") == delivery_profile
        and assembled.get("limit_params") == limit_params
        and isinstance(assembled.get("contract"), dict)
        and isinstance(assembled.get("source_contract"), dict)
    )


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
            # Same isolation contract as ``copy.deepcopy`` on the payload this
            # cache stores (JSON-shaped containers), without its per-object
            # dispatch cost on the hot read path.
            return isolated_clone(response)

    def get_assembled(
        self,
        cache_key,
        source_token,
        *,
        cache_version,
        client_type,
        delivery_profile,
        limit_params,
        digests_key,
    ):
        """Hot read of one assembled slice without re-copying the source graph.

        The stored entry keeps ``ui_data`` and ``_assembled_v2.source_contract``
        on one shared memo, so the fully isolated ``get`` copies the whole source
        graph on every hot assembled hit even though that path only *reads* it.
        This accessor returns the live ``ui_data`` / ``source_contract`` and the
        meta by reference (plus a fresh copy of the meta and of the semantic
        digests, which are cheap), and returns a **fresh deep copy of the
        contract** because ``seal_runtime_contract`` mutates the contract in
        place. Callers must therefore treat ``ui_data`` and ``source_contract``
        as **read-only**.

        It returns ``None`` unless the entry is a live, gate-matching assembled
        hit, so a caller can safely fall back to the fully isolated ``get``.
        """
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
            if not assembled_snapshot_gate_matches(
                response,
                cache_version=cache_version,
                client_type=client_type,
                delivery_profile=delivery_profile,
                limit_params=limit_params,
            ):
                return None
            assembled = response["_assembled_v2"]
            self._entries.move_to_end(cache_key)
            digests = assembled.get(digests_key)
            return {
                "source_type": response.get("source_type"),
                # Shared by reference: read-only on the assembled hit path.
                "ui_data": response.get("ui_data"),
                "ui_meta": copy.deepcopy(response.get("ui_meta")),
                "_assembled_v2": {
                    "cache_version": assembled.get("cache_version"),
                    "client_type": assembled.get("client_type"),
                    "delivery_profile": assembled.get("delivery_profile"),
                    "limit_params": assembled.get("limit_params"),
                    # ``seal_runtime_contract`` mutates the contract in place, so
                    # it is copied; the source payload it reads stays shared.
                    "contract": _DEEPCOPY(assembled["contract"]),
                    "source_contract": assembled["source_contract"],
                    digests_key: dict(digests) if isinstance(digests, dict) else digests,
                },
            }

    def put(self, cache_key, source_token, response):
        if not cache_key or not source_token or not isinstance(response, dict):
            return
        self.put_generated(cache_key, source_token, lambda: copy.deepcopy(response))

    def put_generated(self, cache_key, source_token, snapshot_factory):
        """Store a newly built, exclusively owned snapshot without copying twice.

        Internal producers must copy every externally mutable component and must
        not retain the returned snapshot. Ordinary callers use ``put`` instead.
        The factory runs under the cache lock, preserving ordering with clear().
        ``get`` still returns an isolated copy on every read.
        """
        if not cache_key or not source_token:
            return
        with self._lock:
            response = snapshot_factory()
            if not isinstance(response, dict):
                return
            self._entries[cache_key] = (
                self._clock(),
                source_token,
                response,
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


_CODE_FINGERPRINT_LOCK = RLock()
_CODE_FINGERPRINT_CACHE: dict[str, object] = {
    "value": None,
    "content_recomputations": 0,
}
_CODE_FINGERPRINT_ROOT = "/mnt/source-addons"
_CODE_FINGERPRINT_SUFFIXES = (".py", ".xml")
_CODE_FINGERPRINT_SKIP_DIRS = frozenset({"__pycache__", "tests", ".git"})


def _code_content_digest():
    """代码身份：受管源码根下每个 .py/.xml 的 ``path + 内容`` 的 sha256 聚合摘要。

    身份**只绑定内容**。文件系统的 ``size/mtime_ns/ctime_ns`` 一律不参与身份：
    它们是文件系统的变化信号，``touch``/``utime``、目录重建或镜像层差异都会让
    它们漂移而与代码无关；把它们混进身份会产生假失效，而只依赖 ``mtime+size``
    又会漏掉就地改写，两者都不是可靠的内容身份。
    """
    digest = hashlib.sha256()
    root = os.getenv("SC_SOURCE_ADDONS_ROOT", _CODE_FINGERPRINT_ROOT)
    paths: list[str] = []
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in _CODE_FINGERPRINT_SKIP_DIRS]
            for filename in filenames:
                if filename.endswith(_CODE_FINGERPRINT_SUFFIXES):
                    paths.append(os.path.join(dirpath, filename))
    for full in sorted(paths):
        digest.update(full.encode("utf-8", "replace"))
        digest.update(b"\0")
        try:
            with open(full, "rb") as handle:
                while True:
                    chunk = handle.read(1 << 20)
                    if not chunk:
                        break
                    digest.update(chunk)
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\0")
    return digest.hexdigest()


def contract_code_fingerprint() -> str:
    """契约组装相关后端代码目录的聚合指纹。

    ``build_projection_source_token`` 只依赖权威表的 ``write_date`` 与部署期
    环境变量，纯 Python/XML 代码改动不会改变它们，导致旧契约缓存被继续命中。
    这里对受管源码根下的 .py/.xml 文件做聚合指纹；持久化的 runtime source
    asset 没有 TTL，身份必须自己跟随代码内容，token 变化使旧缓存立即失效。

    身份分层（2026-10-17 修正）：代码身份是内容摘要（``_code_content_digest``），
    文件系统的 ``size/mtime_ns/ctime_ns`` **不参与身份**。因此 ``ctime`` 不再是
    代码身份，也不再是触发手段：

    * 同一 (mtime, size) 下的就地改写（R2 反例）会改变内容摘要，旧 token 立即
      失效；
    * 仅元数据变化（``touch``/``utime``，内容不变）不会移动身份，不会造成假
      失效，也不会让真实内容改动被掩盖。

    正式部署仍应绑定不可变构建或内容摘要：``SC_SOURCE_REVISION`` /
    ``SC_SOURCE_FINGERPRINT`` 已在 token 中，本函数是同一部署内代码内容身份的
    进程内兜底。摘要按进程缓存：运行中的解释器不会重新加载已导入的模块，因此
    进程内重复读取源码没有意义，跨进程/重启时由新进程重新按内容计算。
    """
    with _CODE_FINGERPRINT_LOCK:
        if _CODE_FINGERPRINT_CACHE["value"]:
            return _CODE_FINGERPRINT_CACHE["value"]
        value = _code_content_digest()
        _CODE_FINGERPRINT_CACHE["value"] = value
        _CODE_FINGERPRINT_CACHE["content_recomputations"] = int(
            _CODE_FINGERPRINT_CACHE["content_recomputations"]
        ) + 1
        return value


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
            "code_fingerprint",
            contract_code_fingerprint(),
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
            if model_code == "ui.business.config.contract":
                # write_date is transaction time and can remain identical for
                # A -> B -> A. Bind all relevant definitions, not the latest row.
                records = model.sudo().with_context(active_test=False).search([
                    ("model", "=", model_name), "|", ("company_id", "=", False),
                    ("company_id", "=", env.company.id),
                ], order="id")
                versions.append([model_code, [
                    [row.id, row.definition_sha256, row.version_no, row.status, row.active]
                    for row in records
                ]])
                continue
            if model_code == "ui.form.field.policy" and {
                "field_name", "visible", "active",
            } <= set(model._fields):
                # Field policies are projection inputs, so retiring, creating,
                # editing or role-scoping one changes the assembled contract.
                # write_date is second-resolution and can stay identical for an
                # A -> B -> A change inside one transaction, so bind the
                # definition set for this model/action, not the latest row.
                domain = [
                    ("model", "=", model_name), "|",
                    ("company_id", "=", False),
                    ("company_id", "=", env.company.id),
                ]
                if action_id:
                    domain = domain + [
                        "|",
                        ("action_id", "=", int(action_id)),
                        ("action_id", "=", False),
                    ]
                records = model.sudo().with_context(active_test=False).search(
                    domain, order="id"
                )
                versions.append([model_code, [
                    [
                        row.id,
                        str(row.write_date or ""),
                        bool(row.active),
                        bool(row.visible),
                        str(row.field_name or ""),
                        int(row.action_id.id or 0),
                        int(row.view_id.id or 0),
                        int(row.sequence or 0),
                        str(row.label or ""),
                        sorted(int(group_id) for group_id in row.role_group_ids.ids),
                    ]
                    for row in records
                ]])
                continue
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
    # A create source contains default_get facts (including live configuration
    # and related values), not only reusable view structure. Rebuild it through
    # the existing dynamic path; source tokens do not describe those facts.
    if str(source.get("render_profile") or source.get("renderProfile") or "").strip().lower() == "create":
        return None
    if any(str(source.get(key) or "").strip().lower() == "new" for key in ("record_id", "recordId", "res_id", "resId")):
        return None
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
