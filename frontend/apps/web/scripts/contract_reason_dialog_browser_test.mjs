import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const dialogFile = `${root}/frontend/apps/web/src/pages/contractForm/ContractReasonDialog.vue`;
const planFile = `${root}/frontend/apps/web/src/pages/contractForm/actionExecutionPlan.ts`;

const output = await build({
  stdin: {
    contents: `
import { createApp, h, ref } from 'vue';
import ContractReasonDialog from ${JSON.stringify(dialogFile)};
import { collectActionParams } from ${JSON.stringify(planFile)};
import ScFormField from ${JSON.stringify(`${root}/frontend/apps/web/src/components/design-system/ScFormField.vue`)};

const presentation = {
  title: '驳回付款申请',
  label: '拒绝原因',
  help: '请说明拒绝原因，提交后会正式审批记录。',
  submitLabel: '确认驳回',
  cancelLabel: '取消',
};
const action = {
  key: 'reject',
  requiresReason: true,
  requiredParams: ['reason'],
  reasonPresentation: presentation,
};

window.operationRequests = [];
window.failures = [];
const Host = {
  setup() {
    const dialogRef = ref(null);
    window.runReject = async () => {
      const params = await collectActionParams(
        action,
        failure => window.failures.push(failure),
        input => dialogRef.value.request(input),
      );
      if (params) window.operationRequests.push(params);
      return params;
    };
    const feedbackField = h(ScFormField, {
      label: '反馈字段',
      fieldKey: 'feedback',
      help: '字段帮助',
      error: '字段错误',
    }, {
      default: ({ controlId, describedBy }) => h('input', {
        id: controlId,
        'aria-describedby': describedBy,
      }),
    });
    return () => h('div', [feedbackField, h(ContractReasonDialog, { ref: dialogRef })]);
  },
};
createApp(Host).mount('#app');
`,
    resolveDir: `${root}/frontend/apps/web`,
    loader: 'js',
  },
  bundle: true,
  write: false,
  platform: 'browser',
  format: 'iife',
  define: {
    __VUE_OPTIONS_API__: 'true',
    __VUE_PROD_DEVTOOLS__: 'false',
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    'process.env.NODE_ENV': '"production"',
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  loader: { '.css': 'empty' },
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
    'tdesign-vue-next': `${root}/frontend/packages/ui/node_modules/tdesign-vue-next`,
  },
  plugins: [{
    name: 'actual-vue-sfc',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        return {
          contents: compileScript(descriptor, { id: args.path, inlineTemplate: true }).content,
          loader: 'ts',
          resolveDir: path.dirname(args.path),
        };
      });
    },
  }],
  logLevel: 'error',
});

const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
const browser = await launchChromium();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.setContent('<div id="app"></div>');
  await page.addScriptTag({ content: output.outputFiles[0].text });
  const feedback = page.locator('[data-semantic-component="ScFormField"]').first();
  assert.equal(await feedback.getByText('字段帮助', { exact: true }).count(), 1);
  assert.equal(await feedback.getByText('字段错误', { exact: true }).count(), 1);
  const feedbackInput = feedback.locator('input');
  const feedbackDescribedBy = await feedbackInput.getAttribute('aria-describedby');
  assert.ok(feedbackDescribedBy);
  assert.equal(await page.locator(`#${feedbackDescribedBy.split(' ')[0]}`).innerText(), '字段帮助');
  assert.equal(await page.locator(`#${feedbackDescribedBy.split(' ')[1]}`).innerText(), '字段错误');

  await page.evaluate(() => {
    window.pendingReject = window.runReject();
  });
  const dialog = page.locator('section[role="dialog"][data-state="open"]');
  await dialog.waitFor({ state: 'visible' });
  assert.equal(await dialog.locator('h2').innerText(), '驳回付款申请');
  const dialogText = String(await dialog.textContent() || '').replace(/\s+/g, ' ').trim();
  assert.ok(dialogText.includes('拒绝原因'), dialogText);
  assert.ok(dialogText.includes('请说明拒绝原因，提交后会正式审批记录。'), dialogText);
  const describedBy = await dialog.locator('textarea').getAttribute('aria-describedby');
  assert.ok(describedBy);
  assert.equal(
    await page.locator(`#${describedBy}`).innerText(),
    '请说明拒绝原因，提交后会正式审批记录。',
  );
  assert.equal(await dialog.getByRole('button', { name: '取消', exact: true }).count(), 1);
  assert.equal(await dialog.getByRole('button', { name: '确认驳回', exact: true }).isDisabled(), true);

  await dialog.getByRole('button', { name: '取消', exact: true }).click();
  const cancelled = await page.evaluate(() => window.pendingReject);
  assert.equal(cancelled, null);
  assert.deepEqual(await page.evaluate(() => window.operationRequests), []);
  assert.deepEqual(await page.evaluate(() => window.failures), []);
  await dialog.waitFor({ state: 'hidden' });

  await page.evaluate(() => {
    window.pendingReject = window.runReject();
  });
  await dialog.waitFor({ state: 'visible' });
  await dialog.locator('textarea').fill('  付款依据不完整  ');
  const submit = dialog.getByRole('button', { name: '确认驳回', exact: true });
  assert.equal(await submit.isDisabled(), false);
  await submit.click();
  const submitted = await page.evaluate(() => window.pendingReject);
  assert.deepEqual(submitted, { reason: '付款依据不完整' });
  assert.deepEqual(await page.evaluate(() => window.operationRequests), [{ reason: '付款依据不完整' }]);
  assert.deepEqual(await page.evaluate(() => window.failures), []);
  assert.deepEqual(errors, []);

  console.log(JSON.stringify({
    browser: browser.version(),
    checks: 21,
    consoleErrors: 0,
    contractCopy: 'PASS',
    formFeedback: 'PASS',
    cancelNoRequest: 'PASS',
    submitExactlyOnce: 'PASS',
  }));
} finally {
  await browser.close();
}
