"""Build Odoo 17 onchange output fields from the authorized native form."""
from xml.etree import ElementTree as etree


class NativeOnchangeSpecError(ValueError):
    pass


def build_native_onchange_spec(model, view_id=None):
    # get_view applies the current user's group restrictions and inherited views.
    view = model.get_view(view_id=view_id, view_type="form")
    if view.get("id"):
        # Metadata-only binding after current-user get_view, as in draft_feedback.
        source = model.env["ir.ui.view"].sudo().browse(view["id"])
        if source.model != model._name or source.type != "form":
            raise NativeOnchangeSpecError("view model/type mismatch")
    arch = view.get("arch")
    if not isinstance(arch, (str, bytes)) or not arch:
        raise NativeOnchangeSpecError("missing form architecture")
    try:
        root = etree.fromstring(arch)
    except etree.ParseError as exc:
        raise NativeOnchangeSpecError("invalid form XML") from exc
    if root.tag != "form":
        raise NativeOnchangeSpecError("invalid form architecture")

    def merge(target, incoming):
        for name, spec in incoming.items():
            current = target.setdefault(name, {})
            if "fields" in spec:
                merge(current.setdefault("fields", {}), spec["fields"])

    # Self-referential implicit subviews (for example res.partner.child_ids)
    # must not resolve infinitely. Explicit subviews are finite XML and are not
    # guarded here; only the unbounded comodel-default fallback is.
    resolving = set()

    def implicit_subview(current_model, field):
        """Resolve an x2many field that has no explicit inline subview.

        The child onchange fields come from the comodel's default form view,
        still scoped to the current user by ``get_view``. The result is merged
        exactly like an explicit subview and carries the same fail-closed
        semantics (unknown view field or read-denied field raises).
        """
        comodel_name = field.comodel_name
        if comodel_name in resolving:
            return {}
        resolving.add(comodel_name)
        try:
            comodel = current_model.env[comodel_name]
            comodel.check_access_rights("read")
            implicit = comodel.get_view(view_type="form")
            implicit_arch = implicit.get("arch") if isinstance(implicit, dict) else None
            if not isinstance(implicit_arch, (str, bytes)) or not implicit_arch:
                raise NativeOnchangeSpecError("missing implicit relation subview")
            try:
                implicit_root = etree.fromstring(implicit_arch)
            except etree.ParseError as exc:
                raise NativeOnchangeSpecError("invalid implicit relation subview") from exc
            if implicit_root.tag != "form":
                raise NativeOnchangeSpecError("invalid implicit relation subview architecture")
            return collect(comodel, implicit_root)
        finally:
            resolving.discard(comodel_name)

    def collect(current_model, container):
        current_model.check_access_rights("read")
        result = {}

        def walk(node):
            for child in node:
                if child.tag != "field":
                    walk(child)
                    continue
                name = child.get("name")
                field = current_model._fields.get(name)
                if not field:
                    raise NativeOnchangeSpecError("unknown view field")
                current_model.check_field_access_rights("read", [name])
                spec = {}
                if field.type == "many2one":
                    spec["fields"] = {"display_name": {}}
                if field.type in ("one2many", "many2many"):
                    nested = {}
                    explicit = False
                    for subview in child:
                        if subview.tag in ("tree", "list", "form", "kanban"):
                            explicit = True
                            merge(nested, collect(current_model.env[field.comodel_name], subview))
                    if not explicit:
                        nested = implicit_subview(current_model, field)
                    if nested:
                        spec["fields"] = nested
                merge(result, {name: spec})
        walk(container)
        return result

    return collect(model, root)


