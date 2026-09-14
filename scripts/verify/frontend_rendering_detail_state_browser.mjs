import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0rendering-detail-state-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'rendering-detail-state-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__rendering_detail_state.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><head><meta name="viewport" content="width=device-width"><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__rendering_detail_state.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__rendering_detail_state.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, ref } from 'vue';
        import ScButton from '/src/components/design-system/ScButton.vue';
        import ScCheckbox from '/src/components/design-system/ScCheckbox.vue';
        import ScDateField from '/src/components/design-system/ScDateField.vue';
        import ScEmptyState from '/src/components/design-system/ScEmptyState.vue';
        import ScErrorState from '/src/components/design-system/ScErrorState.vue';
        import ScFormField from '/src/components/design-system/ScFormField.vue';
        import ScInlineState from '/src/components/design-system/ScInlineState.vue';
        import ScInput from '/src/components/design-system/ScInput.vue';
        import ScSelect from '/src/components/design-system/ScSelect.vue';
        import ScTextarea from '/src/components/design-system/ScTextarea.vue';
        import One2ManyCellEditor from '/src/components/template/One2ManyCellEditor.vue';
        import UnsupportedActionSurface from '/src/components/action/UnsupportedActionSurface.vue';
        import BlockRenderer from '/src/components/page/BlockRenderer.vue';
        import ProductListHeader from '/src/components/product-list/ProductListHeader.vue';
        import CollectionBatchActionBar from '/src/components/product-list/CollectionBatchActionBar.vue';
        import CollectionPaginationFooter from '/src/components/product-list/CollectionPaginationFooter.vue';
        import CollectionKanbanRecordCard from '/src/components/product-list/CollectionKanbanRecordCard.vue';
        import CollectionMobileRecordRow from '/src/components/product-list/CollectionMobileRecordRow.vue';
        import ProductFormLoadingSkeleton from '/src/components/product-record/ProductFormLoadingSkeleton.vue';
        import ProductFormErrorSummary from '/src/components/product-record/ProductFormErrorSummary.vue';
        import '/src/styles/design-system.css';
        import '/src/styles/product-patterns.css';
        const FormFeedbackHarness = {
          setup() {
            const fieldError = ref('请输入有效内容');
            const detailError = ref('请填写明细名称');
            const detailAdapter = {
              busy: false,
              one2manyCanInlineEdit: () => true,
              one2manyColumnInputType: () => 'text',
              one2manyColumnDisplayValue: (_column, value) => String(value ?? ''),
              selectPlaceholder: (label) => '请选择' + label,
            };
            const field = (component, key, label, help) => h(ScFormField, {
              label,
              fieldKey: key,
              help,
              error: fieldError.value,
              invalid: Boolean(fieldError.value),
            }, {
              default: ({ controlId, describedBy }) => h(component, {
                id: controlId,
                ariaLabel: label,
                describedBy,
                invalid: Boolean(fieldError.value),
                status: fieldError.value ? 'error' : 'default',
                modelValue: '',
                options: component === ScSelect ? [{ value: '1', label: '示例关系' }] : undefined,
                'onUpdate:modelValue': () => undefined,
              }),
            });
            const detail = (suffix) => h(One2ManyCellEditor, {
              adapter: detailAdapter,
              fieldName: 'line_ids',
              rowKey: 'row-1',
              column: { name: 'name', label: '明细名称', ttype: 'char', required: true, readonly: false },
              value: '',
              error: detailError.value,
              controlId: 'o2m-control-line_ids-row-1-name-' + suffix,
              errorId: 'o2m-error-line_ids-row-1-name-' + suffix,
              validationTarget: 'line_ids:row-1:name',
            });
            return () => h('section', { id: 'form-feedback-harness' }, [
              field(ScInput, 'input', '普通输入', '填写合同约定名称'),
              field(ScTextarea, 'textarea', '说明文本', undefined),
              field(ScDateField, 'date', '业务日期', undefined),
              field(ScSelect, 'relation', '关系选择', undefined),
              h('div', { id: 'detail-feedback-harness' }, [detail('desktop'), detail('mobile')]),
              h('button', {
                id: 'clear-form-feedback',
                type: 'button',
                onClick: () => { fieldError.value = ''; detailError.value = ''; },
              }, '清除错误'),
            ]);
          },
        };
        createApp({ render() { return h('main', { style: 'display:grid;gap:12px;max-width:720px;padding:16px' }, [
          h(FormFeedbackHarness),
          h(ScInlineState, { state: 'loading', label: '正在加载', id: 'loading-state' }),
          h(ScInlineState, { state: 'empty', label: '暂无记录' }),
          h(ScInlineState, { state: 'error', label: '读取失败' }),
          h(ScCheckbox, { indeterminate: true, label: '部分选择' }),
          h(ScEmptyState, { density: 'compact', headingLevel: 5, title: '暂无内容' }),
          h(ScErrorState, { density: 'compact', headingLevel: 5, title: '区块失败', description: '请稍后重试' }, {
            actions: () => h(ScButton, { id: 'retry-action', variant: 'primary' }, () => '重试'),
          }),
          h('section', { id: 'unsupported-consumer' }, [h(UnsupportedActionSurface)]),
          h('section', { id: 'block-consumer' }, [h(BlockRenderer, {
            block: { key: 'unknown-test-block', block_type: 'not_registered', props: {} },
            zoneKey: 'test-zone',
            dataset: {},
          })]),
          h(ProductListHeader, { loading: true, showSearch: true, searchValue: '', searchLabel: '搜索', searchPlaceholder: '输入关键字' }),
          h(CollectionBatchActionBar, { actions: [{ key: 'archive', label: '归档', enabled: true }], selectedCount: 1, selectedCountLabel: '已选 1 项', moreActionsLabel: '更多', clearLabel: '清除', loading: false }),
          h(CollectionPaginationFooter, { mode: 'paged', recordCountText: '共 2 项', loading: false, canPrevious: false, canNext: true, pageText: '1 / 2', pageJumpValue: '1', pageLimitValue: '20', listLimit: 20, totalPages: 2, pageLimitOptions: [20, 50], labels: { region: '分页', previous: '上一页', next: '下一页', groupPrevious: '上一组', groupNext: '下一组', pageInput: '页码', jump: '跳转', pageSize: '每页', pageSizeInput: '每页数量', pageSizeSelect: '选择每页数量' } }),
          h(CollectionKanbanRecordCard, { recordKey: 'project-2', title: '示例项目', disabled: true, disabledReason: '记录不可打开' }),
          h(CollectionMobileRecordRow, { recordKey: 'project-2', identity: '示例项目', openLabel: '打开', selectionEnabled: true, selectionDisabled: true, selectionDisabledReason: '无选择权限' }),
          h(ProductFormLoadingSkeleton, { loadingLabel: '正在载入表单' }),
          h(ProductFormErrorSummary, { errors: ['必填字段缺失'] }),
        ]); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('rendering detail state harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`http://127.0.0.1:${address.port}/__rendering_detail_state.html`);
  try {
    await page.locator('[data-semantic-component="ScInlineState"]').first().waitFor({ timeout: 15000 });
  } catch (error) {
    throw new Error(`rendering detail harness did not mount: ${JSON.stringify({ errors, body: (await page.locator('body').innerText()).slice(0, 500) })}`, { cause: error });
  }
  const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  const inlineStates = await page.locator('[data-semantic-component="ScInlineState"]').evaluateAll((nodes) => nodes.map((node) => ({
    state: node.getAttribute('data-state'),
    role: node.getAttribute('role'),
    busy: node.getAttribute('aria-busy'),
  })));
  const compactHeadings = await page.locator('[data-density="compact"] h5').count();
  const unexpectedHeadings = await page.locator('[data-density="compact"] h2').count();
  const unsupportedConsumerErrors = await page.locator('#unsupported-consumer [data-semantic-component="ScErrorState"]').count();
  const blockConsumerErrors = await page.locator('#block-consumer [data-semantic-component="ScErrorState"][data-density="compact"] h5').count();
  const loadingMotion = await page.locator('#loading-state').evaluate((root) => {
    const durationMs = (value) => value.split(',').map((part) => {
      const item = part.trim();
      return item.endsWith('ms') ? Number.parseFloat(item) : Number.parseFloat(item) * 1000;
    }).filter(Number.isFinite);
    const nodes = [root, ...root.querySelectorAll('*')];
    const styles = nodes.map((node) => getComputedStyle(node));
    return {
      maxAnimationDurationMs: Math.max(0, ...styles.flatMap((style) => durationMs(style.animationDuration))),
      maxTransitionDurationMs: Math.max(0, ...styles.flatMap((style) => durationMs(style.transitionDuration))),
    };
  });
  const collectionStates = await page.locator('[data-semantic-component^="Collection"], [data-semantic-component="ProductListHeader"], [data-appearance="kanban-record"]').evaluateAll((nodes) => nodes.map((node) => ({
    component: node.getAttribute('data-appearance') === 'kanban-record' ? 'CollectionKanbanRecordCard' : node.getAttribute('data-semantic-component'),
    state: node.getAttribute('data-state'),
    disabled: node.getAttribute('aria-disabled'),
    busy: node.getAttribute('aria-busy'),
  })));
  const collectionDisabledReasons = await page.locator('[data-appearance="kanban-record"], [data-semantic-component="CollectionSelectionControl"]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('title')).filter(Boolean));
  const formStates = await page.locator('[data-semantic-component="ProductFormLoadingSkeleton"], [data-semantic-component="ProductFormErrorSummary"]').evaluateAll((nodes) => nodes.map((node) => ({
    component: node.getAttribute('data-semantic-component'),
    state: node.getAttribute('data-state'),
    busy: node.getAttribute('aria-busy'),
  })));
  const mixedCheckbox = await page.locator('[data-semantic-component="ScCheckbox"][data-indeterminate="true"]').evaluate((node) => {
    const input = node.querySelector('input[type="checkbox"]');
    return {
      ariaChecked: input?.getAttribute('aria-checked'),
      nativeIndeterminate: input instanceof HTMLInputElement && input.indeterminate,
      driver: node.getAttribute('data-primitive-driver'),
    };
  });
  const fieldFeedbackBefore = await page.locator('#form-feedback-harness [data-semantic-component="ScFormField"]').evaluateAll((nodes) => nodes.map((node) => {
    const control = node.querySelector('input, textarea');
    const label = node.querySelector('label');
    const describedIds = (control?.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    return {
      id: control?.id || '',
      invalid: control?.getAttribute('aria-invalid'),
      labelFor: label?.getAttribute('for') || '',
      describedIds,
      descriptionsExist: describedIds.every((id) => Boolean(document.getElementById(id))),
    };
  }));
  const detailFeedbackBefore = await page.locator('#detail-feedback-harness [data-semantic-component="One2ManyCellEditor"]').evaluateAll((nodes) => nodes.map((node) => {
    const control = node.querySelector('input');
    const describedIds = (control?.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    return {
      id: control?.id || '',
      label: control?.getAttribute('aria-label'),
      invalid: control?.getAttribute('aria-invalid'),
      describedIds,
      descriptionsExist: describedIds.every((id) => Boolean(document.getElementById(id))),
    };
  }));
  const duplicateIdsBefore = await page.locator('[id]').evaluateAll((nodes) => {
    const ids = nodes.map((node) => node.id).filter((id) => id.startsWith('sc-field-') || id.startsWith('o2m-'));
    return ids.filter((id, index) => ids.indexOf(id) !== index);
  });
  await page.locator('#clear-form-feedback').click();
  await page.locator('#form-feedback-harness [aria-invalid="true"]').first().waitFor({ state: 'detached' });
  const feedbackAfter = await page.locator('#form-feedback-harness input, #form-feedback-harness textarea').evaluateAll((nodes) => nodes.map((node) => ({
    id: node.id,
    invalid: node.getAttribute('aria-invalid'),
    describedIds: (node.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean),
  })));
  await page.locator('[data-semantic-component="ScCheckbox"] input').focus();
  for (let index = 0; index < 20; index += 1) {
    if (await page.evaluate(() => document.activeElement?.id === 'retry-action')) break;
    await page.keyboard.press('Tab');
  }
  const focusVisible = await page.locator('#retry-action').evaluate((node) => {
    const style = getComputedStyle(node);
    return document.activeElement === node && (style.outlineStyle !== 'none' || style.boxShadow !== 'none');
  });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  const pass = inlineStates.length === 3
    && inlineStates.some((state) => state.state === 'loading' && state.role === 'status' && state.busy === 'true')
    && inlineStates.some((state) => state.state === 'empty' && state.role === 'status')
    && inlineStates.some((state) => state.state === 'error' && state.role === 'alert')
    && compactHeadings === 3 && unexpectedHeadings === 0
    && unsupportedConsumerErrors === 1 && blockConsumerErrors === 1
    && collectionStates.some((state) => state.component === 'ProductListHeader' && state.state === 'loading' && state.busy === 'true')
    && collectionStates.some((state) => state.component === 'CollectionBatchActionBar' && state.state === 'ready')
    && collectionStates.some((state) => state.component === 'CollectionPaginationFooter' && state.state === 'ready')
    && collectionStates.some((state) => state.component === 'CollectionKanbanRecordCard' && state.state === 'disabled' && state.disabled === 'true')
    && collectionStates.some((state) => state.component === 'CollectionMobileRecordRow' && state.state === 'selection-disabled')
    && collectionDisabledReasons.includes('记录不可打开') && collectionDisabledReasons.includes('无选择权限')
    && formStates.some((state) => state.component === 'ProductFormLoadingSkeleton' && state.state === 'loading' && state.busy === 'true')
    && formStates.some((state) => state.component === 'ProductFormErrorSummary' && state.state === 'error')
    && mixedCheckbox.ariaChecked === 'mixed' && mixedCheckbox.nativeIndeterminate
    && mixedCheckbox.driver === 'tdesign'
    && fieldFeedbackBefore.length === 4
    && fieldFeedbackBefore.every((field) => field.id && field.invalid === 'true' && field.labelFor === field.id && field.describedIds.length >= 1 && field.descriptionsExist)
    && fieldFeedbackBefore[0].describedIds.length === 2
    && detailFeedbackBefore.length === 2
    && detailFeedbackBefore.every((field) => field.id && field.label === '明细名称' && field.invalid === 'true' && field.describedIds.length === 1 && field.descriptionsExist)
    && detailFeedbackBefore[0].id !== detailFeedbackBefore[1].id
    && duplicateIdsBefore.length === 0
    && feedbackAfter.every((field) => field.invalid === null && (field.id.includes('input') ? field.describedIds.length === 1 : field.describedIds.length === 0))
    && loadingMotion.maxAnimationDurationMs <= 0.01
    && loadingMotion.maxTransitionDurationMs <= 0.01
    && focusVisible
    && !desktopOverflow && !mobileOverflow && errors.length === 0;
  console.log(JSON.stringify({ pass, fieldFeedbackBefore, detailFeedbackBefore, duplicateIdsBefore, feedbackAfter, inlineStates, collectionStates, collectionDisabledReasons, formStates, mixedCheckbox, compactHeadings, unexpectedHeadings, unsupportedConsumerErrors, blockConsumerErrors, loadingMotion, focusVisible, desktopOverflow, mobileOverflow, errors, mutation: 0 }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}
