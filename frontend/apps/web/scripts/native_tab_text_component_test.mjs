import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));

const root = process.cwd();
const source = `${root}/frontend/apps/web/src`;

// Mount the full recursive template with Vue 3 SSR and assert the *final*
// rendered text. This is the regression the user asked for: a notebook page
// whose own text facet and a following inline text child must both survive the
// recursive renderer's root dispatch (no Odoo database involved).
const harness = `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import Tree from '${source}/components/template/NativeFormTreeRenderer.vue';

const emptyAdapter = {
  busy: false, showOne2manyErrors: false, readContext: {},
  visibleOne2manyRows: () => [], one2manyColumns: () => [], one2manyVisibleColumns: () => [],
  prepareOne2manyColumns: () => undefined, isOne2manyHydrating: () => false,
  one2manyCreateLabel: () => '', one2manyCanOpenRow: () => false, one2manyCanCreate: () => false,
  one2manyCanInlineEdit: () => false, one2manyCanUnlink: () => false,
  one2manyColumnInputType: () => 'text', one2manyRowHints: () => [], one2manyRowErrors: () => [],
  one2manyEffectiveColumn: (_n, _r, c) => c, one2manyCellError: () => '', one2manyRowStateLabel: () => '',
  one2manyRowMessages: () => [], one2manyRowError: () => '', one2manyColumnDisplayValue: (_c, v) => String(v ?? ''),
  one2manySummary: () => '', removedOne2manyRows: () => [], selectedRelationOptions: () => [], relationIds: () => [],
  one2manyRowLabel: () => '', one2manyRemovalLabels: () => ({remove:'', cancelCreate:'', restore:'', removedSummary:'', pendingRemoval:''}),
  one2manyFieldError: () => '', one2manyRowHasErrors: () => false, one2manyRowErrorMessages: () => [],
};

export async function render(nodes) {
  const props = { nodes, fieldSchemasForNodes: () => [], isNodeVisible: () => true, relationAdapter: emptyAdapter };
  const app = createSSRApp({ render: () => h(Tree, props) });
  const warnings = [];
  app.config.warnHandler = (message) => warnings.push(message);
  const html = await renderToString(app);
  return { html, warnings };
}
`;

const result = await build({
  stdin: { contents: harness, resolveDir: `${root}/frontend/apps/web`, loader: 'js' },
  bundle: true,
  write: false,
  platform: 'node',
  format: 'esm',
  define: { 'import.meta.env': '{}' },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs', '.vue'],
  loader: { '.css': 'empty' },
  banner: { js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);" },
  alias: {
    'vue/server-renderer': require.resolve('vue/server-renderer'),
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
  },
  plugins: [{
    name: 'actual-vue-sfc',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        if (args.path.endsWith('/ScDialog.vue')) return { contents: 'export default { render: () => null };', loader: 'js' };
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        return { contents: compileScript(descriptor, { id: args.path, inlineTemplate: true }).content, loader: 'ts', resolveDir: args.path.slice(0, args.path.lastIndexOf('/')) };
      });
    },
  }],
  logLevel: 'error',
});

const output = `${root}/.runtime/native-tab-text-component-test.mjs`;
fs.mkdirSync(`${root}/.runtime`, { recursive: true });
fs.writeFileSync(output, result.outputFiles[0].text);
const { render } = await import(output);

const nodes = [{
  type: 'notebook',
  name: 'project_tabs',
  span: 24,
  pages: [{
    type: 'page',
    name: 'overview_page',
    text: '页签首句',
    children: [
      { type: 'field', name: 'state', invisible: true },
      { type: 'text', text: '操作前请核对项目。' },
    ],
  }],
}];

const { html, warnings } = await render(nodes);
const text = html.replace(/<[^>]+>/g, '');
assert.ok(text.includes('页签首句'), 'page own text must render');
assert.ok(text.includes('操作前请核对项目。'), 'inline text after a hidden field must render');
assert.ok(text.indexOf('页签首句') < text.indexOf('操作前请核对项目。'), 'text must render in declared order');
assert.deepEqual(warnings, []);

const observations = { pageText: '页签首句', inlineText: '操作前请核对项目。', ordered: true };
fs.writeFileSync(`${root}/.runtime/native-tab-text-component-observations.json`, JSON.stringify({ kind: 'actual_component_SSR', observations }, null, 2) + '\n');
console.log('[native-tab-text-component] PASS actual NativeFormTreeRenderer SSR page-text=页签首句 inline-text=操作前请核对项目。 ordered');
