"""Fresh work-item provenance, never a client-granted execution capability."""


def work_item_request_access_mode(intent_name, payload, *, authorize):
    """Resolve only the record ACL mode; the request remains a write intent."""
    if intent_name != "execute_button" or not isinstance(payload, dict):
        return None
    meta = payload.get("meta")
    if not isinstance(meta, dict) or "work_item_origin" not in meta:
        return None
    params = payload.get("params")
    if not isinstance(params, dict):
        raise ValueError("ACTION_WORK_ITEM_TARGET_INVALID")
    button = params.get("button")
    if (not isinstance(button, dict) or button.get("type") != "object"
            or not isinstance(button.get("name"), str) or not button["name"].strip()
            or any(key in params for key in ("res_ids", "ids", "id", "record_id"))):
        raise ValueError("ACTION_WORK_ITEM_TARGET_INVALID")
    return validate_work_item_action_origin(meta["work_item_origin"], model=params.get("model"),
        record_id=params.get("res_id"), method_name=button["name"], authorize=authorize)


def validate_work_item_action_origin(origin, *, model, record_id, method_name, authorize):
    if not isinstance(model, str) or not model.strip() or type(record_id) is not int or record_id <= 0:
        raise ValueError("ACTION_WORK_ITEM_TARGET_INVALID")
    if not isinstance(origin, dict) or set(origin) != {"source", "id"}:
        raise ValueError("ACTION_WORK_ITEM_ORIGIN_INVALID")
    source, item_id = origin.get("source"), origin.get("id")
    if not isinstance(source, str) or not source.strip() or type(item_id) is not int or item_id <= 0:
        raise ValueError("ACTION_WORK_ITEM_ORIGIN_INVALID")
    grant = authorize(origin, model=model, record_id=record_id, method_name=method_name)
    if grant is True:
        return "write"
    if (isinstance(grant, dict) and set(grant) == {"allowed", "record_access_mode"}
            and grant["allowed"] is True and grant["record_access_mode"] in ("read", "write")):
        return grant["record_access_mode"]
    raise ValueError("ACTION_WORK_ITEM_NOT_AUTHORIZED")
