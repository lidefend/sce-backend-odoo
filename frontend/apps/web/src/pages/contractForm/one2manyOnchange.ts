import { contractGapError } from '../../app/contract/contractGap';
import { createOne2manyDraftRow, initOne2manyRowsFromRelationSource } from './one2manyUtils';
import type { One2ManyColumn, One2ManyInlineRow } from './types';

export function replayOne2manyOnchange(params: {
  rows: One2ManyInlineRow[]; commands: unknown; columns: One2ManyColumn[]; primary: string; makeKey: () => string;
}): One2ManyInlineRow[] {
  const fail = (): never => { throw contractGapError({ kind: 'contract_defect', missing: 'one2many.onchange_command',
    requiredDeclarationLayer: 'P0:smart_core:onchange' }, '明细联动命令缺少合法身份、字段声明或当前行基线'); };
  const id = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
  const payload = (value: unknown): Record<string, unknown> => {
    if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).some(name => name === 'id' || !params.columns.some(column => column.name === name))) return fail();
    return value as Record<string, unknown>;
  };
  if (!Array.isArray(params.commands)) return fail();
  let rows = params.rows.map(row => ({ ...row, values: { ...row.values }, dirtyFields: [...row.dirtyFields] }));
  const virtual = (value: unknown): value is string => typeof value === 'string' && Boolean(value.trim());
  if (new Set(rows.map(row => row.key)).size !== rows.length) return fail();
  const deleted = new Set<number | string>();
  const target = (identity: unknown) => id(identity)
    ? rows.find(row => !row.isNew && row.id === identity)
    : virtual(identity) ? rows.find(row => row.isNew && row.key === identity) : undefined;
  const patchRow = (row: One2ManyInlineRow, value: unknown) => {
    const patch = payload(value);
    row.values = { ...row.values, ...patch };
    row.dirtyFields = [...new Set([...row.dirtyFields, ...Object.keys(patch)])]; row.dirty = true;
  };
  const link = (recordId: unknown) => {
    if (!id(recordId) || deleted.has(recordId)) return fail();
    let row = rows.find(item => item.id === recordId && !item.isNew);
    if (row) { row.removed = false; row.removalCommand = undefined; }
    else {
      row = initOne2manyRowsFromRelationSource({ source: [recordId], relationOptions: [], primary: params.primary })[0]!;
      if (rows.some(existing => existing.key === row!.key)) return fail();
      rows.push(row);
    }
    return row;
  };
  const set = (ids: unknown) => {
    if (!Array.isArray(ids) || !ids.every(id) || new Set(ids).size !== ids.length) return fail();
    rows = rows.filter(row => !row.isNew);
    rows.forEach(row => { if (!ids.includes(row.id)) { row.removed = true; row.removalCommand = row.removalCommand === 2 ? 2 : 3; row.dirty = true; } });
    ids.forEach(link);
    rows = [...ids.map(recordId => rows.find(row => row.id === recordId)!), ...rows.filter(row => row.removed)];
  };
  if (params.commands.every(id)) { set(params.commands); return rows; }
  for (const command of params.commands) {
    if (!Array.isArray(command)) return fail();
    const [op, recordId, value] = command;
    if (op === 0 && (recordId === 0 || virtual(recordId)) && command.length === 3) {
      const key = recordId === 0 ? params.makeKey() : recordId;
      if (!virtual(key) || deleted.has(key)) return fail();
      const existing = rows.find(row => row.key === key);
      if (existing) {
        if (recordId === 0 || !existing.isNew || existing.removed) return fail();
        patchRow(existing, value);
      } else rows.push(createOne2manyDraftRow({ key, primary: params.primary, columns: params.columns, defaults: payload(value) }));
    } else if (op === 1 && (id(recordId) || virtual(recordId)) && command.length === 3) {
      const row = target(recordId);
      if (!row || row.removed || deleted.has(recordId)) return fail();
      patchRow(row, value);
    } else if ((op === 2 || op === 3) && (id(recordId) || virtual(recordId)) && (command.length === 2 || command.length === 3 && value === 0)) {
      const row = target(recordId);
      if (!row || deleted.has(recordId)) return fail();
      if (row.isNew) {
        rows = rows.filter(item => item !== row);
        deleted.add(recordId);
      } else {
        row.removed = true; row.removalCommand = op; row.dirty = true;
        if (op === 2) deleted.add(recordId);
      }
    } else if (op === 4 && (command.length === 2 || command.length === 3)) {
      let data: Record<string, unknown> | undefined;
      if (command.length === 3 && value !== 0) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) return fail();
        const raw = value as Record<string, unknown>;
        if (Object.prototype.hasOwnProperty.call(raw, 'id') && raw.id !== recordId) return fail();
        const { id: _identity, ...fields } = raw;
        data = payload(fields);
      }
      const row = link(recordId);
      // Native LINK data describes the persisted baseline, not an UPDATE.
      if (data) {
        const baseline = Object.fromEntries(Object.entries(data).filter(([name]) => !row.dirtyFields.includes(name)));
        row.values = { ...row.values, ...baseline, id: row.id };
      }
    } else if (op === 5 && recordId === 0 && (command.length === 2 || command.length === 3 && value === 0)) set([]);
    else if (op === 6 && recordId === 0 && command.length === 3) set(value);
    else return fail();
  }
  return rows;
}
