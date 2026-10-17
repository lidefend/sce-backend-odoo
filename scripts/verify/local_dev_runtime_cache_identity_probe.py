"""Bounded cache-identity probe for the R2 relation-demand boundary (P4 diagnostic).

Three questions, answered with runtime evidence instead of code reading:

1. Where do the R2-changed methods run relative to the persisted runtime-source
   cache write (``upsert_runtime_source_asset`` inside
   ``UiContractV2Handler._handle_contract``)?
2. Does the persisted source token cover the affected code identity, i.e. is the
   old source asset rejected once that identity changes?
3. Is that identity bound to content rather than to file-system metadata? A
   metadata-only touch on unchanged content must keep the identity and must keep
   serving the row written under it (no false invalidation, no needless rebuild),
   while a same-size content rewrite with a restored mtime must still move it.

Read-only apart from rollback-only runtime-source rows on the registered
``sc_dev_demo`` database with the demo finance principal: commit is refused, no
product code, schema, fixture or ACL is changed, and the temp identity root
lives in the container ``/tmp`` and is removed before exit.
"""
import hashlib
import inspect
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from odoo import api

DATABASE = "sc_dev_demo"
PROBE_NONCE = "cache-identity-probe-v1"

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()

_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("cache identity probe forbids commit")


env.cr.commit = _refuse_commit

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.core import ui_base_contract_asset_repository as asset_repo
from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result
from odoo.addons.smart_core.handlers import ui_contract_v2 as v2_module
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.utils import load_contract_response_cache as cache_store

REPORT = {"schema": "runtime-cache-identity-probe/v1", "database": DATABASE, "acceptance_pass": False}
EVENTS = []
_NONCE = {"value": PROBE_NONCE}


def _record(event, note=""):
    frame = sys._getframe(2)
    EVENTS.append({
        "seq": len(EVENTS) + 1,
        "event": event,
        "note": note,
        "caller": "%s:%s:%s" % (
            Path(frame.f_code.co_filename).name, frame.f_code.co_name, frame.f_lineno
        ),
    })


def _reset_fingerprint():
    cache_store._CODE_FINGERPRINT_CACHE["value"] = None


def _fingerprint():
    _reset_fingerprint()
    return cache_store.contract_code_fingerprint()


def _token(actor, *, model_name, action_id, menu_id=None):
    _reset_fingerprint()
    return cache_store.build_projection_source_token(
        actor, model_name=model_name, menu_id=menu_id, action_id=action_id
    )


def _under_root(root, func):
    previous = os.environ.get("SC_SOURCE_ADDONS_ROOT")
    os.environ["SC_SOURCE_ADDONS_ROOT"] = str(root)
    try:
        return func()
    finally:
        if previous is None:
            os.environ.pop("SC_SOURCE_ADDONS_ROOT", None)
        else:
            os.environ["SC_SOURCE_ADDONS_ROOT"] = previous


def _legacy_digest(root):
    """The row tuple this identity used before R2: (path, mtime_ns, size)."""
    rows = []
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [name for name in dirnames if name not in {"__pycache__", "tests", ".git"}]
        for filename in filenames:
            if not filename.endswith((".py", ".xml")):
                continue
            full = os.path.join(dirpath, filename)
            stat = os.stat(full)
            rows.append((full, stat.st_mtime_ns, stat.st_size))
    digest = hashlib.sha256()
    for row in sorted(rows):
        digest.update(repr(row).encode("utf-8", "replace"))
    return digest.hexdigest()


def _file_identity(path):
    stat = path.stat()
    return {
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
        "size": stat.st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _relation_surface(ui_data):
    """The relation-entry facts the persisted source payload actually carries."""
    fields = ui_data.get("fields") if isinstance(ui_data, dict) else None
    entries = {}
    if isinstance(fields, dict):
        for name, desc in fields.items():
            if isinstance(desc, dict) and isinstance(desc.get("relation_entry"), dict):
                entries[str(name)] = desc["relation_entry"]
    dialog_fields = sorted(
        name for name, entry in entries.items() if isinstance(entry.get("search_dialog"), dict)
    )
    return {
        "fields_with_relation_entry": len(entries),
        "fields_with_search_dialog": len(dialog_fields),
        "search_dialog_fields": dialog_fields,
    }


def _lookup(cache_key, token, role_code, company_id):
    payload = asset_repo.get_runtime_source_asset(
        actor, cache_key=cache_key, source_token=token, role_code=role_code, company_id=company_id
    )
    return payload if isinstance(payload, dict) else {}


# --- registered principal and observed action -------------------------------
user = env.ref("smart_construction_demo.user_demo_role_finance")
assert user.active and not user.share, "declared demo finance identity unavailable"
company_id = user.company_id.id
actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [company_id], "lang": "zh_CN"})
assert not actor.su, "actor must not be elevated"
ACTION_ID = int(os.environ.get("PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID") or 878)
ACTION = actor["ir.actions.act_window"].browse(ACTION_ID).exists()
assert ACTION and ACTION.res_model, "observed action unavailable"
MODEL = str(ACTION.res_model)
REPORT["principal"] = {
    "xmlid": "smart_construction_demo.user_demo_role_finance",
    "uid": int(user.id),
    "company_id": int(company_id),
    "action_id": ACTION_ID,
    "model": MODEL,
    "op": "action_open",
}

