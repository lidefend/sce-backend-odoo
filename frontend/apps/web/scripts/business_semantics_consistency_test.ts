import assert from 'node:assert/strict';
import {
  formatBusinessPercentage,
  formatMonetaryDisplayValue,
  presentDeclaredBusinessValue,
  statusBadgeSemantic,
} from '../src/app/presentation/businessValuePresentation';
import { presentCollectionKanbanCell } from '../src/app/presentation/collectionKanbanPresentation';
import { formatProductMyWorkFact } from '../src/app/presentation/productMyWorkPresentation';
import { FIELD_VALUE_EMPTY_TEXT } from '../src/utils/fieldSemantics';
import { presentListCell } from '../src/pages/listPage/listCellPresentation';

const moneyField = {
  name: 'unrelated_value',
  type: 'monetary',
  componentKey: 'sc.value.money',
  digits: [20, 2] as [number, number],
  currencyField: 'currency_id',
};
const money = presentDeclaredBusinessValue({
  field: moneyField,
  value: 1234.5,
  currencyLabel: 'CNY',
  emptyText: FIELD_VALUE_EMPTY_TEXT,
});
assert.deepEqual(money, {
  kind: 'money',
  text: '¥1,234.50',
  tone: 'neutral',
  badgeSemantic: 'default',
});
assert.equal(formatMonetaryDisplayValue(1234.5, moneyField.digits, 'CNY'), money.text);
assert.equal(presentCollectionKanbanCell({
  field: 'opaque_value',
  value: 1234.5,
  row: { currency_id: [1, 'CNY'] },
  statusFields: [],
  columnOptions: [{
    name: 'opaque_value',
    type: 'monetary',
    componentKey: 'sc.value.money',
    digits: [20, 2],
    currencyField: 'currency_id',
  }],
}).text, money.text);

const amountNamedText = presentDeclaredBusinessValue({
  field: { name: 'amount_total_note', type: 'char', componentKey: 'sc.input.text' },
  value: '1234.5',
});
assert.equal(amountNamedText.kind, 'plain');
assert.equal(amountNamedText.text, '1234.5', 'field names never infer monetary identity');
assert.equal(presentCollectionKanbanCell({
  field: 'amount_total_note',
  value: '1234.5',
  statusFields: [],
  columnOptions: [{ name: 'amount_total_note', type: 'char', componentKey: 'sc.input.text' }],
}).text, '1234.5', 'Kanban never infers money from a field name');

const rateNamedFloat = presentDeclaredBusinessValue({
  field: { name: 'conversion_rate', type: 'float', componentKey: 'sc.input.number' },
  value: 12.5,
});
assert.equal(rateNamedFloat.kind, 'plain');
assert.equal(rateNamedFloat.text, '12.5', 'field names never infer percentage identity');
assert.equal(presentCollectionKanbanCell({
  field: 'conversion_rate',
  value: 12.5,
  statusFields: [],
  columnOptions: [{ name: 'conversion_rate', type: 'float', componentKey: 'sc.input.number' }],
}).text, '12.5', 'Kanban never infers percentage from a field name');

const declaredPercentage = presentDeclaredBusinessValue({
  field: { name: 'unrelated_ratio', type: 'float', componentKey: 'sc.value.percentage' },
  value: 12.5,
});
assert.equal(declaredPercentage.kind, 'percentage');
assert.equal(declaredPercentage.text, '12.5%');
assert.equal(formatBusinessPercentage(12.5), declaredPercentage.text);

