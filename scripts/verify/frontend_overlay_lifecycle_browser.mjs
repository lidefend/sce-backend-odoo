import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const scope = process.env.OVERLAY_LIFECYCLE_SCOPE || 'overlay';
if (!['overlay', 'page-renderer'].includes(scope)) throw new Error('unsupported overlay lifecycle scope');
if (scope === 'page-renderer') await runPageRendererScope();
else {
const entryId = '\0overlay-lifecycle-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'overlay-lifecycle-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__overlay_lifecycle.html', (_request, response) => {
        response.setHeader('content-type', 'text/html; charset=utf-8');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><button id="opener">打开</button><div id="app"></div><script type="module" src="/__overlay_lifecycle.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__overlay_lifecycle.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive } from 'vue';
        import ScButton from '/src/components/design-system/ScButton.vue';
        import Dialog from '/src/components/design-system/ScDialog.vue';
        import Drawer from '/src/components/design-system/ScDrawer.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ dialog: false, drawer: false, locked: false, empty: false, closes: 0, structuredDisabled: false, structuredLoading: false, structuredActivations: 0 });
        window.overlayState = state;
        document.querySelector('#opener').addEventListener('click', () => { state.dialog = true; });
        createApp({ render() { return h('div', [
          h(ScButton, {
            id: 'structured-prop-button', appearance: 'metric',
            disabled: state.structuredDisabled, loading: state.structuredLoading, loadingLabel: '组件处理中',
            onClick: () => { state.structuredActivations += 1; },
          }, () => '组件参数按钮'),
          h(Dialog, { open: state.dialog, title: '详情', description: '对话说明', size: 'wide', onClose: () => { state.dialog = false; state.closes += 1; } }, {
            default: () => [h('button', { id: 'dialog-first', 'data-dialog-primary': '' }, '第一项'), h('button', { id: 'open-drawer', onClick: () => { state.drawer = true; } }, '打开抽屉')],
          }),
          h(Drawer, { open: state.drawer, title: '抽屉', description: '抽屉说明', onClose: () => { state.drawer = false; state.closes += 1; } }, {
            default: () => h('button', { id: 'drawer-action', 'data-dialog-primary': '' }, '抽屉动作'),
          }),
          h(Dialog, { open: state.locked, title: '不可关闭', dismissible: false, onClose: () => { state.locked = false; state.closes += 1; } }, { default: () => h('p', '处理中') }),
          h(Dialog, { open: state.empty, title: '无控件', dismissible: false, onClose: () => { state.empty = false; } }, { default: () => h('p', '只读内容') }),
        ]); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('overlay harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.goto(`http://127.0.0.1:${address.port}/__overlay_lifecycle.html`);
  const structuredButton = page.locator('#structured-prop-button');
  await structuredButton.click();
  const initialStructuredActivations = await page.evaluate(() => window.overlayState.structuredActivations);
  await page.evaluate(() => { window.overlayState.structuredDisabled = true; });
  await page.waitForFunction(() => document.querySelector('#structured-prop-button')?.hasAttribute('disabled'));
  await structuredButton.evaluate((node) => node.click());
  const disabledPropEvidence = await structuredButton.evaluate((node) => ({
    disabled: node.hasAttribute('disabled'), ariaDisabled: node.getAttribute('aria-disabled'),
    ariaBusy: node.getAttribute('aria-busy'), dataLoading: node.getAttribute('data-loading'),
  }));
  disabledPropEvidence.activationCount = await page.evaluate(() => window.overlayState.structuredActivations);
  await page.evaluate(() => {
    window.overlayState.structuredDisabled = false;
    window.overlayState.structuredLoading = true;
  });
  await page.waitForFunction(() => document.querySelector('#structured-prop-button')?.getAttribute('data-loading') === 'true');
  await structuredButton.evaluate((node) => node.click());
  const loadingPropEvidence = await structuredButton.evaluate((node) => ({
    disabled: node.hasAttribute('disabled'), ariaDisabled: node.getAttribute('aria-disabled'),
    ariaBusy: node.getAttribute('aria-busy'), dataLoading: node.getAttribute('data-loading'),
    loadingLabel: node.querySelector('.sc-visually-hidden')?.textContent?.trim() || '',
  }));
  loadingPropEvidence.activationCount = await page.evaluate(() => window.overlayState.structuredActivations);
  await page.evaluate(() => { window.overlayState.structuredLoading = false; });
  await page.waitForFunction(() => !document.querySelector('#structured-prop-button')?.hasAttribute('disabled'));
  await structuredButton.click();
  const restoredStructuredActivations = await page.evaluate(() => window.overlayState.structuredActivations);
  const visibleOverlayResidueCount = async () => page.locator('.t-drawer:visible, .t-drawer__mask:visible, .t-dialog:visible, .t-dialog__mask:visible, [data-overlay-kind]:visible').count();
  const initialOverlayResidueCount = await visibleOverlayResidueCount();
  const waitForActiveWithin = async (selector) => {
    await page.waitForFunction((target) => {
      const node = document.querySelector(target);
      return Boolean(node && document.activeElement && node.contains(document.activeElement));
    }, selector);
  };
  await page.locator('#opener').click();
  const dialog = page.locator('[data-overlay-kind="dialog"][data-state="open"]');
  try {
    await dialog.waitFor();
  } catch (error) {
    throw new Error(`overlay dialog did not open: ${JSON.stringify({ errors, body: (await page.locator('body').innerText()).slice(0, 500) })}`, { cause: error });
  }
  await waitForActiveWithin('[data-overlay-kind="dialog"][data-state="open"]');
  const initialFocus = await dialog.evaluate((node) => node.contains(document.activeElement));
  const bodyLocked = await page.evaluate(() => getComputedStyle(document.body).overflow === 'hidden');
  const labelled = await dialog.evaluate((node) => ({ labelledby: node.getAttribute('aria-labelledby'), describedby: node.getAttribute('aria-describedby') }));
  await page.locator('#open-drawer').click();
  const drawer = page.locator('[data-overlay-kind="drawer"][data-state="open"]');
  await drawer.waitFor();
  await waitForActiveWithin('[data-overlay-kind="drawer"][data-state="open"]');
  const nestedFocus = await drawer.evaluate((node) => node.contains(document.activeElement));
  await page.keyboard.press('Escape');
  await drawer.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => !document.querySelector('.t-drawer, .t-drawer__mask, [data-overlay-kind="drawer"]'));
  const closedDrawerResidueCount = await page.locator('.t-drawer, .t-drawer__mask, [data-overlay-kind="drawer"]').count();
  await page.waitForFunction(() => document.activeElement?.id === 'open-drawer');
  const nestedRestore = await page.evaluate(() => document.activeElement?.id === 'open-drawer');
  const nestedBodyLocked = await page.evaluate(() => getComputedStyle(document.body).overflow === 'hidden');
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => document.activeElement?.id === 'opener');
  const openerRestored = await page.evaluate(() => document.activeElement?.id === 'opener');
  const bodyReleased = await page.evaluate(() => getComputedStyle(document.body).overflow !== 'hidden');

  await page.evaluate(() => { window.overlayState.locked = true; });
  const locked = page.locator('[data-overlay-kind="dialog"][data-state="open"][data-dismissible="false"]');
  await locked.waitFor();
  await page.keyboard.press('Escape');
  await locked.dispatchEvent('mousedown', { bubbles: true });
  const lockedRemains = await locked.count() === 1;
  await page.evaluate(() => { window.overlayState.locked = false; });
  await locked.waitFor({ state: 'hidden' });
  await page.evaluate(() => { window.overlayState.empty = true; });
  const emptySurface = page.locator('[data-overlay-kind="dialog"][data-state="open"]');
  await emptySurface.waitFor();
  await waitForActiveWithin('[data-overlay-kind="dialog"][data-state="open"]');
  const emptyInitialFocus = await emptySurface.evaluate((node) => node.contains(document.activeElement));
  await page.keyboard.press('Tab');
  const emptyTabContained = await emptySurface.evaluate((node) => node.contains(document.activeElement));
  await page.evaluate(() => { window.overlayState.empty = false; });

  const pass = initialOverlayResidueCount === 0 && closedDrawerResidueCount === 0
    && initialStructuredActivations === 1
    && disabledPropEvidence.disabled && disabledPropEvidence.ariaDisabled === 'true'
    && disabledPropEvidence.ariaBusy === null && disabledPropEvidence.dataLoading === null
    && disabledPropEvidence.activationCount === 1
    && loadingPropEvidence.disabled && loadingPropEvidence.ariaDisabled === 'true'
    && loadingPropEvidence.ariaBusy === 'true' && loadingPropEvidence.dataLoading === 'true'
    && loadingPropEvidence.loadingLabel === '组件处理中'
    && loadingPropEvidence.activationCount === 1
    && restoredStructuredActivations === 2
    && initialFocus && nestedFocus
    && nestedRestore && openerRestored
    && bodyLocked && nestedBodyLocked && bodyReleased && lockedRemains
    && emptyInitialFocus && emptyTabContained
    && Boolean(labelled.labelledby) && Boolean(labelled.describedby)
    && errors.length === 0;
  console.log(JSON.stringify({ pass, structuredButtonProps: { initialStructuredActivations, disabledPropEvidence, loadingPropEvidence, restoredStructuredActivations }, initialOverlayResidueCount, closedDrawerResidueCount, initialFocus, nestedFocus, nestedRestore, openerRestored, bodyLocked, nestedBodyLocked, bodyReleased, lockedRemains, emptyInitialFocus, emptyTabContained, labelled, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

}

async function runPageRendererScope() {
  const entryId = '\0page-renderer-browser-entry';
  const server = await createServer({
    root: new URL('../../frontend/apps/web', import.meta.url).pathname,
    logLevel: 'error', server: { host: '127.0.0.1', port: 0, hmr: false },
    plugins: [{
      name: 'page-renderer-browser-harness',
      configureServer(vite) {
        vite.middlewares.use('/__page_renderer.html', (_request, response) => {
          response.setHeader('content-type', 'text/html; charset=utf-8');
          response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__page_renderer.js"></script></body></html>');
        });
      },
      resolveId(id) { return id === '/__page_renderer.js' ? entryId : undefined; },
      load(id) {
        if (id !== entryId) return undefined;
        return `
          import { createApp, h, reactive, nextTick } from 'vue';
          import PageRenderer from '/src/components/page/PageRenderer.vue';
          import '/src/styles/design-system.css';
          const types = ['metric_row','todo_list','alert_panel','entry_grid','record_summary','record_table','progress_summary','activity_feed','accordion_group','boq_import_preview','chart_dataset','rich_text_overview'];
          const blocks = types.map((type, index) => ({key:type, block_type:type, title:'Title '+type, data_source:type, priority:12-index,
            ...(type==='todo_list' ? {actions:[{key:'header_probe',label:'Header action'}]} : {})}));
          blocks.push({key:'unknown',block_type:'unregistered_fixture',title:'Unknown'});
          const probe = reactive({
            contract: {page:{title:'Renderer fixture',subtitle:'Declared subtitle',global_actions:[{key:'global_probe',label:'Global probe',intent:'declared.intent',target:{model:'x.fixture',id:7}}]},
              zones:[{key:'secondary',title:'Second zone',priority:0,display_mode:'grid',blocks:[]},
                {key:'today_focus',title:'Declared zone',priority:10,zone_type:'primary',display_mode:'stack',blocks}]},
            datasets: {
              metric_row:[{key:'metric',label:'Metric label',value:42,action_key:'metric_probe'}],
              todo_list:[{id:1,title:'Todo label',description:'Todo body',action_key:'todo_probe'}],
              alert_panel:[{id:2,title:'Alert label',description:'Alert body',action_key:'alert_probe'}],
              entry_grid:[{id:'entry',title:'Entry label',hint:'Entry hint',action_key:'entry_probe'},{id:'readonly',title:'Readonly entry',hint:'No action'}],
              record_summary:[{key:'summary',label:'Summary label',value:'Summary value'}],
              record_table:{columns:['name'],column_labels:{name:'Declared column'},rows:[{name:'First row'},{name:'Second row'}]},
              progress_summary:[{key:'rate',label:'Progress label',value:42,unit:'%'}],
              activity_feed:[{id:3,title:'Activity label',description:'Activity body',action_key:'activity_probe'}],
              accordion_group:[{id:4,title:'Disclosure row',description:'Disclosure body'}],
              boq_import_preview:{data:{empty_message_no_context:'BOQ no context'}},
              chart_dataset:{data:{empty_message_no_context:'Chart no context'}},
              rich_text_overview:{data:{project_id:7,content:'<p>Rich content</p>',overview_digest:'digest',can_edit:false}},
            }, events:[],
          });
          window.sceneProbe=probe;
          window.updateSceneProbe=async () => {probe.datasets.record_table={columns:['name'],column_labels:{name:'Updated column'},rows:[],empty_message:'Declared empty table'};probe.datasets.metric_row=[];probe.contract.page.title='Updated renderer';await nextTick();};
          createApp({render:()=>h(PageRenderer,{contract:probe.contract,datasets:probe.datasets,primaryHeading:true,onAction:event=>probe.events.push(event)})}).mount('#app');
        `;
      },
    }],
  });
  let browser;
  let checks = 0;
  const check = (condition, label) => { if (!condition) throw new Error(label); checks += 1; };
  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (!address || typeof address === 'string') throw new Error('page renderer host needs loopback TCP address');
    const origin = `http://127.0.0.1:${address.port}`;
    browser = await launchChromium({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [], forbiddenRequests = [];
    page.on('console', message => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
    page.on('pageerror', error => errors.push(`page:${error.message}`));
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== origin || request.method() !== 'GET' || url.pathname.startsWith('/api/')) {
        forbiddenRequests.push(`${request.method()} ${url.origin}${url.pathname}`); await route.abort();
      } else await route.continue();
    });
    await page.goto(`${origin}/__page_renderer.html`);
    await page.locator('.block-rich-text-overview').waitFor();
    check(await page.locator('.block-renderer').count() === 12, 'all twelve registered block families render');
    for (const type of ['metric_row','todo_list','alert_panel','entry_grid','record_summary','record_table','progress_summary','activity_feed','accordion_group','boq_import_preview','chart_dataset','rich_text_overview']) {
      const host = page.locator(`[data-block-type="${type}"]`);
      check(await host.locator('[data-semantic-component="ScCard"]').count() === 1, `${type}: one official Card owner`);
      check(await host.locator('.t-card').count() === 1, `${type}: real TDesign Card`);
      check(await host.locator('.t-card--bordered').count() === 0, `${type}: borderless Card`);
      check(await host.locator(':scope > article').evaluate(node => {
        const style = getComputedStyle(node); return style.borderTopWidth === '0px' && style.paddingTop === '0px' && style.boxShadow === 'none' && style.backgroundColor === 'rgba(0, 0, 0, 0)';
      }), `${type}: transparent semantic host`);
    }
    check(await page.locator('.block-fallback').count() === 1, 'unknown block fails soft beside known blocks');
    check(await page.locator('.zone-renderer').first().locator('h3').textContent() === 'Declared zone', 'zone priority retained');
    check(await page.locator('.block-renderer').first().getAttribute('data-block-type') === 'metric_row', 'block priority retained');
    for (const selector of ['.page-renderer-header','.zone-renderer']) check(await page.locator(selector).first().evaluate(node => {
      const style=getComputedStyle(node);return style.borderTopWidth==='0px' && style.boxShadow==='none' && style.backgroundColor==='rgba(0, 0, 0, 0)';
    }), `${selector}: no extra card shell`);
    check(await page.locator('.zone-renderer-body.display-stack').count() === 1 && await page.locator('.zone-renderer-body.display-grid').count() === 1, 'declared stack and grid retained');
    const table = page.locator('[data-block-type="record_table"]');
    check(await table.locator('.t-table tbody tr').count() === 2, 'actual table renders two rows');
    check((await table.innerText()).includes('Declared column') && (await table.innerText()).includes('First row') && (await table.innerText()).includes('Second row'), 'declared table label and values retained');
    await page.getByRole('button', { name: 'Global probe', exact: true }).click();
    check(await page.evaluate(() => JSON.stringify(window.sceneProbe.events[0]) === JSON.stringify({actionKey:'global_probe',blockKey:'',zoneKey:'',item:{},intent:'declared.intent',target:{model:'x.fixture',id:7}})), 'global intent/target event preserved');
    const headerAction = page.getByRole('button', {name:'Header action',exact:true});
    check(await headerAction.evaluate(node => node.classList.contains('t-button')), 'block header action uses actual official button');
    await headerAction.click();
    check(await page.evaluate(() => {const e=window.sceneProbe.events.at(-1);return e.actionKey==='header_probe'&&e.blockKey==='todo_list'&&e.zoneKey==='today_focus';}), 'card action reaches PageRenderer');
    const entry = page.locator('.entry-item').filter({hasText:'Entry label'});
    check(await entry.getAttribute('data-primitive-driver') === 'browser-structured', 'entry tile uses registered structured button extension');
    await entry.click();
    check(await page.evaluate(() => {const e=window.sceneProbe.events.at(-1);return e.actionKey==='entry_probe'&&e.blockKey==='entry_grid'&&e.item.id==='entry';}), 'entry structured action bubbles without payload loss');
    const readonly = page.locator('.entry-item--readonly');
    check(await readonly.evaluate(node=>node.tagName==='ARTICLE'&&!node.hasAttribute('data-primitive-driver')), 'readonly tile remains non-button');
    const eventsBefore = await page.evaluate(()=>window.sceneProbe.events.length); await readonly.click();
    check(await page.evaluate(()=>window.sceneProbe.events.length) === eventsBefore, 'readonly tile emits no action');
    const disclosure=page.locator('[data-block-type="accordion_group"]');
    check(await disclosure.locator('.t-card__title').count() === 0, 'disclosure has no duplicate card title');
    const trigger=disclosure.locator('[data-disclosure-trigger]');
    check(await trigger.getAttribute('aria-expanded')==='true', 'disclosure initially open');
    await trigger.click(); check(await trigger.getAttribute('aria-expanded')==='false','disclosure collapses');
    await trigger.click(); check(await trigger.getAttribute('aria-expanded')==='true','disclosure reopens');
    check((await page.locator('.block-rich-text-overview').innerText()).includes('Rich content') && await page.locator('[data-action="begin-edit"]').count()===0, 'readonly rich content retains permission gate');
    check((await page.locator('.block-chart-dataset').innerText()).includes('Chart no context') && (await page.locator('.block-boq-import-preview').innerText()).includes('BOQ no context'),'declared missing-context states retained');
    await page.evaluate(()=>window.updateSceneProbe());
    check(await page.locator('h1').textContent()==='Updated renderer','contract updates propagate through actual tree');
    check((await table.innerText()).includes('Declared empty table') && await table.locator('tbody tr').count()===0,'table update reaches empty state');
    check((await page.locator('[data-block-type="metric_row"]').innerText()).includes('暂无指标'),'metric update reaches empty state');
    check(await page.locator('[data-semantic-component="ScCard"]').count()===12,'updates retain exactly twelve Card owners');
    check(errors.length===0, `zero browser errors: ${JSON.stringify(errors)}`);
    check(forbiddenRequests.length===0, `no business or external requests: ${JSON.stringify(forbiddenRequests)}`);
    console.log(JSON.stringify({pass:true,scope:'page-renderer',checks,real_chain:'PageRenderer/ZoneRenderer/registry/Sc/TDesign',entry_driver:'browser-structured',transport:'not_exercised',backend_acceptance:false,errors,forbiddenRequests}));
  } finally { try { await browser?.close(); } finally { await server.close(); } }
}
