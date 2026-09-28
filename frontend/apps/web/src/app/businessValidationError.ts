/**
 * Business ownership of a validation error, independent of the client that
 * presents it.
 *
 * A business rule rejects a business value, never a page element. The rule
 * therefore reports the business goal it rejected: which business object
 * (model plus persisted record or unsaved draft), which field, and — for a
 * collection row — which row field. Every client maps that goal onto its own
 * rendering positions. The goal itself never mentions a DOM selector, a
 * component instance, a control prop, a tab index, a pixel offset or a web
 * occurrence key, so a form page and a step of another client present the same
 * error from the same facts.
 *
 * `businessErrorKey` is the page-local display key. It exists so the current
 * page can find the position it registered, and it stays derived from the row
 * identity the draft itself uses. It is rendering context only: it is never
 * business ownership and never an authorization input.
 */

export type BusinessErrorRowIdentity = {
  /** Collection field (a one2many field code, for example) that owns the row. */
  relationField: string;
  /** Persisted record id of the row; null while the row is an unsaved draft. */
  recordId: number | null;
  /** Stable draft row key: unchanged while the row is reordered or re-rendered. */
  rowKey: string;
  /** Sub-field (cell) code inside the row. */
  cellField: string;
};

export type BusinessErrorTarget = {
  /** Business model the rejected value belongs to. */
  model: string;
  /** Persisted record id; null means the unsaved draft of `model`. */
  recordId: number | null;
  /** Business field code (the data path), not a display position. */
  fieldCode: string;
  /** Row scope for a collection error; null for a record-level field. */
  row: BusinessErrorRowIdentity | null;
};

export type BusinessFieldError = {
  /** Rule identity. A stable machine code, never parsed out of the message. */
  code: string;
  /** Safe, user-facing hint. */
  message: string;
  target: BusinessErrorTarget;
  /** Local display context: the occurrence whose control produced the value. */
  sourceOccurrenceKey?: string;
};

export type BusinessErrorRecordScope = {
  model: string;
  recordId: number | null;
};

/** A page-local position decoded from a display key. Never a business target. */
export type BusinessErrorDisplayPosition = {
  key: string;
  fieldCode: string;
  rowKey: string;
  cellField: string;
};

export type BusinessErrorRowCell = {
  rowKey: unknown;
  cellField: unknown;
};

/** Rule identities this layer produces. A new rule adds a code here. */
export const BusinessErrorCodes = {
  REQUIRED_VALUE_MISSING: 'REQUIRED_VALUE_MISSING',
  ROW_KEY_DUPLICATE: 'ROW_KEY_DUPLICATE',
  BUSINESS_RULE_REJECTED: 'BUSINESS_RULE_REJECTED',
} as const;

function text(value: unknown): string {
  return String(value ?? '').trim();
}

export function normalizeBusinessRecordId(value: unknown): number | null {
  if (value === null || value === undefined || value === '' || value === false) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : null;
}

/**
 * Normalize a row identity, or refuse it.
 *
 * An identity that is missing its stable parts is not repaired: the caller
 * keeps the error at collection or form level instead of attaching it to a
 * guessed row. Row number, display text and first-column value are never used
 * as identity.
 */
export function normalizeBusinessRowIdentity(
  row?: Partial<BusinessErrorRowIdentity> | null,
): BusinessErrorRowIdentity | null {
  if (!row) return null;
  const relationField = text(row.relationField);
  const rowKey = text(row.rowKey);
  const cellField = text(row.cellField);
  if (!relationField || !rowKey || !cellField) return null;
  return { relationField, recordId: normalizeBusinessRecordId(row.recordId), rowKey, cellField };
}

export function createBusinessErrorTarget(input: {
  model: unknown;
  recordId?: unknown;
  fieldCode: unknown;
  row?: Partial<BusinessErrorRowIdentity> | null;
}): BusinessErrorTarget | null {
  const model = text(input?.model);
  const fieldCode = text(input?.fieldCode);
  if (!model || !fieldCode) return null;
  return {
    model,
    recordId: normalizeBusinessRecordId(input?.recordId),
    fieldCode,
    row: normalizeBusinessRowIdentity(input?.row ?? null),
  };
}

