import assert from 'node:assert/strict';
import {
  assertNativePresentationConsumption,
  LEGACY_NATIVE_ALERT_TOKENS,
  resolveNativeTextPresentation,
} from '../src/components/template/nativeTextPresentation';

assert.deepEqual(resolveNativeTextPresentation({}), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label' } }), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label text-danger' } }), { kind: 'inline', tone: 'danger' });
assert.deepEqual(
  resolveNativeTextPresentation({ attributes: { role: 'status' } }),
  { kind: 'inline', tone: 'neutral', role: 'status' },
);

for (const token of LEGACY_NATIVE_ALERT_TOKENS) {
  const node = {
    containerId: `legacy-${token}`,
    attributes: { class: `new-unregistered-topic ${token}` },
  };
  assert.throws(
    () => assertNativePresentationConsumption(node),
    (error: unknown) => {
      const gap = error as Error & { defect?: { missing?: string } };
      assert.equal(gap.name, 'ContractGapError');
      assert.match(gap.message, new RegExp(`token:${token}`));
      assert.match(gap.message, new RegExp(`container:legacy-${token}`));
      assert.match(String(gap.defect?.missing), new RegExp(`token:${token}`));
      return true;
    },
  );
  assert.throws(() => resolveNativeTextPresentation({ text: 'must not leak', ...node }), { name: 'ContractGapError' });
}

assert.throws(
  () => resolveNativeTextPresentation({
    containerId: 'legacy-role-alert',
    attributes: { role: 'alert' },
  }),
  (error: unknown) => {
    const gap = error as Error;
    assert.match(gap.message, /role:alert/);
    assert.match(gap.message, /container:legacy-role-alert/);
    assert.doesNotMatch(gap.message, /must not leak/);
    return true;
  },
);

const explicitFeedback = {
  containerId: 'explicit-feedback',
  attributes: { class: 'alert alert-info', role: 'status' },
  nodeComponent: { kind: 'feedback', purpose: 'advisory', content: 'Owned', visible: true, role: 'status' },
};
const explicitAnchor = {
  containerId: 'explicit-anchor',
  attributes: { class: 'alert-link', role: 'button' },
  nodeComponent: { kind: 'anchor', content: 'Open', visible: true, targetContainerId: 'target' },
};
assert.doesNotThrow(() => assertNativePresentationConsumption(explicitFeedback));
assert.doesNotThrow(() => assertNativePresentationConsumption(explicitAnchor));

console.log(`[native_text_presentation_test] PASS cases=${7 + LEGACY_NATIVE_ALERT_TOKENS.length * 2 + 4}`);
