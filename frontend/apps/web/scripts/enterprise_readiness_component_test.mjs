/** Mount the real enterprise readiness SFC; only transport and design-system leaves are controlled. */
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
const root = process.cwd();
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'enterprise-readiness-component-'));
const harnessEntry = path.join(temporary, 'harness.ts');
const output = path.join(temporary, 'harness.mjs');
fs.writeFileSync(harnessEntry, `
export { default as EnterpriseReadinessPanel } from ${JSON.stringify(
  path.join(root, 'frontend/apps/web/src/components/scene/EnterpriseReadinessPanel.vue'),
)};
export { useSessionStore } from ${JSON.stringify(
  path.join(root, 'frontend/apps/web/src/stores/session.ts'),
)};
export { requireReadiness } from ${JSON.stringify(
  path.join(root, 'frontend/apps/web/src/composables/useEnterpriseReadiness.ts'),
)};
export { createApp, createRenderer, defineComponent, h, nextTick } from 'vue';
export { createPinia, setActivePinia } from 'pinia';
`);

const buttonStub = `
import { defineComponent, h } from 'vue';
export default defineComponent({
  name: 'ScButton',
  inheritAttrs: false,
  props: { disabled: Boolean, title: String },
  emits: ['click'],
  setup(props, { attrs, emit, slots }) {
    return () => h('test-button', {
      ...attrs,
      disabled: props.disabled,
      title: props.title,
      onClick: () => { if (!props.disabled) emit('click'); },
    }, slots.default?.());
  },
});`;
const stateStub = `
import { defineComponent, h } from 'vue';
export default defineComponent({
  name: 'ScInlineState',
  inheritAttrs: false,
  setup(_, { attrs }) {
    return () => h('test-state', attrs, attrs.label);
  },
});`;