export function createBusinessFieldError(input: {
  code: unknown;
  message: unknown;
  target: BusinessErrorTarget | null;
  sourceOccurrenceKey?: unknown;
}): BusinessFieldError | null {
  const target = input?.target;
  const message = text(input?.message);
  if (!target || !message) return null;
  const sourceOccurrenceKey = text(input?.sourceOccurrenceKey);
  return {
    code: text(input?.code) || BusinessErrorCodes.BUSINESS_RULE_REJECTED,
    message,
    target,
    ...(sourceOccurrenceKey ? { sourceOccurrenceKey } : {}),
  };
}

/**
 * Page-local display key of one collection row cell.
 *
 * This is the single definition of the triple the collection renderer registers
 * on a cell, the store keys a cell error with, and the focus layer looks up.
 */
export function businessRowErrorKey(fieldCode: unknown, rowKey: unknown, cellField: unknown): string {
  const field = text(fieldCode);
  const row = text(rowKey);
  const cell = text(cellField);
  return field && row && cell ? [field, row, cell].join(':') : '';
}

/**
 * The page-local display key for a business target.
 *
 * A field-scoped error keeps the bare field code, exactly as the existing
 * consumers already look it up. A row error appends the stable row key and the
 * cell code.
 */
export function businessErrorKey(target: Pick<BusinessErrorTarget, 'fieldCode' | 'row'> | null | undefined): string {
  const fieldCode = text(target?.fieldCode);
  if (!fieldCode) return '';
  const row = target?.row ? normalizeBusinessRowIdentity(target.row) : null;
  return row ? businessRowErrorKey(fieldCode, row.rowKey, row.cellField) : fieldCode;
}

/**
 * Decode a display key back into a local position.
 *
 * Unknown shapes return null so the caller degrades to a form-level message
 * rather than guessing a position. The result is a display position: it carries
 * no model, record or field ownership.
 */
export function parseBusinessErrorDisplayPosition(key: unknown): BusinessErrorDisplayPosition | null {
  const raw = text(key);
  if (!raw) return null;
  const parts = raw.split(':');
  if (parts.length === 1) return { key: raw, fieldCode: parts[0], rowKey: '', cellField: '' };
  if (parts.length !== 3) return null;
  const [fieldCode, rowKey, cellField] = parts;
  if (!fieldCode || !rowKey || !cellField) return null;
  return { key: raw, fieldCode, rowKey, cellField };
}

/**
 * Record-scope ownership: the error is about this model and this record or
 * draft. An error that cannot state its own model never matches, so switching
 * record leaves the previous record's errors unable to reach the new draft.
 */
export function errorOwnsRecordScope(
  error: BusinessFieldError | null | undefined,
  scope: BusinessErrorRecordScope,
): boolean {
  const target = error?.target;
  const model = text(target?.model);
  if (!model || model !== text(scope?.model)) return false;
  return normalizeBusinessRecordId(target?.recordId) === normalizeBusinessRecordId(scope?.recordId);
}

/** Ownership of a record-level field (no row scope). */
export function errorOwnsField(
  error: BusinessFieldError | null | undefined,
  scope: BusinessErrorRecordScope & { fieldCode: unknown },
): boolean {
  const fieldCode = text(scope?.fieldCode);
  if (!fieldCode) return false;
  if (text(error?.target?.fieldCode) !== fieldCode) return false;
  if (error?.target?.row) return false;
  return errorOwnsRecordScope(error, scope);
}

/** Ownership of one collection row cell. */
export function errorOwnsRowCell(
  error: BusinessFieldError | null | undefined,
  scope: BusinessErrorRecordScope,
  cell: BusinessErrorRowCell,
): boolean {
  const rowKey = text(cell?.rowKey);
  const cellField = text(cell?.cellField);
  const row = error?.target?.row;
  if (!rowKey || !cellField || !row) return false;
  if (text(row.rowKey) !== rowKey || text(row.cellField) !== cellField) return false;
  return errorOwnsRecordScope(error, scope);
}

