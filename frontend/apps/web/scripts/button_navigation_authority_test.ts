import assert from 'node:assert/strict';
import {
  consumeButtonNavigationAuthority,
  grantButtonNavigationAuthority,
  pendingButtonNavigationAuthorityCount,
} from '../src/app/buttonNavigationAuthority';

const now = Date.now();
grantButtonNavigationAuthority(650, '/f/project.project/1?action_id=650');
assert.equal(pendingButtonNavigationAuthorityCount(), 1);
assert.equal(
  consumeButtonNavigationAuthority(650, '/f/project.project/1?action_id=650'),
  true,
  'granted button route must be authorized once',
);
assert.equal(
  consumeButtonNavigationAuthority(650, '/f/project.project/1?action_id=650'),
  false,
  'the grant is one-shot and must not be replayable',
);
assert.equal(pendingButtonNavigationAuthorityCount(), 0);

grantButtonNavigationAuthority(962, '/a/962?action_id=962');
assert.equal(
  consumeButtonNavigationAuthority(
    962,
    '/a/962?action_id=962&domain_raw=%5B%5D&context_raw=%7B%7D&order=name%20asc',
  ),
  true,
  'the authority remains bound to the action path while contract query transport varies',
);
assert.equal(
  consumeButtonNavigationAuthority(962, '/a/963?action_id=962'),
  false,
  'query normalization must not authorize a different action path',
);

grantButtonNavigationAuthority(593, '/f/project.cost.ledger/1?action_id=593');
assert.equal(
  consumeButtonNavigationAuthority(593, '/f/project.cost.ledger/2?action_id=593'),
  false,
  'a different destination for the same action must stay denied',
);
assert.equal(
  consumeButtonNavigationAuthority(760, '/f/project.cost.ledger/1?action_id=593'),
  false,
  'a different action id must stay denied',
);

// Expiry: a grant must not outlive its short window.
const originalNow = Date.now;
let clock = now;
Date.now = () => clock;
try {
  grantButtonNavigationAuthority(355, '/a/355');
  clock = now + 31_000;
  assert.equal(
    consumeButtonNavigationAuthority(355, '/a/355'),
    false,
    'an expired grant must not authorize navigation',
  );
  assert.equal(pendingButtonNavigationAuthorityCount(), 0, 'expired grants must be pruned');
} finally {
  Date.now = originalNow;
}

console.log('[button_navigation_authority_test] PASS');
