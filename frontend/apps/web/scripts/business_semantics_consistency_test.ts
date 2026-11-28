import assert from 'node:assert/strict';
import {
  formatBusinessDuration,
  formatBusinessPercentage,
  formatMonetaryDisplayValue,
  formatMonetaryInputValue,
  monetaryInputStep,
  presentDeclaredBusinessValue,
  statusBadgeSemantic,
} from '../src/app/presentation/businessValuePresentation';
import { presentCollectionKanbanCell } from '../src/app/presentation/collectionKanbanPresentation';
import { presentCollectionKanbanTitle } from '../src/app/presentation/collectionKanbanPresentation';
import { formatProductMyWorkFact } from '../src/app/presentation/productMyWorkPresentation';
import {
  FIELD_VALUE_EMPTY_TEXT,
  formatNumericFieldValue,
  hasDeclaredAttachmentIdentity,
} from '../src/utils/fieldSemantics';
import { isListAttachmentCountColumn, presentListCell } from '../src/pages/listPage/listCellPresentation';
import { formatDisplayValue } from '../src/utils/display';

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
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'localized_title', type: 'char' },
  value: { zh_CN: '合同甲', en_US: 'Contract A' },
  locale: 'zh_CN',
}).text, '合同甲', 'plain text consumes declared locale mappings');
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'localized_title', type: 'char' },
  value: { zh_CN: '合同甲', en_US: 'Contract A' },
  locale: 'en_US',
}).text, 'Contract A', 'plain text selects the requested locale');
assert.throws(
  () => presentDeclaredBusinessValue({
    field: { name: 'plain_object', type: 'char' },
    value: { display_name: '伪装成业务名称' },
  }),
  { name: 'ContractGapError' },
  'plain text must not infer a business label from object shape',
);
assert.throws(
  () => presentDeclaredBusinessValue({
    field: { name: 'plain_array', type: 'char' },
    value: ['伪装成业务列表'],
  }),
  { name: 'ContractGapError' },
  'plain text must not infer a business list from array shape',
);
assert.equal(presentCollectionKanbanCell({
  field: 'amount_total_note',
  value: '1234.5',
  statusFields: [],
  columnOptions: [{ name: 'amount_total_note', type: 'char', componentKey: 'sc.input.text' }],
}).text, '1234.5', 'Kanban never infers money from a field name');

const rateNamedFloat = presentDeclaredBusinessValue({
  field: {
    name: 'conversion_rate',
    type: 'float',
    componentKey: 'sc.input.number',
    digits: [16, 2],
  },
  value: 12.5,
});
assert.equal(rateNamedFloat.kind, 'plain');
assert.equal(rateNamedFloat.text, '12.50', 'field names never infer percentage identity; plain floats consume declared digits');
assert.equal(presentCollectionKanbanCell({
  field: 'conversion_rate',
  value: 12.5,
  statusFields: [],
  columnOptions: [{
    name: 'conversion_rate',
    type: 'float',
    componentKey: 'sc.input.number',
    digits: [16, 2],
  }],
}).text, '12.50', 'Kanban never infers percentage from a field name; plain floats consume declared digits');

