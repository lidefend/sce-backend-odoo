import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const selectFile = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneSelect.vue`;
const dateFile = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneDateField.vue`;
const output = await build({
  stdin: {
    contents: `
import { createApp, h, ref } from 'vue';
import Select from ${JSON.stringify(selectFile)};
import DateField from ${JSON.stringify(dateFile)};
window.log = [];
const Host = { setup() {
  const selectRef = ref(null); const dateRef = ref(null);
  window.focusSelect = options => selectRef.value.focus(options);
  window.focusDate = options => dateRef.value.focus(options);
  return () => h('div', [
    h(Select, { ref: selectRef, id: 'select', modelValue: 'a', name: 'choice', required: true, filterable: true,
      options: [{value:'a',label:'A'},{value:'b',label:'B'}], ariaLabel: '选择',
      onKeydown: e => window.log.push(e.nativeEvent.type), onFocus: (v,e) => window.log.push(e.nativeEvent.type),
      onSearch: (v,e) => window.log.push('search:'+v), onChange: (v,e) => window.log.push('change:'+v),
      onPopupVisibleChange: (s,e) => window.log.push('popup:'+s.visible) }),
    h(DateField, { ref: dateRef, id: 'date', modelValue: {precision:'date',value:'2026-11-08'},
      required: true, ariaLabel: '日期', onKeydown: e => window.log.push(e.nativeEvent.type), onFocus: (v,e) => window.log.push(e.nativeEvent.type) }),
  ]);
}};
createApp(Host).mount('#app');
`,
    resolveDir: `${root}/frontend/apps/web`, loader: 'js',
  },
  bundle: true, write: false, platform: 'browser', format: 'iife',
  define: {'process.env.NODE_ENV':'"production"','__VUE_OPTIONS_API__':'true','__VUE_PROD_DEVTOOLS__':'false','__VUE_PROD_HYDRATION_MISMATCH_DETAILS__':'false'},
  resolveExtensions: ['.tsx','.ts','.jsx','.js','.css','.json','.mjs'], loader: {'.css':'empty'},
  alias: {vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,'tdesign-vue-next':`${root}/frontend/packages/ui/node_modules/tdesign-vue-next`},
  plugins: [{name:'sfc',setup(b){b.onLoad({filter:/\.vue$/},a=>{const d=parse(fs.readFileSync(a.path,'utf8'),{filename:a.path}).descriptor;return{contents:compileScript(d,{id:a.path,inlineTemplate:true}).content,loader:'ts',resolveDir:path.dirname(a.path)}})}}], logLevel:'error',
});
const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
const browser = await launchChromium();
try {
  const page = await browser.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<div id="app"></div>'); await page.addScriptTag({content: output.outputFiles[0].text});
  await page.locator('#select').waitFor({state:'visible'});
  assert.equal(await page.locator('#select').getAttribute('name'), 'choice');
  assert.equal(await page.locator('#select').getAttribute('aria-label'), '选择');
  assert.equal(await page.locator('#select').getAttribute('required'), '');
  assert.equal(await page.locator('#date').getAttribute('aria-label'), '日期');
  assert.equal(await page.locator('#date').getAttribute('required'), '');
  await page.evaluate(() => window.focusSelect({preventScroll:true}));
  await page.locator('#select').fill('B');
  await page.getByText('B',{exact:true}).last().click();
  await page.evaluate(() => window.focusDate({preventScroll:true}));
  await page.keyboard.press('Tab');
  const events=await page.evaluate(()=>window.log);
  assert.ok(events.includes('focus')); assert.ok(events.some(e=>e.startsWith('search:')));
  assert.ok(events.some(e=>e.startsWith('popup:'))); assert.ok(events.includes('change:b'));
  assert.deepEqual(errors, []);
 console.log(JSON.stringify({browser:browser.version(),checks:11,consoleErrors:0,selectPopupSearch:'PASS',datePopupEvent:'N/A_PORT_HAS_NO_POPUP_EVENT'}));
} finally { await browser.close(); }
