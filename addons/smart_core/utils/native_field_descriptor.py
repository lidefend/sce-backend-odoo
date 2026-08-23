# -*- coding: utf-8 -*-
"""Pure canonical projection for Odoo field metadata used by native contracts."""


def project_native_field_descriptor(
    field_name,
    metadata=None,
    *,
    label=None,
    widget=None,
    preserve_extra=False,
):
    meta = metadata if isinstance(metadata, dict) else {}
    field_type = str(meta.get("type") or meta.get("ttype") or "char").strip().lower()
    resolved_label = str(label or meta.get("string") or meta.get("label") or field_name).strip()
    resolved_widget = str(meta.get("widget") or "" if widget is None else widget).strip()
    out = dict(meta) if preserve_extra else {}
    out.update({
        "name": str(field_name or "").strip(),
        "label": resolved_label,
        "type": field_type,
        "required": bool(meta.get("required", False)),
        "readonly": bool(meta.get("readonly", False)),
        "invisible": bool(meta.get("invisible", False)),
        "help": str(meta.get("help") or ""),
        "widget": resolved_widget,
        "domain": meta.get("domain", []),
        "context": meta.get("context", {}),
        "selection": meta.get("selection", []),
        "colspan": int(meta.get("col", 1)) if str(meta.get("col", "")).isdigit() else 1,
    })
    if meta.get("relation"):
        out["relation"] = meta.get("relation")
    if meta.get("relation_field"):
        out["relation_field"] = meta.get("relation_field")
    if field_type == "monetary":
        out["currency_field"] = str(meta.get("currency_field") or "currency_id").strip()
        digits = meta.get("digits")
        if isinstance(digits, (list, tuple)) and len(digits) == 2:
            out["digits"] = list(digits)
        else:
            out.pop("digits", None)
    return out
