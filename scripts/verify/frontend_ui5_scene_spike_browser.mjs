import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from '../../frontend/apps/scene-ui5-spike/node_modules/playwright/index.mjs';

const baseUrl = process.env.SC_UI5_SPIKE_URL || 'http://127.0.0.1:5186';
const artifactDir = process.env.SC_UI5_SPIKE_ARTIFACT_DIR || '/tmp/sc-ui5-scene-spike';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function inspectViewport(page, name, viewport) {
  await page.setViewportSize(viewport);
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.locator('[data-scene-object-page]').waitFor({ state: 'visible' });
  await page.waitForFunction(() => customElements.get('ui5-dynamic-page'));

  const facts = await page.locator('[data-header-facts] .scene-header-fact').count();
  const workTabs = await page.locator('.scene-worktab').count();
  const activityTabs = await page.locator('[data-activity-tab]').count();
  const taskControls = await page.locator('[data-task-canvas] ui5-input, [data-task-canvas] ui5-select, [data-task-canvas] ui5-date-picker, [data-task-canvas] ui5-textarea').count();
  const contextFacts = await page.locator('[data-context-rail] dd').count();
  const chapterNav = await page.locator('[data-chapter-nav], .scene-chapter-tabs').count();
  const submitAction = await page.locator('[data-action-id="submit"]').count();
  const overflow = await page.evaluate(() => ({
    body: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    shell: document.querySelector('[data-scene-object-page]').scrollWidth - document.querySelector('[data-scene-object-page]').clientWidth,
  }));

  assert(facts === 8, `${name}: expected 8 header facts, got ${facts}`);
  assert(workTabs === 2, `${name}: expected 2 work tabs, got ${workTabs}`);
  assert(activityTabs === 4, `${name}: expected 4 activity tabs, got ${activityTabs}`);
  assert(taskControls >= 12, `${name}: task information density too low (${taskControls})`);
  assert(contextFacts >= 13, `${name}: context information density too low (${contextFacts})`);
  assert(chapterNav === 0, `${name}: internal chapter navigation must stay hidden`);
  assert(submitAction === 1, `${name}: expected one primary submit action`);
  assert(overflow.body <= 0 && overflow.shell <= 0, `${name}: horizontal overflow ${JSON.stringify(overflow)}`);

  const taskBox = await page.locator('[data-task-canvas]').boundingBox();
  const contextBox = await page.locator('[data-context-rail]').boundingBox();
  assert(taskBox && contextBox, `${name}: task/context regions are not measurable`);
  if (viewport.width >= 1100) {
    assert(contextBox.x > taskBox.x + taskBox.width - 2, `${name}: desktop context must be a distinct right rail`);
  } else {
    assert(contextBox.y > taskBox.y, `${name}: mobile context must follow the task canvas`);
  }

  const screenshot = path.join(artifactDir, `${name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  return { name, viewport, facts, workTabs, activityTabs, taskControls, contextFacts, overflow, screenshot };
}

async function main() {
  await mkdir(artifactDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleErrors = [];
  const failedResponses = [];
  const mutatingRequests = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() });
  });
  page.on('request', (request) => {
    if (!['GET', 'HEAD'].includes(request.method())) {
      mutatingRequests.push({ method: request.method(), url: request.url() });
    }
  });

  try {
    const views = [];
    views.push(await inspectViewport(page, 'desktop-1440', { width: 1440, height: 1050 }));
    views.push(await inspectViewport(page, 'mobile-390', { width: 390, height: 844 }));

    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
    assert(failedResponses.length === 0, `failed responses: ${JSON.stringify(failedResponses)}`);
    assert(mutatingRequests.length === 0, `mutating requests: ${JSON.stringify(mutatingRequests)}`);

    const report = {
      status: 'PASS',
      baseUrl,
      views,
      consoleErrors,
      failedResponses,
      mutatingRequests,
      assertions: {
        genericSceneContract: true,
        topWorkTabsRetained: true,
        chapterNavigationHidden: true,
        taskAndContextSeparated: true,
        highInformationDensity: true,
        responsive390: true,
        horizontalOverflow: 0,
        runtimeWrites: 0,
      },
    };
    await writeFile(path.join(artifactDir, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log(`[verify.frontend.ui5_scene_spike.browser] PASS evidence=${artifactDir}`);
  } finally {
    await browser.close();
  }
}

main().catch(async (error) => {
  await mkdir(artifactDir, { recursive: true });
  await writeFile(path.join(artifactDir, 'failure.txt'), `${error.stack || error}\n`);
  console.error(`[verify.frontend.ui5_scene_spike.browser] FAIL ${error.stack || error}`);
  process.exitCode = 1;
});