const declaredPercentage = presentDeclaredBusinessValue({
  field: {
    name: 'unrelated_ratio',
    type: 'float',
    componentKey: 'sc.value.percentage',
    digits: [16, 4],
    unit: { kind: 'percent', code: 'percent', label: '%' },
  },
  value: 12.5,
});
assert.equal(declaredPercentage.kind, 'percentage');
assert.equal(declaredPercentage.text, '12.5000%');
assert.equal(formatBusinessPercentage(
  12.5,
  FIELD_VALUE_EMPTY_TEXT,
  [16, 4],
  { kind: 'percent', code: 'percent', label: '%' },
), declaredPercentage.text);
assert.throws(
  () => formatBusinessPercentage(12.5),
  { name: 'ContractGapError' },
  'percentage precision must come from the field contract',
);
assert.throws(
  () => formatBusinessPercentage(12.5, FIELD_VALUE_EMPTY_TEXT, [16, 4]),
  { name: 'ContractGapError' },
  'percentage unit must come from the field contract',
);
assert.throws(
  () => presentDeclaredBusinessValue({
    field: { name: 'undeclared_ratio', type: 'float', componentKey: 'sc.value.percentage' },
    value: 12.5,
  }),
  { name: 'ContractGapError' },
  'declared percentages cannot use a frontend precision fallback',
);
const moneyWithoutObservedPrecision = {
  name: 'undeclared_money',
  type: 'monetary',
  componentKey: 'sc.value.money',
  currencyField: 'currency_id',
};
assert.deepEqual(presentDeclaredBusinessValue({
  field: moneyWithoutObservedPrecision,
  value: 12.5,
  currencyLabel: 'CNY',
}), {
  kind: 'money',
  text: '12.5 CNY',
  tone: 'neutral',
  badgeSemantic: 'default',
});
assert.equal(
  presentDeclaredBusinessValue({
    field: moneyWithoutObservedPrecision,
    value: '',
    currencyLabel: 'CNY',
  }).kind,
  'empty',
  'an unvalued create field needs no current-record currency precision',
);
assert.equal(
  formatMonetaryDisplayValue(12.5, undefined, 'CNY'),
  '12.5 CNY',
  'money without an observed precision is displayed without inventing decimals',
);
assert.equal(
  formatMonetaryInputValue(12.5, undefined),
  '12.5',
  'money input without an observed precision preserves the entered value',
);
assert.equal(
  monetaryInputStep(undefined),
  'any',
  'money input without an observed precision imposes no frontend step',
);
assert.throws(
  () => formatMonetaryDisplayValue(12.5, [16, 25] as [number, number], 'CNY'),
  { name: 'ContractGapError' },
  'a malformed declared money precision still fails closed',
);
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'declared_quantity', type: 'float', componentKey: 'sc.input.number', digits: [16, 6] },
  value: 12.5,
}).text, '12.500000', 'plain declared floats consume their contract precision');
assert.equal(presentCollectionKanbanCell({
  field: 'unrelated_ratio',
  value: 12.5,
  statusFields: [],
  columnOptions: [{
    name: 'unrelated_ratio',
    type: 'float',
    componentKey: 'sc.value.percentage',
    digits: [16, 4],
    unit: { kind: 'percent', code: 'percent', label: '%' },
  }],
}).text, '12.5000%', 'Kanban consumes percentage identity and declared precision');