await build({
  entryPoints: [harnessEntry],
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node22',
  outfile: output,
  define: { 'import.meta.env': '{}' },
  alias: {
    vue: require.resolve('vue'),
    pinia: require.resolve('pinia'),
  },
  plugins: [{
    name: 'enterprise-readiness-sfc',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        if (args.path.endsWith('/ScButton.vue')) {
          return { contents: buttonStub, loader: 'js', resolveDir: path.dirname(args.path) };
        }
        if (args.path.endsWith('/ScInlineState.vue')) {
          return { contents: stateStub, loader: 'js', resolveDir: path.dirname(args.path) };
        }
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

const storage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    clear: () => values.clear(),
  };
};
globalThis.sessionStorage = storage();
globalThis.localStorage = storage();
globalThis.window = {
  sessionStorage: globalThis.sessionStorage,
  localStorage: globalThis.localStorage,
  location: { pathname: '/', href: 'http://localhost/' },
  matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
};

const {
  EnterpriseReadinessPanel,
  useSessionStore,
  requireReadiness,
  createApp,
  createRenderer,
  defineComponent,
  h,
  nextTick,
  createPinia,
  setActivePinia,
} = await import(pathToFileURL(output));

const pending = [];
globalThis.fetch = ((_url, init) => new Promise((resolve, reject) => {
  pending.push({
    body: JSON.parse(String(init.body)),
    resolve: (data) => resolve(new Response(JSON.stringify({ ok: true, data, meta: {} }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })),
    reject,
  });
}));

setActivePinia(createPinia());
const session = useSessionStore();
session.setToken('enterprise-readiness-component-token');
session.sessionDb = 'sc_dev_demo';
session.initStatus = 'ready';
session.recordContext = {
  company_id: 1,
  company_name: '示例企业',
  selected: null,
};

const sections = [
  ['enterprise.identity', 'enterprise_foundation', '企业与组织', 10, '企业身份'],
  ['enterprise.organization', 'enterprise_foundation', '企业与组织', 10, '组织架构'],
  ['enterprise.positions', 'enterprise_foundation', '企业与组织', 10, '岗位体系'],
  ['enterprise.users', 'people_access', '人员、账号与权限', 20, '用户身份'],
  ['enterprise.employees', 'people_access', '人员、账号与权限', 20, '员工档案'],
  ['enterprise.user_employee_link', 'people_access', '人员、账号与权限', 20, '用户与员工关联'],
  ['enterprise.user_org_position', 'people_access', '人员、账号与权限', 20, '用户与部门、岗位关系'],
  ['enterprise.roles', 'people_access', '人员、账号与权限', 20, '系统角色'],
  ['enterprise.project_responsibility', 'people_access', '人员、账号与权限', 20, '项目成员责任'],
  ['enterprise.scenario_enablement', 'scenario_enablement', '业务场景与启用验证', 30, '企业场景启用'],
  ['enterprise.scenario_dependencies', 'scenario_enablement', '业务场景与启用验证', 30, '场景依赖'],
  ['enterprise.role_delivery', 'scenario_enablement', '业务场景与启用验证', 30, '角色工作空间交付'],
];
const response = (needsAttention) => ({
  contract_version: 'enterprise_readiness.v2',
  company_id: 1,
  company_name: '示例企业',
  maintenance_scope: {
    kind: 'enterprise_configuration',
    company_id: 1,
    company_name: '示例企业',
    enterprise_managed: ['企业信息', '人员与账号'],
    platform_managed: ['企业创建', '产品版本发布'],
    business_validation_required: ['场景依赖', '角色工作空间交付'],
  },
  summary: {
    rule_count: 12,
    applicable_count: 12,
    verified_count: 1,
    configured_count: needsAttention ? 8 : 9,
    needs_attention_count: needsAttention ? 1 : 0,
    pending_business_validation_count: 2,
    not_applicable_count: 0,
  },
  rules: sections.map(([ruleKey, sectionKey, sectionLabel, sectionSequence, label], index) => ({
    rule_key: ruleKey,
    label,
    section_key: sectionKey,
    section_label: sectionLabel,
    section_sequence: sectionSequence,
    applicability: true,
    status: needsAttention && index === 1 ? 'NOT_CONFIGURED' : index === 0 ? 'VERIFIED' : (
      index >= 10 ? 'NOT_EVALUATED' : 'CONFIGURED'
    ),
    status_label: needsAttention && index === 1 ? '未配置' : index === 0 ? '已验证' : (
      index >= 10 ? '待业务验证' : '已配置'
    ),
    failure_reason: needsAttention && index === 1 ? '组织事实缺失' : '',
    suggested_responsible_party: needsAttention && index === 1 ? '组织管理负责人' : '企业管理员',
    remediation: needsAttention && index === 1 ? {
      kind: 'handling_entry',
      key: 'smart_construction_core.action_sc_organization_department',
      label: '组织架构',
    } : null,
  })),
});
requireReadiness(response(true));

function hostNode(type) {
  return { type, children: [], parent: null, props: {}, text: '' };
}
const renderer = createRenderer({
  patchProp(node, key, _old, value) { node.props[key] = value; },
  insert(node, parent, anchor) {
    if (node.parent) {
      const old = node.parent.children.indexOf(node);
      if (old >= 0) node.parent.children.splice(old, 1);
    }
    node.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index >= 0) parent.children.splice(index, 0, node);
    else parent.children.push(node);
  },
  remove(node) {
    if (!node.parent) return;
    const index = node.parent.children.indexOf(node);
    if (index >= 0) node.parent.children.splice(index, 1);
    node.parent = null;
  },
  createElement: hostNode,
  createText: (text) => ({ ...hostNode('text'), text }),
  createComment: (text) => ({ ...hostNode('comment'), text }),
  setText(node, text) { node.text = text; },
  setElementText(node, text) { node.text = text; node.children = []; },
  parentNode: (node) => node.parent,
  nextSibling: (node) => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
  querySelector: () => null,
  setScopeId() {},
  cloneNode: (node) => ({ ...node, props: { ...node.props }, children: [...node.children], parent: null }),
  insertStaticContent(_html, parent, anchor) {
    const node = hostNode('static');
    node.parent = parent;
    if (anchor) parent.children.push(node);
    else parent.children.push(node);
    return [node, node];
  },
});
const rootNode = hostNode('root');
const emitted = [];
const wrapper = defineComponent({
  render: () => h(EnterpriseReadinessPanel, { onRemediate: (target) => emitted.push(target) }),
});
const app = renderer.createApp(wrapper);
app.mount(rootNode);
const tick = async () => { for (let index = 0; index < 8; index += 1) await nextTick(); };
for (let index = 0; index < 20 && !pending.length; index += 1) await tick();
assert.equal(pending.length, 1);
assert.equal(pending[0].body.intent, 'enterprise.readiness.diagnosis.get');
pending[0].resolve(response(true));
await tick();

const all = (node, rows = []) => {
  rows.push(node);
  node.children.forEach((child) => all(child, rows));
  return rows;
};
const textOf = (node) => node.text + node.children.map(textOf).join('');
const buttons = () => all(rootNode).filter((node) => node.type === 'test-button');
const buttonByText = (label) => buttons().find((node) => textOf(node).includes(label));
const pageText = textOf(rootNode);
assert.match(pageText, /当前企业：示例企业/);
assert.match(pageText, /1 项需处理/);
assert.match(pageText, /2 项待业务验证/);
for (const label of ['企业与组织', '人员、账号与权限', '业务场景与启用验证']) {
  assert.match(pageText, new RegExp(label));
}
assert.match(pageText, /用户身份/);
assert.match(pageText, /员工档案/);
assert.match(pageText, /项目成员责任/);
buttonByText('组织架构').props.onClick();
assert.deepEqual(emitted, [{
  kind: 'handling_entry',
  key: 'smart_construction_core.action_sc_organization_department',
  label: '组织架构',
}]);

const refresh = buttonByText('刷新');
refresh.props.onClick();
for (let index = 0; index < 20 && pending.length < 2; index += 1) await tick();
assert.equal(pending.length, 2);
pending[1].resolve(response(false));
await tick();
const refreshedText = textOf(rootNode);
assert.match(refreshedText, /0 项需处理/);
assert.doesNotMatch(refreshedText, /组织事实缺失/);
console.log('[enterprise_readiness_component_test] PASS cases=14 mounted=actual transport=controlled leaves=stubbed');
app.unmount();
fs.rmSync(temporary, { recursive: true, force: true });
