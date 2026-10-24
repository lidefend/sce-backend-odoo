// Offline geometry regression. Uses production SFC styles and the wrapper
// topology observed in view 1772; no server, credentials or business mutations.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { launchChromium } from './playwright_runtime.mjs';

const require = createRequire(`${process.cwd()}/frontend/apps/web/package.json`);
const { parse, compileStyle } = require('vue/compiler-sfc');
const nativePath = 'frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue';
const baseline = process.argv.includes('--baseline');
const nativeSource = baseline
  ? execFileSync('git', ['show', `8ff4cad7f3eb38152e74ec9222297bd692612c07:${nativePath}`], { encoding: 'utf8' })
  : fs.readFileSync(nativePath, 'utf8');
const nativeStyle = compileStyle({ source: parse(nativeSource).descriptor.styles[0].content, id: 'data-v-native', scoped: true });
assert.deepEqual(nativeStyle.errors, []);
const formStyle = compileStyle({ source: parse(fs.readFileSync('frontend/apps/web/src/components/template/FormSection.vue', 'utf8')).descriptor.styles[0].content, id: 'data-v-field', scoped: true });
assert.deepEqual(formStyle.errors, []);
const tree = body => `<div data-v-native class="native-form-tree">${body}</div>`;
const container = (classes, body) => `<section data-v-native class="native-container ${classes}">${body}</section>`;
const text = value => `<p data-v-native class="native-static-text">${value}</p>`;
const field = (key, value, label = '') => `<div data-v-native data-v-field class="template-form-section template-form-section--readonly">
  <div class="card-body"><form data-v-field class="template-form-section-form">
  <div data-v-field class="template-form-section-grid"><div data-v-field class="field${label ? '' : ' field--label-free'}" data-field-name="${key}" data-field-key="${key}.summary" data-native-locator="/summary/${key}" data-field-state="readonly" data-field-band="half">
  <div data-v-field class="field-label-row">${label ? `<label data-v-field>${label}</label>` : ''}</div>
  <div data-v-field class="field-control-row" data-semantic-component="ScFormItem"><span>${value}</span></div>
  </div></div></form></div></div>`;

const identity = container('sc-project-title h3', field('name', '示例工程项目名称与完整身份信息', '名称'))
  + container('small text-muted', text('项目编号') + field('code', 'EXAMPLE-001') + tree(container('', text('经营方式'))) + field('strategy', '直营'))
  + container('text-muted', text('项目负责人') + field('responsible', '示例负责人'))
  + container('text-muted', text('项目经理') + field('manager', '示例经理'))
  + container('small text-muted', text('业主') + field('owner', '示例基础设施建设投资发展有限公司'));
const markup = `<div id="overview">${tree(container('sc-project-overview', tree(
  container('sc-project-overview__header d-flex justify-content-between align-items-start', tree(container('', tree(identity))) + '<div data-v-native class="native-actions"><button>项目设置</button></div>')
  + container('sc-project-stage', tree(container('sc-project-stage__desc', text('立项完成度：') + field('done', '3') + tree(container('', text('/'))) + field('total', '3'))))
)))}</div>
<div id="maintenance">${tree(container('native-container--group', field('maintenance', '保留维护区域')))}<input value="原值"><button>保存草稿</button></div>
<div id="board">${tree(container('native-container--group', field('board', '只读看板')))}</div>`;
const fixture = `<!doctype html><style>:root {--sc-space-xs:8px;--sc-space-sm:12px;--sc-space-md:16px;--sc-field-row-gap:12px}
*{box-sizing:border-box}body{margin:0;padding:16px;font:14px/1.5 sans-serif}p{margin:0}button{white-space:nowrap}.field-control-row span{display:block;min-height:24px}
${formStyle.code}
${nativeStyle.code}</style>${markup}`;
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks += 1; };
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  await page.route('**/*', route => route.abort());
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 950 });
    const unaffected = () => page.locator('#maintenance,#board').evaluateAll(es => es.map(e => ({ html: e.innerHTML, text: e.innerText })));
    await page.setContent(fixture);
    const previous = await unaffected();
    const result = await page.evaluate(() => {
      const header = document.querySelector('.sc-project-overview__header');
      const body = header.querySelector('.native-container');
      const completion = document.querySelector('.sc-project-stage__desc');
      const fields = [...document.querySelectorAll('[data-field-key]')].map(e => ({ key: e.dataset.fieldKey, locator: e.dataset.nativeLocator, state: e.dataset.fieldState }));
      return {
        headerText: header.innerText,
        bodyText: body.innerText,
        completionText: completion.textContent.replace(/\s+/g, ''),
        completionFields: [...completion.querySelectorAll('[data-field-key]')].map(e => e.dataset.fieldKey),
        hasSlash: [...completion.querySelectorAll('p')].some(e => e.textContent === '/'),
        overflow: document.documentElement.scrollWidth > innerWidth,
        fields,
        input: document.querySelector('input').value,
        saveDisabled: document.querySelector('#maintenance button').disabled,
      };
    });
    console.log(JSON.stringify({ width, body: result.bodyText, completion: result.completionText, fieldOrder: result.completionFields }));
    check(result.bodyText.includes('示例工程项目名称与完整身份信息') && result.headerText.includes('项目设置'), `${width}: identity and declared action are present`);
    check(!result.overflow, `${width}: no horizontal overflow`);
    check(result.completionText === '立项完成度：3/3' && result.hasSlash, `${width}: completion text order remains label value / value`);
    check(JSON.stringify(result.completionFields) === JSON.stringify(['done.summary', 'total.summary']), `${width}: completion field identity and order retained`);
    check(result.fields.length === 10 && result.fields.every(f => f.state === 'readonly' && f.locator), `${width}: occurrence and readonly identity retained`);
    check(result.input === '原值' && !result.saveDisabled, `${width}: maintenance control state retained`);
    // Presentation is scoped to the declared regions, not nearby maintenance
    // or board fields. Removing that region must leave their sizing untouched.
    await page.locator('#overview').evaluate(e => e.remove());
    check(JSON.stringify(previous) === JSON.stringify(await unaffected()), `${width}: maintenance/board content and identity are independent`);
  }
  console.log(`[project-detail-summary] PASS checks=${checks} source=${baseline ? 'baseline' : 'working-tree'} offline=true production_css=true fixture_dom=true`);
} finally {
  await browser.close();
}
