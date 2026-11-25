import assert from 'node:assert/strict';
import formProject from '../../../../docs/architecture/unified_page_contract_v2/examples/form_project.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const current = clone(formProject as Record<string, unknown>);
decodeContractV2Snapshot(current);

function firstWidget(rows: unknown): Record<string, unknown> | null {
  if (!Array.isArray(rows)) return null;
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue;
    const record = row as Record<string, unknown>;
    const widgets = Array.isArray(record.widgetList) ? record.widgetList : [];
    if (widgets[0] && typeof widgets[0] === 'object') return widgets[0] as Record<string, unknown>;
    const child = firstWidget(record.children);
    if (child) return child;
  }
  return null;
}

const strictDescriptor = {
  schemaVersion: '1.0.0',
  fieldCode: 'project.name',
  label: '项目名称',
  fieldType: 'char',
  widgetType: 'input',
  semanticType: 'text',
};
const strictWidget = firstWidget((current.layoutContract as Record<string, unknown>).containerTree);
assert.ok(strictWidget);
strictWidget.fieldDescriptor = strictDescriptor;
decodeContractV2Snapshot(current);

const legacyVersion = clone(current);
(legacyVersion.pageInfo as Record<string, unknown>).contractVersion = '2.6.0';
assert.throws(
  () => decodeContractV2Snapshot(legacyVersion),
  /must be a negotiated 2\.7 version/,
  'pre-production legacy protocol must not be accepted',
);

const componentIdentity = clone(current);
firstWidget((componentIdentity.layoutContract as Record<string, unknown>).containerTree)!.componentKey = 'sc.input.text';
assert.throws(
  () => decodeContractV2Snapshot(componentIdentity),
  /frontend implementation identity/,
  'V2.7 must not accept backend component identity',
);

const attachmentCarrier = clone(current);
const attachmentRuntime = attachmentCarrier.runtimeContract as Record<string, unknown>;
attachmentRuntime.attachmentFacts = { schemaVersion: '1.0.0', facts: [] };
assert.throws(
  () => decodeContractV2Snapshot(attachmentCarrier),
  /attachmentFacts is not allowed/,
  'the current strict decoder must reject an undeclared attachment carrier',
);

const actionFeedbackCarrier = clone(current);
const feedbackRuntime = actionFeedbackCarrier.runtimeContract as Record<string, unknown>;
feedbackRuntime.actionFeedback = [{ schemaVersion: '1.0.0', actionId: 'example' }];
assert.throws(
  () => decodeContractV2Snapshot(actionFeedbackCarrier),
  /actionFeedback is not allowed/,
  'the current strict decoder must reject an undeclared action-feedback carrier',
);

console.log('P0_DESIGN_DECODER=PASS current_version=accepted legacy_version=rejected component_identity=rejected undeclared_carriers=rejected');
