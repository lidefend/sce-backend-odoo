import assert from 'node:assert/strict';
import {
  SC_PRIMITIVE_KEYS,
  normalizePrimitiveSize,
  normalizePrimitiveStatus,
  resolvePrimitiveControlUpdate,
  semanticPrimitiveIdentity,
  tdesignButtonPresentation,
  tdesignDropdownOptions,
  tdesignTabsSize,
} from '../src/components/design-system/primitiveAdapter.ts';
import { resolveModalKeyboardAction } from '../src/composables/modalKeyboard.ts';

const expected = [
  'ScActionBar', 'ScIconButton', 'ScLayout', 'ScAside', 'ScHeader', 'ScContent', 'ScButton', 'ScCheckbox', 'ScRadioGroup', 'ScRadio', 'ScInput', 'ScInputGroup', 'ScInlineState', 'ScTextarea', 'ScSelect', 'ScDialog', 'ScDrawer', 'ScTabs', 'ScTable',
  'ScBadge', 'ScTooltip', 'ScDropdown', 'ScFormField', 'ScLoading', 'ScEmptyState', 'ScErrorState',
  'ScAutoComplete', 'ScNumberInput', 'ScSwitch', 'ScDatePicker', 'ScTimePicker', 'ScUpload', 'ScForm', 'ScFormItem', 'ScCard', 'ScCollapse',
  'ScDisclosure', 'ScProgress', 'ScSkeleton', 'ScDescriptions', 'ScList', 'ScTimeline', 'ScSteps', 'ScPagination', 'ScPopconfirm',
];

assert.deepEqual([...SC_PRIMITIVE_KEYS], expected, 'Phase 2 primitive API must remain explicit and ordered');
assert.equal(normalizePrimitiveSize(), 'medium');
assert.equal(normalizePrimitiveSize('small'), 'small');
assert.equal(normalizePrimitiveStatus(), 'default');
assert.equal(normalizePrimitiveStatus('error'), 'error');
assert.equal(resolvePrimitiveControlUpdate({ value: 'next' }), 'next');
assert.equal(resolvePrimitiveControlUpdate({ value: 7 }), '7');
assert.equal(resolvePrimitiveControlUpdate({ value: 'blocked', disabled: true }), null);
assert.equal(resolvePrimitiveControlUpdate({ value: 'blocked', readonly: true }), null);
assert.equal(resolvePrimitiveControlUpdate({ value: 'blocked', loading: true }), null);
assert.equal(tdesignTabsSize('small'), 'medium');
assert.equal(tdesignTabsSize('medium'), 'medium');
assert.equal(tdesignTabsSize('large'), 'large');
assert.deepEqual(tdesignButtonPresentation('primary'), { theme: 'primary', variant: 'base' });
assert.deepEqual(tdesignButtonPresentation('secondary'), { theme: 'default', variant: 'outline' });
assert.deepEqual(tdesignButtonPresentation('ghost'), { theme: 'default', variant: 'text' });
assert.deepEqual(tdesignButtonPresentation('danger'), { theme: 'danger', variant: 'base' });
assert.deepEqual(tdesignButtonPresentation('secondary', 'success'), { theme: 'success', variant: 'base' });
assert.deepEqual(tdesignButtonPresentation('ghost', 'warning'), { theme: 'warning', variant: 'text' });
assert.deepEqual(tdesignButtonPresentation('primary', 'error'), { theme: 'danger', variant: 'base' });
assert.deepEqual(tdesignDropdownOptions([
  { value: 'open', label: 'Open' },
  { value: 2, label: 'Disabled', disabled: true },
]), [
  { value: 'open', content: 'Open', disabled: false },
  { value: 2, content: 'Disabled', disabled: true },
]);

for (const key of SC_PRIMITIVE_KEYS) {
  assert.deepEqual(semanticPrimitiveIdentity(key), {
    'data-semantic-component': key,
    'data-semantic-layer': 'primitive',
  });
}

assert.equal(resolveModalKeyboardAction({ key: 'Escape', shiftKey: false, focusableCount: 2, activeIndex: 0, surfaceActive: false }), 'close');
assert.equal(resolveModalKeyboardAction({ key: 'Tab', shiftKey: false, focusableCount: 0, activeIndex: -1, surfaceActive: true }), 'focus-surface');
assert.equal(resolveModalKeyboardAction({ key: 'Tab', shiftKey: true, focusableCount: 2, activeIndex: 0, surfaceActive: false }), 'focus-last');
assert.equal(resolveModalKeyboardAction({ key: 'Tab', shiftKey: false, focusableCount: 2, activeIndex: 1, surfaceActive: false }), 'focus-first');
assert.equal(resolveModalKeyboardAction({ key: 'Enter', shiftKey: false, focusableCount: 2, activeIndex: 1, surfaceActive: false }), 'none');

console.log(`[primitive_adapter_contract_test] PASS components=${SC_PRIMITIVE_KEYS.length}`);
