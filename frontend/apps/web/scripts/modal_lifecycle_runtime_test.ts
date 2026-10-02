import assert from 'node:assert/strict';
import { createRenderer, defineComponent, h, nextTick, ref, shallowRef } from 'vue';
import { useModalLifecycle } from '../src/composables/useModalLifecycle';

// Real Vue watch/mount/unmount scheduling, with only the browser platform faked.
// These checks prove hook behavior, not TDesign rendering or browser geometry.
class ElementStub {
  readonly __v_skip = true;
  parent: ElementStub | null = null;
  children: ElementStub[] = [];
  attrs: Record<string, unknown> = {};
  style = { overflow: '', paddingRight: '' };
  isConnected = true;
  visible = true;
  focusCount = 0;
  text = '';
  constructor(public tag: string) {}
  focus() { if (this.isConnected) { documentStub.activeElement = this; this.focusCount += 1; } }
  contains(target: unknown): boolean { return target === this || this.children.some(child => child.contains(target)); }
  getClientRects() { return this.visible && this.isConnected ? [{}] : []; }
  getAttribute(name: string) { return this.attrs[name] ?? null; }
  descendants(): ElementStub[] { return this.children.flatMap(child => [child, ...child.descendants()]); }
  querySelector(selector: string) { void selector; return this.descendants().find(child => 'autofocus' in child.attrs || 'data-dialog-primary' in child.attrs) || null; }
  querySelectorAll(selector: string) { void selector; return this.descendants().filter(child => child.tag === 'button' && !child.attrs.disabled); }
}
const documentStub = {
  activeElement: null as ElementStub | null,
  body: new ElementStub('body'),
  documentElement: { clientWidth: 980 },
};
let frameId = 0;
const frames = new Map<number, FrameRequestCallback>();
const savedGlobals = new Map<string, PropertyDescriptor | undefined>();
for (const [name, value] of Object.entries({
  HTMLElement: ElementStub, document: documentStub, window: { innerWidth: 1000 },
  requestAnimationFrame: (callback: FrameRequestCallback) => { frames.set(++frameId, callback); return frameId; },
})) {
  savedGlobals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
  Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
}
function drainFrames() {
  let rounds = 0;
  while (frames.size) {
    assert.ok(++rounds < 130, 'animation callbacks must terminate');
    const pending = [...frames.values()]; frames.clear();
    pending.forEach(callback => callback(0));
  }
}
async function settle() { await nextTick(); await nextTick(); }
const renderer = createRenderer<ElementStub, ElementStub>({
  createElement: tag => new ElementStub(tag),
  createText: text => Object.assign(new ElementStub('#text'), { text }),
  createComment: text => Object.assign(new ElementStub('#comment'), { text }),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; },
  parentNode: node => node.parent,
  nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
  patchProp: (node, key, _previous, value) => { node.attrs[key] = value; },
  insert(node, parent, anchor) {
    node.parent = parent; node.isConnected = true;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index < 0) parent.children.push(node); else parent.children.splice(index, 0, node);
  },
  remove(node) {
    for (const removed of [node, ...node.descendants()]) removed.isConnected = false;
    if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1);
    node.parent = null;
  },
});
function mountModal(initialOpen = true, existingSurface: ElementStub | null = null) {
  const open = ref(initialOpen);
  const dismissible = ref(true);
  const surface = shallowRef<HTMLElement | null>(existingSurface as unknown as HTMLElement | null);
  let closeCount = 0;
  let keydown: (event: KeyboardEvent) => void;
  const app = renderer.createApp(defineComponent({
    setup() {
      ({ onKeydown: keydown } = useModalLifecycle({
        open: () => open.value, surface, closeOnEscape: () => dismissible.value,
        close: () => { closeCount += 1; open.value = false; },
      }));
      return () => open.value ? h('section', { ref: surface }, [h('button', { 'data-dialog-primary': true }), h('button')]) : null;
    },
  }));
  app.mount(new ElementStub('root'));
  return { open, surface, dismissible, unmount: () => app.unmount(), closeCount: () => closeCount,
    key(key: string, shiftKey = false) {
      let prevented = 0; let stopped = 0;
      keydown!({ key, shiftKey, preventDefault: () => { prevented += 1; }, stopPropagation: () => { stopped += 1; } } as unknown as KeyboardEvent);
      return { prevented, stopped };
    },
  };
}
let checks = 0;
function equal(actual: unknown, expected: unknown, message: string) { assert.deepEqual(actual, expected, message); checks += 1; }
function opener() { const node = new ElementStub('button'); node.focus(); return node; }
try {
  documentStub.body.style.overflow = 'auto'; documentStub.body.style.paddingRight = '7px';
  const first = opener(); const modal = mountModal(); await settle(); drainFrames();
  equal(documentStub.activeElement, (modal.surface.value as unknown as ElementStub).children[0], 'mounted dialog focuses primary');
  equal(documentStub.body.style, { overflow: 'hidden', paddingRight: '20px' }, 'opening locks scroll with scrollbar compensation');
  modal.open.value = false; await settle(); drainFrames();
  equal(documentStub.activeElement, first, 'normal close restores captured opener');
  equal(documentStub.body.style, { overflow: 'auto', paddingRight: '7px' }, 'close restores exact original styles');
  modal.unmount();

  const original = opener(); const rapid = mountModal(); await settle(); drainFrames();
  rapid.open.value = false; await settle();
  equal(frames.size > 0, true, 'close has queued restoration frames');
  const replacement = opener(); rapid.open.value = true; await settle();
  const reopenedPrimary = (rapid.surface.value as unknown as ElementStub).children[0];
  const beforeOldFrames = original.focusCount;
  drainFrames();
  equal(documentStub.activeElement, reopenedPrimary, 'old close frames cannot steal focus from reopened dialog');
  equal(original.focusCount, beforeOldFrames, 'obsolete target is never refocused');
  rapid.open.value = false; await settle(); drainFrames();
  equal(documentStub.activeElement, replacement, 'old restore cannot clear the new opener');
  rapid.unmount();

  opener(); const preexisting = new ElementStub('section');
  const pendingInitial = mountModal(true, preexisting);
  pendingInitial.unmount(); const outside = opener(); await settle(); drainFrames();
  equal(documentStub.activeElement, outside, 'unmount before awaited nextTick cannot schedule initial focus');
  equal(preexisting.focusCount, 0, 'awaited initial focus does not run after disposal');
  equal(documentStub.body.style.overflow, 'auto', 'unmount releases its lock');

  const restoreTarget = opener(); const disposing = mountModal(); await settle(); drainFrames();
  disposing.open.value = false; await settle();
  disposing.unmount(); const afterDispose = opener(); const targetCount = restoreTarget.focusCount;
  drainFrames();
  equal(documentStub.activeElement, afterDispose, 'unmount invalidates queued restoration');
  equal(restoreTarget.focusCount, targetCount, 'disposed restore does not focus captured target');

  const removed = opener(); const removedModal = mountModal(); await settle(); drainFrames();
  removed.isConnected = false; removedModal.open.value = false; await settle();
  const safeFocus = opener(); drainFrames();
  equal(documentStub.activeElement, safeFocus, 'disconnected opener is ignored');
  removedModal.unmount();

  const outerOpener = opener(); const outer = mountModal(); await settle(); drainFrames();
  const outerPrimary = documentStub.activeElement;
  const inner = mountModal(); await settle(); drainFrames();
  inner.open.value = false; await settle(); drainFrames();
  equal(documentStub.body.style.overflow, 'hidden', 'closing nested overlay retains outer scroll lock');
  equal(documentStub.activeElement, outerPrimary, 'nested close restores outer focused element');
  inner.unmount();
  equal(documentStub.body.style.overflow, 'hidden', 'closed nested unmount cannot decrement lock twice');
  outer.open.value = false; await settle(); drainFrames();
  equal(documentStub.activeElement, outerOpener, 'outer close restores page opener');
  equal(documentStub.body.style, { overflow: 'auto', paddingRight: '7px' }, 'last lock restores initial styles');
  outer.unmount();

  opener(); const keyboard = mountModal(); await settle(); drainFrames();
  const keySurface = keyboard.surface.value as unknown as ElementStub;
  keySurface.children[1].focus();
  equal(keyboard.key('Tab').prevented, 1, 'forward Tab at last item is trapped');
  equal(documentStub.activeElement, keySurface.children[0], 'Tab wraps to first');
  keyboard.key('Tab', true);
  equal(documentStub.activeElement, keySurface.children[1], 'Shift-Tab wraps to last');
  keyboard.dismissible.value = false;
  equal(keyboard.key('Escape'), { prevented: 0, stopped: 0 }, 'non-dismissible escape remains untouched');
  equal(keyboard.closeCount(), 0, 'non-dismissible escape never closes');
  keyboard.dismissible.value = true;
  equal(keyboard.key('Escape'), { prevented: 1, stopped: 1 }, 'dismissible escape is handled once');
  equal(keyboard.closeCount(), 1, 'escape invokes exactly one close');
  await settle(); drainFrames(); keyboard.unmount();
  equal(documentStub.body.style.overflow, 'auto', 'keyboard close leaves no lock');
  console.log(`[modal_lifecycle_runtime_test] PASS checks=${checks} actual_hook=true actual_vue_lifecycle=true browser_platform=stubbed`);
} finally {
  for (const [name, descriptor] of savedGlobals) {
    if (descriptor) Object.defineProperty(globalThis, name, descriptor);
    else Reflect.deleteProperty(globalThis, name);
  }
}
