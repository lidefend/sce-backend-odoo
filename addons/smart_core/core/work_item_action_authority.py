"""Fresh work-item provenance, never a client-granted execution capability."""


def validate_work_item_action_origin(origin, *, model, record_id, method_name, authorize):
    if not isinstance(model, str) or not model.strip() or type(record_id) is not int or record_id <= 0:
        raise ValueError("ACTION_WORK_ITEM_TARGET_INVALID")
    if not isinstance(origin, dict) or set(origin) != {"source", "id"}:
        raise ValueError("ACTION_WORK_ITEM_ORIGIN_INVALID")
    source, item_id = origin.get("source"), origin.get("id")
    if not isinstance(source, str) or not source.strip() or type(item_id) is not int or item_id <= 0:
        raise ValueError("ACTION_WORK_ITEM_ORIGIN_INVALID")
    if authorize(origin, model=model, record_id=record_id, method_name=method_name) is not True:
        raise ValueError("ACTION_WORK_ITEM_NOT_AUTHORIZED")
