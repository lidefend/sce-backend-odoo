import assert from 'node:assert/strict';
import {
  PROFESSIONAL_BUSINESS_VALUE_KEYS,
  businessValueKind,
  formatDuration,
  formatPercentage,
  isProfessionalBusinessValueField,
  statusSemantic,
} from '../src/components/professional-fields/professionalBusinessValueModel';

const fieldTypes = new Map([
  ['sc.value.money', 'monetary'],
  ['sc.value.currency', 'many2one'],
  ['sc.value.percentage', 'float'],
  ['sc.display.status', 'selection'],
  ['sc.value.duration', 'float'],
  ['sc.value.user', 'many2one'],
  ['sc.value.company', 'many2one'],
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
assert.equal(matrix, 42);
assert.equal(isProfessionalBusinessValueField({ componentKey: 'sc.value.money', type: 'char' } as never), false);
assert.equal(isProfessionalBusinessValueField({ componentKey: 'sc.input.number', type: 'monetary' } as never), false);
assert.throws(() => businessValueKind({ componentKey: 'sc.value.user', type: 'char' } as never), /PROFESSIONAL_BUSINESS_VALUE_UNSUPPORTED/);
assert.equal(formatPercentage(12.5), '12.5%');
assert.equal(formatDuration(1.5), '1 小时 30 分钟');
assert.equal(statusSemantic('approved'), 'success');
assert.equal(statusSemantic('rejected'), 'danger');

console.log(`[professional_business_value_model_test] PASS matrix=${matrix} counterexamples=7`);
