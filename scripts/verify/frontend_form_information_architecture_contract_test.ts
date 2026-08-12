import assert from 'node:assert/strict';
import {
  isOrdinaryFormInternalField,
  isOrdinaryFormInternalSection,
  isReadonlyEmptyBusinessValue,
} from '../../frontend/apps/web/src/pages/contractForm/formInformationArchitecture.ts';

assert.equal(isOrdinaryFormInternalField('create_uid'), true);
assert.equal(isOrdinaryFormInternalField('legacy_source_created_at'), true);
assert.equal(isOrdinaryFormInternalField('carrier_payload'), true);
assert.equal(isOrdinaryFormInternalField('source_created_at'), true);
assert.equal(isOrdinaryFormInternalField('legacy_owner_unit'), false, 'formalized business migration facts stay visible');
assert.equal(isOrdinaryFormInternalField('name', { surface_role: 'audit_only' }), true);

assert.equal(isOrdinaryFormInternalSection('系统办理信息'), true);
assert.equal(isOrdinaryFormInternalSection('来源追溯'), true);
assert.equal(isOrdinaryFormInternalSection('项目与合同'), false);

assert.equal(isReadonlyEmptyBusinessValue(null), true);
assert.equal(isReadonlyEmptyBusinessValue([]), true);
assert.equal(isReadonlyEmptyBusinessValue({}), true);
assert.equal(isReadonlyEmptyBusinessValue(false, 'boolean'), false, 'false is a meaningful boolean fact');
assert.equal(isReadonlyEmptyBusinessValue(false, 'many2one'), true, 'false is empty for non-boolean fields');
assert.equal(isReadonlyEmptyBusinessValue(0), false, 'zero is a meaningful numeric fact');

console.log('[frontend_form_information_architecture_contract_test] PASS matrix=17');
