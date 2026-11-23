import assert from 'node:assert/strict';
import formProject from '../../../../docs/architecture/unified_page_contract_v2/examples/form_project.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const legacy = clone(formProject as Record<string, unknown>);
delete (legacy.runtimeContract as Record<string, unknown>).deliveryProfile;
decodeContractV2Snapshot(legacy);

const currentOuterVersion = clone(legacy);
const currentPageInfo = currentOuterVersion.pageInfo as Record<string, unknown>;
currentPageInfo.contractVersion = '2.6.0';
function stripLegacyDescriptors(rows: unknown): void {
  if (!Array.isArray(rows)) return;
  rows.forEach((row) => {
    if (!row || typeof row !== 'object') return;
    const record = row as Record<string, unknown>;
    const widgets = Array.isArray(record.widgetList) ? record.widgetList : [];
    widgets.forEach((widget) => {
      if (widget && typeof widget === 'object') delete (widget as Record<string, unknown>).fieldDescriptor;
    });
    stripLegacyDescriptors(record.children);
  });
}
stripLegacyDescriptors((currentOuterVersion.layoutContract as Record<string, unknown>).containerTree);
decodeContractV2Snapshot(currentOuterVersion);

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
  componentKey: 'sc.input.text',
  semanticType: 'text',
};
const strictWidget = firstWidget((currentOuterVersion.layoutContract as Record<string, unknown>).containerTree);
assert.ok(strictWidget);
strictWidget.fieldDescriptor = strictDescriptor;
decodeContractV2Snapshot(currentOuterVersion);

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

console.log('P0_DESIGN_DECODER=PASS old_projection=accepted current_version=accepted undeclared_carriers=rejected');
