/** Real SFC setup/template and Vue lifecycle; only transport and presentation boundaries are mocked. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const kind = process.argv[process.argv.indexOf('--kind') + 1];
assert.ok(['chart', 'boq', 'grid'].includes(kind), '--kind chart|boq|grid required');
const root = process.cwd();
const component = { chart: 'components/page/blocks/BlockChartDataset.vue', boq: 'components/page/blocks/BlockBoqImportPreview.vue', grid: 'views/SceneContractBlockGridView.vue' }[kind];
const entry = `${root}/frontend/apps/web/src/${component}`;
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), `readonly-block-${kind}-`));
const output = path.join(temporary, 'mounted.mjs');

async function runMounted({ Component, kind, createRenderer, h, ref, nextTick, calls, route, assert }) {
  let checks = 0;
  const equal = (actual, expected, label) => { assert.deepEqual(actual, expected, label); checks += 1; };
  const node = type => ({ type, children: [], parent: null, props: {}, text: '' });
  const renderer = createRenderer({
    patchProp(n, key, _old, value) { n.props[key] = value; },
    insert(n, parent, anchor) {
      if (n.parent) { const old = n.parent.children.indexOf(n); if (old >= 0) n.parent.children.splice(old, 1); }
      n.parent = parent;
      const index = anchor ? parent.children.indexOf(anchor) : -1;
      if (index < 0) parent.children.push(n); else parent.children.splice(index, 0, n);
    },
    remove(n) { if (n.parent) { const index = n.parent.children.indexOf(n); if (index >= 0) n.parent.children.splice(index, 1); n.parent = null; } },
    createElement: type => node(type), createText: text => ({ ...node('text'), text }), createComment: text => ({ ...node('comment'), text }),
    setText(n, text) { n.text = text; }, setElementText(n, text) { n.text = text; n.children = []; },
    parentNode: n => n.parent, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] || null,
    querySelector: () => null, setScopeId() {}, cloneNode: n => ({ ...n, children: [...n.children], props: { ...n.props }, parent: null }),
    insertStaticContent(_html, parent, anchor) { const n = node('static'); n.parent = parent; parent.children.push(n); return [n, n]; },
  });
  const rootNode = node('root');
  function find(type, from = rootNode) { return from.type === type ? from : from.children.map(child => find(type, child)).find(Boolean); }
  const tick = async () => { for (let i = 0; i < 6; i += 1) { await Promise.resolve(); await nextTick(); } };
  const waitCalls = async total => { for (let i = 0; calls.length < total && i < 20; i += 1) await tick(); equal(calls.length, total, 'actual transport call count'); };
  const props = ref(kind === 'grid' ? { intent: 'example.entry', sceneKey: 'scene.a' } : { block: { key: 'test', title: 'Test' }, zoneKey: 'main', dataset: {} });
  const app = renderer.createApp({ setup: () => () => h(Component, props.value) });
  app.mount(rootNode); await tick();
  const state = () => find(kind === 'grid' ? 'section' : 'article')?.props['data-state'];
  const setProps = async patch => { props.value = { ...props.value, ...patch }; await tick(); };
  if (kind !== 'grid') {
    const intent = kind === 'chart' ? 'project.dashboard.chart.fetch' : 'project.boq.import.preview.fetch';
    const declaration = (id, extra = {}) => ({ data: { fetch_intent: intent, fetch_params: kind === 'chart' ? { chart_key: 'declared.chart', project_id: id } : { batch_id: id }, ...extra } });
    const response = label => kind === 'chart'
      ? { schema: 'sc.visualization.chart.v1', chart_key: 'declared.chart', title: label, chart_type: 'bar', series: [{ name: label, points: [{ dimension_value: label, value: 1 }] }] }
      : { batch: { id: 12, name: label, project_id: 3, state: 'done', preview_payload: { schema: 'sc.boq.import.preview.v1', row_count: 1 } }, preview_schema: 'sc.boq.import.preview.v1' };
    const displayed = () => { const model = find('test-panel')?.props.model; return kind === 'chart' ? model?.title : model?.batch?.name; };
    equal([calls.length, state(), Boolean(find('test-panel'))], [0, 'idle', false], 'missing declaration never dispatches');
    await setProps({ dataset: declaration(1) }); await waitCalls(1);
    equal(calls[0].request, { intent, params: kind === 'chart' ? { chart_key: 'declared.chart', project_id: 1 } : { batch_id: 1 } }, 'actual API adapter sends declared request');
    equal(state(), 'loading');
    await setProps({ dataset: declaration(2) }); await waitCalls(2);
    calls[1].resolve(response('new')); await tick();
    equal([state(), displayed()], ['idle', 'new']);
    calls[0].resolve(response('old')); await tick();
    equal([state(), displayed()], ['idle', 'new'], 'old success cannot overwrite new panel');
    await setProps({ dataset: declaration(2, { loading_message: 'Copy changed', empty_message: 'Empty changed' }) });
    equal(calls.length, 2, 'copy-only change does not dispatch');
    if (kind === 'boq') {
      await setProps({ dataset: { data: { fetch_intent: intent, fetch_params: { batch_id: 2, project_id: 3 } } } }); await waitCalls(3);
      equal(calls[2].request.params, { batch_id: 2, project_id: 3 }, 'both declared selectors retained');
      calls[2].resolve(response('both')); await tick(); equal(displayed(), 'both');
    }
    const offset = calls.length;
    await setProps({ dataset: declaration(3) }); await waitCalls(offset + 1);
    await setProps({ dataset: declaration(4) }); await waitCalls(offset + 2);
    calls[offset].reject(new Error('old failure')); await tick();
    equal([state(), Boolean(find('test-panel'))], ['loading', false], 'old catch/finally cannot end current loading');
    calls[offset + 1].resolve(response('latest')); await tick();
    equal([state(), displayed()], ['idle', 'latest']);
    await setProps({ dataset: declaration(4, { fetch_intent: 'api.data' }) });
    equal([calls.length, state(), Boolean(find('test-panel'))], [offset + 2, 'idle', false], 'invalid declaration clears rendered data');
    await setProps({ dataset: declaration(5) }); await waitCalls(offset + 3);
    await setProps({ dataset: declaration(0) });
    equal([state(), Boolean(find('test-panel')), calls.length], ['idle', false, offset + 3], 'zero context invalidates pending request');
    calls[offset + 2].resolve(response('removed')); await tick();
    equal([state(), Boolean(find('test-panel'))], ['idle', false]);
    await setProps({ dataset: declaration(6) }); await waitCalls(offset + 4);
    await setProps({ dataset: declaration(7) }); await waitCalls(offset + 5);
    app.unmount(); await tick();
    calls[offset + 3].resolve(response('unmounted success')); calls[offset + 4].reject(new Error('unmounted failure')); await tick();
    equal([rootNode.children.length, calls.length], [0, offset + 5], 'unmount suppresses both response paths');
  } else {
    const contract = (label, blocks = ['first', 'second']) => ({ title: label, blocks: blocks.map(key => ({ key, title: key, state: 'deferred' })),
      runtime_fetch_hints: { blocks: Object.fromEntries(blocks.map(key => [key, { intent: `custom.${key}.fetch`, params: { block_key: key, nested: { flags: [label] } }, context: { declared: label } }])) } });
    const displayed = () => find('test-page')?.props.contract?.page?.title;
    await waitCalls(1);
    equal(calls[0].request, { intent: 'example.entry', params: { project_id: 99, record_id: 5 }, context: { scene_key: 'scene.a', project_id: 99, record_id: 5 } }, 'entry keeps existing route input');
    await setProps({ sceneKey: 'scene.b' }); await waitCalls(2);
    calls[1].resolve(contract('new entry', [])); await tick(); equal([state(), displayed()], ['idle', 'new entry']);
    calls[0].resolve(contract('old entry')); await tick(); equal([calls.length, displayed()], [2, 'new entry'], 'stale entry never starts hydration');
    await setProps({ sceneKey: 'scene.c' }); await waitCalls(3);
    const oldHydration = contract('old hydration'); delete oldHydration.runtime_fetch_hints.blocks.first.context;
    calls[2].resolve(oldHydration); await waitCalls(4);
    equal(calls[3].request, { intent: 'custom.first.fetch', params: { block_key: 'first', nested: { flags: ['old hydration'] } }, context: { scene_key: 'scene.c' } }, 'deferred nested params retain captured generic scene without route project synthesis');
    await setProps({ intent: 'other.entry', sceneKey: 'scene.d' }); await waitCalls(5);
    calls[3].reject(new Error('old hydration failure')); await tick();
    equal([state(), calls.length], ['loading', 5], 'stale hydrate catch stops old loop without ending new load');
    const currentContract = contract('current', ['first']);
    currentContract.runtime_fetch_hints.blocks.first.context.scene_key = 'declared.override';
    calls[4].resolve(currentContract); await waitCalls(6);
    equal(calls[5].request.context, { scene_key: 'declared.override', declared: 'current' }, 'explicit context overrides captured scene');
    calls[5].resolve({ block: { block_type: 'metric_card', title: 'Materialized', data: { value: 42 } } }); await tick();
    equal([state(), displayed()], ['idle', 'current']);
    equal(find('test-page').props.datasets, { first: { value: 42 } }, 'current hydrated dataset published');
    const staleSuccessStart = calls.length;
    await setProps({ sceneKey: 'scene.old-success' }); await waitCalls(staleSuccessStart + 1);
    calls[staleSuccessStart].resolve(contract('old hydration success')); await waitCalls(staleSuccessStart + 2);
    await setProps({ sceneKey: 'scene.new-success' }); await waitCalls(staleSuccessStart + 3);
    calls[staleSuccessStart + 2].resolve(contract('new retained', [])); await tick();
    calls[staleSuccessStart + 1].resolve({ block: { data: { stale: true } } }); await tick();
    equal([state(), displayed(), calls.length], ['idle', 'new retained', staleSuccessStart + 3], 'old hydration success cannot publish or dispatch its next block');
    const failSoftStart = calls.length;
    await setProps({ sceneKey: 'scene.fail-soft' }); await waitCalls(failSoftStart + 1);
    calls[failSoftStart].resolve(contract('fail soft')); await waitCalls(failSoftStart + 2);
    calls[failSoftStart + 1].reject(new Error('current block failure')); await waitCalls(failSoftStart + 3);
    calls[failSoftStart + 2].resolve({ block: { block_type: 'metric_card', data: { value: 84 } } }); await tick();
    equal([state(), displayed()], ['idle', 'fail soft'], 'current block failure does not fail entire scene');
    equal(find('test-page').props.contract.zones[0].blocks[0].state, 'error', 'failed stub retains error state');
    equal(find('test-page').props.datasets, { second: { value: 84 } }, 'remaining block succeeds after fail-soft error');
    const closingStart = calls.length;
    await setProps({ sceneKey: 'scene.e' }); await waitCalls(closingStart + 1);
    await setProps({ sceneKey: 'scene.f' }); await waitCalls(closingStart + 2);
    calls[closingStart].reject(new Error('old entry failure')); await tick();
    equal([state(), Boolean(find('test-page'))], ['loading', false], 'old entry catch/finally ignored');
    calls[closingStart + 1].resolve(contract('unmount hydration')); await waitCalls(closingStart + 3);
    app.unmount(); await tick();
    calls[closingStart + 2].resolve({ block: { data: { stale: true } } }); await tick();
    equal([rootNode.children.length, calls.length], [0, closingStart + 3], 'dispose prevents next deferred request');
  }
  return checks;
}

const boundary = `import { reactive } from 'vue';
export const calls = [];
export const route = reactive({query:{project_id:'99',record_id:'5'},fullPath:'/s/test?project_id=99&record_id=5'});
export function intentRequest(request) { return new Promise((resolve,reject)=>calls.push({request:JSON.parse(JSON.stringify(request)),resolve,reject})); }
`;
const harness = `import assert from 'node:assert/strict';
import {createRenderer,h,ref,nextTick} from 'vue';
import Component from ${JSON.stringify(entry)};
import {calls,route} from 'test-boundary';
${runMounted.toString()}
export default () => runMounted({Component,kind:${JSON.stringify(kind)},createRenderer,h,ref,nextTick,calls,route,assert});`;
try {
  await build({ stdin: { contents: harness, resolveDir: `${root}/frontend/apps/web`, loader: 'js' }, bundle: true,
    platform: 'node', format: 'esm', outfile: output, logLevel: 'error',
    define: { __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false' },
    alias: { vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js` },
    plugins: [{ name: 'actual-sfc-with-boundaries', setup(builder) {
      builder.onResolve({ filter: /(^|\/)intents$|^test-boundary$/ }, () => ({ path: 'transport', namespace: 'boundary' }));
      builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({ contents: boundary, loader: 'js', resolveDir: `${root}/frontend/apps/web` }));
      builder.onResolve({ filter: /^vue-router$|\/stores\/session$|\/resolvers\/sceneRegistry$|\/app\/pageContract$/ }, args => ({ path: args.path, namespace: 'context' }));
      builder.onLoad({ filter: /.*/, namespace: 'context' }, args => ({ contents:
        args.path === 'vue-router' ? "import {route} from 'test-boundary'; export const useRoute=()=>route; export const useRouter=()=>({push:async()=>{}});"
          : args.path.endsWith('/session') ? 'export const useSessionStore=()=>({menuTree:[]});'
            : args.path.endsWith('/sceneRegistry') ? 'export const getSceneByKey=()=>null;'
              : "export const usePageContract=()=>({sectionEnabled:()=>true,sectionStyle:()=>({}),sectionTagIs:()=>true});",
        loader: 'js', resolveDir: `${root}/frontend/apps/web` }));
      builder.onLoad({ filter: /\.vue$/ }, args => {
        if (args.path !== entry) {
          if (args.path.endsWith('/ScCard.vue')) return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({setup:(_, {slots})=>()=>h('test-card',{},[slots.actions?.(),slots.default?.()])});`, loader: 'js', resolveDir: path.dirname(args.path) };
          assert.ok(/\/(ChartDatasetPanel|BoqImportPreviewPanel|PageRenderer|StatusPanel)\.vue$/.test(args.path), `unexpected stub ${args.path}`);
          const name = args.path.endsWith('/PageRenderer.vue') ? 'test-page' : args.path.endsWith('/StatusPanel.vue') ? 'test-status' : 'test-panel';
          return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({props:['model','contract','datasets','message','title','variant'],setup:props=>()=>h('${name}',{...props})});`, loader: 'js', resolveDir: path.dirname(args.path) };
        }
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        const compiled = compileScript(descriptor, { id: args.path, inlineTemplate: true });
        return { contents: compiled.content, loader: 'ts', resolveDir: path.dirname(args.path) };
      });
    } }],
  });
  const run = (await import(pathToFileURL(output).href)).default;
  const checks = await run();
  console.log(`[readonly-block-component] PASS kind=${kind} checks=${checks} actual_sfc=true vue_mount=true transport=mocked presentation=stubbed card_driver=stubbed${kind === 'grid' ? ' grid_child_renderer=stubbed' : ''}`);
} finally { fs.rmSync(temporary, { recursive: true, force: true }); }
