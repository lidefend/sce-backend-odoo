import assert from 'node:assert/strict';
import fs from 'node:fs';

Object.assign(globalThis, {
  __SC_BUILD_SHA__: '33513f00f0000000000000000000000000000000',
  __SC_BUILD_TIME__: '2026-11-09T16:00:00.000Z',
  __SC_BUILD_ENV__: 'daily',
  __SC_BUILD_VERSION__: '9.8.7-rc.20',
});

const {
  FRONTEND_BUILD_IDENTITY,
  buildIdentityCopyText,
  buildIdentityTitle,
  compactProductVersion,
  productIdentityLabel,
  shortBuildRevision,
} = await import('../src/app/runtime/buildIdentity');

assert.equal(shortBuildRevision('33513F00F0000000000000000000000000000000'), '33513f00f');
assert.equal(shortBuildRevision('unknown'), 'unknown');
assert.equal(shortBuildRevision('abc'), 'unknown');
assert.equal(compactProductVersion('9.8.7-rc.20'), 'rc.20');
assert.equal(compactProductVersion('2.3.4'), '2.3.4');
assert.equal(compactProductVersion(''), 'unknown');
assert.equal(
  productIdentityLabel('9.8.7-rc.20', '33513f00f0000000000000000000000000000000'),
  'rc.20 · 33513f00f',
);
const build = {
  sha: '33513f00f0000000000000000000000000000000',
  builtAt: '2026-11-09T16:00:00.000Z',
  environment: 'daily',
  version: '9.8.7-rc.20',
};
assert.match(
  buildIdentityTitle('9.8.7-rc.20', build.sha, build),
  /33513f00f0000000000000000000000000000000/,
);
assert.match(buildIdentityTitle('9.8.7-rc.20', build.sha, build), /2026-11-09T16:00:00.000Z/);
assert.match(buildIdentityCopyText('9.8.7-rc.20', build.sha, build), /source_revision=33513f00f/);
assert.equal(FRONTEND_BUILD_IDENTITY.sha.length, 40);
assert.match(FRONTEND_BUILD_IDENTITY.builtAt, /^\d{4}-\d{2}-\d{2}T/);
assert.ok(FRONTEND_BUILD_IDENTITY.environment);
assert.ok(FRONTEND_BUILD_IDENTITY.version);
const viteConfig = fs.readFileSync('frontend/apps/web/vite.config.ts', 'utf8');
for (const token of [
  '__SC_BUILD_SHA__',
  '__SC_BUILD_TIME__',
  '__SC_BUILD_ENV__',
  '__SC_BUILD_VERSION__',
  'build-info.json',
  'frontend.build_info.v1',
]) {
  assert.ok(viteConfig.includes(token), token);
}

console.log('frontend_build_identity_test PASS assertions=19');
