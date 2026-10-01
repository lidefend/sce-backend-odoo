"""Validate a relation origin without treating client navigation as authority."""


def validate_relation_action_origin(env, origin, *, model, record_id, load_contract, validate_entry):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    def positive(value):
        try:
            return int(value) if not isinstance(value, bool) and int(value) > 0 else 0
        except (TypeError, ValueError):
            return 0

    require(isinstance(origin, dict), 'ACTION_RELATION_ORIGIN_MISSING')
    parent_model = str(origin.get('model') or '').strip()
    field_name = str(origin.get('field') or '').strip()
    parent_id = positive(origin.get('record_id'))
    action_id, menu_id = positive(origin.get('action_id')), positive(origin.get('menu_id'))
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
            return entry.get('model') == model and entry.get('can_read') is True and entry.get('can_open') is True
        return any(can_open(item, depth + 1) for item in value.values())

    require(can_open(contract.get('layoutContract')), 'ACTION_RELATION_OPEN_NOT_AUTHORIZED')
