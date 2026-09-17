// Behavioural counter-examples for the business-popup readiness decision.
//
// The point of these cases is the rule, not the implementation: which observations may
// interrupt the journey, and which must fall through to the strict assertion.
import assert from 'node:assert/strict';
import { resolvePopupReadiness } from './designer_popup_readiness.mjs';

let cases = 0;
const base = 'http://127.0.0.1:5174/f/sc.invoice.registration/new?action_id=785&view_id=1651&menu_id=532&activity_page_id=ap_mu5m8nwb_28bhc0';
const mounted = { ready_state: 'complete', app_mounted: true, app_shell_children: 1, field_nodes: 0, loading_title: false };
const loading = { ...mounted, loading_title: true };

// 1. A popup the product actually closed cannot be asserted against; a page whose state
//    merely could not be read yet (evaluate racing a navigation) must still fall through to
//    the strict assertion instead of failing the run on the probe's own timing.
{
  const closed = resolvePopupReadiness({ state: null, url: base, entryModel: 'sc.invoice.registration', closed: true });
  assert.equal(closed.verdict, 'popup_unreachable');
  assert.equal(closed.blocking, true);
  const unreadable = resolvePopupReadiness({ state: null, url: base, entryModel: 'sc.invoice.registration', closed: false });
  assert.equal(unreadable.verdict, 'popup_unreachable');
  assert.equal(unreadable.blocking, false);
  cases++;
}

// 2. A route the product itself denied is a proven failure state, not a slow page.
{
  for (const url of ['http://127.0.0.1:5174/login', 'http://127.0.0.1:5174/access-denied?from=/a/789']) {
    const result = resolvePopupReadiness({ state: mounted, url, entryModel: 'sc.invoice.registration' });
    assert.equal(result.verdict, 'popup_route_denied', url);
    assert.equal(result.blocking, true, url);
  }
  cases++;
}

// 3. Regression: this shell renders menu chrome that legitimately contains the denial
//    wording for entries the current principal may not open. A mounted page carrying that
//    text must stay a *mounted* page; classifying it as denied fails a run that the strict
//    assertion would have passed. The decision therefore takes no body text at all.
{
  const withChromeText = { ...mounted, body_text: '销项开票申请\n预缴税款\n无权访问\n无权访问\n进项发票' };
  const stillLoading = resolvePopupReadiness({ state: { ...loading, body_text: withChromeText.body_text }, url: base });
  assert.equal(stillLoading.verdict, 'popup_still_loading');
  assert.equal(stillLoading.blocking, false);
  const ready = resolvePopupReadiness({ state: withChromeText, url: base, entryModel: 'sc.invoice.registration' });
  assert.equal(ready.verdict, 'popup_ready_for_assertion');
  assert.equal(ready.blocking, false);
  cases++;
}

// 4. A mounted shell whose record request is still in flight reads one render tick early;
//    it is an observation, never an interruption.
{
  const result = resolvePopupReadiness({ state: loading, url: base, entryModel: 'sc.invoice.registration' });
  assert.equal(result.verdict, 'popup_still_loading');
  assert.equal(result.blocking, false);
  assert.equal(result.shell_mounted, true);
  cases++;
}

// 5. A shell that never mounted is likewise an observation: the strict label assertion
//    below it remains the judge, so a slow mount cannot become a diagnostic-only failure.
{
  const result = resolvePopupReadiness({ state: { ...mounted, app_mounted: false, app_shell_children: 0 }, url: base });
  assert.equal(result.verdict, 'popup_shell_not_mounted');
  assert.equal(result.blocking, false);
  cases++;
}

// 6. The route is reported as evidence, not as a silent pass: a popup that landed on
//    another entry must be visible in the record.
{
  const mine = resolvePopupReadiness({ state: mounted, url: base, entryModel: 'sc.invoice.registration' });
  assert.equal(mine.verdict, 'popup_ready_for_assertion');
  assert.equal(mine.route_matches_entry, true);
  assert.equal(mine.path, '/f/sc.invoice.registration/new');
  const other = resolvePopupReadiness({ state: mounted, url: base, entryModel: 'sc.material.inbound' });
  assert.equal(other.route_matches_entry, false);
  assert.equal(other.blocking, false);
  cases++;
}

console.log(`[designer_popup_readiness] PASS cases=${cases}`);
