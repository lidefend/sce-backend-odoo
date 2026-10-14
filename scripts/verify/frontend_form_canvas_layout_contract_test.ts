import assert from 'node:assert/strict';
import {
  declaredLayoutSpan,
  requireDeclaredLayoutColumns,
  containedFieldLayout,
  isDeclaredLayoutSpan,
  layoutGridUnits,
  requireDeclaredLayoutSpan,
} from '../../frontend/apps/web/src/components/template/layoutSpan.ts';
import { isContractGapError } from '../../frontend/apps/web/src/app/contract/contractGap.ts';
import { nativeFieldPresentation } from '../../frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts';

let cases = 0;
const expectEqual = (actual: unknown, expected: unknown, message?: string): void => {
  cases += 1;
  assert.equal(actual, expected, message);
};
const expectThrows = (run: () => unknown, ctor: unknown, message?: string): void => {
  cases += 1;
  assert.throws(run, ctor as never, message);
};

// The single renderer-facing layout unit.  The projection folds the native arch
// `col` / `col-*` and the low-code `columns` / `field_size` into one `span` on a
// 24-unit grid, and the renderer consumes that number only: it must never map a
// field type to a width class (`field--normal` etc. used to live here).
expectEqual(layoutGridUnits(), 24);

const declared = [1, 6, 8, 12, 16, 23, 24];
for (const span of declared) {
  expectEqual(isDeclaredLayoutSpan(span), true, `declared ${span}`);
  expectEqual(declaredLayoutSpan(span), span, `declared span ${span}`);
  expectEqual(requireDeclaredLayoutSpan(span), span, `required span ${span}`);
}

function assertGap(value: unknown, label: string) {
  expectEqual(isDeclaredLayoutSpan(value), false, `undeclared ${label}`);
  expectThrows(() => declaredLayoutSpan(value), isContractGapError, `missing declaration must stop: ${label}`);
}

// A missing or malformed declaration is a contract defect: the renderer stops
// instead of coercing it to the full grid width.  A `true` used to become a
// 1-wide field and a malformed value used to become a full row.
const undeclared = [undefined, null, 0, -1, 25, 12.5, 'wide', '8', '', NaN, true, {}];
for (const value of undeclared) assertGap(value, JSON.stringify(value) ?? String(value));

const presentation = (node: Record<string, unknown>, editable = false): { span: number } =>
  nativeFieldPresentation({ node: node as never, editable, effectiveFieldSize: () => 'normal' });

// A projected node carries its declared span, and the renderer passes it through.
for (const span of [6, 8, 12, 16, 24]) {
  expectEqual(presentation({ name: 'amount', span }).span, span, `projected span ${span}`);
}
// Without a declared span the node stops, including one that only carries a
// legacy width class name: a class name is not a declared width.
expectThrows(() => presentation({ name: 'amount' }), isContractGapError, 'missing span must stop');
expectThrows(() => presentation({ name: 'amount', class: 'field--compact' }), isContractGapError, 'class name must stop');
// The low-code size facet is a declaration rather than a class name, so the field
// configuration preview still resolves through the same unit.
expectEqual(presentation({ name: 'amount', field_size: 'compact' }).span, 8);
expectEqual(presentation({ name: 'amount', field_size: 'wide' }).span, 16);
expectEqual(presentation({ name: 'amount', field_size: 'half' }).span, 12);
expectEqual(presentation({ name: 'amount', field_size: 'normal' }).span, 12);
// An unrecognised facet is a contract defect, not the editor's `normal` default.
expectThrows(() => presentation({ name: 'amount', field_size: 'nonsense' }), isContractGapError, 'unknown facet must stop');
expectThrows(() => presentation({ name: 'amount', field_size: '' }), isContractGapError, 'empty facet must stop');
// The editable field-order preview resolves through the editor's own size, which
// is not a contract declaration, so it never reaches the span gap.
expectEqual(presentation({ name: 'amount' }, true).span, 12);

for (const count of [1, 2, 3, 4, 6, 8, 12, 24]) expectEqual(requireDeclaredLayoutColumns(count), count);
for (const count of [undefined, null, false, '2', 0, -1, 1.5, 5, 7, 25]) {
  expectThrows(() => requireDeclaredLayoutColumns(count), isContractGapError);
}
expectEqual(containedFieldLayout().columns, 1);
expectEqual(containedFieldLayout().span, 24);

console.log(
  `[frontend_form_canvas_layout_contract_test] PASS cases=${cases} declared=${declared.length} undeclared=${undeclared.length} facets=3`,
);
