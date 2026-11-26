import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

// Exercise the probe's actual request classifier without launching a browser.
const source = fs.readFileSync(new URL('./local_dev_enterprise_configuration_consumer.mjs', import.meta.url), 'utf8');
const declarations = source.slice(source.indexOf('function intentBody('), source.indexOf('async function login('));
const isBusinessWrite = new Function(`${declarations}; return isBusinessWrite;`)();
const request = body => ({ postData: () => JSON.stringify(body) });

for (const intent of ['scenario.activation.set', 'scenario.center.activation.set', 'user.role.assign', 'workflow.execute', 'release.publish', 'data.rollback']) {
  test(`read-only initialization blocks ${intent}`, () => {
    assert.equal(isBusinessWrite(request({ intent, params: {} })), true);
  });
}
for (const op of ['create', 'write', 'unlink']) {
  test(`read-only initialization blocks api.data ${op}`, () => {
    assert.equal(isBusinessWrite(request({ intent: 'api.data', params: { op } })), true);
  });
}
for (const body of [
  { intent: 'login' },
  { intent: 'system.init' },
  { intent: 'ui.contract.v2', params: { op: 'action_open' } },
  { intent: 'api.data', params: { op: 'read' } },
  { intent: 'api.data', params: { op: 'search_read' } },
  { intent: 'enterprise.readiness.diagnosis.get' },
  { intent: 'scenario.activation.catalog.get' },
]) {
  test(`read-only initialization permits ${body.intent} ${body.params?.op || ''}`, () => {
    assert.equal(isBusinessWrite(request(body)), false);
  });
}
