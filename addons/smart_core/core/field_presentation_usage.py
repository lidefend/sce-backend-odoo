"""Native field usage authority shared by metadata, configuration and projection."""
from .form_configuration_compiler import FormConfigurationError


def field_presentation_usage(value=None):
    # P0 declares ordinary native fields to be facts unless their owner says otherwise.
    if value is None:
        return "fact"
    if type(value) is not str or value not in {"fact", "interaction"}:
        raise FormConfigurationError("FIELD_PRESENTATION_USAGE_INVALID", "sc_ui_usage")
    return value


def assert_field_body_usage(metadata, target, *, hidden=False):
    usage = field_presentation_usage(metadata.get("sc_ui_usage"))
    if usage == "interaction" and not hidden:
        raise FormConfigurationError("INTERACTION_FIELD_BODY_FORBIDDEN", target)


def statically_hidden(node):
    attributes = node.get("attributes") or node.get("attrs") or {}
    return node.get("visible") is False or any(
        carrier.get("invisible") is True or carrier.get("invisible") in (1, "1", "True", "true")
        for carrier in (node, attributes) if isinstance(carrier, dict)
    )


def assert_configuration_field_usage(spec, fields):
    """Validate declared body references, including sections and precise patches."""
    def check(name, row, path):
        field = fields.get(name)
        if field is None:
            return
        metadata = field if isinstance(field, dict) else {"sc_ui_usage": getattr(field, "sc_ui_usage", None)}
        assert_field_body_usage(metadata, path, hidden=statically_hidden(row))

    def visit(value, path, carrier=""):
        if isinstance(value, list):
            for index, row in enumerate(value):
                visit(row, f"{path}[{index}]", carrier)
        elif isinstance(value, dict):
            name = value.get("name") or value.get("field") or value.get("field_name")
            if (carrier in {"fields", "field_slots", "columns"} or value.get("type") == "field") and isinstance(name, str):
                check(name, value, path)
            if carrier == "node_patches":
                expected = value.get("expected") or {}
                if expected.get("type") == "field" and expected.get("name"):
                    check(expected["name"], value.get("set") or {}, path)
            for key, nested in value.items():
                if isinstance(nested, (dict, list)):
                    visit(nested, f"{path}.{key}", key)
        elif isinstance(value, str) and carrier in {"fields", "field_slots", "columns"}:
            check(value, {}, path)
    visit(spec, "view_orchestration")
