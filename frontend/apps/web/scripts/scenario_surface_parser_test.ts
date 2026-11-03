import assert from 'node:assert';
import { parseScenarioSurface } from '../src/app/scenarioSurface';

const valid = {
  ok: true,
  tree: {
    domains: [
      {
        key: 'finance',
        name: '资金财务',
        scenarios: [
          {
            key: 'payment.capital',
            name: '付款与资金办理',
            type: 'COMPOSITE',
            intents: [
              {
                intent: 'handle',
                label: '办理',
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
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
    horizontal: [],
    platform: [],
  },
};

assert.strictEqual(parseScenarioSurface(undefined), null);
assert.strictEqual(parseScenarioSurface(null), null);
assert.strictEqual(parseScenarioSurface({}), null);
assert.strictEqual(parseScenarioSurface({ ok: false, tree: valid.tree }), null);
assert.deepStrictEqual(parseScenarioSurface({ ok: true, tree: { domains: [], horizontal: [] } }), { domains: [], horizontal: [] });
assert.strictEqual(parseScenarioSurface({ ok: true }), null);
assert.strictEqual(parseScenarioSurface({ ok: true, tree: { domains: {}, horizontal: [] } }), null);

const model = parseScenarioSurface(valid);
assert.ok(model);
assert.strictEqual(model.domains.length, 1);
assert.strictEqual(model.domains[0].name, '资金财务');
const entry = model.domains[0].scenarios[0].intents[0].entries[0];
assert.strictEqual(entry.menu_id, 11);
assert.strictEqual(entry.action_id, 11);
assert.strictEqual(entry.action_xmlid, 'smart_construction_core.action_payment_request_user_payment_apply');
assert.strictEqual(entry.route, '/a/11?menu_id=11');

console.log('scenario_surface_parser_test PASS');