const durationCases: Array<[unknown, string]> = [
  [null, FIELD_VALUE_EMPTY_TEXT],
  [undefined, FIELD_VALUE_EMPTY_TEXT],
  [false, FIELD_VALUE_EMPTY_TEXT],
  ['', FIELD_VALUE_EMPTY_TEXT],
  [0, '0.000 小时'],
  [1, '1.000 小时'],
  [1.5, '1.500 小时'],
  [1.999, '1.999 小时'],
  [0.58, '0.580 小时'],
  [59 / 60, '0.983 小时'],
  [59.6 / 60, '0.993 小时'],
  [-0.5, '-0.500 小时'],
  [-1.5, '-1.500 小时'],
  ['not-a-duration', FIELD_VALUE_EMPTY_TEXT],
  [Number.NaN, FIELD_VALUE_EMPTY_TEXT],
  [Number.POSITIVE_INFINITY, FIELD_VALUE_EMPTY_TEXT],
];
const durationField = {
  name: 'opaque_hours',
  type: 'float',
  widget: 'float_time',
  componentKey: 'sc.value.duration',
  digits: [16, 3] as [number, number],
  unit: { kind: 'duration', code: 'hour', label: '小时' },
};
for (const [value, expected] of durationCases) {
  assert.equal(formatBusinessDuration(value, FIELD_VALUE_EMPTY_TEXT, durationField.digits, durationField.unit), expected);
  assert.equal(presentDeclaredBusinessValue({ field: durationField, value }).kind === 'empty'
    ? FIELD_VALUE_EMPTY_TEXT
    : presentDeclaredBusinessValue({ field: durationField, value }).text, expected);
  assert.equal(presentListCell({
    raw: value,
    column: {
      field: 'opaque_hours',
      label: 'Hours',
      type: 'float',
      widget: 'float_time',
      componentKey: 'sc.value.duration',
      digits: durationField.digits,
      unit: durationField.unit,
    },
  }).text, expected);
  assert.equal(presentCollectionKanbanCell({
    field: 'opaque_hours',
    value,
    columnOptions: [{
      name: 'opaque_hours',
      type: 'float',
      widget: 'float_time',
      componentKey: 'sc.value.duration',
      digits: durationField.digits,
      unit: durationField.unit,
    }],
  }).text, expected);
}
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'duration_without_unit',
    type: 'float',
    widget: 'float_time',
    componentKey: 'sc.value.duration',
    digits: [16, 3],
  },
  value: 1.5,
}), { name: 'ContractGapError' }, 'duration unit must be declared');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'duration_without_digits',
    type: 'float',
    widget: 'float_time',
    componentKey: 'sc.value.duration',
    unit: { kind: 'duration', code: 'hour', label: '小时' },
  },
  value: 1.5,
}), { name: 'ContractGapError' }, 'duration precision must be declared');

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
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'empty_status_without_type',
  },
  value: null,
  status: true,
}), { name: 'ContractGapError' }, 'empty status values cannot hide a missing field type');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'empty_selection_status_without_projection',
    type: 'selection',
    componentKey: 'sc.display.status',
  },
  value: null,
}), { name: 'ContractGapError' }, 'empty status values cannot hide missing selection metadata');
assert.deepEqual(presentDeclaredBusinessValue({
  field: {
    name: 'empty_valid_selection_status',
    type: 'selection',
    componentKey: 'sc.display.status',
    selection: statusSelection,
  },
  value: null,
}), {
  kind: 'empty',
  text: FIELD_VALUE_EMPTY_TEXT,
  tone: 'neutral',
  badgeSemantic: 'default',
}, 'a valid status declaration still renders the platform empty value');
assert.equal(statusBadgeSemantic('approved'), 'success');
assert.equal(statusBadgeSemantic('rejected'), 'danger');
assert.equal(
  formatNumericFieldValue(12.5, 'float', { digits: [16, 3] }),
  '12.500',
  'generic float values consume their declared scale',
);
assert.equal(formatNumericFieldValue(2.7, 'integer'), '3', 'integer precision follows the declared field type');
assert.throws(
  () => formatNumericFieldValue(12.5, 'float'),
  { name: 'ContractGapError' },
  'generic float values without declared digits must stop instead of defaulting to two places',
);
assert.throws(
  () => formatNumericFieldValue(12.5, 'float', { digits: [16, 25] }),
  { name: 'ContractGapError' },
  'invalid generic float digits must stop instead of being rounded to a frontend default',
);
assert.throws(
  () => formatNumericFieldValue(null, 'float'),
  { name: 'ContractGapError' },
  'an empty generic float still requires its declared display precision',
);
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
  field: {
    name: 'business_date',
    type: 'date',
    temporal: { kind: 'date', timezoneAuthority: 'not_applicable' },
  },
  value: dateValue,
  temporalProfile: 'compact',
}).text, '2026-09-09');
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'business_datetime',
    type: 'datetime',
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
  },
  value: dateValue,
  temporalProfile: 'full',
  timeZone: 'UTC',
}).text, '2026-09-09 08:30:45');
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'business_datetime',
    type: 'datetime',
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
  },
  value: dateValue,
  temporalProfile: 'full',
  timeZone: 'Asia/Shanghai',
}).text, '2026-09-09 16:30:45');
assert.equal(presentDeclaredBusinessValue({
  field: {
    name: 'midnight_datetime',
    type: 'datetime',
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
  },
  value: '2026-09-09T00:00:00Z',
  temporalProfile: 'full',
  timeZone: 'UTC',
}).text, '2026-09-09 00:00:00', 'datetime never downgrades to a date at midnight');
assert.throws(() => presentDeclaredBusinessValue({
  field: { name: 'missing_temporal', type: 'datetime' },
  value: dateValue,
}), { name: 'ContractGapError' }, 'datetime requires its declared temporal authority');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'mismatched_temporal',
    type: 'date',
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
  },
  value: '2026-09-09',
}), { name: 'ContractGapError' }, 'temporal kind must match the declared field type');
assert.throws(() => presentDeclaredBusinessValue({
  field: {
    name: 'record_time_datetime',
    type: 'datetime',
    temporal: { kind: 'datetime', timezoneAuthority: 'record' },
  },
  value: dateValue,
}), { name: 'ContractGapError' }, 'record timezone authority requires a declared record timezone');
assert.equal(presentCollectionKanbanCell({
  field: 'business_datetime',
  value: dateValue,
  columnOptions: [{
    name: 'business_datetime',
    type: 'datetime',
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
  }],
  timeZone: 'UTC',
}).text, '2026-09-09 08:30');

