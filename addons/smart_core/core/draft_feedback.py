"""Controlled draft feedback evaluation over the existing onchange transport.

The browser may describe one server-authorized native advisory binding and
evaluate an exact dependency snapshot.  The server owns the binding identity,
authorization checks, native compute implementation and result visibility.
Nothing in this module persists state or returns an ordinary form patch.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
from copy import deepcopy
from datetime import date

from odoo.exceptions import AccessError

from . import native_advisory
from .form_configuration_compiler import FormConfigurationError
from .node_component_validation import walk

VERSION = "1.0.0"
CAPABILITY = native_advisory.DRAFT_FEEDBACK_CAPABILITY
COMPONENT_KEY = "sc.feedback.message"
COMPONENT_VERSION = "1.0.0"
PURPOSE = "advisory"
VISIBILITY_OWNER = native_advisory.DRAFT_FEEDBACK_VISIBILITY_OWNER
RELATION_PRESENCE = "many2one_presence"
RELATION_INPUT_TYPES = {RELATION_PRESENCE: "many2one", "many2many_presence": "many2many"}
SCALAR_INPUT_TYPES = frozenset({"date", "text", "char", "selection", "number_nonzero"})
SUPPORTED_INPUT_TYPES = SCALAR_INPUT_TYPES | set(RELATION_INPUT_TYPES)
REQUEST_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
DIAGNOSTIC_STATUS = {
    "FEEDBACK_CONFIG_INVALID": 400,
    "FEEDBACK_INPUT_INVALID": 422,
    "FEEDBACK_SOURCE_INVALID": 422,
    "FEEDBACK_SOURCE_FORBIDDEN": 403,
    "FEEDBACK_CONDITION_INVALID": 422,
    "FEEDBACK_BINDING_STALE": 409,
    "FEEDBACK_EVALUATION_FAILED": 500,
    "COMPONENT_CAPABILITY_REQUIRED": 409,
}


class DraftFeedbackError(Exception):
    """A safe feedback diagnostic; field values and permission objects stay out."""

    def __init__(self, code, path="feedback_evaluation", request_id=""):
        self.code = code
        self.path = path
        self.request_id = request_id if isinstance(request_id, str) else ""
        self.http_status = DIAGNOSTIC_STATUS.get(code, 500)
        super().__init__(code)

    def public_details(self):
        feedback = {
            "version": VERSION,
            "status": "failed",
            "diagnostic": {"code": self.code, "path": self.path},
        }
        if REQUEST_ID_RE.fullmatch(self.request_id):
            feedback["request_id"] = self.request_id
        return {"feedback_evaluation": feedback}


def fail(code, path="feedback_evaluation", request_id=""):
    raise DraftFeedbackError(code, path, request_id)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _context_identity(env):
    cr = getattr(env, "cr", None)
    company = getattr(env, "company", None)
    companies = getattr(env, "companies", None)
    user = getattr(env, "user", None)
    return {
        "database": getattr(cr, "dbname", ""),
        "uid": getattr(env, "uid", getattr(user, "id", False)),
        "company": getattr(company, "id", False),
        "companies": tuple(getattr(companies, "ids", ()) or ()),
        "sudo": bool(getattr(env, "su", False)),
    }


def decode_request(block):
    """Decode the strict public request without executing or authorizing it."""
    if type(block) is not dict:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation")
    operation = block.get("operation")
    if operation not in {"describe", "evaluate"}:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.operation")
    common = {"version", "operation", "request_id", "view_id", "container_id"}
    expected = common | ({"binding_etag", "inputs"} if operation == "evaluate" else set())
    if set(block) != expected:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation")
    if block.get("version") != VERSION:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.version")
    request_id = block.get("request_id")
    if type(request_id) is not str or not REQUEST_ID_RE.fullmatch(request_id):
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.request_id")
    view_id = block.get("view_id")
    if type(view_id) is not int or view_id <= 0:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.view_id", request_id)
    container_id = block.get("container_id")
    if type(container_id) is not str or not container_id or len(container_id) > 256:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.container_id", request_id)
    decoded = {
        "version": VERSION,
        "operation": operation,
        "request_id": request_id,
        "view_id": view_id,
        "container_id": container_id,
    }
    if operation == "describe":
        return decoded
    binding_etag = block.get("binding_etag")
    if type(binding_etag) is not str or not SHA256_RE.fullmatch(binding_etag):
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.binding_etag", request_id)
    inputs = block.get("inputs")
    if type(inputs) is not list:
        fail("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.inputs", request_id)
    seen = set()
    decoded_inputs = []
    for index, item in enumerate(inputs):
        path = f"feedback_evaluation.inputs[{index}]"
        if type(item) is not dict or set(item) not in ({"field", "present"}, {"field", "present", "value"}):
            fail("FEEDBACK_CONFIG_INVALID", path, request_id)
        name, present = item.get("field"), item.get("present")
        if type(name) is not str or not name or type(present) is not bool or name in seen:
            fail("FEEDBACK_CONFIG_INVALID", path, request_id)
        if present is False and set(item) != {"field", "present"}:
            fail("FEEDBACK_CONFIG_INVALID", path, request_id)
        if present is True and (set(item) != {"field", "present", "value"}
                                or not (type(item.get("value")) is bool or type(item.get("value")) is str)):
            fail("FEEDBACK_CONFIG_INVALID", path, request_id)
        seen.add(name)
        decoded_inputs.append(deepcopy(item))
    decoded.update(binding_etag=binding_etag, inputs=decoded_inputs)
    return decoded


def _method_source_sha256(method):
    function = getattr(method, "__func__", method)
    try:
        source = inspect.getsource(function)
    except (OSError, TypeError) as exc:
        raise DraftFeedbackError("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.binding") from exc
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def reviewed_content_field(model, field):
    """Resolve the reviewed input/compute contract from runtime declarations."""
    method = getattr(model, field.compute, None) if isinstance(field.compute, str) else None
    declared_method = getattr(method, "__func__", method)
    review = getattr(declared_method, "_sc_feedback_evaluation_review", None)
    if (method is None or type(review) is not dict or set(review) != {"purpose", "inputs"}
            or review.get("purpose") != PURPOSE or type(review.get("inputs")) is not list):
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.binding")
    entries = review["inputs"]
    names, expected_types = [], {}
    for index, item in enumerate(entries):
        if type(item) is not dict or set(item) != {"field", "type"}:
            fail("FEEDBACK_SOURCE_INVALID", f"feedback_evaluation.binding.inputs[{index}]")
        name, field_type = item.get("field"), item.get("type")
        if (type(name) is not str or not name or name in expected_types
                or field_type not in SUPPORTED_INPUT_TYPES):
            fail("FEEDBACK_SOURCE_INVALID", f"feedback_evaluation.binding.inputs[{index}]")
        names.append(name)
        expected_types[name] = field_type
    if (field.type not in {"char", "text"} or field.store or field.compute_sudo
            or field.related or field.inverse or not field.compute):
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.binding.content")
    dependencies, context_dependencies = field.get_depends(model)
    if context_dependencies or tuple(dependencies) != tuple(names):
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.binding.inputs")
    selection_options = {}
    for name, expected_type in expected_types.items():
        dependency = model._fields.get(name)
        actual_type = RELATION_INPUT_TYPES.get(expected_type, expected_type)
        allowed_types = {"integer", "float", "monetary"} if expected_type == "number_nonzero" else {actual_type}
        if (dependency is None or dependency.type not in allowed_types or dependency.compute
                or dependency.related or dependency.inverse):
            fail("FEEDBACK_SOURCE_INVALID", f"feedback_evaluation.binding.inputs.{name}")
        if expected_type == "selection":
            options = [key for key, _label in dependency._description_selection(model.env)]
            if not options or any(type(key) is not str or not key for key in options) or len(set(options)) != len(options):
                fail("FEEDBACK_SOURCE_INVALID", f"feedback_evaluation.binding.inputs.{name}")
            selection_options[name] = options
    return {
        "compute": field.compute,
        "implementation_sha256": _method_source_sha256(method),
        "inputs": [{"field": name, "type": expected_types[name]} for name in names],
        "review_sha256": _sha256({"review": review, "selection_options": selection_options}) if selection_options else _sha256(review),
        "selection_options": selection_options,
    }


class ControlledDraftProof:
    """Request-local proof used only when final validation has no persisted record."""

    def __init__(self, model, view_id):
        self.model = model
        self.view_id = view_id
        self._content = {}

    def review(self, field):
        name = field.name
        if name not in self._content:
            self._content[name] = reviewed_content_field(self.model, field)
        return self._content[name]

    def validate_source(self, env, model_name, field, host, source, originals, path):
        if model_name != self.model._name or getattr(field, "sc_feedback_usage", None) is None:
            fail("FEEDBACK_SOURCE_INVALID", path)
        invisible = native_advisory.validate_binding(
            env, model_name, field, host, source, originals, path,
        )
        self.review(field)
        return invisible


def _native_layout(model, view_id):
    from lxml import etree

    env = model.env
    try:
        # get_view is the current-user authorization boundary. The stored view
        # row is read afterwards only to verify model/type identity; ordinary
        # business users are not required to hold backend ir.ui.view ACLs.
        view_data = model.get_view(view_id=view_id, view_type="form")
        view = env["ir.ui.view"].sudo().browse(view_id)
        if (not view.exists() or view.model != model._name or view.type != "form"
                or view_data.get("model", model._name) != model._name):
            fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.view_id")
        arch = view_data["arch"]
        metadata = model.fields_get()
        layout = env["app.view.parser"]._extract_form_layout_dom(
            etree.fromstring(arch.encode() if isinstance(arch, str) else arch),
            metadata,
        )
    except DraftFeedbackError:
        raise
    except AccessError:
        fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.view_id")
    except Exception as exc:
        raise DraftFeedbackError("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.view_id") from exc
    return layout, metadata


def _assemble_contract(model, view_id):
    from .unified_page_contract_v2_assembler import assemble_unified_page_contract_v2
    layout, metadata = _native_layout(model, view_id)
    projected_layout = deepcopy(layout)
    source = {
        "model": model._name,
        "view_type": "form",
        "view_id": view_id,
        "fields": metadata,
        # Both carriers intentionally share this graph. native_advisory.project
        # rewrites the projection marker; the UI assembler consumes views.form.
        # A deep copy of the whole source preserves this alias as one tree.
        "nativeFormProjection": {"layout": projected_layout, "fieldDescriptors": metadata},
        "views": {"form": {"layout": projected_layout}},
    }
    proof = ControlledDraftProof(model, view_id)
    contract = assemble_unified_page_contract_v2(
        source,
        source_type="ui.contract",
        node_actor_env=model.env,
        draft_feedback=proof,
    )
    return contract, proof


def _binding(model, contract, proof, view_id, container_id, request_id):
    rows = list(walk((contract.get("layoutContract") or {}).get("containerTree") or []))
    hosts = [node for node, _ in rows if node.get("containerId") == container_id]
    if len(hosts) != 1 or hosts[0].get("componentKey") != COMPONENT_KEY:
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.container_id", request_id)
    host = hosts[0]
    config = host.get("componentConfig")
    ref = config.get("contentRef") if isinstance(config, dict) else None
    ref_id = ref.get("containerId") if isinstance(ref, dict) else None
    sources = [node for node, _ in rows if node.get("containerId") == ref_id]
    evaluation = config.get("evaluation") if isinstance(config, dict) else None
    if (type(config) is not dict or set(config) != {"purpose", "contentRef", "evaluation"}
            or config.get("purpose") != PURPOSE or type(ref_id) is not str or len(sources) != 1
            or type(evaluation) is not dict or set(evaluation) != {"capability", "visibilityOwner"}
            or evaluation.get("capability") != CAPABILITY
            or evaluation.get("visibilityOwner") != VISIBILITY_OWNER):
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.container_id", request_id)
    source = sources[0]
    field_name = source.get("name")
    field = model._fields.get(field_name) if type(field_name) is str else None
    if field is None or getattr(field, "sc_feedback_usage", None) is None or source.get("type") != "field":
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.container_id", request_id)
    review = proof.review(field)
    registry = (contract.get("layoutContract") or {}).get("componentRegistry") or {}
    registration = registry.get(COMPONENT_KEY)
    if (not isinstance(registration, dict) or registration.get("version") != COMPONENT_VERSION):
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.component", request_id)
    invisible = native_advisory.condition(host, field_name, "feedback_evaluation.condition")
    locator = source.get("nativeLocator") or source.get("native_locator")
    occurrence = source.get("occurrenceIndex") or source.get("occurrence_index")
    if type(locator) is not str or type(occurrence) is not int or occurrence <= 0:
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.binding", request_id)
    projection = {
        "version": VERSION,
        "model": model._name,
        "view_id": view_id,
        "container_id": container_id,
        "source_container_id": ref_id,
        "native_locator": locator,
        "occurrence_index": occurrence,
        "component_key": COMPONENT_KEY,
        "component_version": COMPONENT_VERSION,
        "purpose": PURPOSE,
        "visibility_owner": VISIBILITY_OWNER,
        "dependencies": review["inputs"],
        "condition": invisible,
        "compute": {
            "name": review["compute"],
            "implementation_sha256": review["implementation_sha256"],
            "review_sha256": review["review_sha256"],
        },
    }
    return host, source, field, review, {**projection, "etag": _sha256(projection)}


def _check_source_authorization(model, field, origin):
    env = model.env
    if env.su:
        fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.context")
    allowed_company_ids = env.context.get("allowed_company_ids")
    if allowed_company_ids is None:
        allowed_company_ids = [env.company.id]
    if (type(allowed_company_ids) is not list
            or not allowed_company_ids
            or any(type(company_id) is not int or company_id <= 0 for company_id in allowed_company_ids)
            or any(company_id not in env.user.company_ids.ids for company_id in allowed_company_ids)
            or env.company.id not in allowed_company_ids):
        fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.company")
    names = [field.name, *[item["field"] for item in reviewed_content_field(model, field)["inputs"]]]
    try:
        model.check_access_rights("read")
        model.check_access_rights("create" if origin is None else "write")
        allowed = model.check_field_access_rights("read", names)
        if allowed is None or not set(names).issubset(allowed):
            fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.source")
        if origin is not None:
            if (origin._name != model._name or origin.env is not env or len(origin) != 1
                    or type(origin.id) is not int or origin.id <= 0 or not origin.exists()):
                fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.record")
            origin.check_access_rule("read")
            origin.check_access_rule("write")
            if model.search([("id", "=", origin.id)], limit=1) != origin:
                fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.record")
    except DraftFeedbackError:
        raise
    except AccessError as exc:
        raise DraftFeedbackError("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.source") from exc


def _decoded_inputs(inputs, dependencies, request_id, selection_options=None):
    expected = {item["field"]: item["type"] for item in dependencies}
    if len(inputs) != len(expected):
        fail("FEEDBACK_INPUT_INVALID", "feedback_evaluation.inputs", request_id)
    values = {}
    for index, item in enumerate(inputs):
        name = item.get("field")
        path = f"feedback_evaluation.inputs[{index}]"
        if name not in expected or name in values:
            fail("FEEDBACK_INPUT_INVALID", path, request_id)
        if item.get("present") is not True:
            fail("FEEDBACK_INPUT_INVALID", path + ".present", request_id)
        value = item.get("value")
        if expected[name] == "date" and value is not False:
            if type(value) is not str:
                fail("FEEDBACK_INPUT_INVALID", path + ".value", request_id)
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError as exc:
                raise DraftFeedbackError("FEEDBACK_INPUT_INVALID", path + ".value", request_id) from exc
        if expected[name] in {"text", "char"} and value is not False and type(value) is not str:
            fail("FEEDBACK_INPUT_INVALID", path + ".value", request_id)
        if expected[name] in RELATION_INPUT_TYPES and type(value) is not bool:
            fail("FEEDBACK_INPUT_INVALID", path + ".value", request_id)
        if expected[name] == "number_nonzero" and type(value) is not bool:
            fail("FEEDBACK_INPUT_INVALID", path + ".value", request_id)
        if expected[name] == "selection" and value is not False:
            if type(value) is not str or value not in (selection_options or {}).get(name, ()):
                fail("FEEDBACK_INPUT_INVALID", path + ".value", request_id)
        values[name] = value
    if set(values) != set(expected):
        fail("FEEDBACK_INPUT_INVALID", "feedback_evaluation.inputs", request_id)
    return values


def _condition_invisible(condition, facts):
    def evaluate(value):
        if type(value) is dict and value.get("kind") == "not":
            return not evaluate(value.get("expr"))
        if type(value) is dict and value.get("kind") == "field_truthy":
            return bool(facts.get(value.get("field")))
        if type(value) is bool:
            return value
        fail("FEEDBACK_CONDITION_INVALID", "feedback_evaluation.condition")
    return bool(evaluate(condition))


def _evaluate_native(model, field, review, values, condition, request_id):
    from odoo.models import NewId

    snapshot = _context_identity(model.env)
    try:
        native_values = {}
        for item in review["inputs"]:
            name, expected = item["field"], item["type"]
            value = values[name]
            if expected in RELATION_INPUT_TYPES:
                dependency = model._fields[name]
                # A NewId comodel record carries presence only. It is never read
                # for id/display_name/attributes and never persisted.
                native_values[name] = model.env[dependency.comodel_name].new({}) if value else False
            elif expected == "date":
                native_values[name] = date.fromisoformat(value) if value is not False else False
            elif expected == "number_nonzero":
                # Reviewed computes may inspect truthiness only, never magnitude
                # or sign. Actual amounts/period numbers never cross this wire.
                native_values[name] = 1 if value else 0
            else:
                native_values[name] = value
        draft = model.new(native_values)
        if not isinstance(draft.id, NewId) or draft._origin:
            fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.record", request_id)
        for item in review["inputs"]:
            name, expected = item["field"], item["type"]
            actual = draft[name]
            if expected == "date":
                expected_value = date.fromisoformat(values[name]) if values[name] is not False else False
            elif expected in RELATION_INPUT_TYPES:
                expected_value = values[name]
                normalized = bool(actual)
            elif expected == "number_nonzero":
                expected_value = values[name]
                normalized = bool(actual)
            else:
                expected_value = values[name]
            if expected not in RELATION_INPUT_TYPES and expected != "number_nonzero":
                normalized = False if actual in (None, False) else actual
            if expected in {"text", "char"}:
                normalized = normalized or ""
                expected_value = expected_value or ""
            if normalized != expected_value:
                fail("FEEDBACK_INPUT_INVALID", f"feedback_evaluation.inputs.{name}", request_id)
        content = draft[field.name]
    except DraftFeedbackError:
        raise
    except Exception as exc:
        raise DraftFeedbackError("FEEDBACK_EVALUATION_FAILED", "feedback_evaluation.result", request_id) from exc
    if content is False:
        content = ""
    if type(content) is not str:
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.content", request_id)
    facts = {field.name: content, **values}
    visible = not _condition_invisible(condition, facts)
    if visible and not content:
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.content", request_id)
    if not visible:
        content = ""
    if _context_identity(model.env) != snapshot:
        fail("FEEDBACK_SOURCE_INVALID", "feedback_evaluation.context", request_id)
    return {"content": content, "visible": visible}


def evaluate(model, block, *, origin=None):
    """Describe or evaluate one controlled binding in the authenticated env."""
    request = decode_request(block)
    request_id = request["request_id"]
    if model.env.su:
        fail("FEEDBACK_SOURCE_FORBIDDEN", "feedback_evaluation.context", request_id)
    contract, proof = _assemble_contract(model, request["view_id"])
    host, source, field, review, binding = _binding(
        model, contract, proof, request["view_id"], request["container_id"], request_id,
    )
    _check_source_authorization(model, field, origin)
    if request["operation"] == "describe":
        return {
            "version": VERSION,
            "request_id": request_id,
            "status": "described",
            "binding": {
                key: deepcopy(binding[key]) for key in (
                    "etag", "model", "view_id", "container_id", "source_container_id",
                    "native_locator", "occurrence_index", "component_key",
                    "component_version", "purpose", "dependencies", "visibility_owner",
                )
            },
        }
    if request["binding_etag"] != binding["etag"]:
        fail("FEEDBACK_BINDING_STALE", "feedback_evaluation.binding_etag", request_id)
    values = _decoded_inputs(request["inputs"], review["inputs"], request_id, review["selection_options"])
    result = _evaluate_native(model, field, review, values, binding["condition"], request_id)
    return {
        "version": VERSION,
        "request_id": request_id,
        "status": "ready",
        "binding_etag": binding["etag"],
        "container_id": request["container_id"],
        "result": result,
    }