# --- step 0: identity facts -------------------------------------------------
identity_root = os.getenv("SC_SOURCE_ADDONS_ROOT") or cache_store._CODE_FINGERPRINT_ROOT
root_path = Path(identity_root)
owner_paths = {
    "ui_contract_v2.py": Path(inspect.getsourcefile(UiContractV2Handler)).resolve(),
    "page_assembler.py": Path(inspect.getsourcefile(PageAssembler)).resolve(),
    "load_contract_response_cache.py": Path(inspect.getsourcefile(cache_store)).resolve(),
}
real_fingerprint = _fingerprint()
token_real = _token(actor, model_name=MODEL, action_id=ACTION_ID, menu_id=None)
_original_code_fingerprint = cache_store.contract_code_fingerprint
cache_store.contract_code_fingerprint = lambda: hashlib.sha256(b"identity-probe-code-change").hexdigest()
try:
    token_on_fingerprint_change = _token(actor, model_name=MODEL, action_id=ACTION_ID, menu_id=None)
finally:
    cache_store.contract_code_fingerprint = _original_code_fingerprint
    _reset_fingerprint()

REPORT["step0_identity"] = {
    "SC_SOURCE_REVISION": os.getenv("SC_SOURCE_REVISION"),
    "SC_SOURCE_FINGERPRINT": os.getenv("SC_SOURCE_FINGERPRINT"),
    "SC_SOURCE_ADDONS_ROOT": os.getenv("SC_SOURCE_ADDONS_ROOT"),
    "identity_root": identity_root,
    "identity_root_is_dir": root_path.is_dir(),
    "identity_basis": "sha256 over (path, content) of every .py/.xml under the identity root",
    "identity_signal_not_used": (
        "size / mtime_ns / ctime_ns are deliberately NOT part of the code identity: "
        "they are a file-system change signal that also drifts on metadata-only touches"
    ),
    "affected_sources": {
        label: {
            "path": str(path),
            "inside_identity_root": bool(
                str(path) == identity_root.rstrip("/")
                or str(path).startswith(identity_root.rstrip("/") + "/")
            ),
            "file_identity": _file_identity(path),
        }
        for label, path in owner_paths.items()
    },
    "code_fingerprint": real_fingerprint,
    "token": token_real,
    "token_changes_with_code_fingerprint": token_real != token_on_fingerprint_change,
}

# --- step 1: position of the R2 methods relative to the source cache write ---
_original_build = v2_module.build_projection_source_token
_original_read = v2_module.get_runtime_source_asset
_original_write = v2_module.upsert_runtime_source_asset
_original_inject = PageAssembler._inject_relation_entry_contract
source_reads = []
source_writes = []
served_tokens = {}


def _probe_build(env_, **kwargs):
    base = _original_build(env_, **kwargs)
    if not base:
        return base
    served_tokens.setdefault("base", base)
    served_tokens.setdefault("model_name", kwargs.get("model_name"))
    served_tokens.setdefault("action_id", kwargs.get("action_id"))
    served_tokens.setdefault("menu_id", kwargs.get("menu_id"))
    served = hashlib.sha256((base + "|" + _NONCE["value"]).encode("utf-8")).hexdigest()
    served_tokens["served"] = served
    return served


def _probe_read(env_, **kwargs):
    result = _original_read(env_, **kwargs)
    _record("source_asset_read", "hit" if result else "miss")
    source_reads.append({"hit": bool(result)})
    return result


def _probe_write(env_, **kwargs):
    payload = kwargs.get("payload") if isinstance(kwargs.get("payload"), dict) else {}
    surface = _relation_surface(payload.get("ui_data") or {})
    result = _original_write(env_, **kwargs)
    _record("source_asset_write", "persisted" if result else "failed")
    source_writes.append({
        "cache_key": kwargs.get("cache_key"),
        "persisted": bool(result),
        "payload_sections": sorted(payload.keys()),
        "ui_data_sections": sorted((payload.get("ui_data") or {}).keys()),
        "persisted_source_relation_surface": surface,
    })
    return result


def _probe_inject(assembler, *args, **kwargs):
    result = _original_inject(assembler, *args, **kwargs)
    _record("relation_entry_inject", "")
    return result


