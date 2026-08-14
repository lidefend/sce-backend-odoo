#!/usr/bin/env node

import assert from 'node:assert/strict';
import {
  captureEvidenceScreenshot,
  installEvidenceSensitivityTracker,
  stopEvidenceTrace,
} from './frontend_evidence_capture_guard.mjs';

function fakeContext() {
  const instance = {
    binding: null,
    initScript: null,
    traceCalls: [],
    exposeBinding: async (_name, callback) => { instance.binding = callback; },
    addInitScript: async (callback, args) => { instance.initScript = { callback, args }; },
  };
  instance.tracing = {
    stop: async (options) => { instance.traceCalls.push(options || null); },
  };
  return instance;
}

function makePage(context, sensitive = false) {
  const page = {
    screenshotCalls: 0,
    closed: false,
    context: () => context,
    isClosed: () => page.closed,
    evaluate: async () => sensitive,
    screenshot: async () => {
      page.screenshotCalls += 1;
      return Buffer.from('image');
    },
  };
  return page;
}

let context = fakeContext();
await installEvidenceSensitivityTracker(context);
const ordinaryPage = makePage(context, false);
await captureEvidenceScreenshot(ordinaryPage, { path: 'ordinary.png' });
await stopEvidenceTrace(context, [ordinaryPage], 'ordinary.zip');
assert.equal(ordinaryPage.screenshotCalls, 1);
assert.deepEqual(context.traceCalls, [{ path: 'ordinary.zip' }]);

context = fakeContext();
await installEvidenceSensitivityTracker(context);
const sensitivePage = makePage(context, true);
await assert.rejects(
  captureEvidenceScreenshot(sensitivePage, { path: 'secret.png' }),
  /EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=screenshot/,
);
assert.equal(sensitivePage.screenshotCalls, 0);

// A child-frame report taints the Node-side context for its full lifetime.
await context.binding({
  frame: { url: () => 'http://example.test/secret-frame' },
  page: { url: () => 'http://example.test/host' },
});

// Navigation replaces the document and closing removes the page, but neither
// may erase evidence already captured by the context trace.
const navigatedPage = makePage(context, false);
sensitivePage.closed = true;
await assert.rejects(
  stopEvidenceTrace(context, [navigatedPage], 'secret-after-navigation.zip'),
  /EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=trace/,
);
assert.deepEqual(context.traceCalls, [null]);

context = fakeContext();
await assert.rejects(
  stopEvidenceTrace(context, [], 'untracked.zip'),
  /EVIDENCE_SENSITIVITY_UNRESOLVED: tracker not installed/,
);
assert.deepEqual(context.traceCalls, [null]);

console.log('[frontend_evidence_capture_guard.test] PASS sensitive_screenshot=0 sensitive_trace_export=0 navigation_close_frame=denied ordinary_capture=2');
