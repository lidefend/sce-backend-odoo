"""Consume native action metadata referencing a native, actor-readable fact.

No condition language, configuration selection or business eligibility rule.
"""
from .form_configuration_compiler import FormConfigurationError


def _gap(path):
    raise FormConfigurationError('NATIVE_ACTION_GUIDANCE_INVALID', path)


def declared_fact(action):
    presentation = action.get('presentation') or {}
    if 'action_guidance' not in presentation:
        return None
    binding = presentation['action_guidance']
    if not isinstance(binding, dict) or set(binding) != {'field', 'profiles', 'trigger'}:
        _gap('action.presentation.action_guidance')
    if not isinstance(binding['field'], str) or not binding['field'].isidentifier():
        _gap('action_guidance.field')
    profiles = binding['profiles']
    if (not isinstance(profiles, list) or not profiles or any(item not in ('edit', 'readonly') for item in profiles)
            or len(set(profiles)) != len(profiles) or binding['trigger'] != 'invoke'):
        _gap('action_guidance.trigger/profiles')
    if action.get('button', {}).get('type') != 'object' or not action.get('button', {}).get('name'):
        _gap('action_guidance.object_action')
    return binding


def project_native_action_guidance(contract, read_fact):
    """read_fact(field) enforces actor field/read ACL before returning native JSON."""
    profile = contract.get('statusContract', {}).get('globalStatus', {}).get('effectiveRenderProfile')
    model = contract.get('pageInfo', {}).get('model')
    record_id = contract.get('dataContract', {}).get('mainData', {}).get('id')
    facts = {}
    for action in contract.get('actionContract', {}).get('actionRuleList', []):
        binding = declared_fact(action)
        if binding is None:
            continue
        view_type = contract.get('pageInfo', {}).get('viewType')
        if not isinstance(view_type, str) or not view_type:
            _gap('action_guidance.viewType')
        # A collection may carry native form action declarations, but has no
        # single-record fact. Evaluate the binding only on its form surface.
        if view_type != 'form':
            continue
        if profile not in ('create', 'edit', 'readonly'):
            _gap('action_guidance.effectiveRenderProfile')
        if profile not in binding['profiles']:
            continue
        if type(record_id) is not int or record_id <= 0 or not model:
            _gap('action_guidance.record_identity')
        target = action.get('target') or {}
        if (not isinstance(target, dict) or target.get('model', model) != model
                or type(target.get('id', record_id)) is not int or target.get('id', record_id) != record_id
                or target.get('method', action['button']['name']) != action['button']['name']):
            _gap('action_guidance.target_identity')
        field = binding['field']
        if field not in facts:
            facts[field] = read_fact(field)
        fact = facts[field]
        required = {'method', 'blocking', 'requires_confirmation', 'message', 'reason_code', 'severity'}
        if not isinstance(fact, dict) or set(fact) != required:
            _gap(field + '.fact_schema')
        if (fact['method'] != action['button']['name'] or type(fact['blocking']) is not bool
                or type(fact['requires_confirmation']) is not bool
                or not isinstance(fact['message'], str) or not isinstance(fact['reason_code'], str)
                or fact['severity'] not in ('none', 'warning', 'error')):
            _gap(field + '.fact_identity')
        active = fact['blocking'] or fact['requires_confirmation']
        if (active and (not fact['message'].strip() or not fact['reason_code'].strip())
                or fact['blocking'] and (fact['requires_confirmation'] or fact['severity'] != 'error')
                or fact['requires_confirmation'] and fact['severity'] != 'warning'):
            _gap(field + '.fact_message')
        trace = list(action.get('sourceTrace') or [])
        trace.append({'source': 'native_model_field', 'model': model, 'record_id': record_id,
                      'field': field, 'method': fact['method'], 'trigger': binding['trigger']})
        action['sourceTrace'] = trace
        if fact['requires_confirmation']:
            presentation = dict(action.get('presentation') or {})
            messages = [presentation.get('warning_message'), fact['message']]
            presentation.update(requires_confirmation=True, warning_message='\n'.join(dict.fromkeys(item for item in messages if item)))
            action['presentation'] = presentation
        if fact['blocking']:
            denied = action.get('allowed') is False or action.get('enabled') is False or action.get('disabled') is True
            if not denied or action.get('reasonCode') in (None, '', 'OK', 'ACTION_NOT_ALLOWED', fact['reason_code']):
                action.update(reasonCode=fact['reason_code'], reasonMessage=fact['message'])
            action.update(allowed=False, enabled=False, disabled=True, businessAvailable=False)
            for status in contract.get('statusContract', {}).get('buttonStatus', []):
                if (action.get('backendIdentity') and status.get('backendIdentity') == action['backendIdentity']
                        or not status.get('backendIdentity') and status.get('btnId') == 'btn.' + str(action.get('actionKey', ''))):
                    if status.get('disabled') is not True or status.get('reasonCode') in (None, '', 'OK', 'ACTION_NOT_ALLOWED', action.get('reasonCode')):
                        status.update(reasonCode=action.get('reasonCode'), reasonMessage=action.get('reasonMessage'))
                    status['disabled'] = True
    return contract
