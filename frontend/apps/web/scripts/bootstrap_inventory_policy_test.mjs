import assert from 'node:assert/strict';
import test from 'node:test';
import { permitsInventoryRequest as allow } from './bootstrap_inventory_policy.mjs';
test('known startup and read intents permitted', () => {
  for (const intent of ['login', 'system.init', 'ui.contract.v2', 'my.work.summary', 'user.view.preference.get', 'ui.business_config.coverage.scan']) assert.equal(allow('POST', '/api/v1/intent', { intent }), true);
});
test('registered non-mutating data operations permitted', () => {
  for (const op of ['read', 'list', 'default_get']) assert.equal(allow('POST', '/api/v1/intent', { intent: 'api.data', params: { op } }), true);
  for (const op of ['create', 'write', 'unlink', 'execute', undefined]) assert.equal(allow('POST', '/api/v1/intent', { intent: 'api.data', params: { op } }), false);
});
test('unknown and configuration intents fail closed', () => {
  for (const intent of ['ui.business_config.change_set.stage', 'ui.business_config.change_set.discard', 'ui.business_config.change_set.open', 'ui.business_config.change_set.validate', 'ui.business_config.coverage.bootstrap_missing', 'ui.business_config.coverage.bootstrap_list_search', 'bootstrap', 'new.intent']) assert.equal(allow('POST', '/api/v1/intent', { intent }), false);
});
test('non-intent API and wrong HTTP methods denied', () => {
  assert.equal(allow('POST', '/api/write', { intent: 'system.init' }), false);
  assert.equal(allow('GET', '/api/v1/intent', { intent: 'system.init' }), false);
});
test('wrapped envelope is checked by the same policy', () => {
  assert.equal(allow('POST', '/api/v1/intent', { params: { intent: 'system.init' } }), true);
  assert.equal(allow('POST', '/api/v1/intent', { params: { intent: 'api.data', params: { op: 'write' } } }), false);
});

test('navigation telemetry requires the explicit candidate journey mode', () => {
  assert.equal(allow('POST', '/api/v1/intent', { intent: 'usage.track' }), false);
  assert.equal(allow('POST', '/api/v1/intent', { intent: 'usage.track' }, true), true);
  assert.equal(allow('POST', '/api/v1/intent', { intent: 'api.data', params: { op: 'write' } }, true), false);
});

test('anonymous contract GET is the only additional public API read', () => {
  assert.equal(allow('GET', '/api/v1/auth/page-contracts', null), true);
  assert.equal(allow('POST', '/api/v1/auth/page-contracts', {}), false);
  assert.equal(allow('GET', '/api/v1/auth/activation/start', null), false);
});

test('configuration resume may read but cannot create a fresh draft', () => {
  const request = params => ({ intent: 'ui.business_config.change_set.open', params });
  assert.equal(allow('POST', '/api/v1/intent', request({resume_only:true})), true);
  for (const params of [{}, {resume_only:false}, {resume_only:'true'}, {resume_only:true,fresh:true}]) assert.equal(allow('POST', '/api/v1/intent', request(params)), false);
});

test('menu panel read does not allow menu writes', () => {
  assert.equal(allow('POST', '/api/v1/intent', {intent:'ui.menu_config.panel.get'}), true);
  for (const intent of ['ui.menu_config.panel.set','ui.menu_config.entry.create','ui.menu_config.entry.delete','ui.menu_config.rollback']) assert.equal(allow('POST','/api/v1/intent',{intent}),false);
});

test('menu versions read never authorizes rollback', () => {
  assert.equal(allow('POST','/api/v1/intent',{intent:'ui.menu_config.versions'}),true);
  for (const key of ['allow_bootstrap','allowBootstrap','bootstrap']) assert.equal(allow('POST','/api/v1/intent',{intent:'ui.menu_config.versions',params:{[key]:true}}),false);
  for (const intent of ['ui.menu_config.rollback','ui.menu_config.menu.create','ui.menu_config.menu.delete']) assert.equal(allow('POST','/api/v1/intent',{intent}),false);
});
