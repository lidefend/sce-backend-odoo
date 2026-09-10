import assert from 'node:assert/strict';
import { createRenderer, defineAsyncComponent, defineComponent, h, nextTick, ref, Teleport } from 'vue';
import { useConfig } from '../../../packages/ui/node_modules/tdesign-vue-next/es/config-provider/hooks/useConfig.mjs';
import { TDesignConfigProvider, TDesignTag } from '../src/components/design-system/tdesignPrimitiveBridge.ts';

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

const theme = await import('../src/styles/theme.ts');
const componentConfig = await import('../src/styles/tdesignGlobalConfig.ts');
const applicationRuntime = await import('../src/styles/themeApplicationRuntime.ts');

theme.bootTheme();
applicationRuntime.startThemeApplicationRuntime();
assert.equal(darkMedia.addCount, 1, 'system theme listener must be application-singleton');
assert.equal(motionMedia.addCount, 1, 'reduced motion listener must be application-singleton');
assert.equal(attributes.get('data-sc-theme'), 'light');
assert.equal(attributes.get('data-sc-reduced-motion'), 'no-preference');
assert.deepEqual(componentConfig.tdesignGlobalConfig.value, { animation: { include: ['ripple', 'expand', 'fade'], exclude: [] } }, 'normal motion must explicitly restore the audited official animation defaults');

type HostNode = {
  children: HostNode[];
  parent: HostNode | null;
  props: Record<string, unknown>;
  text?: string;
  type?: string;
};
const hostNode = (type?: string): HostNode => ({ children: [], parent: null, props: {}, type });
const teleportTarget = hostNode('teleport-target');
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
  querySelector: () => teleportTarget,
  setScopeId: () => {},
  cloneNode: (node) => ({ ...node, children: [...node.children], props: { ...node.props }, parent: null }),
  insertStaticContent: () => {
    const node = hostNode('static');
    return [node, node];
  },
});

const normalAnimation = { include: ['ripple', 'expand', 'fade'], exclude: [] };
const reducedAnimation = { include: [], exclude: ['ripple', 'expand', 'fade'] };
const localAnimation = { include: ['fade'], exclude: [] };
const routeChildVisible = ref(true);

function capabilityProbe(name: string) {
  return defineComponent({
    name: `${name}CapabilityProbe`,
    setup() {
      const { globalConfig } = useConfig('animation');
      return () => h('section', {
        'data-capability-probe': name,
        'data-animation-config': JSON.stringify(globalConfig.value),
      }, [
        h(TDesignTag, { 'data-official-component-probe': name }, () => `${name}:${globalConfig.value.exclude?.join(',') || 'default'}`),
      ]);
    },
  });
}

const RegularProbe = capabilityProbe('regular');
const LazyProbe = defineAsyncComponent(async () => capabilityProbe('lazy'));
const OverlayProbe = capabilityProbe('overlay');
const LocalProbe = capabilityProbe('local');
const RouteChild = defineComponent({ setup: () => () => h('span', { 'data-route-child': 'mounted' }) });
const LocalProviderProbe = defineComponent({
  setup(_props, { slots }) {
    return () => h(TDesignConfigProvider, { globalConfig: { animation: localAnimation } }, slots);
  },
});
const RootProbe = defineComponent({
  setup() {
    applicationRuntime.useThemeApplicationRuntime();
    return () => h(TDesignConfigProvider, { globalConfig: componentConfig.tdesignGlobalConfig.value }, () => [
      h(RegularProbe),
      h(LazyProbe),
      h(Teleport, { to: '#overlay' }, h(OverlayProbe)),
      h(LocalProviderProbe, null, () => h(LocalProbe)),
      routeChildVisible.value ? h(RouteChild) : null,
    ]);
  },
});

function descendants(root: HostNode): HostNode[] {
  return root.children.flatMap((child) => [child, ...descendants(child)]);
}

function probe(root: HostNode, name: string): HostNode {
  const match = descendants(root).find((node) => node.props['data-capability-probe'] === name);
  assert.ok(match, `${name} capability probe must be rendered`);
  return match;
}

function animation(root: HostNode, name: string): Record<string, string[]> {
  return JSON.parse(String(probe(root, name).props['data-animation-config'] || '{}'));
}

async function settleAsyncComponents() {
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
}

const root = hostNode('root');
const app = renderer.createApp(RootProbe);
app.mount(root);
await settleAsyncComponents();

assert.deepEqual(animation(root, 'regular'), normalAnimation);
assert.deepEqual(animation(root, 'lazy'), normalAnimation);
assert.deepEqual(animation(teleportTarget, 'overlay'), normalAnimation);
assert.deepEqual(animation(root, 'local'), localAnimation);
const officialTags = [...descendants(root), ...descendants(teleportTarget)]
  .filter((node) => typeof node.props['data-official-component-probe'] === 'string');
assert.equal(officialTags.length, 4, 'all consumers must render a real TDesign component');
assert.ok(officialTags.every((node) => String(node.props.class || '').includes('t-tag')), 'public TDesign Tag rendering must be observable');

darkMedia.dispatch(true);
assert.equal(attributes.get('data-sc-theme'), 'dark', 'system theme changes must update the shared root');
motionMedia.dispatch(true);
await nextTick();
assert.equal(attributes.get('data-sc-reduced-motion'), 'reduce');
assert.deepEqual(animation(root, 'regular'), reducedAnimation);
assert.deepEqual(animation(root, 'lazy'), reducedAnimation);
assert.deepEqual(animation(teleportTarget, 'overlay'), reducedAnimation);
assert.deepEqual(animation(root, 'local'), localAnimation, 'nested explicit config must remain authoritative');

motionMedia.dispatch(false);
await nextTick();
assert.equal(attributes.get('data-sc-reduced-motion'), 'no-preference');
assert.deepEqual(animation(root, 'regular'), normalAnimation, 'regular consumer must restore official defaults');
assert.deepEqual(animation(root, 'lazy'), normalAnimation, 'async consumer must restore official defaults');
assert.deepEqual(animation(teleportTarget, 'overlay'), normalAnimation, 'Teleport consumer must restore official defaults');
assert.deepEqual(animation(root, 'local'), localAnimation, 'local override must survive root recovery');

routeChildVisible.value = false;
await nextTick();
routeChildVisible.value = true;
await nextTick();
assert.equal(darkMedia.addCount, 1, 'route switches must not duplicate the system theme listener');
assert.equal(motionMedia.addCount, 1, 'route switches must not duplicate the reduced-motion listener');

app.unmount();
assert.equal(darkMedia.removeCount, 1, 'application unmount must release the system theme listener');
assert.equal(motionMedia.removeCount, 1, 'application unmount must release the reduced-motion listener');
motionMedia.dispatch(true);
assert.deepEqual(componentConfig.tdesignGlobalConfig.value, { animation: normalAnimation }, 'disposed config subscription must ignore later media changes');

const remountRoot = hostNode('remount-root');
const remountApp = renderer.createApp(RootProbe);
remountApp.mount(remountRoot);
await settleAsyncComponents();
assert.equal(darkMedia.addCount, 2, 'root remount must restore the system theme listener once');
assert.equal(motionMedia.addCount, 2, 'root remount must restore the reduced-motion listener once');
assert.deepEqual(animation(remountRoot, 'regular'), reducedAnimation, 'root remount must resync the current media preference');
remountApp.unmount();
assert.equal(darkMedia.removeCount, 2);
assert.equal(motionMedia.removeCount, 2);

console.log('[global_component_capability_test] PASS tests=31 provider=public dynamic=normal-reduce-normal lifecycle=release-remount');