assert.equal(presentDeclaredBusinessValue({
  field: moneyField,
  value: null,
}).text, FIELD_VALUE_EMPTY_TEXT);
assert.equal(presentListCell({
  raw: null,
  column: {
    field: 'amount',
    label: '金额',
    type: 'monetary',
    cellRole: 'money',
    digits: [16, 2],
  },
  numeric: true,
}).text, FIELD_VALUE_EMPTY_TEXT, 'missing list amounts are not business zeroes');
assert.equal(isListAttachmentCountColumn({
  field: 'attachment_summary',
  label: '附件',
  type: 'char',
}), false, 'attachment behavior is never inferred from a localized label');
assert.equal(isListAttachmentCountColumn({
  field: 'ordinary_integer',
  label: '附件',
  type: 'integer',
}), false, 'ordinary integers cannot become attachment actions');
assert.equal(isListAttachmentCountColumn({
  field: 'attachment_count',
  label: 'Attachments',
  type: 'integer',
  cellRole: 'attachment-count',
}), true, 'attachment behavior requires an explicit contract cell role');
assert.deepEqual(presentListCell({
  raw: 'pending',
  column: {
    field: 'opaque_state',
    label: '状态',
    type: 'selection',
    cellRole: 'status',
    selection: [...statusSelection],
  },
}), {
  text: '待处理',
  tone: 'warning',
});
assert.throws(() => presentListCell({
  raw: 'missing',
  column: {
    field: 'opaque_state',
    label: '状态',
    type: 'selection',
    cellRole: 'status',
    selection: [...statusSelection],
  },
}), { name: 'ContractGapError' }, 'List unknown selection must fail closed without exposing its storage key');
assert.throws(() => formatDisplayValue('missing', {
  type: 'selection',
  selection: [['pending', '待处理']],
}), { name: 'ContractGapError' }, 'generic display delegates selection semantics to the authority');
assert.throws(
  () => formatDisplayValue('business text without a field descriptor'),
  { name: 'ContractGapError' },
  'business values without a field descriptor must stop instead of using an appearance-based formatter',
);
assert.equal(
  formatDisplayValue('合同.pdf | /web/content/123', { type: 'char' }),
  '合同.pdf | /web/content/123',
  'ordinary character fields retain their complete text even when it resembles an attachment reference',
);
assert.equal(formatDisplayValue(12.5, {
  type: 'float',
  componentKey: 'sc.value.percentage',
  digits: [16, 4],
  unit: { kind: 'percent', code: 'percent', label: '%' },
}), '12.5000%', 'generic display delegates percentage identity and digits');

