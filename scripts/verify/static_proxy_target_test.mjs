import assert from 'node:assert/strict'
import {
  normalizeProxyBasePath,
  proxyResponseHeaders,
  upstreamRequestPath,
} from '../release/static_proxy_target.mjs'

assert.equal(normalizeProxyBasePath(''), '')
assert.equal(normalizeProxyBasePath('/'), '')
assert.equal(normalizeProxyBasePath('/t/demo/'), '/t/demo')
assert.throws(() => normalizeProxyBasePath('t/demo'))
assert.throws(() => normalizeProxyBasePath('/t/demo?db=1'))
assert.throws(() => normalizeProxyBasePath('/t/demo#fragment'))
assert.throws(() => normalizeProxyBasePath('//other'))

assert.equal(upstreamRequestPath('/api/v1/intent?x=1', ''), '/api/v1/intent?x=1')
assert.equal(upstreamRequestPath('/api/v1/intent?x=1', '/t/demo'), '/t/demo/api/v1/intent?x=1')
assert.equal(upstreamRequestPath('/t/demo/api/v1/intent?x=1', '/t/demo'), '/t/demo/api/v1/intent?x=1')
assert.equal(upstreamRequestPath('/web/login', '/t/demo/'), '/t/demo/web/login')

assert.deepEqual(proxyResponseHeaders({}, '/t/demo'), {})
const rewritten = proxyResponseHeaders({
  'set-cookie': [
    'session_id=abc; Path=/t/demo/; HttpOnly; SameSite=Lax',
    'other=xyz; Path=/t/demo/',
  ],
}, '/t/demo')
assert.deepEqual(rewritten['set-cookie'], [
  'session_id=abc; Path=/; HttpOnly; SameSite=Lax',
  'other=xyz; Path=/',
])
assert.deepEqual(proxyResponseHeaders({
  'set-cookie': ['session_id=abc; Path=/t/demo/'],
}, ''), {
  'set-cookie': ['session_id=abc; Path=/t/demo/'],
})

console.log('[static_proxy_target_test] PASS cases=13')