const statusSelection = [
  { value: 'draft', label: '草稿' },
  { value: 'pending', label: '待处理' },
  { value: 'approved', label: '已批准' },
  { value: 'rejected', label: '已驳回' },
] as const;
assert.deepEqual(presentDeclaredBusinessValue({
  field: {
    name: 'opaque_state',
    type: 'selection',
    componentKey: 'sc.display.status',
    selection: statusSelection,
  },
  value: 'pending',
}), {
  kind: 'status',
  text: '待处理',
  tone: 'warning',
  badgeSemantic: 'warning',
});
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'opaque_state',
    type: 'selection',
    componentKey: 'sc.display.status',
    selection: statusSelection,
  },
  value: 'missing',
}), { name: 'ContractGapError' });
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'missing_selection_state',
    type: 'selection',
    componentKey: 'sc.display.status',
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'selection-backed status without selection metadata must fail closed');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'empty_selection_state',
    type: 'selection',
    componentKey: 'sc.display.status',
    selection: [],
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'selection-backed status with empty selection metadata must fail closed');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'datatype_missing_selection_state',
    dataType: 'selection',
    componentKey: 'sc.display.status',
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'dataType-only selection status without selection metadata must fail closed');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'datatype_empty_selection_state',
    dataType: 'selection',
    componentKey: 'sc.display.status',
    selection: [],
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'dataType-only selection status with empty selection metadata must fail closed');
assert.deepEqual(presentDeclaredBusinessValue({
  field: {
    name: 'datatype_selection_state',
    dataType: 'selection',
    componentKey: 'sc.display.status',
    selection: statusSelection,
  },
  value: 'pending',
}), {
  kind: 'status',
  text: '待处理',
  tone: 'warning',
  badgeSemantic: 'warning',
});
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'native_char_over_datatype_status',
    type: 'char',
    dataType: 'selection',
    componentKey: 'sc.display.status',
  },
  value: '待复核',
}).text, '待复核', 'explicit char type must win over conflicting dataType');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'native_selection_over_datatype_status',
    type: 'selection',
    dataType: 'char',
    componentKey: 'sc.display.status',
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'explicit selection type must win over conflicting dataType');
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'readable_char_status',
    type: 'char',
    componentKey: 'sc.display.status',
  },
  value: '待复核',
}).text, '待复核', 'declared char-status keeps its contract-provided readable value');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'cell_role_selection_state',
    type: 'selection',
    cellRole: 'status',
    selection: statusSelection,
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'cellRole=status must reject a value missing from its selection');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'status_without_type',
  },
  value: 'pending_review',
  status: true,
}), { name: 'ContractGapError' }, 'status=true is an identity marker, not a field type declaration');
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'cell_role_char_state',
    type: 'char',
    cellRole: 'status',
  },
  value: '待复核',
}).text, '待复核', 'cellRole=status with explicit char type consumes the readable value');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'component_without_type',
    componentKey: 'sc.display.status',
  },
  value: 'pending_review',
}), { name: 'ContractGapError' }, 'sc.display.status must declare selection or char field type');
assert.equal(statusBadgeSemantic('approved'), 'success');
assert.equal(statusBadgeSemantic('rejected'), 'danger');
assert.equal(presentCollectionKanbanCell({
  field: 'opaque_state',
  value: 'pending',
  statusFields: ['opaque_state'],
  fieldSelections: { opaque_state: [...statusSelection] },
  columnOptions: [{
    name: 'opaque_state',
    type: 'selection',
    selection: [...statusSelection],
  }],
}).badgeSemantic, 'warning');

const dateValue = '2026-09-09T08:30:45Z';
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'business_date', type: 'date' },
  value: dateValue,
  temporalProfile: 'compact',
}).text, '2026-09-09');
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'business_datetime', type: 'datetime' },
  value: dateValue,
  temporalProfile: 'full',
}).text, '2026-09-09 08:30:45');
assert.equal(presentCollectionKanbanCell({
  field: 'business_datetime',
  value: dateValue,
  columnOptions: [{ name: 'business_datetime', type: 'datetime' }],
}).text, '2026-09-09 08:30');

assert.equal(presentDeclaredBusinessValue({
  field: moneyField,
  value: null,
}).text, FIELD_VALUE_EMPTY_TEXT);
assert.equal(presentListCell({
  raw: null,
  column: { field: 'amount', label: '金额', type: 'monetary', cellRole: 'money' },
  numeric: true,
}).text, FIELD_VALUE_EMPTY_TEXT, 'missing list amounts are not business zeroes');
assert.deepEqual(presentListCell({
  raw: 'pending',
  column: { field: 'opaque_state', label: '状态', type: 'selection', cellRole: 'status' },
  selectionText: '待处理',
}), {
  text: '待处理',
  tone: 'warning',
});
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'generated_value', componentKey: 'sc.input.text' },
  value: null,
  emptyText: '尚未生成',
}).text, '尚未生成');

assert.equal(formatProductMyWorkFact({
  key: 'amount',
  label: '金额',
  display_role: 'money',
  money: { value: 50, currency: 'CNY', digits: 2 },
}), '¥50.00');
assert.equal(formatProductMyWorkFact({
  key: 'created_at',
  label: '创建时间',
  display_role: 'datetime',
  value: dateValue,
}), '2026-09-09 08:30');
assert.equal(formatProductMyWorkFact({
  key: 'empty',
  label: '空值',
  display_role: 'text',
}), FIELD_VALUE_EMPTY_TEXT);

console.log('[business_semantics_consistency_test] PASS money=6 status=17 temporal=4 empty=3');
