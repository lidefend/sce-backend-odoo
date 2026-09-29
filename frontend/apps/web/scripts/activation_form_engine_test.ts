/** Actual official form engine with rules extracted from the shipped activation template. No account writes. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRenderer, defineComponent, h, nextTick, ref } from 'vue';
import { TDesignForm, TDesignFormItem } from '../src/components/design-system/tdesignPrimitiveBridge';
type HostNode = {
  children: HostNode[];
  parent: HostNode | null;
  props: Record<string, unknown>;
  text?: string;
  type?: string;
};
const hostNode = (type?: string): HostNode => ({ children: [], parent: null, props: {}, type });
const renderer = createRenderer<HostNode, HostNode>({
  patchProp(node, key, _previous, value) {
    if (value === null || value === undefined) delete node.props[key];
    else node.props[key] = value;
  },
  insert(child, parent, anchor) {
    child.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index >= 0) parent.children.splice(index, 0, child);
    else parent.children.push(child);
  },
  remove(child) {
    if (!child.parent) return;
    const index = child.parent.children.indexOf(child);
    if (index >= 0) child.parent.children.splice(index, 1);
    child.parent = null;
  },
  createElement: (type) => hostNode(type),
  createText: (text) => ({ ...hostNode('text'), text }),
  createComment: (text) => ({ ...hostNode('comment'), text }),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; },
  parentNode: (node) => node.parent,
  nextSibling(node) {
    if (!node.parent) return null;
    const index = node.parent.children.indexOf(node);
    return node.parent.children[index + 1] || null;
  },
  querySelector: () => null,
  setScopeId: () => {},
  cloneNode: (node) => ({ ...node, children: [...node.children], props: { ...node.props }, parent: null }),
  insertStaticContent: () => {
    const node = hostNode('static');
    return [node, node];
  },
});
(globalThis as unknown as Record<string, unknown>).document = {
  documentElement: { style: {}, setAttribute: () => {}, getAttribute: () => null },
};
(globalThis as unknown as Record<string, unknown>).window = {
  location: { href: 'http://localhost/', origin: 'http://localhost' },
};


const source = fs.readFileSync('frontend/apps/web/src/views/AccountActivationView.vue', 'utf8');
const ruleExpressions = [...source.matchAll(/<ScFormItem name="([^"]+)"[\s\S]*?:rules="([^"]+)"/g)];
assert.equal(ruleExpressions.length, 3);
const pageText = (_key: string, fallback: string) => fallback;
let checks = 0;
for (const [data, expected] of [
  [{ activationCode: '' }, false],
  [{ activationCode: 'synthetic-code' }, true],
  [{ password: '', confirmPassword: '' }, false],
  [{ password: 'short', confirmPassword: 'short' }, false],
  [{ password: 'synthetic-1234', confirmPassword: 'short' }, false],
  [{ password: 'synthetic-1234', confirmPassword: 'synthetic-1234' }, true],
] as const) {
  const form = ref<{ validate: () => Promise<unknown> } | null>(null);
  const app = renderer.createApp(defineComponent({ setup() {
    return () => h(TDesignForm as never, { ref: form, data, showErrorMessage: false }, () =>
      ruleExpressions.filter(([,name]) => name in data).map(([,name,expression]) => {
        const values = data as Record<string, string>;
        const rules = new Function('pageText', 'password', 'confirmPassword', `return (${expression})`)(pageText, values.password || '', values.confirmPassword || '');
        return h(TDesignFormItem as never, { name, rules, showErrorMessage: false }, () => h('input'));
      }));
  } }));
  app.mount(hostNode('root'));
  await nextTick();
  assert.equal((await form.value!.validate()) === true, expected);
  checks++;
  app.unmount();
}
for (const [name, action] of [['onCodeValidated', 'startActivation'], ['onPasswordValidated', 'finishActivation']]) {
  const body = source.match(new RegExp(`function ${name}\\(result: \\{ validateResult: unknown \\}\\) \\{([\\s\\S]*?)\\n\\}`))?.[1];
  assert.ok(body);
  let calls = 0;
  const busy = { value: false };
  const handler = new Function('result', 'busy', action, body!);
  for (const validateResult of [false, undefined, {}, 'true']) handler({ validateResult }, busy, () => { calls++; });
  assert.equal(calls, 0); checks++;
  handler({ validateResult: true }, busy, () => { calls++; });
  assert.equal(calls, 1); checks++;
  busy.value = true;
  handler({ validateResult: true }, busy, () => { calls++; });
  assert.equal(calls, 1); checks++;
}
assert.ok(source.includes('key="code" novalidate') && source.includes('key="password" novalidate'));
console.log(`[activation-form-engine] PASS ${checks} behavior cases`);
