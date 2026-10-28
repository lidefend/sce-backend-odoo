"""Read projection and Vue navigation for the existing stage requirements rules."""
from copy import deepcopy


def project_stage_requirements_payload(project):
    # This method owns stage selection, ACL/record-rule checks and completion.
    items = project.sc_get_stage_requirements(limit=0)
    stage = project._fields['lifecycle_state'].convert_to_export(project.lifecycle_state, project)
    return {
        'title': '阶段要求',
        'project': {'id': project.id, 'name': project.display_name},
        'stage': {'value': project.lifecycle_state, 'label': stage},
        'labels': {'project': '项目', 'stage': '当前阶段', 'required': '必做',
                   'optional': '选做', 'done': '已完成', 'pending': '待完成',
                   'empty': '当前阶段暂无已配置的要求项', 'back': '返回项目详情'},
        # Read-only surface deliberately does not advertise handling actions.
        'items': [{'title': item['title'], 'required': item['required'], 'done': item['done']}
                  for item in items],
        'return_path': f'/r/project.project/{project.id}',
    }


def stage_requirements_navigation(contract, context):
    source = (context or {}).get('source_contract') or {}
    model = source.get('model') or (source.get('head') or {}).get('model')
    record_id = (contract.get('dataContract', {}).get('mainData') or {}).get('id')
    if model != 'project.project' or type(record_id) is not int or record_id <= 0:
        return None
    rules = contract.get('actionContract', {}).get('actionRuleList', [])
    matches = [r for r in rules if (r.get('button') or {}).get('name') == 'action_view_stage_requirements'
               and (r.get('button') or {}).get('type') == 'object']
    if not matches:
        return None
    out = deepcopy(contract)
    for rule in out['actionContract']['actionRuleList']:
        if (rule.get('button') or {}).get('name') != 'action_view_stage_requirements' or (rule.get('button') or {}).get('type') != 'object':
            continue
        # Preserve occurrence identity, visibility and authorization. Only the
        # declared execution destination changes; native Odoo keeps its wizard.
        rule['button'] = {}
        rule['intent'] = 'open'
        rule['target'] = {'url': f'/project-stage-requirements/{record_id}', 'target': 'self'}
    return out
