"""Validate a relation origin without treating client navigation as authority."""


def positive_relation_id(value):
    # IDs in this browser protocol are exact JS-safe integers, never coercions.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return 0
    if isinstance(value, str) and (len(value) > 16 or not value.isascii() or not value.isdecimal() or value.startswith('0')):
        return 0
    parsed = int(value) if value else 0
    return parsed if 0 < parsed <= 9007199254740991 else 0


def validate_relation_action_origin(env, origin, *, model, record_id, load_contract, validate_entry,
                                    target_action_id=None, target_menu_id=None):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    require(isinstance(origin, dict), 'ACTION_RELATION_ORIGIN_MISSING')
    exact_target = target_action_id is not None or target_menu_id is not None
    if exact_target:
        require(positive_relation_id(target_action_id) and positive_relation_id(target_menu_id)
                and positive_relation_id(record_id), 'ACTION_RELATION_TARGET_INCOMPLETE')
    parent_model = str(origin.get('model') or '').strip()
    field_name = str(origin.get('field') or '').strip()
    parent_id = positive_relation_id(origin.get('record_id'))
    action_id, menu_id = positive_relation_id(origin.get('action_id')), positive_relation_id(origin.get('menu_id'))
    require(parent_model and field_name and parent_id and action_id and menu_id, 'ACTION_RELATION_ORIGIN_INCOMPLETE')
    require(not validate_entry(action_id, menu_id, parent_model), 'ACTION_RELATION_ENTRY_DENIED')
    parent = env[parent_model].browse(parent_id).exists()
    require(bool(parent), 'ACTION_RELATION_PARENT_NOT_FOUND')
    parent.check_access_rights('read')
    parent.check_access_rule('read')
    field = parent._fields.get(field_name)
    require(field and field.type in ('many2one', 'one2many', 'many2many')
            and field.comodel_name == model, 'ACTION_RELATION_FIELD_MISMATCH')
    parent.check_field_access_rights('read', [field_name])
    require(record_id in parent[field_name].ids, 'ACTION_RELATION_RECORD_MISMATCH')
    contract = load_contract(model=parent_model, record_id=parent_id, action_id=action_id, menu_id=menu_id)
    require(contract.get('statusContract', {}).get('globalStatus', {}).get('effectiveRecordCapabilities', {}).get('read') is True,
            'ACTION_RELATION_PARENT_CONTRACT_DENIED')

    def can_open(value, depth=0):
        if depth > 32:
            return False
        if isinstance(value, list):
            return any(can_open(item, depth + 1) for item in value)
        if not isinstance(value, dict):
            return False
        if value.get('invisible') is True or value.get('modifiers', {}).get('invisible') not in (None, False):
            return False
        if value.get('type') == 'field':
            if value.get('name') != field_name:
                return False  # Never authorize through a nested subview field of the same name.
            entry = (value.get('fieldInfo') or {}).get('relation_entry') or value.get('relation_entry') or {}
            return (entry.get('model') == model and entry.get('can_read') is True and entry.get('can_open') is True
                    and (not exact_target or (positive_relation_id(entry.get('action_id')) == target_action_id
                                              and positive_relation_id(entry.get('menu_id')) == target_menu_id)))
        return any(can_open(item, depth + 1) for item in value.values())

    require(can_open(contract.get('layoutContract')), 'ACTION_RELATION_OPEN_NOT_AUTHORIZED')
