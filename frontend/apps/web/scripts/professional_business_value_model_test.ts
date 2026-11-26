import assert from 'node:assert/strict';
import {
  PROFESSIONAL_BUSINESS_VALUE_KEYS,
  businessValueKind,
  formatPercentage,
  isProfessionalBusinessValueField,
  normalizeBusinessValueChoiceOptions,
} from '../src/components/professional-fields/professionalBusinessValueModel';
import {
  formatBusinessDuration,
  statusBadgeSemantic,
} from '../src/app/presentation/businessValuePresentation';

const fieldTypes = new Map([
  ['sc.value.money', 'monetary'],
  ['sc.value.percentage', 'float'],
  ['sc.display.status', 'selection'],
  ['sc.value.duration', 'float'],
]);
const modes = ['task', 'workspace'] as const;
const profiles = ['create', 'edit', 'readonly'] as const;
let matrix = 0;
for (const presentationMode of modes) {
  for (const renderProfile of profiles) {
    for (const componentKey of PROFESSIONAL_BUSINESS_VALUE_KEYS) {
      const field = { componentKey, type: fieldTypes.get(componentKey), presentationMode, renderProfile } as never;
      assert.equal(isProfessionalBusinessValueField(field), true);
      assert.equal(businessValueKind(field), componentKey);
      matrix += 1;
    }
  }
}
assert.equal(matrix, 24);
assert.equal(isProfessionalBusinessValueField({ componentKey: 'sc.value.money', type: 'char' } as never), false);
assert.equal(isProfessionalBusinessValueField({ componentKey: 'sc.input.number', type: 'monetary' } as never), false);
assert.throws(() => businessValueKind({ componentKey: 'sc.value.money', type: 'char' } as never), /PROFESSIONAL_BUSINESS_VALUE_UNSUPPORTED/);
assert.throws(
  () => formatPercentage(12.5),
  { name: 'ContractGapError' },
  'percentage precision must be declared by the field contract',
);
const percentUnit = { kind: 'percent' as const, code: 'percent', label: '%' };
const durationUnit = { kind: 'duration' as const, code: 'hour', label: '小时' };
assert.equal(formatPercentage(12.5, [16, 4], percentUnit), '12.5000%');
assert.throws(
  () => formatPercentage(12.5, [16, 4]),
  { name: 'ContractGapError' },
  'percentage unit must be declared by the field contract',
);
assert.equal(formatBusinessDuration(1.5, '--', [16, 3], durationUnit), '1.500 小时');
assert.equal(formatBusinessDuration(null, '--', [16, 3], durationUnit), '--');
assert.equal(formatBusinessDuration(false, '--', [16, 3], durationUnit), '--');
assert.equal(formatBusinessDuration(0, '--', [16, 3], durationUnit), '0.000 小时');
assert.equal(formatBusinessDuration(1.999, '--', [16, 3], durationUnit), '1.999 小时');
assert.equal(statusBadgeSemantic('approved'), 'success');
assert.equal(statusBadgeSemantic('rejected'), 'danger');
assert.deepEqual(
  normalizeBusinessValueChoiceOptions([
    { id: 50, value: 50, label: 'Demo Role Owner' },
    { value: 'approved', label: '已审批' },
  ]),
  [
    { value: '50', label: 'Demo Role Owner' },
    { value: 'approved', label: '已审批' },
  ],
);

console.log(`[professional_business_value_model_test] PASS matrix=${matrix} counterexamples=8`);
