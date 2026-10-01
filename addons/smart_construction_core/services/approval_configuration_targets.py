"""Approval configuration targets owned by a formal business page.

The policy model declares eligibility; native one2many fields declare ownership.
This projection grants neither record access nor permission to save a policy.
"""


def approval_configuration_targets(env, model):
    if not model or model not in env or "sc.approval.policy" not in env:
        return []
    parent = env[model]
    if not parent.check_access_rights("read", raise_exception=False):
        return []
    selection = env["sc.approval.policy"].fields_get(["target_model"])
    eligible = dict(selection.get("target_model", {}).get("selection") or [])
    candidates = [(model, "")]
    candidates.extend(
        (field.comodel_name, name)
        for name, field in sorted(parent._fields.items())
        if field.type == "one2many" and field.comodel_name
    )
    result, seen = [], set()
    for target, field_name in candidates:
        if target in seen or target not in eligible or target not in env:
            continue
        seen.add(target)
        if not env[target].check_access_rights("read", raise_exception=False):
            continue
        result.append({"value": target, "label": eligible[target],
                       "relation_field": field_name})
    return result