def _run_trace(label, params):
    del EVENTS[:]
    del source_reads[:]
    del source_writes[:]
    served_tokens.clear()
    _NONCE["value"] = "%s|%s" % (PROBE_NONCE, label)
    v2_module.build_projection_source_token = _probe_build
    v2_module.get_runtime_source_asset = _probe_read
    v2_module.upsert_runtime_source_asset = _probe_write
    PageAssembler._inject_relation_entry_contract = _probe_inject
    try:
        result = adapt_handler_result(
            UiContractV2Handler(env=actor).handle({"params": dict(params)})
        )
    finally:
        v2_module.build_projection_source_token = _original_build
        v2_module.get_runtime_source_asset = _original_read
        v2_module.upsert_runtime_source_asset = _original_write
        PageAssembler._inject_relation_entry_contract = _original_inject
    write_seq = next(
        (event["seq"] for event in EVENTS if event["event"] == "source_asset_write"), None
    )
    injects = [event for event in EVENTS if event["event"] == "relation_entry_inject"]
    return {
        "surface": label,
        "request_params": dict(params),
        "handler_ok": isinstance(result, dict) and result.get("ok") is not False,
        "handler_error": (result.get("error") if isinstance(result, dict) else None),
        "cache_key": source_writes[-1]["cache_key"] if source_writes else "",
        "served_token_forced_miss": served_tokens.get("served"),
        "base_token": served_tokens.get("base"),
        "source_asset_write_seq": write_seq,
        "events": list(EVENTS),
        "write": source_writes[-1] if source_writes else None,
        "reads": list(source_reads),
        "relation_entry_inject_before_source_write": [
            {"seq": event["seq"], "caller": event["caller"]}
            for event in injects if write_seq and event["seq"] < write_seq
        ],
        "relation_entry_inject_after_source_write": [
            {"seq": event["seq"], "caller": event["caller"]}
            for event in injects if write_seq and event["seq"] > write_seq
        ],
        "source_asset_read_precedes_write": bool(
            source_reads and write_seq and EVENTS[0]["event"] == "source_asset_read"
        ),
    }


REPORT["step1_position"] = {
    "list": _run_trace("list", {"action_id": ACTION_ID, "op": "action_open"}),
    "form": _run_trace("form", {"action_id": ACTION_ID, "op": "action_open", "view_type": "form"}),
}

CACHE_KEY = REPORT["step1_position"]["list"]["cache_key"]
assert CACHE_KEY, "the real handler did not produce a runtime source cache key"
env.cr.rollback()

# --- step 2: old source present -> code identity change -> old source rejected
ROLE_CODE = cache_store.projection_role_code(actor)
COMPANY = int(actor.company.id)
RELATIVE = "smart_core/app_config_engine/services/assemblers/page_assembler.py"
tmp_root = Path(tempfile.mkdtemp(prefix="sce-cache-identity-"))
probe_file = tmp_root / RELATIVE
probe_file.parent.mkdir(parents=True, exist_ok=True)
probe_file.write_bytes(owner_paths["page_assembler.py"].read_bytes())

MARKER = {"source_type": "identity_probe", "ui_data": {"probe_marker": "old-source"}, "ui_meta": {}}
tmp_token_1 = _under_root(tmp_root, lambda: _token(actor, model_name=MODEL, action_id=ACTION_ID, menu_id=None))
tmp_legacy_1 = _legacy_digest(tmp_root)
written = asset_repo.upsert_runtime_source_asset(
    actor, cache_key=CACHE_KEY, source_token=tmp_token_1, payload=MARKER,
    role_code=ROLE_CODE, company_id=COMPANY, source_ref="cache-identity-probe",
)
old_source = _lookup(CACHE_KEY, tmp_token_1, ROLE_CODE, COMPANY)
old_present = (old_source.get("ui_data") or {}).get("probe_marker") == "old-source"

stat_before = probe_file.stat()
content_before = hashlib.sha256(probe_file.read_bytes()).hexdigest()
content_bytes = bytearray(probe_file.read_bytes())
content_bytes[-2] = (content_bytes[-2] + 1) % 256
probe_file.write_bytes(bytes(content_bytes))
os.utime(probe_file, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns))
stat_after = probe_file.stat()
content_after = hashlib.sha256(probe_file.read_bytes()).hexdigest()
tmp_token_2 = _under_root(tmp_root, lambda: _token(actor, model_name=MODEL, action_id=ACTION_ID, menu_id=None))
tmp_legacy_2 = _legacy_digest(tmp_root)
after_change = _lookup(CACHE_KEY, tmp_token_2, ROLE_CODE, COMPANY)

