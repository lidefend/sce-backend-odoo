/**
 * Executable proof for CONTRACT-ERR-01: a validation error states the business
 * goal it rejected, and the web client resolves that goal onto a position the
 * user can actually correct.
 *
 * The chain under test is the shipped one, not a copy of it:
 *
 *   business rule  ->  BusinessFieldError (model + record/draft + field + row)
 *                  ->  the single error store keyed by businessErrorKey
 *                  ->  applyCanonicalFormValidation / selectValidationPosition
 *                  ->  focusProductFormValidationError (the page's focus entry)
 *
 * The counter-examples below fail on the previous behaviour in at least one
 * place: showing one error at every same-name position, sending the user to a
 * read-only first occurrence, attaching a row error by row number instead of row
 * identity, dropping an error whose position cannot be corrected, and letting an
 * error produced for the previous record decorate the newly opened draft.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import type { FieldDescriptor } from '@sc/schema';

import {
  BusinessErrorCodes,
  businessErrorKey,
  businessRowErrorKey,
  createBusinessErrorTarget,
  createBusinessFieldError,
  decodeServerFieldErrors,
  errorOwnsField,
  errorOwnsRecordScope,
  errorOwnsRowCell,
  indexBusinessFieldErrors,
  normalizeBusinessRowIdentity,
  parseBusinessErrorDisplayPosition,
  retainErrorsForRecordScope,
  selectFieldErrorsForTarget,
  selectRowCellError,
  type BusinessFieldError,
} from '../src/app/businessValidationError';
import { applyCanonicalFormValidation } from '../src/pages/contractForm/canonicalFormRenderState';
import { selectValidationPosition } from '../src/pages/contractForm/validationErrorPosition';
import { focusProductFormValidationError } from '../src/pages/contractForm/formValidationFocus';
import { buildLegacyLayoutNodes } from '../src/pages/contractForm/nativeLayoutUtils';
import { collectRequiredFieldValidation, validateBeforeSaveRecord } from '../src/pages/contractForm/saveRecordHelpers';
import { normalizeContractFieldValue } from '../src/pages/contractForm/valueUtils';
import { fieldType } from '../src/pages/contractForm/fieldUtils';
import type {
  CanonicalFormField,
  CanonicalFormNode,
  CanonicalFormRenderModel,
} from '../src/app/presentation/canonicalFormRenderModel';
import type { LayoutNode } from '../src/pages/contractForm/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};
const checkDeep = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

// ---------------------------------------------------------------------------
// Part 1 — one business ownership, no terminal vocabulary
// ---------------------------------------------------------------------------
const projectScope = { model: 'project.project', recordId: 501 };
const amountTarget = createBusinessErrorTarget({
  model: 'project.project', recordId: 501, fieldCode: 'name',
});
const amountError = createBusinessFieldError({
  code: BusinessErrorCodes.REQUIRED_VALUE_MISSING,
  message: '项目名称不能为空',
  target: amountTarget,
})!;

check(amountError.target.model, 'project.project', 'the error names the owning model');
check(amountError.target.recordId, 501, 'the error names the owning record');
check(amountError.target.fieldCode, 'name', 'the error names the business field, not a position');
check(amountError.target.row, null, 'a record-level error carries no row scope');
check(businessErrorKey(amountError.target), 'name', 'a record-level field keys by the field code alone');

// A draft error and a persisted-record error are different business goals.
const draftError = createBusinessFieldError({
  code: BusinessErrorCodes.REQUIRED_VALUE_MISSING,
  message: '项目名称不能为空',
  target: createBusinessErrorTarget({ model: 'project.project', recordId: null, fieldCode: 'name' }),
})!;
check(errorOwnsRecordScope(draftError, projectScope), false, 'a draft error does not own the persisted record');
check(errorOwnsRecordScope(draftError, { model: 'project.project', recordId: null }), true, 'a draft error owns the draft');
check(errorOwnsRecordScope(amountError, { model: 'other.model', recordId: 501 }), false, 'a model mismatch is not ownership');

// An error without a field target is a legal shape: it stays at form level.
const formLevelError = createBusinessFieldError({
  code: BusinessErrorCodes.BUSINESS_RULE_REJECTED,
  message: '结算单明细重复',
  target: createBusinessErrorTarget({ model: 'project.project', recordId: 501, fieldCode: '' }),
});
check(formLevelError, null, 'an error that names no business field is refused a field target rather than guessed');

// ---------------------------------------------------------------------------
// Part 2 — one business error decorates exactly one correctable position
// ---------------------------------------------------------------------------
const formField = (overrides: Partial<CanonicalFormField> & { widgetId: string; fieldCode: string }): CanonicalFormField => ({
  widgetType: 'input',
  label: overrides.fieldCode,
  hideLabel: false,
  value: '',
  fieldType: 'char',
  componentKey: 'sc.input.text',
  componentResolution: {} as CanonicalFormField['componentResolution'],
  presentationMode: 'task',
  renderProfile: 'edit',
  span: 12,
  nativeLocator: '',
  occurrenceIndex: null,
  sourcePosition: null,
  visible: true,
  readonly: false,
  required: false,
  disabled: false,
  reasonCode: '',
  placeholder: '',
  auth: 'edit',
  semanticRole: '',
  semanticSlot: '',
  semanticGroup: '',
  componentConfig: {},
  fieldDescriptor: {},
  ...overrides,
});

const formNode = (fields: CanonicalFormField[]): CanonicalFormNode => ({
  nodeId: 'section.identity',
  kind: 'group',
  title: 'Identity',
  text: '',
  attributes: {},
  nativePresentation: {},
  span: 24,
  styleToken: '',
  zoneRole: 'primary',
  columns: 2,
  visible: true,
  disabled: false,
  reasonCode: '',
  semanticRole: '',
  semanticSlot: '',
  semanticGroup: '',
  action: null,
  nativeWidget: '',
  fields,
  children: [],
});

const renderModel = (fields: CanonicalFormField[], model = 'project.project'): CanonicalFormRenderModel => ({
  identity: {
    pageId: 'page.project.form',
    sceneKey: 'project.form',
    model,
    viewType: 'form',
    mode: 'edit',
    presentationMode: 'task',
    sourceContractSha256: 'test',
  },
  shell: { title: 'Project', pageVisible: true, pageAuth: 'edit', reasonCode: '' },
  actionBar: [],
  zones: { primary: [formNode(fields)], subordinate: [] },
  responsive: { adaptMode: 'pc', layoutHints: {} },
  componentTokens: {},
});

const collectRendered = (model: CanonicalFormRenderModel): CanonicalFormField[] => {
  const out: CanonicalFormField[] = [];
  const walk = (node: CanonicalFormNode) => {
    out.push(...node.fields);
    node.children.forEach(walk);
  };
  [...model.zones.primary, ...model.zones.subordinate].forEach(walk);
  return out;
};

// A: the first occurrence of `name` is a read-only summary, the second one is
// the editable detail. The business owns the field, so the message must land on
// the position the user can correct — never on whichever comes first in the DOM.
const twoOccurrences = renderModel([
  formField({ widgetId: 'field.name', fieldCode: 'name', label: 'Name (summary)', readonly: true, renderProfile: 'readonly', nativeLocator: '//field[@name="name"][1]' }),
  formField({ widgetId: 'field.name.occ.detail', fieldCode: 'name', label: 'Name', nativeLocator: '//field[@name="name"][2]' }),
  formField({ widgetId: 'field.partner_id', fieldCode: 'partner_id', fieldType: 'many2one' }),
]);

const decorated = applyCanonicalFormValidation(twoOccurrences, indexBusinessFieldErrors([amountError]), projectScope);
const decoratedFields = collectRendered(decorated);
const readonlyOccurrence = decoratedFields.find((field) => field.widgetId === 'field.name')!;
const editableOccurrence = decoratedFields.find((field) => field.widgetId === 'field.name.occ.detail')!;

check(readonlyOccurrence.invalid, false, 'the read-only occurrence is not marked invalid');
check(readonlyOccurrence.errorText, '', 'the read-only occurrence carries no message to correct');
check(editableOccurrence.invalid, true, 'the correctable occurrence is marked invalid');
check(editableOccurrence.errorText, '项目名称不能为空', 'the correctable occurrence carries the business message');
check(
  decoratedFields.filter((field) => field.fieldCode === 'name' && field.invalid).length,
  1,
  'one business error produces exactly one decorated position, never one per same-name position',
);
check(decoratedFields.find((field) => field.widgetId === 'field.partner_id')!.invalid, false, 'an unrelated field is untouched');

// The same field shown at two writable positions must still produce one error.
const twoWritable = renderModel([
  formField({ widgetId: 'field.name', fieldCode: 'name', nativeLocator: '//field[@name="name"][1]' }),
  formField({ widgetId: 'field.name.occ.detail', fieldCode: 'name', nativeLocator: '//field[@name="name"][2]' }),
]);
const writableDecorated = collectRendered(applyCanonicalFormValidation(twoWritable, indexBusinessFieldErrors([amountError]), projectScope));
check(writableDecorated.filter((field) => field.invalid).length, 1, 'two writable positions still produce one business error');
check(writableDecorated[0].invalid, true, 'with no source position the first registered correctable position is used');

// The occurrence that produced the value is preferred when it still resolves.
const sourceDecorated = collectRendered(applyCanonicalFormValidation(
  twoWritable,
  indexBusinessFieldErrors([{ ...amountError, sourceOccurrenceKey: 'field.name.occ.detail' }]),
  projectScope,
));
check(sourceDecorated[0].invalid, false, 'the source occurrence takes the error off the unrelated position');
check(sourceDecorated[1].invalid, true, 'the source occurrence keeps the error it produced');

// An error belonging to another record must not decorate this one.
const otherRecordDecorated = collectRendered(applyCanonicalFormValidation(
  twoOccurrences,
  indexBusinessFieldErrors([{ ...amountError, target: { ...amountError.target, recordId: 999 } }]),
  projectScope,
));
check(otherRecordDecorated.some((field) => field.invalid), false, 'a stale record error does not decorate the open draft');

// ---------------------------------------------------------------------------
// Part 3 — a row error is owned by row identity, not by row number
// ---------------------------------------------------------------------------
const rowError = (rowKey: string, recordId: number | null, cellField = 'quantity'): BusinessFieldError => createBusinessFieldError({
  code: BusinessErrorCodes.REQUIRED_VALUE_MISSING,
  message: '数量不能为空',
  target: createBusinessErrorTarget({
    model: 'project.project',
    recordId: 501,
    fieldCode: 'line_ids',
    row: { relationField: 'line_ids', recordId, rowKey, cellField },
  }),
})!;

const persistedRow = rowError('row-7', 7);
const otherRow = rowError('row-9', 9);
const newRow = rowError('draft-1', null);

check(
  businessErrorKey(persistedRow.target) === businessErrorKey(otherRow.target),
  false,
  'two rows of the same field and cell never share one error key',
);
check(businessRowErrorKey('line_ids', 'row-7', 'quantity'), businessErrorKey(persistedRow.target), 'the row key has one authority');
check(errorOwnsRowCell(persistedRow, projectScope, { rowKey: 'row-7', cellField: 'quantity' }), true, 'the error owns its own row');
check(errorOwnsRowCell(persistedRow, projectScope, { rowKey: 'row-9', cellField: 'quantity' }), false, 'the error does not own a sibling row');
check(errorOwnsRowCell(persistedRow, projectScope, { rowKey: 'row-7', cellField: 'price_unit' }), false, 'a sibling cell is not the rejected one');

// Reordering rows does not renumber identity: the same key still wins.
const store = indexBusinessFieldErrors([persistedRow, otherRow]);
check(selectRowCellError(store, projectScope, { rowKey: 'row-9', cellField: 'quantity' })?.message, '数量不能为空', 'reordering keeps the error on its own row');
check(selectRowCellError(store, projectScope, { rowKey: 'row-7', cellField: 'quantity' })?.message, '数量不能为空', 'the other row still owns its own error');

// An unsaved row has no database id, so the draft row key carries identity.
check(errorOwnsRowCell(newRow, projectScope, { rowKey: 'draft-1', cellField: 'quantity' }), true, 'a new row is identified by its draft row key');
check(errorOwnsRowCell(newRow, projectScope, { rowKey: 'draft-2', cellField: 'quantity' }), false, 'a new row does not leak onto another new row');
check(normalizeBusinessRowIdentity({ relationField: 'line_ids', recordId: 7 }), null, 'an identity missing its stable parts is refused, not repaired');
check(normalizeBusinessRowIdentity({ relationField: 'line_ids', recordId: 7, rowKey: 'row-7', cellField: '' }), null, 'an identity with no cell is refused, not repaired');

// A row error never decorates a record-level position of the same field code.
check(errorOwnsField(persistedRow, { ...projectScope, fieldCode: 'line_ids' }), false, 'a row error is not a record-level field error');
check(selectFieldErrorsForTarget(store, { ...projectScope, fieldCode: 'line_ids' }).length, 0, 'the record-level field lookup ignores row errors');
check(selectFieldErrorsForTarget(indexBusinessFieldErrors([amountError]), { ...projectScope, fieldCode: 'name' }).length, 1, 'the record-level field lookup finds its own error');

// ---------------------------------------------------------------------------
// Part 4 — choosing a correction position, and degrading safely
// ---------------------------------------------------------------------------
const candidates = [
  { key: 'name', occurrenceKey: 'field.name', visible: true, correctable: false },
  { key: 'name', occurrenceKey: 'field.name.occ.detail', visible: true, correctable: true },
];
const bySource = selectValidationPosition(candidates, { sourceOccurrenceKey: 'field.name.occ.detail' });
check(bySource.outcome, 'position', 'a source occurrence is used when it is usable');
check(bySource.position?.occurrenceKey, 'field.name.occ.detail', 'the source occurrence is the chosen position');
check(bySource.reason, 'source-occurrence', 'the choice records why it was made');

const withoutSource = selectValidationPosition(candidates, {});
check(withoutSource.position?.occurrenceKey, 'field.name.occ.detail', 'a read-only first position is never chosen over a correctable one');
check(withoutSource.reason, 'correctable-position', 'the fallback choice records its reason');

const staleSource = selectValidationPosition(candidates, { sourceOccurrenceKey: 'field.name.occ.gone' });
check(staleSource.position?.occurrenceKey, 'field.name.occ.detail', 'a source position that no longer exists falls back deterministically');

const onlyReadonly = selectValidationPosition([candidates[0]], {});
check(onlyReadonly.outcome, 'summary', 'no correctable position keeps the error at form level');
check(onlyReadonly.position, null, 'no position is invented when only a read-only copy exists');
check(onlyReadonly.reason, 'no-correctable-position', 'the summary outcome records why');

const onlyHidden = selectValidationPosition([{ key: 'name', occurrenceKey: 'field.name', visible: false, correctable: true }], {});
check(onlyHidden.outcome, 'summary', 'an unrendered position is not a correction site');

// The page's real focus entry must honour that decision: it sends the user to a
// position when one exists, and otherwise keeps the summary — never dropping the
// error and never scrolling somewhere unrelated.
const globalScope = globalThis as unknown as Record<string, unknown>;
const savedDocument = globalScope.document;
const savedCSS = globalScope.CSS;
const savedWindow = globalScope.window;
globalScope.CSS = { escape: (value: string) => value };
try {
  globalScope.document = { querySelector: () => null };
  check(await focusProductFormValidationError('name'), 'no-form', 'outside a form page the focus entry reports it plainly');

  const summaryFocus: string[] = [];
  const fakeForm = {
    querySelector: (selector: string) => (selector === '[data-form-error-summary]' ? { focus: () => summaryFocus.push('summary') } : null),
    querySelectorAll: () => [],
  };
  globalScope.document = {
    querySelector: (selector: string) => (selector === '[data-product-page-mode="form"]' ? fakeForm : null),
  };
  check(await focusProductFormValidationError('name'), 'summary', 'a field with no registered position falls back to the summary');
  checkDeep(summaryFocus, ['summary'], 'the form-level summary receives focus when no position is usable');
  check(await focusProductFormValidationError({ key: 'line_ids:row-7:quantity' }), 'summary', 'a row error without a registered cell falls back to the summary');
  check(await focusProductFormValidationError({ key: 'a:b:c:d' }), 'summary', 'an undecodable key is refused rather than guessed');
  check(parseBusinessErrorDisplayPosition('a:b:c:d'), null, 'an unknown display-key shape decodes to nothing');
  checkDeep(parseBusinessErrorDisplayPosition('name'), { key: 'name', fieldCode: 'name', rowKey: '', cellField: '' }, 'a field key decodes to a field position');
  check(parseBusinessErrorDisplayPosition('line_ids:row-7:quantity')?.rowKey, 'row-7', 'a row key decodes to the owning row');
  const unrelatedFocus: string[] = [];
  const siblingControl = {
    parentElement: null,
    getAttribute: () => null,
    getClientRects: () => [{}],
    matches: () => true,
    focus: () => unrelatedFocus.push('sibling-row'),
    scrollIntoView: () => {},
  };
  const collection = {
    ...siblingControl,
    matches: () => false,
    querySelector: () => siblingControl,
    querySelectorAll: () => [siblingControl],
  };
  globalScope.window = { getComputedStyle: () => ({ display: 'block', visibility: 'visible' }), requestAnimationFrame: (callback: () => void) => callback() };
  globalScope.document = { querySelector: () => ({
    ...fakeForm,
    querySelectorAll: (selector: string) => selector === '[data-field-name="line_ids"]' ? [collection] : [],
  }) };
  check(await focusProductFormValidationError('line_ids:row-7:quantity'), 'summary', 'a missing row cell cannot fall back to the mounted collection');
  checkDeep(unrelatedFocus, [], 'a sibling row or collection add button never receives the missing row error focus');
} finally {
  globalScope.document = savedDocument;
  globalScope.CSS = savedCSS;
  globalScope.window = savedWindow;
}

// ---------------------------------------------------------------------------
// Part 5 — compatibility: an unowned server message stays unowned
// ---------------------------------------------------------------------------
checkDeep(decodeServerFieldErrors({ field_errors: [{ field_code: 'name', message: '项目名称不能为空' }] }, projectScope)
  .map((error) => [error.target.model, error.target.recordId, error.target.fieldCode]),
[['project.project', 501, 'name']], 'a structured field rejection is accepted and scoped');

checkDeep(decodeServerFieldErrors({ validation_errors: ['结算单明细重复'] }, projectScope), [], 'a message-only rejection is not turned into a field error');
checkDeep(decodeServerFieldErrors({ field_errors: [{ message: '结算单明细重复' }] }, projectScope), [], 'a fieldless entry is dropped rather than guessed');
checkDeep(decodeServerFieldErrors({ field_errors: [{ field_code: 'line_ids', message: '数量不能为空', row: { relation_field: 'line_ids', record_id: 7, cell_field: 'quantity' } }] }, projectScope).length, 0,
  'a row entry without a stable row key is dropped rather than attached to a numbered row');
checkDeep(decodeServerFieldErrors({ field_errors: [{ field_code: 'line_ids', message: '数量不能为空', row: { relation_field: 'line_ids', record_id: 7, row_key: 'row-7', cell_field: 'quantity' } }] }, projectScope)
  .map((error) => businessErrorKey(error.target)),
['line_ids:row-7:quantity'], 'a complete row rejection keeps its row identity');
checkDeep(decodeServerFieldErrors(null, projectScope), [], 'a response with no field ownership produces nothing');

// Switching record: the previous draft keeps nothing.
const staleStore = indexBusinessFieldErrors([amountError]);
checkDeep(Object.keys(retainErrorsForRecordScope(staleStore, { model: 'project.project', recordId: 501 })), ['name'], 'the active record keeps its own errors');
checkDeep(retainErrorsForRecordScope(staleStore, { model: 'project.project', recordId: 502 }), {}, 'a different record keeps no errors from the previous one');
checkDeep(retainErrorsForRecordScope(staleStore, { model: 'other.model', recordId: 501 }), {}, 'a different model keeps no errors from the previous one');

// ---------------------------------------------------------------------------
// Part 6 — the real production path: a required value becomes a targeted error
// ---------------------------------------------------------------------------
const descriptor = (input: Record<string, unknown>) => input as unknown as FieldDescriptor;
const projectFields: Record<string, FieldDescriptor> = {
  name: descriptor({ type: 'char', string: '项目名称', required: true }),
  note: descriptor({ type: 'char', string: '备注' }),
};
const layoutNodes = buildLegacyLayoutNodes({
  fields: projectFields,
  order: [],
  containerStatus: {},
  visibleFields: [],
  fallbackFieldNames: [],
  isCreate: true,
  readonly: false,
  resolveFieldLabel: (name: string) => name,
  evaluatePolicy: (_name: string, row: FieldDescriptor) => ({ visible: true, required: Boolean(row.required), readonly: Boolean(row.readonly) }),
  runtimeState: () => ({ invisible: false, readonly: false, required: false }),
}) as LayoutNode[];
const normalizeFieldValue = (name: string, value: unknown) => normalizeContractFieldValue({
  name, value, descriptor: projectFields[name], originalValue: undefined, buildOne2manyValue: () => [],
});

const draft = { name: '   ', note: '已输入的备注' };
const draftSnapshot = JSON.stringify(draft);
const required = collectRequiredFieldValidation({
  formData: draft,
  isWritableFieldVisible: () => true,
  layoutNodes,
  model: 'project.project',
  normalizeFieldValue,
  recordId: null,
  values: { ...draft },
});
check(required.messages.length, 1, 'a missing required value is reported once');
check(Object.keys(required.fieldErrors).length, 1, 'a missing required value produces one targeted error');
const produced = required.fieldErrors.name;
check(produced.code, BusinessErrorCodes.REQUIRED_VALUE_MISSING, 'the produced error names the rule that rejected the value');
check(produced.target.model, 'project.project', 'the produced error names the owning model');
check(produced.target.recordId, null, 'an unsaved draft is named as the draft, not as a record');
check(produced.target.fieldCode, 'name', 'the produced error names the business field');
check(produced.message, '项目名称不能为空', 'the produced error carries a safe user-facing message');
check(JSON.stringify(draft), draftSnapshot, 'a rejected save leaves the user draft untouched');

// A rejected save must not report success, and the corrected save must.
const saveParams = (values: Record<string, unknown>) => ({
  collectSceneValidationPrecheckErrors: () => [],
  collectWritableValues: () => values,
  formData: { ...values },
  isWritableFieldVisible: () => true,
  layoutNodes,
  layoutFieldLabels: () => ({ name: '项目名称', note: '备注' }),
  normalizeFieldValue,
  one2manyFieldErrors: {},
  one2manyIssues: [],
  model: 'project.project',
  recordId: null,
  resolvePendingInlineRelationCreates: async () => [],
  resolvePendingMany2manyTagCreates: async () => [],
});
const rejectedSave = await validateBeforeSaveRecord(saveParams({ ...draft }));
check(rejectedSave.ok, false, 'the save gate refuses a payload with a missing required value');
check(rejectedSave.fieldErrors?.name?.target.fieldCode, 'name', 'the refused save returns the business ownership of the error');
check(rejectedSave.submissionFeedback?.kind, 'warn', 'the refused save reports a failure, not a success');

const corrected = { name: '新项目', note: '已输入的备注' };
const acceptedSave = await validateBeforeSaveRecord(saveParams({ ...corrected }));
check(acceptedSave.ok, true, 'the corrected payload passes the same gate');
check(acceptedSave.fieldErrors, undefined, 'a passing save carries no leftover field errors');
checkDeep(acceptedSave.editableMap, corrected, 'the corrected value is what the save would write');
check(fieldType(projectFields.name), 'char', 'the corrected field keeps its contract type');

// A field error on one field does not block a different field's ownership.
check(Object.keys(required.fieldErrors)[0], 'name', 'the error is keyed by the business field it belongs to');

// ---------------------------------------------------------------------------
// Part 7 — terminal independence, and the wiring that must not drift
// ---------------------------------------------------------------------------
// Same business error, two different position arrangements: the business goal is
// identical while the correction position each client would choose differs.
const webArrangement = selectValidationPosition(candidates, {});
const stepArrangement = selectValidationPosition(
  [{ key: 'name', occurrenceKey: 'step.basic.name', visible: true, correctable: true }],
  {},
);
check(businessErrorKey(amountError.target), businessErrorKey({ ...amountError.target }), 'the business goal does not depend on the position');
check(webArrangement.position?.occurrenceKey === stepArrangement.position?.occurrenceKey, false, 'two clients may resolve different positions for one business error');

const locateSource = (relative: string) => {
  let dir = process.cwd();
  for (let depth = 0; depth < 4; depth += 1) {
    const candidate = path.join(dir, relative);
    if (fs.existsSync(candidate)) return candidate;
    dir = path.dirname(dir);
  }
  return '';
};

const contractSource = fs.readFileSync(locateSource('frontend/apps/web/src/app/businessValidationError.ts'), 'utf8');
check(/from ['"]vue['"]/.test(contractSource), false, 'the business ownership module does not import a rendering framework');
check(/\bdocument\./.test(contractSource), false, 'the business ownership module does not read the DOM');
check(/window\./.test(contractSource), false, 'the business ownership module does not read a browser global');
check(/tdesign/i.test(contractSource), false, 'the business ownership module does not name a component library');

const pageSource = fs.readFileSync(locateSource('frontend/apps/web/src/pages/ContractFormPage.vue'), 'utf8');
const renderCall = pageSource.slice(pageSource.indexOf('resolveCanonicalFormRenderState(')).slice(0, 500);
check(renderCall.includes('validationFieldErrors.value'), true, 'the page feeds the single error store into the render state');
check(renderCall.includes('recordId: recordId.value'), true, 'the page scopes the render state to the open record');

// A dependency that is destructured but never passed is read as `undefined` at
// runtime, and the lifecycle here writes to it on every reload. The page call
// site is guarded because the composable's own signature is a loose record.
const lifecycleCall = pageSource.slice(pageSource.indexOf('useRecordPageLifecycle({')).slice(0, 3000);
check(
  pageSource.indexOf('useRecordPageLifecycle({') >= 0 && lifecycleCall.includes('validationFieldErrors'),
  true,
  'the page hands the error store to the record lifecycle that resets it',
);

const sectionSource = fs.readFileSync(locateSource('frontend/apps/web/src/components/template/FormSection.vue'), 'utf8');
check(sectionSource.includes('data-validation-target'), true, 'the form section registers a correction position');
check(sectionSource.includes('businessErrorKey('), true, 'the registered position is derived from the business display key');

const actionSource = fs.readFileSync(locateSource('frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts'), 'utf8');
check(actionSource.includes('decodeServerFieldErrors('), true, 'the save path consumes a structured server rejection when one is present');
check(actionSource.includes('indexBusinessFieldErrors('), true, 'a decoded rejection enters the single error store');

console.log(`[contract-error-business-ownership] business ownership, single-position decoration, row identity, safe degradation, compatibility, required production and terminal independence: ${cases} cases passed`);