const titleColumnOptions = [{
  name: 'declared_title',
  type: 'char',
}];
assert.equal(presentCollectionKanbanTitle({
  titleField: 'declared_title',
  value: '合同甲',
  columnOptions: titleColumnOptions,
}), '合同甲');
assert.throws(
  () => presentCollectionKanbanTitle({
    titleField: '',
    value: '合同甲',
    columnOptions: titleColumnOptions,
  }),
  { name: 'ContractGapError' },
  'Kanban cannot synthesize a title field',
);
assert.throws(
  () => presentCollectionKanbanTitle({
    titleField: 'missing_title',
    value: '合同甲',
    columnOptions: titleColumnOptions,
  }),
  { name: 'ContractGapError' },
  'Kanban cannot format a title without its declared column option',
);

assert.equal(hasDeclaredAttachmentIdentity({
  relation: 'ir.attachment',
  attachmentRole: 'invoice_evidence',
}), true);
assert.equal(hasDeclaredAttachmentIdentity({ relation: 'ir.attachment' }), false);
assert.equal(hasDeclaredAttachmentIdentity({ type: 'char', attachmentRole: 'invoice_evidence' }), false);

const relationField = { name: 'project_id', type: 'many2one' };
assert.deepEqual(presentDeclaredBusinessValue({
  field: relationField,
  value: [7, '项目甲'],
}), {
  kind: 'relation',
  text: '项目甲',
  tone: 'neutral',
  badgeSemantic: 'default',
});
assert.equal(presentDeclaredBusinessValue({
  field: relationField,
  value: { id: 7, displayName: '项目甲' },
}).text, '项目甲');
const localizedRelationLabel = {
  zh_CN: '项目甲',
  en_US: 'Project A',
};
assert.equal(presentDeclaredBusinessValue({
  field: relationField,
  value: [7, localizedRelationLabel],
  locale: 'zh-CN',
}).text, '项目甲');
assert.equal(presentDeclaredBusinessValue({
  field: relationField,
  value: [7, localizedRelationLabel],
  locale: 'en-US',
}).text, 'Project A');
assert.equal(presentDeclaredBusinessValue({
  field: relationField,
  value: { id: 7, display_name: localizedRelationLabel },
  locale: 'en-US',
}).text, 'Project A');
assert.equal(presentDeclaredBusinessValue({
  field: relationField,
  value: false,
}).text, FIELD_VALUE_EMPTY_TEXT);
assert.throws(() => presentDeclaredBusinessValue({
  field: relationField,
  value: 7,
}), { name: 'ContractGapError' }, 'bare relation identity is never rendered as a business value');
assert.throws(() => presentDeclaredBusinessValue({
  field: relationField,
  value: [7, ''],
}), { name: 'ContractGapError' }, 'relation identity without a declared label fails closed');
assert.equal(formatDisplayValue([7, '项目甲'], relationField), '项目甲');
assert.equal(formatDisplayValue([7, localizedRelationLabel], relationField, { locale: 'zh_CN' }), '项目甲');
assert.equal(formatDisplayValue([7, localizedRelationLabel], relationField, { locale: 'en_US' }), 'Project A');
assert.throws(() => formatDisplayValue(7, relationField), { name: 'ContractGapError' });
assert.equal(presentDeclaredBusinessValue({
  field: { name: 'tag_ids', type: 'many2many' },
  value: [[1, '标签甲'], { id: 2, display_name: '标签乙' }],
}).text, '标签甲、标签乙');
assert.throws(() => presentDeclaredBusinessValue({
  field: { name: 'tag_ids', type: 'many2many' },
  value: [1, 2],
}), { name: 'ContractGapError' }, 'many2many bare IDs fail closed');
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

console.log('[business_semantics_consistency_test] PASS money=6 status=20 temporal=4 empty=3 duration=16 consumers=3');
