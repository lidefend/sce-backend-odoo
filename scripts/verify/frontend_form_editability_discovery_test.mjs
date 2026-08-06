#!/usr/bin/env node

import assert from 'node:assert/strict';
import {
  discoverEditableFormRoute,
  editableFormRoute,
  extractUnifiedContract,
  isEditableFormContract,
  parseActionRoute,
} from './lib/frontend_form_editability_discovery.mjs';

function actionContract(model = 'demo.dynamic.model') {
  return {
    ok: true,
    data: {
      __unified_page_contract_v2: {
        pageInfo: { model },
        dataContract: {
          dataSource: {
            primary: {
              params: { domain: [['company_id', '=', 7]], context: { allowed_company_ids: [7] }, order: 'business_date desc' },
            },
          },
        },
      },
    },
  };
}

function formContract(pageAuth) {
  return {
    ok: true,
    data: {
      __unified_page_contract_v2: {
        statusContract: { globalStatus: { pageAuth } },
      },
    },
  };
}

assert.deepEqual(parseActionRoute('/a/91?menu_id=37'), { actionId: 91, menuId: 37 });
assert.throws(() => parseActionRoute('/f/demo.model/1'), /requires an action route/);
assert.equal(extractUnifiedContract(formContract('edit')).statusContract.globalStatus.pageAuth, 'edit');
assert.equal(isEditableFormContract(formContract('edit')), true);
assert.equal(isEditableFormContract(formContract('read')), false);
assert.equal(editableFormRoute({ model: 'demo.dynamic.model', recordId: 1, actionId: 91, menuId: 37 }), '/f/demo.dynamic.model/1?action_id=91&menu_id=37');

const calls = [];
const lockedTopRecords = Array.from({ length: 40 }, (_, index) => ({ id: 2_000 - index }));
const discovered = await discoverEditableFormRoute({
  listRoute: '/a/91?menu_id=37',
  requestIntent: async (intent, params) => {
    calls.push({ intent, params });
    if (intent === 'ui.contract.v2' && params.op === 'action_open') return actionContract();
    if (intent === 'api.data') {
      if (params.order === 'id asc') return { ok: true, data: { records: [{ id: 1 }, ...lockedTopRecords.slice(0, 39)] } };
      return { ok: true, data: { records: lockedTopRecords } };
    }
    if (intent === 'ui.contract.v2' && params.op === 'model') return formContract(params.record_id === 1 ? 'edit' : 'read');
    throw new Error(`unexpected request: ${intent}`);
  },
});

assert.equal(discovered.model, 'demo.dynamic.model');
assert.equal(discovered.record_id, 1, 'contract discovery must find an editable record outside the list default ordering');
assert.equal(discovered.route, '/f/demo.dynamic.model/1?action_id=91&menu_id=37');
assert.deepEqual(calls.find((call) => call.intent === 'api.data').params.domain, [['company_id', '=', 7]], 'runtime action domain must be preserved');
assert.deepEqual(calls.find((call) => call.intent === 'api.data').params.context, { allowed_company_ids: [7] }, 'runtime action context must be preserved');
assert.equal(calls.some((call) => call.params?.model === 'sc.general.contract'), false, 'discovery must not hardcode a business model');
assert.equal(calls.some((call) => call.params?.record_id === 1 && call.params?.render_profile === 'edit'), true, 'candidate editability must be proven by the form contract');

const absent = await discoverEditableFormRoute({
  listRoute: '/a/12',
  requestIntent: async (intent, params) => {
    if (intent === 'ui.contract.v2' && params.op === 'action_open') return actionContract('demo.no_editable');
    if (intent === 'api.data') return { ok: true, data: { records: [{ id: 8 }] } };
    return formContract('read');
  },
});
assert.equal(absent.route, '');
assert.equal(absent.inspected.length, 1, 'negative result must retain inspected-record evidence');

console.log('[frontend_form_editability_discovery_test] PASS');