# A source row written under the NEW content identity, so the metadata-only case
# below can prove the identity does not drift on its own (no false invalidation
# and therefore no needless rebuild).
asset_repo.upsert_runtime_source_asset(
    actor, cache_key=CACHE_KEY, source_token=tmp_token_2, payload=MARKER,
    role_code=ROLE_CODE, company_id=COMPANY, source_ref="cache-identity-probe-metadata",
)
new_source = _lookup(CACHE_KEY, tmp_token_2, ROLE_CODE, COMPANY)
new_present = (new_source.get("ui_data") or {}).get("probe_marker") == "old-source"

mtime_only_ns = stat_after.st_mtime_ns + 1_000_000
os.utime(probe_file, ns=(stat_after.st_atime_ns, mtime_only_ns))
tmp_token_3 = _under_root(tmp_root, lambda: _token(actor, model_name=MODEL, action_id=ACTION_ID, menu_id=None))
after_touch = _lookup(CACHE_KEY, tmp_token_3, ROLE_CODE, COMPANY)

REPORT["step2_identity_change"] = {
    "cache_key": CACHE_KEY,
    "role_code": ROLE_CODE,
    "company_id": COMPANY,
    "row_written": bool(written),
    "old_source_present": old_present,
    "content_change_same_size_same_mtime": {
        "size_equal": stat_before.st_size == stat_after.st_size,
        "mtime_equal": stat_before.st_mtime_ns == stat_after.st_mtime_ns,
        "content_changed": content_before != content_after,
        "ctime_changed": stat_before.st_ctime_ns != stat_after.st_ctime_ns,
        "token_unchanged_by_content": tmp_token_1 == tmp_token_2,
        "legacy_row_tuple_unchanged": tmp_legacy_1 == tmp_legacy_2,
        "old_source_still_served": bool(after_change),
    },
    "mtime_only_change": {
        "rows_written_under_new_identity": bool(new_present),
        "token_unchanged_by_metadata": tmp_token_2 == tmp_token_3,
        "token_unchanged_vs_initial_identity": tmp_token_1 == tmp_token_3,
        "old_source_still_served": bool(after_touch),
        "note": (
            "the identity must be compared against the post-content-change token "
            "(tmp_token_2), not the initial one: a metadata-only touch on unchanged "
            "content must not move the identity and must not invalidate the row "
            "written under the current content identity"
        ),
    },
    "token_initial": tmp_token_1,
    "token_after_content_change": tmp_token_2,
    "token_after_mtime_touch": tmp_token_3,
}

shutil.rmtree(str(tmp_root), ignore_errors=True)
REPORT["step2_identity_change"]["temp_root_removed"] = not tmp_root.exists()

# --- step 3: verdict --------------------------------------------------------
content_case = REPORT["step2_identity_change"]["content_change_same_size_same_mtime"]
list_trace = REPORT["step1_position"]["list"]
form_trace = REPORT["step1_position"]["form"]
REPORT["verdict"] = {
    "list_source_write_after_relation_injection": bool(
        list_trace["relation_entry_inject_before_source_write"]
    ),
    "list_delivered_relation_injection_after_source_write": bool(
        list_trace["relation_entry_inject_after_source_write"]
    ),
    "form_source_write_after_relation_injection": bool(
        form_trace["relation_entry_inject_before_source_write"]
    ),
    "form_late_relation_injection_after_source_write": bool(
        form_trace["relation_entry_inject_after_source_write"]
    ),
    "persisted_source_token_tracks_code_fingerprint": REPORT["step0_identity"]["token_changes_with_code_fingerprint"],
    "same_size_content_change_reaches_the_token": not content_case["token_unchanged_by_content"],
    "old_source_rejected_after_identity_change": bool(
        content_case["content_changed"] and not content_case["old_source_still_served"]
    ),
    "metadata_only_change_keeps_the_identity": REPORT["step2_identity_change"]["mtime_only_change"][
        "token_unchanged_by_metadata"
    ],
    "metadata_only_change_does_not_force_a_rebuild": bool(
        content_case["content_changed"]
        and REPORT["step2_identity_change"]["mtime_only_change"]["rows_written_under_new_identity"]
        and REPORT["step2_identity_change"]["mtime_only_change"]["old_source_still_served"]
    ),
    "ttl_not_involved": (
        "the persisted runtime source asset has no expiry column; rejection is by "
        "asset_version (source token) and status only"
    ),
}
REPORT["limitations"] = [
    "in-process probe on the registered local demo principal and one observed action",
    "the identity-change case uses a temp identity root in the container /tmp holding a byte-identical copy of the real assembler",
    "the real root is not writable for the container user, so no real code file was mutated",
    "not an SLO, capacity or cross-role claim; no freeze, commit, push or deployment",
]
env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("CACHE_IDENTITY_PROBE_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
