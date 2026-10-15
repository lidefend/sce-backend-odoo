"""Demo manual rectification inputs, executed through native role-bound APIs."""
from odoo import models

from ..hooks import assert_demo_seed_principal, guard_demo_scope


def close_demo_issue(issue, issue_xmlid, rectification_xmlid, rectification_values,
                     recheck_xmlid, recheck_values):
    assert_demo_seed_principal(issue.env)
    guard_demo_scope(issue.env)
    from ..tools.scenario_loader import _demo_action_record, _bind_generated_demo_xmlid
    from ..seed.business_roles import prepare_project

    allowed = {
        'smart_construction_demo.sc_demo_quality_issue_080_rebar',
        'smart_construction_demo.sc_demo_safety_issue_080_guardrail',
        'smart_construction_demo.sc_demo_quality_issue_089_rebar',
        'smart_construction_demo.sc_demo_safety_issue_089_high_support',
    }
    if issue_xmlid not in allowed or issue != issue.env.ref(issue_xmlid):
        raise ValueError('Demo issue must match its declared identity')
    stem = issue_xmlid.split('.', 1)[1]
    if (rectification_xmlid != stem.replace('_issue_', '_rectification_')
            or recheck_xmlid != stem.replace('_issue_', '_recheck_')):
        raise ValueError('Demo child identities must belong to the declared issue')
    if (set(rectification_values) != {'rectification_date', 'source_channel', 'result'}
            or set(recheck_values) != {'recheck_date', 'source_channel', 'result', 'comment'}
            or recheck_values['result'] != 'passed'):
        raise ValueError('Demo issue inputs must be explicit manual facts')
    prepare_project(issue.env, issue.project_id)
    author = _demo_action_record(issue.env, issue, 'action_submit',
                                'smart_construction_demo.user_sc_project_user')
    checker = _demo_action_record(issue.env, issue, 'create',
                                 'smart_construction_demo.user_sc_project_manager_cap')
    if author.state == 'draft':
        author.action_submit()

    def ensure_fact(actor, model, xmlid, values, person_field):
        expected = dict(values, issue_id=actor.id, **{person_field: actor.env.uid})
        existing = actor.env.ref('smart_construction_demo.' + xmlid, raise_if_not_found=False)
        if existing:
            if existing._name != model:
                raise ValueError('Demo issue child model mismatch')
            for field, value in expected.items():
                actual = existing[field]
                if existing._fields[field].type == 'many2one':
                    actual = actual.id
                elif existing._fields[field].type == 'date':
                    actual = str(actual)
                if actual != value:
                    raise ValueError('Demo issue child source mismatch: ' + field)
            return existing
        record = actor.env[model].create(expected)
        _bind_generated_demo_xmlid(issue.env, xmlid, record)
        return record

    prefix = issue._name.rsplit('.', 1)[0]
    ensure_fact(author, prefix + '.rectification', rectification_xmlid,
                rectification_values, 'handler_id')
    if author.state == 'rectifying':
        author.action_request_recheck()
    ensure_fact(checker, prefix + '.recheck', recheck_xmlid, recheck_values, 'recheck_user_id')
    if checker.state != 'closed':
        raise ValueError('Native issue recheck did not close the demo issue')
    return True


class QualityIssueDemoSeed(models.Model):
    _inherit = 'sc.quality.issue'

    def sc_demo_close_issue(self, issue_xmlid, rectification_xmlid, rectification_values,
                            recheck_xmlid, recheck_values):
        return close_demo_issue(self, issue_xmlid, rectification_xmlid,
                                rectification_values, recheck_xmlid, recheck_values)


class SafetyIssueDemoSeed(models.Model):
    _inherit = 'sc.safety.issue'

    def sc_demo_close_issue(self, issue_xmlid, rectification_xmlid, rectification_values,
                            recheck_xmlid, recheck_values):
        return close_demo_issue(self, issue_xmlid, rectification_xmlid,
                                rectification_values, recheck_xmlid, recheck_values)
