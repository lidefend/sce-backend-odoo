import assert from 'node:assert/strict';
import { resolveNativeTextPresentation } from '../src/components/template/nativeTextPresentation';

assert.deepEqual(resolveNativeTextPresentation({}), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label' } }), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label text-danger' } }), { kind: 'inline', tone: 'danger' });
for (const node of [
  { attributes: { class: 'alert alert-info', role: 'alert' } },
  { attributes: { class: 'new-unregistered-topic alert alert-warning' } },
  { className: 'alert alert-danger' },
  { attributes: { class: 'alert alert-success' } },
  { attributes: { role: 'alert' } },
]) assert.throws(() => resolveNativeTextPresentation(node), { name: 'ContractGapError' });
console.log('[native_text_presentation_test] PASS cases=8');
