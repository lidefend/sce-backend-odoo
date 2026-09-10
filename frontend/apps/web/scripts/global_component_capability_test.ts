import assert from 'node:assert/strict';
import { createRenderer, defineAsyncComponent, defineComponent, h, nextTick, Teleport } from 'vue';
import { provideConfig, useConfig } from '../../../packages/ui/node_modules/tdesign-vue-next/es/config-provider/hooks/useConfig.mjs';

type Listener = () => void;

class FakeMediaQueryList {
  matches = false;
  addCount = 0;
  removeCount = 0;
  private listeners = new Set<Listener>();

  addEventListener(type: string, listener: Listener) {
    assert.equal(type, 'change');
    this.addCount += 1;
    this.listeners.add(listener);
  }

  removeEventListener(type: string, listener: Listener) {
    assert.equal(type, 'change');
    this.removeCount += 1;
    this.listeners.delete(listener);
  }

  dispatch(matches: boolean) {
    this.matches = matches;
    for (const listener of this.listeners) listener();
  }
}

const attributes = new Map<string, string>();
const darkMedia = new FakeMediaQueryList();
const motionMedia = new FakeMediaQueryList();
const storage = new Map<string, string>([['sc_theme', 'system']]);
const theme = await import('../src/styles/theme.ts');

Object.assign(globalThis, {
  document: {
    documentElement: {
      style: { colorScheme: '' },
      setAttribute: (name: string, value: string) => attributes.set(name, value),
      getAttribute: (name: string) => attributes.get(name) ?? null,
    },
  },
  localStorage: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  },
  window: {
    matchMedia: (query: string) => query.includes('color-scheme') ? darkMedia : motionMedia,
  },
});

theme.bootTheme();
theme.ensureThemeRuntimeWatch();
assert.equal(darkMedia.addCount, 1, 'system theme listener must be application-singleton');
assert.equal(motionMedia.addCount, 1, 'reduced motion listener must be application-singleton');
assert.equal(attributes.get('data-sc-theme'), 'light');
assert.equal(attributes.get('data-sc-reduced-motion'), 'no-preference');
assert.deepEqual(theme.tdesignGlobalConfig.value, {}, 'normal motion must inherit official defaults');

darkMedia.dispatch(true);
assert.equal(attributes.get('data-sc-theme'), 'dark', 'system theme changes must update the shared root');
motionMedia.dispatch(true);
assert.equal(attributes.get('data-sc-reduced-motion'), 'reduce');
assert.deepEqual(theme.tdesignGlobalConfig.value, {
  animation: { include: [], exclude: ['ripple', 'expand', 'fade'] },
});

theme.stopThemeRuntime();
assert.equal(darkMedia.removeCount, 1);
assert.equal(motionMedia.removeCount, 1);

type HostNode = { children: HostNode[]; parent: HostNode | null; text?: string };
const hostNode = (): HostNode => ({ children: [], parent: null });
const teleportTarget = hostNode();
const renderer = createRenderer<HostNode, HostNode>({
  patchProp: () => {},
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
  createElement: hostNode,
  createText: (text) => ({ ...hostNode(), text }),
  createComment: (text) => ({ ...hostNode(), text }),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; },
  parentNode: (node) => node.parent,
  nextSibling(node) {
    if (!node.parent) return null;
    const index = node.parent.children.indexOf(node);
    return node.parent.children[index + 1] || null;
  },
  querySelector: () => teleportTarget,
  setScopeId: () => {},
  cloneNode: (node) => ({ ...node, children: [...node.children], parent: null }),
  insertStaticContent: () => {
    const node = hostNode();
    return [node, node];
  },
});

const providerEvidence: Record<string, unknown> = {};
function capabilityProbe(name: string) {
  return defineComponent({
    name: `${name}CapabilityProbe`,
    setup() {
      const { globalConfig } = useConfig('animation');
      providerEvidence[name] = globalConfig.value;
      return () => h('span');
    },
  });
}
const RegularProbe = capabilityProbe('regular');
const LazyProbe = defineAsyncComponent(async () => capabilityProbe('lazy'));
const OverlayProbe = capabilityProbe('overlay');
const LocalProbe = capabilityProbe('local');
const LocalProviderProbe = defineComponent({
  setup(_props, { slots }) {
    provideConfig({ globalConfig: { animation: { include: ['fade'], exclude: [] } } });
    return () => slots.default?.();
  },
});
const RootProbe = defineComponent({
  setup() {
    provideConfig({ globalConfig: theme.tdesignGlobalConfig.value });
    return () => [
      h(RegularProbe),
      h(LazyProbe),
      h(Teleport, { to: '#overlay' }, h(OverlayProbe)),
      h(LocalProviderProbe, null, () => h(LocalProbe)),
    ];
  },
});

renderer.createApp(RootProbe).mount(hostNode());
await Promise.resolve();
await new Promise((resolve) => setTimeout(resolve, 0));
await nextTick();
assert.deepEqual(providerEvidence.regular, { include: [], exclude: ['ripple', 'expand', 'fade'] });
assert.deepEqual(providerEvidence.lazy, { include: [], exclude: ['ripple', 'expand', 'fade'] });
assert.deepEqual(providerEvidence.overlay, { include: [], exclude: ['ripple', 'expand', 'fade'] });
assert.deepEqual(providerEvidence.local, { include: ['fade'], exclude: [] });

console.log('[global_component_capability_test] PASS tests=16');
