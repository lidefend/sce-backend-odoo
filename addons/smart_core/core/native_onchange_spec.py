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
