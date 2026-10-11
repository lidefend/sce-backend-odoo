import assert from 'node:assert/strict';
import {
  declaredLayoutSpan,
  isDeclaredLayoutSpan,
  layoutGridUnits,
} from '../../frontend/apps/web/src/components/template/layoutSpan.ts';
import { nativeFieldPresentation } from '../../frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts';

// The single renderer-facing layout unit.  The projection folds the native arch
// `col` / `col-*` and the low-code `columns` / `field_size` into one `span` on a
// 24-unit grid, and the renderer consumes that number only: it must never map a
// field type to a width class (`field--normal` etc. used to live here).
assert.equal(layoutGridUnits(), 24);

const declared = [1, 6, 8, 12, 16, 23, 24];
for (const span of declared) {
  assert.equal(isDeclaredLayoutSpan(span), true, `declared ${span}`);
  assert.equal(declaredLayoutSpan(span), span, `declared span ${span}`);
}

// A missing or malformed declaration fails closed to the full grid width instead
// of being coerced into a plausible one: a `true` used to become a 1-wide field.
const undeclared = [undefined, null, 0, -1, 25, 12.5, 'wide', '8', '', NaN, true, {}];
for (const value of undeclared) {
  assert.equal(isDeclaredLayoutSpan(value), false, `undeclared ${String(value)}`);
  assert.equal(declaredLayoutSpan(value), 24, `undeclared span ${JSON.stringify(value)}`);
}

const presentation = (node: Record<string, unknown>, editable = false): { span: number } =>
  nativeFieldPresentation({ node: node as never, editable, effectiveFieldSize: () => 'normal' });

// A projected node carries its declared span, and the renderer passes it through.
for (const span of [6, 8, 12, 16, 24]) {
  assert.equal(presentation({ name: 'amount', span }).span, span, `projected span ${span}`);
}
// Without a declared span the node fails closed, including one that only carries
// a legacy width class name: a class name is not a declared width.
assert.equal(presentation({ name: 'amount' }).span, 24);
assert.equal(presentation({ name: 'amount', class: 'field--compact' }).span, 24);
// The low-code size facet is a declaration rather than a class name, so the field
// configuration preview still resolves through the same unit.
assert.equal(presentation({ name: 'amount', field_size: 'compact' }).span, 8);
assert.equal(presentation({ name: 'amount', field_size: 'wide' }).span, 16);
assert.equal(presentation({ name: 'amount', field_size: 'half' }).span, 12);
assert.equal(presentation({ name: 'amount', field_size: 'normal' }).span, 12);
// An unrecognised facet is a contract defect, not the editor's `normal` default.
assert.equal(presentation({ name: 'amount', field_size: 'nonsense' }).span, 24);
assert.equal(presentation({ name: 'amount', field_size: '' }).span, 24);

console.log(
  `[frontend_form_canvas_layout_contract_test] PASS declared=${declared.length} undeclared=${undeclared.length} facets=3`,
);
