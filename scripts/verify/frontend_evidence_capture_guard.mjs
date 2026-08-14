const SENSITIVE_SELECTOR = '[data-evidence-sensitive]';
const TRACKER_KEY = '__scEvidenceSensitiveObserved';

export async function installEvidenceSensitivityTracker(context) {
  await context.addInitScript(({ selector, trackerKey }) => {
    const markSensitive = () => {
      if (document.querySelector(selector)) window[trackerKey] = true;
    };
    window[trackerKey] = false;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', markSensitive, { once: true });
    } else {
      markSensitive();
    }
    new MutationObserver(markSensitive).observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['data-evidence-sensitive'],
    });
  }, { selector: SENSITIVE_SELECTOR, trackerKey: TRACKER_KEY });
}

export async function evidenceSensitivityObserved(page) {
  if (!page || (typeof page.isClosed === 'function' && page.isClosed())) return false;
  try {
    return await page.evaluate(({ selector, trackerKey }) => (
      Boolean(window[trackerKey]) || Boolean(document.querySelector(selector))
    ), { selector: SENSITIVE_SELECTOR, trackerKey: TRACKER_KEY });
  } catch (error) {
    throw new Error(`EVIDENCE_SENSITIVITY_UNRESOLVED: ${error?.message || error}`);
  }
}

export async function assertEvidenceCaptureAllowed(page, captureKind) {
  if (await evidenceSensitivityObserved(page)) {
    throw new Error(`EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=${captureKind}`);
  }
}

export async function captureEvidenceScreenshot(page, options) {
  await assertEvidenceCaptureAllowed(page, 'screenshot');
  return page.screenshot(options);
}

export async function stopEvidenceTrace(context, pages, outputPath) {
  for (const page of pages || []) {
    if (await evidenceSensitivityObserved(page)) {
      await context.tracing.stop();
      throw new Error('EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=trace');
    }
  }
  await context.tracing.stop({ path: outputPath });
}
