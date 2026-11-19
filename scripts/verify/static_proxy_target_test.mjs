import assert from 'node:assert/strict'
import {
  isBackendRequestPath,
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
assert.equal(
  upstreamRequestPath('/zh_CN/t/acceptance/api/v1/auth/page-contracts', '/t/acceptance'),
  '/zh_CN/t/acceptance/api/v1/auth/page-contracts',
)
assert.equal(
  upstreamRequestPath('/t/acceptance/api/v1/auth/page-contracts?x=1', '', '/t/acceptance'),
  '/api/v1/auth/page-contracts?x=1',
)
assert.equal(
  upstreamRequestPath('/zh_CN/t/acceptance/api/v1/auth/page-contracts?x=1', '', '/t/acceptance'),
  '/api/v1/auth/page-contracts?x=1',
)
assert.equal(upstreamRequestPath('/web/login', '/t/demo/'), '/t/demo/web/login')
for (const path of [
  '/api/v1/intent',
  '/web/login',
  '/t/demo/api/v1/intent',
  '/zh_CN/t/acceptance/api/v1/auth/page-contracts',
  '/zh_CN/web/login',
]) assert.equal(isBackendRequestPath(path), true, path)
assert.equal(isBackendRequestPath('/t/demo/admin/capability-explorer'), false)

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
assert.equal(
  proxyResponseHeaders(
    { location: 'http://127.0.0.1:18088/zh_CN/t/acceptance/api/v1/auth/page-contracts' },
    '',
    'http://127.0.0.1:18088',
  ).location,
  '/zh_CN/t/acceptance/api/v1/auth/page-contracts',
)

console.log('[static_proxy_target_test] PASS cases=23')
