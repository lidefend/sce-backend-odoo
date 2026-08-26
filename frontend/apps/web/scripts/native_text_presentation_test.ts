import assert from 'node:assert/strict';
import { resolveNativeTextPresentation } from '../src/components/template/nativeTextPresentation';

assert.deepEqual(resolveNativeTextPresentation({}), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label' } }), { kind: 'inline', tone: 'neutral' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'o_form_label text-danger' } }), { kind: 'inline', tone: 'danger' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'alert alert-info', role: 'alert' } }), { kind: 'callout', tone: 'info', role: 'alert' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'alert alert-warning' } }), { kind: 'callout', tone: 'warning', role: 'alert' });
assert.deepEqual(resolveNativeTextPresentation({ className: 'alert alert-danger' }), { kind: 'callout', tone: 'danger', role: 'alert' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { class: 'alert alert-success' } }), { kind: 'callout', tone: 'success', role: 'alert' });
assert.deepEqual(resolveNativeTextPresentation({ attributes: { role: 'alert' } }), { kind: 'callout', tone: 'info', role: 'alert' });

console.log('[native_text_presentation_test] PASS cases=8');
