const SENSITIVE_SELECTOR = '[data-evidence-sensitive]';
const REPORT_BINDING = '__scReportEvidenceSensitive';
const FRAME_TRACKER_KEY = '__scEvidenceSensitiveObserved';
const contextSensitivity = new WeakMap();

function sensitivityState(context) {
  return contextSensitivity.get(context);
}

export async function installEvidenceSensitivityTracker(context) {
  if (sensitivityState(context)) return;
  const state = { observed: false, sources: [] };
  contextSensitivity.set(context, state);
  await context.exposeBinding(REPORT_BINDING, ({ frame, page }) => {
    state.observed = true;
    state.sources.push({
      frame_url: typeof frame?.url === 'function' ? frame.url() : '',
      page_url: typeof page?.url === 'function' ? page.url() : '',
    });
  });
  await context.addInitScript(({ selector, reportBinding, frameTrackerKey }) => {
    const reportSensitive = () => {
      if (!document.querySelector(selector)) return;
      window[frameTrackerKey] = true;
      const report = window[reportBinding];
      if (typeof report === 'function') void report().catch(() => {});
    };
    const observe = () => {
      reportSensitive();
      if (!document.documentElement) return;
      new MutationObserver(reportSensitive).observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['data-evidence-sensitive'],
      });
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', observe, { once: true });
    } else {
      observe();
    }
  }, {
    selector: SENSITIVE_SELECTOR,
    reportBinding: REPORT_BINDING,
    frameTrackerKey: FRAME_TRACKER_KEY,
  });
}

export async function evidenceSensitivityObserved(page) {
  if (!page) return false;
  const context = typeof page.context === 'function' ? page.context() : null;
  if (context && sensitivityState(context)?.observed) return true;
  if (typeof page.isClosed === 'function' && page.isClosed()) return false;
  try {
    const frames = typeof page.frames === 'function' ? page.frames() : [page];
    for (const frame of frames) {
      const observed = await frame.evaluate(({ selector, frameTrackerKey }) => (
        Boolean(window[frameTrackerKey]) || Boolean(document.querySelector(selector))
      ), { selector: SENSITIVE_SELECTOR, frameTrackerKey: FRAME_TRACKER_KEY });
      if (observed) {
        const state = context ? sensitivityState(context) : null;
        if (state) state.observed = true;
        return true;
      }
    }
    return false;
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
  const state = sensitivityState(context);
  if (!state) {
    await context.tracing.stop();
    throw new Error('EVIDENCE_SENSITIVITY_UNRESOLVED: tracker not installed');
  }
  if (state.observed) {
    await context.tracing.stop();
    throw new Error('EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=trace');
  }
  try {
    for (const page of pages || []) {
      if (!(await evidenceSensitivityObserved(page))) continue;
      await context.tracing.stop();
      throw new Error('EVIDENCE_SENSITIVE_CAPTURE_DENIED kind=trace');
    }
  } catch (error) {
    if (!state.observed) await context.tracing.stop().catch(() => {});
    throw error;
  }
  await context.tracing.stop({ path: outputPath });
}
