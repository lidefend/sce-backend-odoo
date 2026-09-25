import assert from 'node:assert/strict';
import { buildIdempotentIntentIdentity, canonicalIntentRequestValue } from '../src/api/intentRequestIdentity.ts';

const identity = (params: Record<string, unknown>, intent = 'api.data') => buildIdempotentIntentIdentity({ intent, params });
const listParams = (overrides: Record<string, unknown> = {}) => ({
  op: 'list', model: 'res.partner', fields: ['id', 'name'], domain: [], limit: 40, offset: 0, order: '', search_term: 'UM', ...overrides,
});
let cases = 0;
const equal = (left: Record<string, unknown>, right: Record<string, unknown>) => {
  cases += 1;
  assert.equal(identity(left), identity(right));
};
const differ = (left: Record<string, unknown>, right: Record<string, unknown>, label: string) => {
  cases += 1;
  assert.notEqual(identity(left), identity(right), `${label} must change the request identity`);
};

const base = listParams();
// Every result-affecting parameter is part of the identity. `search_term`,
// `offset`, `order`, grouping and the raw domain were previously omitted from
// the coalescing key, so different searches reused one in-flight request.
equal(base, listParams());
differ(base, listParams({ search_term: 'P1' }), 'search_term');
differ(base, listParams({ search_term: undefined }), 'cleared search_term');
differ(base, listParams({ offset: 40 }), 'offset');
differ(base, listParams({ limit: 80 }), 'limit');
differ(base, listParams({ order: 'name desc' }), 'order');
differ(base, listParams({ group_by: ['partner_id'] }), 'group_by');
differ(base, listParams({ group_offset: 10 }), 'group_offset');
differ(base, listParams({ group_limit: 5 }), 'group_limit');
differ(base, listParams({ group_page_size: 20 }), 'group_page_size');
differ(base, listParams({ group_sample_limit: 3 }), 'group_sample_limit');
differ(base, listParams({ domain_raw: "[('name','ilike','UM')]" }), 'domain_raw');
differ(base, listParams({ domain: [['name', 'ilike', 'UM']] }), 'domain');
differ(base, listParams({ need_total: true }), 'need_total');
differ(base, listParams({ need_aggregates: true }), 'need_aggregates');
differ(base, listParams({ context: { lang: 'zh_CN' } }), 'context');
differ(base, { ...base, op: 'read' }, 'op');

// Key order is not part of the identity; array order is (domain tuples).
equal(base, { offset: 0, search_term: 'UM', order: '', limit: 40, model: 'res.partner', fields: ['id', 'name'], domain: [], op: 'list' });
equal({ op: 'list', model: 'res.partner', fields: ['id', 'name'] }, { model: 'res.partner', op: 'list', fields: ['id', 'name'] });
cases += 1;
assert.equal(
  identity({ op: 'list', model: 'res.partner', domain: [['a', '=', 1], ['b', '=', 2]] }),
  identity({ op: 'list', model: 'res.partner', domain: [['a', '=', 1], ['b', '=', 2]] }),
);
cases += 1;
assert.notEqual(
  identity({ op: 'list', model: 'res.partner', domain: [['a', '=', 1], ['b', '=', 2]] }),
  identity({ op: 'list', model: 'res.partner', domain: [['b', '=', 2], ['a', '=', 1]] }),
);

// `undefined` cannot reach the server (JSON drops it) so it must not split
// the identity; `null` is a real value and must.
const droppedUndefined = identity({ op: 'list', model: 'res.partner', search_term: undefined });
cases += 1;
assert.equal(droppedUndefined, identity({ op: 'list', model: 'res.partner' }));
cases += 1;
assert.notEqual(droppedUndefined, identity({ op: 'list', model: 'res.partner', search_term: null }));

// Top-level context participates too, and a missing params object is stable.
cases += 1;
assert.notEqual(
  buildIdempotentIntentIdentity({ intent: 'chatter.timeline', params: { model: 'project.project', res_id: 1 }, context: { lang: 'zh_CN' } }),
  buildIdempotentIntentIdentity({ intent: 'chatter.timeline', params: { model: 'project.project', res_id: 1 }, context: { lang: 'en_US' } }),
);
cases += 1;
assert.equal(
  buildIdempotentIntentIdentity({ intent: 'ui.contract.v2' }),
  buildIdempotentIntentIdentity({ intent: 'ui.contract.v2', params: undefined }),
);
cases += 1;
assert.notEqual(
  buildIdempotentIntentIdentity({ intent: 'ui.contract.v2', params: { op: 'action_open', action_id: 7 } }),
  buildIdempotentIntentIdentity({ intent: 'ui.contract.v2', params: { op: 'action_open', action_id: 8 } }),
);

// Normalization is a projection, not a mutation of the caller's payload.
const source = { op: 'list', nested: { beta: 2, alpha: 1 }, list: [3, 1] };
cases += 1;
assert.deepEqual(canonicalIntentRequestValue(source), { list: [3, 1], nested: { alpha: 1, beta: 2 }, op: 'list' });
cases += 1;
assert.deepEqual(source, { op: 'list', nested: { beta: 2, alpha: 1 }, list: [3, 1] });

console.log(`[intent_request_identity_test] PASS cases=${cases}`);