export function selectFieldErrorsForTarget(
  errors: Record<string, BusinessFieldError> | null | undefined,
  scope: BusinessErrorRecordScope & { fieldCode: unknown },
): BusinessFieldError[] {
  const fieldCode = text(scope?.fieldCode);
  if (!fieldCode) return [];
  return Object.values(errors || {}).filter((error) => errorOwnsField(error, scope));
}

export function selectRowCellError(
  errors: Record<string, BusinessFieldError> | null | undefined,
  scope: BusinessErrorRecordScope,
  cell: BusinessErrorRowCell,
): BusinessFieldError | null {
  return Object.values(errors || {}).find((error) => errorOwnsRowCell(error, scope, cell)) || null;
}

/** Key of the field error a user edit clears: record-level, stable code. */
export function fieldErrorKeyForTarget(target: Pick<BusinessErrorTarget, 'fieldCode' | 'row'>): string {
  return businessErrorKey({ fieldCode: target?.fieldCode, row: null });
}

/**
 * Keep only the errors that still belong to the active record or draft.
 *
 * Used when the record identity changes: an error produced for the previous
 * record must never decorate the newly opened one.
 */
export function retainErrorsForRecordScope(
  errors: Record<string, BusinessFieldError> | null | undefined,
  scope: BusinessErrorRecordScope,
): Record<string, BusinessFieldError> {
  const kept: Record<string, BusinessFieldError> = {};
  Object.values(errors || {}).forEach((error) => {
    if (!errorOwnsRecordScope(error, scope)) return;
    const key = businessErrorKey(error.target);
    if (key) kept[key] = error;
  });
  return kept;
}

/**
 * Decode a server payload that states field ownership, or return nothing.
 *
 * Only a payload that names the owning field is accepted. A response that
 * carries a business message without a field stays an operation-level error:
 * field ownership is never recovered from the message text, a field label or a
 * request parameter. Entries that do not state a usable target are dropped
 * rather than guessed, and the decoder never invents a row.
 *
 * The server of this product does not currently emit this payload; the decoder
 * exists so a structured rejection is used when it is present, and so a
 * compatible extension cannot silently become an unowned message.
 */
export function decodeServerFieldErrors(
  details: unknown,
  scope: BusinessErrorRecordScope,
): BusinessFieldError[] {
  if (!details || typeof details !== 'object') return [];
  const raw = (details as Record<string, unknown>).field_errors;
  if (!Array.isArray(raw)) return [];
  const errors: BusinessFieldError[] = [];
  raw.forEach((entry) => {
    if (!entry || typeof entry !== 'object') return;
    const record = entry as Record<string, unknown>;
    const fieldCode = text(record.field_code ?? record.fieldCode);
    if (!fieldCode) return;
    const rowSource = record.row && typeof record.row === 'object'
      ? record.row as Record<string, unknown>
      : null;
    const row = rowSource
      ? normalizeBusinessRowIdentity({
        relationField: text(rowSource.relation_field),
        recordId: normalizeBusinessRecordId(rowSource.record_id),
        rowKey: text(rowSource.row_key),
        cellField: text(rowSource.cell_field),
      })
      : null;
    // A rejection that declares a row but does not identify it is dropped: it is
    // never re-scoped onto the relation field as if the whole collection were
    // rejected, because that would be an ownership the server did not state.
    if (rowSource && !row) return;
    const error = createBusinessFieldError({
      code: text(record.code),
      message: record.message,
      target: createBusinessErrorTarget({ model: scope.model, recordId: scope.recordId, fieldCode, row }),
    });
    if (!error) return;
    errors.push(error);
  });
  return errors;
}

/**
 * Re-key a decoded error list for the single error store.
 */
export function indexBusinessFieldErrors(
  errors: readonly BusinessFieldError[] | null | undefined,
): Record<string, BusinessFieldError> {
  const indexed: Record<string, BusinessFieldError> = {};
  (errors || []).forEach((error) => {
    const key = businessErrorKey(error.target);
    if (key) indexed[key] = error;
  });
  return indexed;
}