def normalize_native_onchange_values(model, values):
    """Keep the public relation wire format while consuming web_read objects."""
    output = dict(values)
    for name, value in values.items():
        field = model._fields.get(name)
        if field is None:
            continue
        if field.type == "many2one" and isinstance(value, dict):
            record_id = value.get("id")
            if record_id is False:
                output[name] = False
            elif type(record_id) is int and record_id > 0 and isinstance(value.get("display_name"), str):
                output[name] = [record_id, value["display_name"]]
            else:
                raise NativeOnchangeSpecError("invalid native many2one result")
        elif field.type in ("one2many", "many2many") and isinstance(value, (list, tuple)):
            commands = []
            for command in value:
                if (isinstance(command, (list, tuple)) and len(command) == 3
                        and command[0] in (0, 1, 4) and isinstance(command[2], dict)):
                    commands.append([command[0], command[1], normalize_native_onchange_values(
                        model.env[field.comodel_name], command[2])])
                else:
                    commands.append(command)
            output[name] = commands
    return output


def initialize_native_child(parent, parent_values, parent_spec, block, parent_id=0):
    return _evaluate_native_child(parent, parent_values, parent_spec, block, parent_id, initialize=True)


def onchange_native_child(parent, parent_values, parent_spec, block, parent_id=0):
    return _evaluate_native_child(parent, parent_values, parent_spec, block, parent_id, initialize=False)


def _evaluate_native_child(parent, parent_values, parent_spec, block, parent_id, *, initialize):
    """Run child ORM semantics with the authorized parent view and inverse."""
    keys = {'field', 'fields', 'values'} if initialize else {'field', 'fields', 'values', 'changed_fields', 'record_id'}
    if type(block) is not dict or set(block) != keys:
        raise NativeOnchangeSpecError('invalid child initialization request')
    name, names, values = block['field'], block['fields'], block['values']
    if type(name) is not str or type(names) is not list or not names or any(type(n) is not str for n in names):
        raise NativeOnchangeSpecError('invalid child field selection')
    field = parent._fields.get(name)
    if not field or field.type != 'one2many' or name not in parent_spec:
        raise NativeOnchangeSpecError('child relation absent from authorized parent view')
    child = parent.env[field.comodel_name]
    child.check_access_rights('read')
    inverse = field.inverse_name
    inverse_field = child._fields.get(inverse)
    if not inverse_field or inverse_field.type != 'many2one' or inverse_field.comodel_name != parent._name:
        raise NativeOnchangeSpecError('invalid inverse relation')
    allowed = parent_spec[name].get('fields', {})
    if len(set(names)) != len(names) or any(n not in allowed or n in ('id', inverse) for n in names):
        raise NativeOnchangeSpecError('child fields outside authorized subview')
    if type(values) is not dict or any(n not in names for n in values):
        raise NativeOnchangeSpecError('child defaults outside requested fields')
    if any(n not in parent_spec and n != 'id' for n in parent_values):
        raise NativeOnchangeSpecError('parent draft fields outside authorized view')
    if 'id' in parent_values and parent_values['id'] not in (False, parent_id):
        raise NativeOnchangeSpecError('parent identity mismatch')
    parent.check_field_access_rights('read', list(parent_values))
    child.check_field_access_rights('read', [*names, inverse])
    changed = [] if initialize else block['changed_fields']
    child_id = 0 if initialize else block['record_id']
    if type(child_id) is not int or child_id < 0:
        raise NativeOnchangeSpecError('invalid child identity')
    if not initialize and (type(changed) is not list or not changed
                           or any(type(n) is not str or n not in names or n not in values for n in changed)
                           or len(set(changed)) != len(changed)):
        raise NativeOnchangeSpecError('invalid changed child fields')
    if child_id:
        if not parent_id:
            raise NativeOnchangeSpecError('existing child requires persisted parent')
        child = child.browse(child_id).exists()
        if not child:
            raise NativeOnchangeSpecError('child does not exist')
        child.check_access_rule('read')
        if child[inverse].id != parent_id:
            raise NativeOnchangeSpecError('child belongs to another parent')
    else:
        child.check_access_rights('create')
    parent_draft = dict(parent_values)
    parent_draft.pop('id', None)
    if parent_id:
        parent_draft['id'] = parent_id
    child_values = {**values, inverse: parent_draft}
    return child, child.onchange(child_values, changed, {n: allowed[n] for n in names})
