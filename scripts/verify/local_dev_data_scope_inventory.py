"""Read-only native ownership candidates, not an authorization declaration.

Executed only by local.dev.data_scope.inventory in the registered demo DB.

Uses existing local.dev metadata only. No business values, fixtures or actor
credentials are read. Candidate paths require owning-model review before use.
"""
import json

assert env.cr.dbname == 'sc_dev_demo', 'requires exact local.dev database'
env.cr.rollback()
original_commit = env.cr.commit

def reject_commit(*args, **kwargs):
    raise RuntimeError('data scope inventory forbids commit')

env.cr.commit = reject_commit
try:
    references = env['ir.model.data'].sudo().search([
        ('module', '=', 'smart_construction_core'),
        ('model', 'in', ['ir.model', 'ir.ui.view', 'ir.actions.act_window']),
    ])
    names = set()
    for carrier, field in [('ir.model', 'model'), ('ir.ui.view', 'model'), ('ir.actions.act_window', 'res_model')]:
        identifiers = references.filtered(lambda ref: ref.model == carrier).mapped('res_id')
        names.update(env[carrier].sudo().browse(identifiers).exists().mapped(field))
    p1_referenced_names = set(filter(None, names))
    # Product navigation is not the security perimeter. Include models with
    # no P1 menu/view, core metadata, transient services and abstract carriers.
    names = set(env.registry.models)
    rows = []
    for name in sorted(names):
        Model = env[name]
        paths = []
        for field_name, field in Model._fields.items():
            if field_name in {'create_uid', 'write_uid'}:
                continue  # Audit actors never establish business ownership.
            if field.type != 'many2one':
                continue
            if field.comodel_name == 'res.company':
                paths.append({'path': field_name, 'stored': field.store, 'related': field.related or []})
            elif field.comodel_name in env:
                company = env[field.comodel_name]._fields.get('company_id')
                if company and company.type == 'many2one' and company.comodel_name == 'res.company':
                    paths.append({'path': field_name + '.company_id', 'stored': field.store, 'related': field.related or []})
        rows.append({'model': name, 'abstract': Model._abstract, 'transient': Model._transient,
                     'auto': Model._auto, 'inherits': Model._inherits,
                     'p1_referenced': name in p1_referenced_names,
                     'company_path_candidates': paths})
    print('DATA_SCOPE_INVENTORY=' + json.dumps({'status': 'observed_not_authorized', 'database': env.cr.dbname,
          'scope': 'complete_installed_registry', 'p1_referenced_count': len(p1_referenced_names),
          'count': len(rows), 'models': rows}, ensure_ascii=False, sort_keys=True))
finally:
    env.cr.rollback()
    env.cr.commit = original_commit
