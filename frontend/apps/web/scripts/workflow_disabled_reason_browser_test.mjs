import assert from 'node:assert/strict';
import { createServer } from '../node_modules/vite/dist/node/index.js';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const entryId = '\0workflow-disabled-reason-browser-entry';
const reason = '先完成审批前置条件';
const overflowReason = '当前记录不允许归档';
const providerUrl = `/@fs${new URL('../../../packages/ui/src/components/SceneUiProvider.vue', import.meta.url).pathname}`;
const server = await createServer({
  root: new URL('..', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'workflow-disabled-reason-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__workflow_disabled_reason.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body style="min-height:1800px"><div id="app"></div><script type="module" src="/__workflow_disabled_reason.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__workflow_disabled_reason.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h } from 'vue';
        import SceneUiProvider from ${JSON.stringify(providerUrl)};
        import CanonicalActionBar from '/src/pages/contractForm/CanonicalActionBar.vue';
        import '/src/styles/design-system.css';

        const actionRef = (key, enabled) => ({
          actionId: key + '-action',
          actionKey: key,
          backendIdentity: 'fixture:' + key,
          triggerType: 'button',
          sourceWidgetId: 'fixture',
          targetIds: [],
          dispatchMode: 'client',
          targetScope: 'record',
          refreshMode: 'none',
          allowed: enabled,
          enabled,
          button: { name: 'action_' + key },
        });
        const action = (key, label, enabled, reasonMessage = '') => ({
          key,
          label,
          icon: '',
          tier: key === 'save' ? 'primary' : 'secondary',
          visible: true,
          enabled,
          reasonCode: enabled ? '' : 'FIXTURE_BLOCKED',
          reasonMessage,
          visibleProfiles: ['create', 'edit', 'readonly'],
          safety: {},
          actionRef: actionRef(key, enabled),
        });
        window.workflowReasonEvidence = { events: [] };
        createApp({
          render: () => h(SceneUiProvider, { kit: 'sc-native' }, {
            default: () => h('main', { style: 'width:min(100%,960px);padding:24px;box-sizing:border-box' }, [
              h(CanonicalActionBar, {
                directActions: [
                  action('save', '保存', true),
                  action('approve', '审批', false, ${JSON.stringify(reason)}),
                ],
                overflowActions: [
                  action('archive', '归档', false, ${JSON.stringify(overflowReason)}),
                  action('publish', '发布', true),
                ],
                effectivePrimaryKey: 'save',
                onActionRef: value => window.workflowReasonEvidence.events.push(value.actionKey),
              }),
            ]),
          }),
        }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('Vite browser harness did not expose a TCP port');

const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage({ hasTouch: true });
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  const results = [];

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`http://127.0.0.1:${address.port}/__workflow_disabled_reason.html`);
    const bar = page.locator('[data-canonical-action-bar]');
    await bar.waitFor({ state: 'visible' });
    const denied = bar.locator('[data-action-key="approve"]');
    const trigger = bar.locator('[data-workflow-reason-trigger="approve"]');
    await trigger.waitFor({ state: 'visible' });
    assert.equal(await denied.isDisabled(), true);
    assert.equal(await trigger.getAttribute('tabindex'), '0');
    assert.equal(await trigger.getAttribute('role'), 'button');
    assert.equal(await trigger.getAttribute('aria-label'), reason);

    const scrollBeforeSpace = await page.evaluate(() => scrollY);
    await trigger.focus();
    await trigger.press('Enter');
    await page.getByText(reason, { exact: true }).waitFor({ state: 'visible' });
    const enterVisible = await page.getByText(reason, { exact: true }).isVisible();
    const keyboardFocusOutline = await trigger.evaluate((element) => {
      const style = getComputedStyle(element);
      return { style: style.outlineStyle, width: style.outlineWidth };
    });
    await trigger.click();
    await page.getByText(reason, { exact: true }).waitFor({ state: 'hidden' });

    await trigger.focus();
    await trigger.press(' ');
    await page.getByText(reason, { exact: true }).waitFor({ state: 'visible' });
    const spaceVisible = await page.getByText(reason, { exact: true }).isVisible();
    const scrollAfterSpace = await page.evaluate(() => scrollY);
    await trigger.click();
    await page.getByText(reason, { exact: true }).waitFor({ state: 'hidden' });

    if (width === 390) await trigger.tap();
    else await trigger.click();
    await page.getByText(reason, { exact: true }).waitFor({ state: 'visible' });
    const pointerVisible = await page.getByText(reason, { exact: true }).isVisible();
    await trigger.click();
    await page.getByText(reason, { exact: true }).waitFor({ state: 'hidden' });

    const enabled = bar.locator('[data-action-key="save"]');
    if (width === 390) await enabled.tap();
    else await enabled.click();

    const more = page.getByRole('button', { name: '展开更多表单操作', exact: true });
    if (width === 390) await more.tap();
    else await more.click();
    const overflowExplanation = page.getByRole('button', {
      name: `归档: ${overflowReason}`,
      exact: true,
    });
    await overflowExplanation.waitFor({ state: 'visible' });
    const overflowTabIndex = await overflowExplanation.getAttribute('tabindex');
    const overflowRole = await overflowExplanation.getAttribute('role');
    let overflowTabFocused = false;
    for (let index = 0; index < 12 && !overflowTabFocused; index += 1) {
      await page.keyboard.press('Tab');
      overflowTabFocused = await overflowExplanation.evaluate((element) => element === document.activeElement);
    }

    const overflowScrollBeforeSpace = await page.evaluate(() => scrollY);
    await overflowExplanation.press('Enter');
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'visible' });
    const overflowEnterVisible = await page.getByText(overflowReason, { exact: true }).isVisible();
    await overflowExplanation.click();
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'hidden' });

    await overflowExplanation.focus();
    await overflowExplanation.press(' ');
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'visible' });
    const overflowSpaceVisible = await page.getByText(overflowReason, { exact: true }).isVisible();
    const overflowScrollAfterSpace = await page.evaluate(() => scrollY);
    await overflowExplanation.click();
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'hidden' });

    if (width === 390) await overflowExplanation.tap();
    else await overflowExplanation.click();
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'visible' });
    const overflowPointerVisible = await page.getByText(overflowReason, { exact: true }).isVisible();
    await overflowExplanation.click();
    await page.getByText(overflowReason, { exact: true }).waitFor({ state: 'hidden' });

    const enabledOverflow = page.getByText('发布', { exact: true }).last();
    if (width === 390) await enabledOverflow.tap();
    else await enabledOverflow.click();

    const evidence = await page.evaluate(() => window.workflowReasonEvidence);
    const layout = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: innerWidth,
    }));
    results.push({
      width,
      pointer: width === 390 ? 'touch' : 'mouse',
      enterVisible,
      spaceVisible,
      pointerVisible,
      keyboardFocusOutline,
      spaceScrollDelta: scrollAfterSpace - scrollBeforeSpace,
      overflowTabIndex,
      overflowRole,
      overflowTabFocused,
      overflowEnterVisible,
      overflowSpaceVisible,
      overflowPointerVisible,
      overflowSpaceScrollDelta: overflowScrollAfterSpace - overflowScrollBeforeSpace,
      disabledActionEvents: evidence.events.filter((key) => key === 'approve').length,
      enabledActionEvents: evidence.events.filter((key) => key === 'save').length,
      disabledOverflowEvents: evidence.events.filter((key) => key === 'archive').length,
      enabledOverflowEvents: evidence.events.filter((key) => key === 'publish').length,
      layout,
      pass: enterVisible && spaceVisible && pointerVisible
        && keyboardFocusOutline.style !== 'none'
        && Number.parseFloat(keyboardFocusOutline.width) > 0
        && scrollAfterSpace === scrollBeforeSpace
        && overflowTabIndex === '0'
        && overflowRole === 'button'
        && overflowTabFocused
        && overflowEnterVisible
        && overflowSpaceVisible
        && overflowPointerVisible
        && overflowScrollAfterSpace === overflowScrollBeforeSpace
        && evidence.events.filter((key) => key === 'approve').length === 0
        && evidence.events.filter((key) => key === 'save').length === 1
        && evidence.events.filter((key) => key === 'archive').length === 0
        && evidence.events.filter((key) => key === 'publish').length === 1
        && layout.documentWidth <= layout.viewportWidth + 1,
    });
  }

  const pass = results.every((result) => result.pass) && errors.length === 0;
  console.log(JSON.stringify({ pass, gatedAssertions: results.length * 22 + 1, viewportCount: results.length, browserErrorCount: errors.length, driver: 'real CanonicalActionBar + ScPopover + ScDropdown + SceneButton', reason, overflowReason, results, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}
