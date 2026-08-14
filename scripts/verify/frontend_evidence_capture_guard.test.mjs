#!/usr/bin/env node

import assert from 'node:assert/strict';
import {
  captureEvidenceScreenshot,
  stopEvidenceTrace,
} from './frontend_evidence_capture_guard.mjs';

function makePage(sensitive) {
  const page = {
    screenshotCalls: 0,
    isClosed: () => false,
    evaluate: async () => sensitive,
  };
  page.screenshot = async () => {
    page.screenshotCalls += 1;
    return Buffer.from('image');
  };
  return page;
}

function fakeContext() {
  const instance = {
    traceCalls: [],
  };
  instance.tracing = {
    stop: async (options) => {
      instance.traceCalls.push(options || null);
    },
  };
  return instance;
}

let context = fakeContext();
const sensitivePage = makePage(true);
await assert.rejects(
  captureEvidenceScreenshot(sensitivePage, { path: 'secret.png' }),
  /EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=screenshot/,
);
assert.equal(sensitivePage.screenshotCalls, 0);
await assert.rejects(
  stopEvidenceTrace(context, [sensitivePage], 'secret.zip'),
  /EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=trace/,
);
assert.deepEqual(context.traceCalls, [null]);

context = fakeContext();
const ordinaryPage = makePage(false);
await captureEvidenceScreenshot(ordinaryPage, { path: 'ordinary.png' });
assert.equal(ordinaryPage.screenshotCalls, 1);
await stopEvidenceTrace(context, [ordinaryPage], 'ordinary.zip');
assert.deepEqual(context.traceCalls, [{ path: 'ordinary.zip' }]);

console.log('[frontend_evidence_capture_guard.test] PASS sensitive_screenshot=0 sensitive_trace_export=0 ordinary_capture=2');
