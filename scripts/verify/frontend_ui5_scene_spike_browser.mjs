import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from '../../frontend/apps/scene-ui5-spike/node_modules/playwright/index.mjs';

const baseUrl = process.env.SC_UI5_SPIKE_URL || 'http://127.0.0.1:5186';
const artifactDir = process.env.SC_UI5_SPIKE_ARTIFACT_DIR || '/tmp/sc-ui5-scene-spike';
const activeRequests = new Set();

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForRequestQuiescence(timeoutMs = 15000, idleMs = 600) {
  const startedAt = Date.now();
  let idleSince = activeRequests.size === 0 ? Date.now() : 0;
  while (Date.now() - startedAt < timeoutMs) {
    if (activeRequests.size === 0) {
      if (!idleSince) idleSince = Date.now();
      if (Date.now() - idleSince >= idleMs) return;
    } else {
      idleSince = 0;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`runtime requests did not settle: ${activeRequests.size} still active`);
}

function luminance(hex) {
  const channels = hex.replace('#', '').match(/.{2}/g).map((value) => Number.parseInt(value, 16) / 255);
  const linear = channels.map((value) => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(foreground, background) {
  const first = luminance(foreground);
  const second = luminance(background);
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}

async function auditAccessibility(page, surfaceSelector, name) {
  const result = await page.locator(surfaceSelector).evaluate((surface) => {
    const ids = [...surface.querySelectorAll('[id]')].map((element) => element.id).filter(Boolean);
    const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
    const interactive = [...surface.querySelectorAll('button, input, select, textarea, [role="button"], [role="option"]')]
      .filter((element) => !element.hasAttribute('disabled'));
    const unnamed = interactive.filter((element) => {
      const aria = element.getAttribute('aria-label') || element.getAttribute('aria-labelledby');
      const text = element.textContent?.trim();
      const id = element.getAttribute('id');
      const label = id ? surface.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
      return !aria && !text && !label;
    }).map((element) => element.outerHTML.slice(0, 180));
    return { duplicateIds, unnamed, interactiveCount: interactive.length };
  });
  assert(result.duplicateIds.length === 0, `${name}: duplicate ids ${JSON.stringify(result.duplicateIds)}`);
  assert(result.unnamed.length === 0, `${name}: unnamed interactive controls ${JSON.stringify(result.unnamed)}`);
  assert(result.interactiveCount > 0, `${name}: expected keyboard-interactive controls`);
  return result;
}

async function selectActivityTab(page, kit, tabId) {
  if (kit === 'ui5-horizon') {
    await page.locator('.scene-ui5-tabs').evaluate((container, requestedTabId) => {
      const tab = container.querySelector(`[data-activity-tab="${requestedTabId}"]`);
      if (!tab || typeof container.selectTab !== 'function') {
        throw new Error('UI5 public tab selection API is unavailable');
      }
      const tabs = [...container.querySelectorAll('ui5-tab')];
      const tabIndex = tabs.indexOf(tab);
      if (!container.selectTab(tab, tabIndex)) {
        throw new Error('UI5 tab-select event was prevented');
      }
      tabs.forEach((item) => {
        item.selected = item === tab;
      });
    }, tabId);
  } else if (kit === 'tdesign-modern') {
    const label = tabId === 'attachments' ? '附件' : tabId;
    await page.locator('.scene-driver-tabs .t-tabs__nav-item').filter({ hasText: label }).evaluate((element) => element.click());
  } else {
    await page.locator(`.scene-native-tabs [data-activity-tab="${tabId}"]`).click();
  }
}

async function inspectReviewPanel(page, name, expectedKit) {
  const trigger = page.locator('[data-review-trigger]');
  assert(await trigger.count() === 1, `${name}: expected one review trigger`);
  await trigger.click();
  if (expectedKit === 'ui5-horizon') {
    await page.waitForFunction(() => Boolean(customElements.get('ui5-dialog')));
  }
  const panel = page.locator('[data-review-panel]').last();
  await panel.waitFor({ state: 'visible' });
  if (expectedKit === 'tdesign-modern') {
    await page.waitForFunction(() => document.querySelector('[data-review-panel]')?.classList.contains('t-drawer--open'));
  }
  await page.getByText('提交前业务核对', { exact: true }).last().waitFor({ state: 'visible' });
  await page.getByText('发票完整度', { exact: true }).last().waitFor({ state: 'visible' });
  await page.waitForTimeout(350);

  const screenshot = path.join(artifactDir, `${name}-review-panel.png`);
  await page.screenshot({ path: screenshot });

  if (expectedKit === 'ui5-horizon') {
    await panel.getByText('核对完成', { exact: true }).click();
  } else if (expectedKit === 'tdesign-modern') {
    await page.keyboard.press('Escape');
  } else {
    await panel.getByRole('button', { name: '关闭核对面板' }).click({ position: { x: 8, y: 8 } });
  }
  if (expectedKit === 'tdesign-modern') {
    await page.waitForFunction(() => !document.querySelector('[data-review-panel]')?.classList.contains('t-drawer--open'));
  } else {
    await panel.waitFor({ state: 'hidden' });
  }
  return screenshot;
}

async function verifyReviewStateSurvivesDriverSwitch(page) {
  await page.locator('[data-review-trigger]').click();
  await page.waitForFunction(() => Boolean(customElements.get('ui5-dialog')));
  await page.locator('[data-review-panel]').last().waitFor({ state: 'visible' });
  await page.evaluate(() => document.querySelector('[data-kit-choice="tdesign-modern"]')?.click());
  await page.locator('[data-scene-ui-kit="tdesign-modern"] [data-scene-object-page]').waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.querySelector('[data-review-panel]')?.classList.contains('t-drawer--open'));
  await page.getByText('提交前业务核对', { exact: true }).last().waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('[data-review-panel]')?.classList.contains('t-drawer--open'));
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(350);
  await page.locator('[data-kit-choice="ui5-horizon"]').click();
  await page.locator('[data-scene-ui-kit="ui5-horizon"] [data-scene-object-page]').waitFor({ state: 'visible' });
}

async function inspectRenderedScene(page, name, viewport, expectedKit) {
  await page.setViewportSize(viewport);
  await page.locator(`[data-scene-ui-kit="${expectedKit}"] [data-scene-object-page]`).waitFor({ state: 'visible' });
  if (expectedKit === 'ui5-horizon') {
    await page.waitForFunction(() => customElements.get('ui5-dynamic-page') && customElements.get('ui5-tabcontainer'));
  } else if (expectedKit === 'tdesign-modern') {
    await page.locator('[data-control-driver="tdesign-modern"]').first().waitFor({ state: 'visible' });
  }

  const facts = await page.locator('[data-header-facts] .scene-header-fact').count();
  const workTabs = await page.locator('.scene-worktab').count();
  const activityTabs = expectedKit === 'tdesign-modern'
    ? await page.locator('.scene-driver-tabs .t-tabs__nav-item').count()
    : await page.locator('[data-activity-tab]').count();
  const taskControls = await page.locator('[data-task-canvas] input, [data-task-canvas] select, [data-task-canvas] textarea, [data-task-canvas] ui5-input, [data-task-canvas] ui5-select, [data-task-canvas] ui5-date-picker, [data-task-canvas] ui5-textarea').count();
  const contextFacts = await page.locator('[data-context-rail] dd').count();
  const notices = await page.locator('[data-scene-notices] [data-notice-id]').count();
  const relationTables = await page.locator('[data-relation-zone] [data-relation-table]').count();
  const relationRows = expectedKit === 'tdesign-modern'
    ? await page.locator('[data-relation-zone] .t-table__body tr').count()
    : await page.locator('[data-relation-zone] [data-row-id]').count();
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
  assert(notices === 1, `${name}: expected one contract-driven notice, got ${notices}`);
  assert(relationTables === 2, `${name}: expected two relation tables, got ${relationTables}`);
  assert(relationRows === 4, `${name}: expected four relation rows, got ${relationRows}`);
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

  let taskScreenshot;
  let activityScreenshot;
  let relationScreenshot;
  let reviewScreenshot;
  if (viewport.width < 640) {
    await page.locator('[data-task-canvas]').scrollIntoViewIfNeeded();
    await page.waitForTimeout(350);
    const visibleTaskPixels = await page.locator('[data-task-canvas]').evaluate((element) => {
      const rect = element.getBoundingClientRect();
      return Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
    });
    assert(visibleTaskPixels >= 240, `${name}: task canvas did not become materially visible (${visibleTaskPixels}px)`);
    taskScreenshot = path.join(artifactDir, `${name}-task.png`);
    await page.screenshot({ path: taskScreenshot });
  } else {
    await page.locator('[data-relation-zone]').scrollIntoViewIfNeeded();
    await page.getByText('待补发票', { exact: true }).waitFor({ state: 'visible' });
    relationScreenshot = path.join(artifactDir, `${name}-relations.png`);
    await page.screenshot({ path: relationScreenshot });
    reviewScreenshot = await inspectReviewPanel(page, name, expectedKit);
    await page.locator('[data-activity-tabs]').scrollIntoViewIfNeeded();
    await selectActivityTab(page, expectedKit, 'attachments');
    await page.getByText('第3期结算确认单.pdf', { exact: true }).waitFor({ state: 'visible' });
    activityScreenshot = path.join(artifactDir, `${name}-activity.png`);
    await page.screenshot({ path: activityScreenshot });
  }

  await waitForRequestQuiescence();

  return {
    name,
    kit: expectedKit,
    viewport,
    facts,
    workTabs,
    activityTabs,
    taskControls,
    contextFacts,
    notices,
    relationTables,
    relationRows,
    overflow,
    screenshot,
    taskScreenshot,
    activityScreenshot,
    relationScreenshot,
    reviewScreenshot,
  };
}

async function inspectCollectionScene(page, name, viewport, expectedKit) {
  await page.setViewportSize(viewport);
  const surface = page.locator(`[data-scene-ui-kit="${expectedKit}"] [data-scene-collection-surface]`);
  await surface.waitFor({ state: 'visible' });
  if (expectedKit === 'ui5-horizon' && viewport.width >= 640) {
    await page.waitForFunction(() => Boolean(customElements.get('ui5-table')));
  }
  const summaries = await surface.locator('[data-collection-summaries] article').count();
  const filters = await surface.locator('[data-filter-id]').count();
  const desktopRows = expectedKit === 'tdesign-modern'
    ? await surface.locator('[data-collection-table] .t-table__body tr').count()
    : await surface.locator('[data-collection-table] [data-row-id]').count();
  const mobileRows = await surface.locator('[data-collection-mobile-cards] [data-collection-row]').count();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert(summaries === 4, `${name}: expected four collection summaries, got ${summaries}`);
  assert(filters === 4, `${name}: expected four contract filters, got ${filters}`);
  assert(desktopRows === 4, `${name}: expected four desktop rows, got ${desktopRows}`);
  assert(mobileRows === 4, `${name}: expected four mobile cards, got ${mobileRows}`);
  assert(overflow <= 0, `${name}: collection horizontal overflow ${overflow}`);
  if (viewport.width < 640) {
    assert(await surface.locator('[data-collection-mobile-cards]').isVisible(), `${name}: compact cards must be visible`);
    assert(!(await surface.locator('[data-collection-table]').isVisible()), `${name}: desktop table must yield to compact cards`);
  }
  const screenshot = path.join(artifactDir, `${name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  await waitForRequestQuiescence();
  return { name, kind: 'list', kit: expectedKit, viewport, summaries, filters, desktopRows, mobileRows, overflow, screenshot };
}

async function inspectNormalizedCollectionPilot(page, name, viewport, expectedKit) {
  await page.setViewportSize(viewport);
  const provider = page.locator(`[data-scene-ui-kit="${expectedKit}"]`);
  const surface = provider.locator('[data-scene-collection-surface]');
  await surface.waitFor({ state: 'visible' });
  if (expectedKit === 'ui5-horizon' && viewport.width >= 640) {
    await page.waitForFunction(() => Boolean(customElements.get('ui5-table')));
  }
  const source = await surface.getAttribute('data-scene-contract-source');
  const pageId = await surface.getAttribute('data-scene-contract-page-id');
  const readonly = await surface.getAttribute('data-scene-collection-readonly');
  const title = await surface.locator('h1').innerText();
  const tableText = await surface.locator('[data-collection-table]').innerText();
  const actionCount = await surface.locator('.scene-collection-actions button, .scene-collection-actions ui5-button').count();
  const filterButtonCount = await surface.locator('.scene-collection-filters button').count();
  const summaries = await surface.locator('[data-collection-summaries] article').count();
  const filters = await surface.locator('[data-filter-id]').count();
  const desktopRows = expectedKit === 'tdesign-modern'
    ? await surface.locator('[data-collection-table] .t-table__body tr').count()
    : await surface.locator('[data-collection-table] [data-row-id]').count();
  const mobileList = surface.locator('[data-collection-mobile-cards]');
  const mobileRows = await mobileList.locator('[data-collection-row]').count();
  const mobileRole = await mobileList.getAttribute('role');
  const firstMobileRow = mobileList.locator('[data-collection-row]').first();
  const firstMobileRole = await firstMobileRow.getAttribute('role');
  const firstTabIndex = await firstMobileRow.getAttribute('tabindex');
  const firstSelected = await firstMobileRow.getAttribute('aria-selected');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

  assert(await page.locator('[data-normalized-pilot="active"]').count() === 1, `${name}: pilot feature flag is not observable`);
  assert(source === 'normalized-collection', `${name}: source mismatch ${source}`);
  assert(pageId === 'res-company-directory', `${name}: page identity mismatch ${pageId}`);
  assert(readonly === 'true', `${name}: pilot must be read-only`);
  assert(title === '公司目录', `${name}: normalized title mismatch ${title}`);
  ['公司名称', '国家/地区', '本位币', '状态', '最近更新'].forEach((label) => {
    assert(tableText.includes(label), `${name}: missing authoritative column label ${label}`);
  });
  assert(!tableText.includes('付款申请'), `${name}: payment fixture leaked into normalized pilot`);
  assert(actionCount === 0, `${name}: read-only pilot rendered actions`);
  assert(filterButtonCount === 0, `${name}: read-only filters must not masquerade as buttons`);
  assert(summaries === 4 && filters === 2, `${name}: normalized summary/filter projection mismatch`);
  assert(desktopRows === 3 && mobileRows === 3, `${name}: normalized rows mismatch desktop=${desktopRows} mobile=${mobileRows}`);
  assert(mobileRole === 'list' && firstMobileRole === 'listitem', `${name}: read-only cards must expose list semantics`);
  assert(firstTabIndex === null && firstSelected === null, `${name}: read-only cards must not expose selection state`);
  assert(overflow <= 0, `${name}: normalized pilot horizontal overflow ${overflow}`);
  if (viewport.width < 640) {
    assert(await mobileList.isVisible(), `${name}: normalized compact cards must be visible`);
    assert(!(await surface.locator('[data-collection-table]').isVisible()), `${name}: normalized desktop table must yield on mobile`);
  }
  const screenshot = path.join(artifactDir, `${name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  await waitForRequestQuiescence();
  return {
    name,
    kind: 'normalized-collection-pilot',
    kit: expectedKit,
    viewport,
    source,
    pageId,
    readonly,
    title,
    summaries,
    filters,
    desktopRows,
    mobileRows,
    overflow,
    screenshot,
  };
}

async function inspectHierarchyScene(page, name, viewport, expectedKit) {
  await page.setViewportSize(viewport);
  const surface = page.locator(`[data-scene-ui-kit="${expectedKit}"] [data-scene-hierarchy-surface]`);
  await surface.waitFor({ state: 'visible' });
  const summaries = await surface.locator('[data-hierarchy-summaries] article').count();
  const nodes = await surface.locator('[data-hierarchy-node]').count();
  const tree = surface.locator('[data-hierarchy-tree]');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert(summaries === 4, `${name}: expected four hierarchy summaries, got ${summaries}`);
  assert(nodes === 7, `${name}: expected seven visible hierarchy nodes, got ${nodes}`);
  assert(await tree.getAttribute('role') === 'tree', `${name}: hierarchy must expose semantic tree role`);
  assert(overflow <= 0, `${name}: hierarchy horizontal overflow ${overflow}`);
  const screenshot = path.join(artifactDir, `${name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  await waitForRequestQuiescence();
  return { name, kind: 'hierarchy', kit: expectedKit, viewport, summaries, nodes, overflow, screenshot };
}

async function preferenceFacts(page) {
  const provider = page.locator('[data-scene-ui-kit]').first();
  return {
    kit: await provider.getAttribute('data-scene-ui-kit'),
    source: await page.locator('[data-preference-source]').getAttribute('data-preference-source'),
  };
}

async function main() {
  await mkdir(artifactDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleErrors = [];
  const failedResponses = [];
  const failedRequests = [];
  const mutatingRequests = [];
  const requestedAssets = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push({ text: message.text(), location: message.location() });
  });
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() });
  });
  page.on('request', (request) => {
    activeRequests.add(request);
    requestedAssets.push(request.url());
    if (!['GET', 'HEAD'].includes(request.method())) {
      mutatingRequests.push({ method: request.method(), url: request.url() });
    }
  });
  page.on('requestfinished', (request) => {
    activeRequests.delete(request);
  });
  page.on('requestfailed', (request) => {
    activeRequests.delete(request);
    failedRequests.push({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      pageUrl: page.url(),
      failure: request.failure(),
    });
  });

  try {
    const views = [];
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    await page.locator('[data-scene-ui-kit="sc-native"] [data-scene-object-page]').waitFor({ state: 'visible' });

    const initialAssetCount = requestedAssets.length;
    const ui5DefinedBeforeSwitch = await page.evaluate(() => Boolean(customElements.get('ui5-dynamic-page')));
    const tdesignBeforeSwitch = await page.locator('[data-control-driver="tdesign-modern"]').count();
    assert(!ui5DefinedBeforeSwitch, 'native driver must not register UI5 before switching');
    assert(tdesignBeforeSwitch === 0, 'native driver must not render TDesign before switching');
    views.push(await inspectRenderedScene(page, 'native-desktop-1440', { width: 1440, height: 1050 }, 'sc-native'));

    const draftMarker = '切换驱动后仍保留的未保存付款说明';
    await page.locator('#payment-purpose').fill(draftMarker);

    await page.locator('[data-token-profile-choice]').selectOption('accessible-contrast');
    const tokenFacts = await page.locator('[data-scene-ui-kit]').evaluate((provider) => {
      const style = getComputedStyle(provider);
      return {
        profile: provider.getAttribute('data-scene-token-profile'),
        text: style.getPropertyValue('--sc-scene-text').trim(),
        surface: style.getPropertyValue('--sc-scene-surface').trim(),
        focus: style.getPropertyValue('--sc-scene-focus').trim(),
      };
    });
    assert(tokenFacts.profile === 'accessible-contrast', `token profile mismatch: ${JSON.stringify(tokenFacts)}`);
    assert(contrastRatio(tokenFacts.text, tokenFacts.surface) >= 7, `high contrast text ratio is too low: ${JSON.stringify(tokenFacts)}`);
    assert(await page.locator('#payment-purpose').inputValue() === draftMarker, 'draft state must survive token switching');
    await page.evaluate(() => {
      window.scrollTo(0, 0);
      document.querySelector('.scene-native-page-frame')?.scrollTo(0, 0);
    });
    await page.waitForTimeout(250);
    const highContrastScreenshot = path.join(artifactDir, 'native-desktop-1440-high-contrast.png');
    await page.screenshot({ path: highContrastScreenshot, fullPage: true });

    await page.locator('[data-kit-choice="sc-native"]').focus();
    await page.keyboard.press('Tab');
    const focusFacts = await page.evaluate(() => {
      const element = document.activeElement;
      const style = element ? getComputedStyle(element) : null;
      return { tag: element?.tagName, outlineStyle: style?.outlineStyle, outlineWidth: style?.outlineWidth };
    });
    assert(focusFacts.outlineStyle !== 'none' && focusFacts.outlineWidth !== '0px', `keyboard focus ring missing: ${JSON.stringify(focusFacts)}`);
    const objectAccessibility = await auditAccessibility(page, '[data-scene-object-page]', 'object-accessibility');

    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    await page.locator('[data-scene-ui-kit="tdesign-modern"] [data-scene-object-page]').waitFor({ state: 'visible' });
    const tdesignAssetsLoadedAfterSwitch = requestedAssets.length > initialAssetCount;
    assert(tdesignAssetsLoadedAfterSwitch, 'TDesign driver must load lazily after the explicit switch');
    const tdesignDraftValue = await page.locator('[data-control-driver="tdesign-modern"] [data-scene-driver-control="textarea"] textarea').inputValue();
    assert(tdesignDraftValue === draftMarker, 'draft state must survive native-to-TDesign switching');
    views.push(await inspectRenderedScene(page, 'tdesign-desktop-1440', { width: 1440, height: 1050 }, 'tdesign-modern'));
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.goto(`${baseUrl}?kit=tdesign-modern`, { waitUntil: 'networkidle' });
    views.push(await inspectRenderedScene(page, 'tdesign-mobile-390', { width: 390, height: 844 }, 'tdesign-modern'));
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.locator('[data-kit-choice="ui5-horizon"]').click();
    await page.locator('[data-scene-ui-kit="ui5-horizon"] [data-scene-object-page]').waitFor({ state: 'visible' });
    await page.waitForFunction(() => customElements.get('ui5-dynamic-page') && customElements.get('ui5-tabcontainer'));
    const ui5AssetsLoadedAfterSwitch = requestedAssets.length > initialAssetCount;
    assert(ui5AssetsLoadedAfterSwitch, 'UI5 driver must load lazily after the explicit switch');
    views.push(await inspectRenderedScene(page, 'ui5-desktop-1440', { width: 1440, height: 1050 }, 'ui5-horizon'));
    await verifyReviewStateSurvivesDriverSwitch(page);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.goto(`${baseUrl}?kit=ui5-horizon`, { waitUntil: 'networkidle' });
    views.push(await inspectRenderedScene(page, 'ui5-mobile-390', { width: 390, height: 844 }, 'ui5-horizon'));
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    await page.locator('[data-scene-ui-kit="tdesign-modern"] [data-scene-object-page]').waitFor({ state: 'visible' });
    await waitForRequestQuiescence();
    await page.reload({ waitUntil: 'networkidle' });
    await page.locator('[data-scene-ui-kit="tdesign-modern"] [data-scene-object-page]').waitFor({ state: 'visible' });
    const persistedDriver = await page.locator('[data-scene-ui-kit]').getAttribute('data-scene-ui-kit');
    assert(persistedDriver === 'tdesign-modern', 'explicit user driver preference must survive reload');
    const persistedTokenProfile = await page.locator('[data-scene-ui-kit]').getAttribute('data-scene-token-profile');
    assert(persistedTokenProfile === 'accessible-contrast', 'explicit design-token preference must survive reload');

    await page.locator('[data-kit-choice="sc-native"]').click();
    await page.locator('[data-scene-ui-kit="sc-native"] [data-scene-object-page]').waitFor({ state: 'visible' });
    const contractParity = await page.evaluate(() => ({
      facts: document.querySelectorAll('[data-header-facts] .scene-header-fact').length,
      controls: document.querySelectorAll('[data-task-canvas] input, [data-task-canvas] select, [data-task-canvas] textarea').length,
      context: document.querySelectorAll('[data-context-rail] dd').length,
      activities: document.querySelectorAll('[data-activity-tab]').length,
      notices: document.querySelectorAll('[data-scene-notices] [data-notice-id]').length,
      relationTables: document.querySelectorAll('[data-relation-table]').length,
      relationRows: document.querySelectorAll('[data-row-id]').length,
    }));
    const allowedOrigin = new URL(baseUrl).origin;
    const externalRequests = requestedAssets.filter((url) => {
      const protocol = new URL(url).protocol;
      return !['data:', 'blob:'].includes(protocol) && new URL(url).origin !== allowedOrigin;
    });
    assert(
      contractParity.facts === 8
        && contractParity.controls >= 12
        && contractParity.context >= 13
        && contractParity.activities === 4
        && contractParity.notices === 1
        && contractParity.relationTables === 2
        && contractParity.relationRows === 4,
      `contract parity failed after switching back: ${JSON.stringify(contractParity)}`,
    );

    const collectionViews = [];
    await page.goto(`${baseUrl}?scene=list&kit=sc-native`, { waitUntil: 'networkidle' });
    collectionViews.push(await inspectCollectionScene(page, 'native-list-desktop-1440', { width: 1440, height: 980 }, 'sc-native'));
    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    collectionViews.push(await inspectCollectionScene(page, 'tdesign-list-desktop-1440', { width: 1440, height: 980 }, 'tdesign-modern'));
    await page.locator('[data-kit-choice="ui5-horizon"]').click();
    collectionViews.push(await inspectCollectionScene(page, 'ui5-list-desktop-1440', { width: 1440, height: 980 }, 'ui5-horizon'));
    collectionViews.push(await inspectCollectionScene(page, 'ui5-list-mobile-390', { width: 390, height: 844 }, 'ui5-horizon'));
    await page.locator('[data-collection-row="pr-001"]').focus();
    await page.keyboard.press('Space');
    assert(await page.locator('[data-collection-row="pr-001"]').getAttribute('aria-selected') === 'true', 'Space must select a compact collection card');
    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    await page.locator('[data-scene-ui-kit="tdesign-modern"] [data-scene-collection-surface]').waitFor({ state: 'visible' });
    assert(
      await page.locator('[data-collection-row="pr-001"]').evaluate((element) => element.classList.contains('scene-collection-mobile-card--selected')),
      'collection selection state must survive driver switching',
    );
    const collectionAccessibility = await auditAccessibility(page, '[data-scene-collection-surface]', 'collection-accessibility');

    const normalizedPilotViews = [];
    await page.goto(`${baseUrl}?scene=list&pilot=normalized-collection&kit=sc-native`, { waitUntil: 'networkidle' });
    normalizedPilotViews.push(await inspectNormalizedCollectionPilot(page, 'normalized-company-native-desktop-1440', { width: 1440, height: 980 }, 'sc-native'));
    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    normalizedPilotViews.push(await inspectNormalizedCollectionPilot(page, 'normalized-company-tdesign-desktop-1440', { width: 1440, height: 980 }, 'tdesign-modern'));
    await page.locator('[data-kit-choice="ui5-horizon"]').click();
    normalizedPilotViews.push(await inspectNormalizedCollectionPilot(page, 'normalized-company-ui5-desktop-1440', { width: 1440, height: 980 }, 'ui5-horizon'));
    normalizedPilotViews.push(await inspectNormalizedCollectionPilot(page, 'normalized-company-ui5-mobile-390', { width: 390, height: 844 }, 'ui5-horizon'));

    const hierarchyViews = [];
    await page.goto(`${baseUrl}?scene=hierarchy&kit=sc-native`, { waitUntil: 'networkidle' });
    hierarchyViews.push(await inspectHierarchyScene(page, 'native-hierarchy-desktop-1440', { width: 1440, height: 980 }, 'sc-native'));
    await page.locator('[data-kit-choice="tdesign-modern"]').click();
    hierarchyViews.push(await inspectHierarchyScene(page, 'tdesign-hierarchy-desktop-1440', { width: 1440, height: 980 }, 'tdesign-modern'));
    await page.locator('[data-kit-choice="ui5-horizon"]').click();
    hierarchyViews.push(await inspectHierarchyScene(page, 'ui5-hierarchy-desktop-1440', { width: 1440, height: 980 }, 'ui5-horizon'));
    hierarchyViews.push(await inspectHierarchyScene(page, 'ui5-hierarchy-mobile-390', { width: 390, height: 844 }, 'ui5-horizon'));
    await page.getByRole('button', { name: '折叠CC-3102 / 土建工程' }).focus();
    await page.keyboard.press('Enter');
    assert(await page.locator('[data-hierarchy-node]').count() === 5, 'hierarchy collapse must remove descendant rows');
    await page.locator('[data-kit-choice="sc-native"]').click();
    await page.locator('[data-scene-ui-kit="sc-native"] [data-scene-hierarchy-surface]').waitFor({ state: 'visible' });
    assert(await page.locator('[data-hierarchy-node]').count() === 5, 'hierarchy expansion state must survive driver switching');
    const hierarchyAccessibility = await auditAccessibility(page, '[data-scene-hierarchy-surface]', 'hierarchy-accessibility');

    await page.evaluate(() => window.localStorage.removeItem('sc.scene.ui.driver'));
    await page.goto(`${baseUrl}?scene=list&organizationKit=ui5-horizon`, { waitUntil: 'networkidle' });
    const organizationPreference = await preferenceFacts(page);
    assert(
      organizationPreference.kit === 'ui5-horizon' && organizationPreference.source === 'organization-default',
      `organization default preference mismatch: ${JSON.stringify(organizationPreference)}`,
    );
    await page.evaluate(() => window.localStorage.setItem('sc.scene.ui.driver', 'tdesign-modern'));
    await page.goto(`${baseUrl}?scene=list&organizationKit=ui5-horizon`, { waitUntil: 'networkidle' });
    const userPreference = await preferenceFacts(page);
    assert(
      userPreference.kit === 'tdesign-modern' && userPreference.source === 'user',
      `user preference must override organization default: ${JSON.stringify(userPreference)}`,
    );
    await page.goto(`${baseUrl}?scene=list&organizationKit=sc-native&lockedKit=ui5-horizon`, { waitUntil: 'networkidle' });
    const organizationLockPreference = await preferenceFacts(page);
    assert(
      organizationLockPreference.kit === 'ui5-horizon' && organizationLockPreference.source === 'organization-lock',
      `organization lock must override user preference: ${JSON.stringify(organizationLockPreference)}`,
    );
    await page.evaluate(() => window.localStorage.removeItem('sc.scene.ui.driver'));
    await page.goto(`${baseUrl}?scene=list&systemKit=tdesign-modern`, { waitUntil: 'networkidle' });
    const systemPreference = await preferenceFacts(page);
    assert(
      systemPreference.kit === 'tdesign-modern' && systemPreference.source === 'system-default',
      `system default preference mismatch: ${JSON.stringify(systemPreference)}`,
    );

    await page.evaluate(() => window.localStorage.setItem('sc.scene.ui.driver', 'unsupported-driver'));
    await page.goto(`${baseUrl}?kit=unsupported-driver&organizationKit=unsupported-driver&systemKit=unsupported-driver`, { waitUntil: 'networkidle' });
    await page.locator('[data-scene-ui-kit="sc-native"] [data-scene-object-page]').waitFor({ state: 'visible' });
    const invalidPreferenceFallback = await page.locator('[data-scene-ui-kit]').getAttribute('data-scene-ui-kit');
    assert(invalidPreferenceFallback === 'sc-native', 'unknown preview/user drivers must fail closed to the safe default');

    await page.goto(`${baseUrl}?kit=ui5-horizon&failDriver=ui5-horizon`, { waitUntil: 'networkidle' });
    const fallbackProvider = page.locator('[data-scene-driver-fallback="true"]');
    await fallbackProvider.locator('[data-scene-object-page]').waitFor({ state: 'visible' });
    const driverFallback = {
      requested: await fallbackProvider.getAttribute('data-scene-ui-requested-kit'),
      resolved: await fallbackProvider.getAttribute('data-scene-ui-kit'),
      notice: await fallbackProvider.locator('[data-driver-fallback-notice]').innerText(),
    };
    assert(driverFallback.requested === 'ui5-horizon', `fallback requested driver mismatch: ${JSON.stringify(driverFallback)}`);
    assert(driverFallback.resolved === 'sc-native', `fallback must resolve to native: ${JSON.stringify(driverFallback)}`);
    assert(driverFallback.notice.includes('已切换到安全组件'), 'fallback must be visible and actionable to the user');

    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
    assert(failedResponses.length === 0, `failed responses: ${JSON.stringify(failedResponses)}`);
    assert(failedRequests.length === 0, `failed requests: ${JSON.stringify(failedRequests)}`);
    assert(externalRequests.length === 0, `external runtime assets: ${JSON.stringify(externalRequests)}`);
    assert(mutatingRequests.length === 0, `mutating requests: ${JSON.stringify(mutatingRequests)}`);

    const report = {
      status: 'PASS',
      baseUrl,
      views,
      consoleErrors,
      failedResponses,
      failedRequests,
      mutatingRequests,
      requestedAssetCount: requestedAssets.length,
      externalRequests,
      contractParity,
      collectionViews,
      normalizedPilotViews,
      hierarchyViews,
      accessibility: { objectAccessibility, collectionAccessibility, hierarchyAccessibility, focusFacts },
      tokenFacts,
      persistedTokenProfile,
      highContrastScreenshot,
      preferences: { organizationPreference, userPreference, organizationLockPreference, systemPreference },
      invalidPreferenceFallback,
      driverFallback,
      assertions: {
        rendererNeutralSceneContract: true,
        nativeTdesignUi5RuntimeSwitch: true,
        tdesignLazyRegistration: true,
        nativeToUi5RuntimeSwitch: true,
        ui5LazyRegistration: true,
        draftStateSurvivesDriverSwitch: true,
        userPreferenceSurvivesReload: true,
        vendorAssetsSelfHosted: true,
        switchBackParity: true,
        topWorkTabsRetained: true,
        chapterNavigationHidden: true,
        taskAndContextSeparated: true,
        highInformationDensity: true,
        contractDrivenNotice: true,
        relationTableParity: true,
        driverNativeReviewPanel: true,
        reviewPanelStateSurvivesDriverSwitch: true,
        invalidPreferenceFailsClosed: true,
        driverLoadFailureFallsBackSafely: true,
        collectionSurfaceAcrossThreeDrivers: true,
        normalizedReadonlyCollectionFeatureFlag: true,
        normalizedReadonlyCollectionReadOnlyAuthority: true,
        normalizedReadonlyCollectionNoSemanticInference: true,
        normalizedReadonlyCollectionAcrossThreeDrivers: true,
        hierarchySurfaceAcrossThreeDrivers: true,
        collectionSelectionSurvivesDriverSwitch: true,
        hierarchyExpansionSurvivesDriverSwitch: true,
        preferenceAuthorityUserOrganizationSystem: true,
        semanticDesignTokenProfiles: true,
        designTokenPreferenceSurvivesReload: true,
        highContrastRatioAtLeastSeven: true,
        tokenSwitchPreservesBusinessState: true,
        keyboardFocusVisible: true,
        keyboardCollectionSelection: true,
        keyboardHierarchyToggle: true,
        accessibleNamesAndUniqueIds: true,
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
