import assert from 'node:assert';
import { createScenarioSelectionSnapshot, parseScenarioSurface, searchScenarioSurface } from '../src/app/scenarioSurface';

const valid = {
  ok: true,
  tree: {
    centers: [
      {
        key: 'smart_construction_core.menu_sc_finance_center',
        name: '财务账款',
        sequence: 50,
        scenarios: [
          {
            key: 'payment.capital',
            name: '付款与资金办理',
            sequence: 10,
            entries: [
              {
                menu_xmlid: 'smart_construction_core.menu_sc_user_payment_apply',
                menu_id: 11,
                action_id: 11,
                action_xmlid: 'smart_construction_core.action_payment_request_user_payment_apply',
                model: 'payment.request',
                view_modes: ['tree', 'form'],
                route: '/a/11?menu_id=11',
                label: '付款申请',
                intent: 'handle',
                intent_label: '办理',
                configured: true,
              },
            ],
          },
        ],
        entries: [
          {
            menu_xmlid: 'smart_construction_core.menu_sc_unconfigured',
            menu_id: 12,
            action_id: 12,
            action_xmlid: '',
            model: 'project.project',
            view_modes: ['tree'],
            route: '/a/12?menu_id=12',
            label: '未配置入口',
            intent: '',
            intent_label: '',
            configured: false,
          },
        ],
      },
    ],
  },
};

assert.strictEqual(parseScenarioSurface(undefined), null);
assert.strictEqual(parseScenarioSurface(null), null);
assert.strictEqual(parseScenarioSurface({}), null);
assert.strictEqual(parseScenarioSurface({ ok: false, tree: valid.tree }), null);
assert.strictEqual(parseScenarioSurface({ ok: true, tree: {} }), null);
assert.deepStrictEqual(parseScenarioSurface({ ok: true, tree: { centers: [] } }), { centers: [] });

const model = parseScenarioSurface(valid);
assert.ok(model);
assert.strictEqual(model.centers.length, 1);
assert.strictEqual(model.centers[0].name, '财务账款');
assert.strictEqual(model.centers[0].scenarios.length, 1);
const entry = model.centers[0].scenarios[0].entries[0];
assert.strictEqual(entry.menu_id, 11);
assert.strictEqual(entry.action_id, 11);
assert.strictEqual(entry.intent, 'handle');
assert.strictEqual(entry.configured, true);
assert.strictEqual(model.centers[0].entries[0].configured, false);

assert.deepStrictEqual(searchScenarioSurface(model, ''), []);
assert.deepStrictEqual(searchScenarioSurface(model, '不存在的业务'), []);
const hits = searchScenarioSurface(model, '付款申请');
assert.strictEqual(hits.length, 1);
assert.strictEqual(hits[0].entry.menu_id, 11);
assert.strictEqual(hits[0].centerName, '财务账款');
assert.strictEqual(hits[0].scenarioName, '付款与资金办理');
const unconfiguredHits = searchScenarioSurface(model, '未配置入口');
assert.strictEqual(unconfiguredHits.length, 1);
assert.strictEqual(unconfiguredHits[0].scenarioName, '');

const authority = {
  primary_actions: [{ ...entry, context_requirements: { required_query: ['menu_id'] } }],
  role_home_actions: [], contextual_actions: [], admin_actions: [], menu_containers: [],
} as unknown as NonNullable<Parameters<typeof createScenarioSelectionSnapshot>[1]>;
const selection = createScenarioSelectionSnapshot(entry, authority);
assert.ok(selection);
assert.ok(Object.isFrozen(selection.authority.context_requirements));
authority.primary_actions[0].route = '/changed';
assert.strictEqual(selection.route, entry.route);
assert.strictEqual(createScenarioSelectionSnapshot(entry, authority), null);
authority.primary_actions[0].route = entry.route;
assert.strictEqual(createScenarioSelectionSnapshot({ ...entry, menu_id: 999 }, authority), null);
assert.strictEqual(createScenarioSelectionSnapshot({ ...entry, action_id: 999 }, authority), null);
assert.strictEqual(createScenarioSelectionSnapshot({ ...entry, menu_xmlid: 'other' }, authority), null);
assert.strictEqual(createScenarioSelectionSnapshot(entry, null), null);
console.log('scenario_surface_parser_test PASS authority_cases=7');
