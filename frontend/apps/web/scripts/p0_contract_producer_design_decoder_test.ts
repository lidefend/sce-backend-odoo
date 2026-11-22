import assert from 'node:assert/strict';
import formProject from '../../../../docs/architecture/unified_page_contract_v2/examples/form_project.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const legacy = clone(formProject as Record<string, unknown>);
delete (legacy.runtimeContract as Record<string, unknown>).deliveryProfile;
decodeContractV2Snapshot(legacy);

const futureOuterVersion = clone(legacy);
const futurePageInfo = futureOuterVersion.pageInfo as Record<string, unknown>;
futurePageInfo.contractVersion = '2.6.0';
assert.throws(
  () => decodeContractV2Snapshot(futureOuterVersion),
  /must be a negotiated 2\.0 through 2\.5 version/,
  'the current decoder must reject a future outer contract version',
);

const attachmentCarrier = clone(legacy);
const attachmentRuntime = attachmentCarrier.runtimeContract as Record<string, unknown>;
attachmentRuntime.attachmentFacts = { schemaVersion: '1.0.0', facts: [] };
assert.throws(
  () => decodeContractV2Snapshot(attachmentCarrier),
  /attachmentFacts is not allowed/,
  'the current strict decoder must reject an undeclared attachment carrier',
);

const actionFeedbackCarrier = clone(legacy);
const feedbackRuntime = actionFeedbackCarrier.runtimeContract as Record<string, unknown>;
feedbackRuntime.actionFeedback = [{ schemaVersion: '1.0.0', actionId: 'example' }];
assert.throws(
  () => decodeContractV2Snapshot(actionFeedbackCarrier),
  /actionFeedback is not allowed/,
  'the current strict decoder must reject an undeclared action-feedback carrier',
);

console.log('P0_DESIGN_DECODER=PASS old_projection=accepted new_version=rejected undeclared_carriers=rejected');
