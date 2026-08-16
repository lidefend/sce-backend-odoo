import fs from 'node:fs';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { resolveUnifiedPageContractV2 } from '../src/app/contracts/unifiedPageContractV2';
import type { CanonicalFormNode, CanonicalFormRenderMode } from '../src/app/presentation/canonicalFormRenderModel';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function collectFieldCodes(nodes: CanonicalFormNode[]): string[] {
  return nodes.flatMap((node) => [
    ...node.fields.map((field) => field.fieldCode),
    ...collectFieldCodes(node.children),
  ]);
}

const [payloadPath, requestedMode] = process.argv.slice(2);
if (!payloadPath || !['create', 'edit', 'readonly'].includes(requestedMode || '')) {
  throw new Error('usage: canonical_form_payload_audit <payload.json> <create|edit|readonly>');
}
const envelope = asRecord(JSON.parse(fs.readFileSync(payloadPath, 'utf8')));
const raw = asRecord(envelope.data || asRecord(envelope.result).data || envelope);
const resolved = resolveUnifiedPageContractV2(raw);
if (!resolved) throw new Error('UNIFIED_PAGE_CONTRACT_V2_MISSING');
const snapshot = decodeContractV2Snapshot(resolved);
const store = createContractV2Store(snapshot);
const model = presentContractV2Form(store, requestedMode as CanonicalFormRenderMode);
const renderedFields = collectFieldCodes([...model.zones.primary, ...model.zones.subordinate]);
const renderedSet = new Set(renderedFields);
const missingFields = [...store.widgetsByFieldCode.keys()].filter((fieldCode) => !renderedSet.has(fieldCode));
const duplicateFields = [...new Set(renderedFields.filter((fieldCode, index) => renderedFields.indexOf(fieldCode) !== index))];
const actionRefsIntact = model.actionBar.every((action) => store.actionsById.get(action.actionRef.actionId) === action.actionRef);
const visiblePrimary = model.actionBar.filter((action) => action.visible && action.tier === 'primary');
const result = {
  ok: !missingFields.length && !duplicateFields.length && actionRefsIntact && visiblePrimary.length <= 1,
  payload: payloadPath,
  mode: requestedMode,
  sourceContractSha256: model.identity.sourceContractSha256,
  normalizedFields: store.widgetsByFieldCode.size,
  renderedFields: renderedFields.length,
  missingFields,
  duplicateFields,
  normalizedActions: store.actionsById.size,
  renderedActions: model.actionBar.length,
  actionRefsIntact,
  visiblePrimaryCount: visiblePrimary.length,
  primaryZones: model.zones.primary.length,
  subordinateZones: model.zones.subordinate.length,
  subordinateKinds: model.zones.subordinate.map((node) => node.kind),
};
console.log(JSON.stringify(result, null, 2));
if (!result.ok) process.exitCode = 1;
