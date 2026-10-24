"""R6.1 test-only adapter. Never imported by a handler or production model.

No business calculation is reproduced here: a native new record and its field
descriptor invoke the reviewed industry compute. Inputs are ordered pairs so
duplicates remain detectable before normalization. No fallback to saved values.
"""
from dataclasses import dataclass
from datetime import date

from odoo.exceptions import AccessError
from odoo.models import NewId
from odoo.addons.smart_core.core import native_advisory
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import _evaluate_action_modifier
from ..models.support.team_loan_deduction_workspace import ScTeamLoanDeductionWorkspace

MODEL = 'sc.team.loan.deduction.workspace'
CONTENT = 'processing_advisory'
DEPENDENCIES = ('business_date', 'note')
VIEW = 'smart_construction_core.view_sc_team_loan_deduction_workspace_form'
LOCATOR = '/form[1]/sheet[1]/div[1]/field[1]'


class DraftRejected(ValueError):
    """Internal test outcome; no values or restricted field names in errors."""


def context_identity(model):
    env = model.env
    return (env.cr.dbname, id(env), env.uid, env.company.id, tuple(env.companies.ids), env.su)


@dataclass(frozen=True)
class DraftResult:
    content: str
    invisible: bool
    visible: bool
    context: tuple
    native_id: object


def normalize(pairs):
    if type(pairs) is not list:
        raise DraftRejected('INPUT_INVALID')
    values = {}
    for pair in pairs:
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise DraftRejected('INPUT_INVALID')
        key, value = pair
        if type(key) is not str or key not in DEPENDENCIES or key in values:
            raise DraftRejected('INPUT_INVALID')
        values[key] = value
    if set(values) != set(DEPENDENCIES):
        raise DraftRejected('INPUT_MISSING')
    day, note = values['business_date'], values['note']
    if day is not False:
        if type(day) is not str:
            raise DraftRejected('INPUT_INVALID')
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError()
        except ValueError as exc:
            raise DraftRejected('INPUT_INVALID') from exc
    if note is not False and type(note) is not str:
        raise DraftRejected('INPUT_INVALID')
    return values


def evaluate(model, pairs, *, view_id, layout, expected_context, origin=None):
    """One synchronous evaluation; no cache, stored state or public protocol.

    `layout` is the trusted parser output, not browser-supplied tree data. A
    future integration must establish this trust boundary independently.
    `origin`, when supplied, is a native existing record used only for ACL/rule
    checks, never as a substitute for a complete current draft input.
    """
    if model._name != MODEL or model or model.env.su:
        raise DraftRejected('CONTEXT_INVALID')
    snapshot = context_identity(model)
    if expected_context != snapshot:
        raise DraftRejected('CONTEXT_INVALID')
    values = normalize(pairs)
    field = model._fields[CONTENT]
    # Pin the reviewed implementation, not merely its decorator or name.
    method = getattr(model, field.compute, None) if isinstance(field.compute, str) else None
    if (getattr(method, '__func__', None) is not ScTeamLoanDeductionWorkspace._compute_processing_advisory
            or field.type != 'char' or field.store or field.compute_sudo or field.related
            or field.inverse):
        raise DraftRejected('SOURCE_INVALID')
    deps, context_deps = field.get_depends(model)
    if tuple(deps) != DEPENDENCIES or context_deps:
        raise DraftRejected('SOURCE_INVALID')
    for name, expected_type in [('business_date', 'date'), ('note', 'text')]:
        dependency = model._fields.get(name)
        if (not dependency or dependency.type != expected_type or dependency.compute
                or dependency.related or dependency.inverse):
            raise DraftRejected('SOURCE_INVALID')
    names = [CONTENT, *DEPENDENCIES]
    try:
        model.check_access_rights('read')
        model.check_access_rights('create' if origin is None else 'write')
        if set(model.check_field_access_rights('read', names)) != set(names):
            raise AccessError('Restricted source')
        if origin is not None:
            if (origin._name != MODEL or origin.env is not model.env or len(origin) != 1
                    or type(origin.id) is not int or origin.id <= 0 or not origin.exists()):
                raise DraftRejected('CONTEXT_INVALID')
            origin.check_access_rule('read')
            origin.check_access_rule('write')
            # Confirm exact current-user search visibility as well as ir.rule.
            # Do not infer a creator-only rule from the model's transient flag.
            if model.search([('id', '=', origin.id)], limit=1) != origin:
                raise AccessError('Restricted source')
    except AccessError as exc:
        raise DraftRejected('SOURCE_FORBIDDEN') from exc
    rows = native_advisory.bindings(model.env, MODEL, field, view_id, 'draft.source')
    if not rows or len(rows) != 1:
        raise DraftRejected('SOURCE_INVALID')
    row = rows[0]
    if row != {'view_xmlid': VIEW, 'native_locator': LOCATOR, 'occurrence_index': 1}:
        raise DraftRejected('SOURCE_INVALID')
    matches = [(n, p) for n, p in native_advisory.walk(layout)
               if native_advisory.identity(n) == (row['native_locator'], row['occurrence_index'])]
    if len(matches) != 1:
        raise DraftRejected('SOURCE_INVALID')
    source, host = matches[0]
    if source.get('type') != 'field' or source.get('name') != CONTENT:
        raise DraftRejected('SOURCE_INVALID')
    native_advisory.host_shape(host, source, 'draft.source')
    condition = native_advisory.condition(host, CONTENT, 'draft.condition')
    # `new` is an in-memory ORM record. Reading the descriptor triggers the
    # actual registered compute; no onchange or business method is called.
    draft = model.new(values)
    if not isinstance(draft.id, NewId) or draft._origin:
        raise DraftRejected('CONTEXT_INVALID')
    content = draft[CONTENT]
    expected_day = date.fromisoformat(values['business_date']) if values['business_date'] else False
    if draft.business_date != expected_day or (draft.note or '') != (values['note'] or ''):
        raise DraftRejected('INPUT_CHANGED')
    if content is False:
        content = ''  # Odoo Char's explicit empty representation, not missing input.
    if type(content) is not str:
        raise DraftRejected('CONTENT_INVALID')
    invisible = _evaluate_action_modifier(condition, {CONTENT: content}, strict=True)
    if type(invisible) is not bool:
        raise DraftRejected('CONDITION_INVALID')
    if context_identity(model) != snapshot:
        raise DraftRejected('CONTEXT_INVALID')
    return DraftResult(content, invisible, not invisible and bool(content), snapshot, draft.id)
