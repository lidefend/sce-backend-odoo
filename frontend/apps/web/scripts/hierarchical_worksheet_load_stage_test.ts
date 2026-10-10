import { strict as assert } from 'node:assert';
import {
  ContractGapError,
  loadHierarchicalWorksheet,
  type WorksheetHierarchyConfig,
  type WorksheetLoadResult,
  type WorksheetSheetConfig,
} from '../src/app/action_runtime/hierarchicalWorksheetDataSource';

// These cases bind the declared load staging to actual behaviour: a worksheet is
// "ready" once its first batch is usable, and whole-table continuation is a
// separate background progress. They assert ordering and row identity, never a
// selector string.

type Row = Record<string, unknown>;

function rows(count: number, offset: number): Row[] {
  return Array.from({ length: count }, (_value, index) => ({ id: offset + index + 1, name: `row-${offset + index + 1}` }));
}

const sheetGroupsHierarchy: WorksheetHierarchyConfig = {
  navigation_mode: 'sheet_groups',
  navigation_groups: [{ field: 'project_id', label: '项目', empty_label: '未归属项目' }],
  model: '',
  fields: [],
  parent_field: '',
  project_field: '',
  code_field: 'code',
  label_field: 'name',
  type_field: 'type',
  leaf_values: [],
  group_field_map: {},
  domain: [],
  order: 'id asc',
  navigation_depth: 4,
};

const relationHierarchy: WorksheetHierarchyConfig = {
  ...sheetGroupsHierarchy,
  navigation_mode: 'relation',
  navigation_groups: [],
  model: 'project.project',
  fields: ['id', 'name'],
  parent_field: 'parent_id',
};

// Deliberately omits `page_size`: the fail-closed cases depend on the contract gap
// being real, while every load case that expects data passes a declared value.
const sheet: WorksheetSheetConfig = {
  model: 'construction.contract',
  fields: ['id', 'name'],
  binding_field: '',
  ordinal_field: '',
  presentation_mode: 'source_order',
  row_kind_field: '',
  item_values: [],
  heading_values: [],
  summary_values: [],
  variance_field: '',
  variance_tolerance: 0,
  blank_fields_by_kind: {},
  domain: [],
  order: 'id asc',
};

function limitsSource(total: number, limits: number[]) {
  return async (params: { offset: number; limit: number; model: string }) => {
    const offset = Number(params.offset || 0);
    const limit = Number(params.limit || 0);
    limits.push(limit);
    const size = Math.max(0, Math.min(limit, total - offset));
    return { records: rows(size, offset), total } as unknown as { records: Row[] };
  };
}

function pagedSource(total: number, log: string[], gapMs = 0) {
  return async (params: { offset: number; limit: number; model: string }) => {
    const offset = Number(params.offset || 0);
    const limit = Number(params.limit || 0);
    const size = Math.max(0, Math.min(limit, total - offset));
    log.push(`request:${params.model}@${offset}+${limit}->${size}`);
    if (gapMs) await new Promise((resolve) => setTimeout(resolve, gapMs));
    return { records: rows(size, offset), total } as unknown as { records: Row[] };
  };
}

async function caseFirstBatchIsReadyBeforeWholeTable(): Promise<void> {
  const log: string[] = [];
  const usable: WorksheetLoadResult[] = [];
  const result = await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    sheet,
    { onUsable: (value) => usable.push(value) },
    { list: pagedSource(7, log) as never, firstPageLimit: 3, drainPageLimit: 3, drainBatchYieldMs: 0 },
  );
  assert.equal(usable.length, 1, 'first batch must publish exactly one usable result');
  assert.equal(usable[0].sourceRows.length, 3, 'usable result carries only the arrived first batch');
  assert.equal(usable[0].recordCount, 3, 'usable record count reflects the arrived rows');
  assert.equal(result.sourceRows.length, 7, 'the resolved result still carries the whole table');
  assert.equal(result.recordCount, 7, 'the resolved record count is the whole-table count');
  assert.equal(log.filter((entry) => entry.startsWith('request:construction.contract')).length, 3, 'drain keeps paging until the table is exhausted');
  assert.equal(log[0], 'request:construction.contract@0+3->3', 'the first request is the bounded first page, not the whole-table page');
}

async function caseUsableFiresOnceWhileDraining(): Promise<void> {
  const log: string[] = [];
  let usableCount = 0;
  let firstUsableAtRequest = -1;
  await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    sheet,
    { onUsable: () => { usableCount += 1; firstUsableAtRequest = log.length; } },
    { list: pagedSource(20, log) as never, firstPageLimit: 2, drainPageLimit: 2, drainBatchYieldMs: 0 },
  );
  assert.equal(usableCount, 1, 'background continuation must not re-declare usability');
  assert.equal(firstUsableAtRequest, 1, 'usability is declared at the first batch, before later batches arrive');
}

async function caseRelationModeWaitsForBothFirstBatches(): Promise<void> {
  const log: string[] = [];
  const usable: WorksheetLoadResult[] = [];
  await loadHierarchicalWorksheet(
    relationHierarchy,
    sheet,
    { onUsable: (value) => usable.push(value) },
    { list: pagedSource(1, log) as never, firstPageLimit: 1, drainPageLimit: 1, drainBatchYieldMs: 0 },
  );
  assert.equal(usable.length, 1, 'relation worksheets declare usability once both streams are usable');
  assert.equal(usable[0].roots.length, 1, 'usability requires the hierarchy batch too');
  assert.equal(usable[0].sourceRows.length, 1, 'usability carries the arrived sheet batch');
}

async function caseEmptySheetDeclaresEmptyUsable(): Promise<void> {
  const log: string[] = [];
  const usable: WorksheetLoadResult[] = [];
  const result = await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    sheet,
    { onUsable: (value) => usable.push(value) },
    { list: pagedSource(0, log) as never, firstPageLimit: 5, drainPageLimit: 5, drainBatchYieldMs: 0 },
  );
  assert.equal(usable.length, 1, 'an empty first page is still a usable (empty) surface');
  assert.equal(usable[0].sourceRows.length, 0, 'empty declaration carries no rows');
  assert.equal(result.sourceRows.length, 0, 'empty table resolves with no rows');
}

async function caseBackgroundDrainYieldsBetweenBatches(): Promise<void> {
  const log: string[] = [];
  const started = Date.now();
  const result = await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    sheet,
    {},
    { list: pagedSource(4, log) as never, firstPageLimit: 2, drainPageLimit: 2, drainBatchYieldMs: 60 },
  );
  const elapsed = Date.now() - started;
  // Offset pagination without a server total learns "table exhausted" only from a
  // short batch, so an exact page multiple needs one extra probe request. Assert on
  // arrived row identity and on data batches, not on the probe's existence.
  const dataBatches = log.filter((entry) => !entry.endsWith('->0'));
  assert.equal(dataBatches.length, 2, 'two data batches cover the table');
  assert.ok(log.length > dataBatches.length, 'an exhaustion probe confirms an exact page boundary ended the table');
  assert.deepEqual(result.sourceRows.map((row) => row.id), [1, 2, 3, 4], 'the drain resolves every row exactly once');
  assert.ok(elapsed >= 100, `background drain must yield between batches (elapsed=${elapsed}ms)`);
}

async function caseDeclaredPageSizeDrivesFirstBatch(): Promise<void> {
  const limits: number[] = [];
  const usable: WorksheetLoadResult[] = [];
  const declared: WorksheetSheetConfig = { ...sheet, page_size: 120 };
  const result = await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    declared,
    { onUsable: (value) => usable.push(value) },
    { list: limitsSource(40, limits) as never, drainPageLimit: 2, drainBatchYieldMs: 0 },
  );
  assert.equal(limits[0], 120, 'the first request consumes the contract-declared page size');
  assert.equal(usable.length, 1, 'a declared first page still declares usability once');
  assert.equal(usable[0].sourceRows.length, 40, 'a declared page larger than the table is usable in one batch');
  assert.equal(result.recordCount, 40, 'the declared page size never truncates the resolved table');
}

async function caseMissingDeclaredPageSizeStopsTheSurface(): Promise<void> {
  const limits: number[] = [];
  let defect: { kind: string; missing: string } | null = null;
  await assert.rejects(
    loadHierarchicalWorksheet(
      sheetGroupsHierarchy,
      sheet,
      {},
      { list: limitsSource(1, limits) as never, drainPageLimit: 5, drainBatchYieldMs: 0 },
    ),
    (error: unknown) => {
      if (!(error instanceof ContractGapError)) return false;
      defect = error.defect;
      return true;
    },
    'a surface whose contract omits page_size must stop instead of defaulting',
  );
  assert.equal(limits.length, 0, 'the stopped surface must not issue a request with an invented page size');
  assert.equal(defect?.kind, 'contract_defect', 'a missing declaration is reported as a contract defect');
  assert.equal(defect?.missing, 'config.sheet.page_size', 'the defect names the exact missing declaration');
}

async function caseInvalidDeclaredPageSizeStopsTheSurface(): Promise<void> {
  for (const invalid of [0, -5, Number.NaN]) {
    const limits: number[] = [];
    await assert.rejects(
      loadHierarchicalWorksheet(
        sheetGroupsHierarchy,
        { ...sheet, page_size: invalid as unknown as number },
        {},
        { list: limitsSource(1, limits) as never, drainPageLimit: 5, drainBatchYieldMs: 0 },
      ),
      ContractGapError,
      `an invalid declared page size (${String(invalid)}) must stop the surface`,
    );
    assert.equal(limits.length, 0, 'an invalid declaration must not be replaced by a fallback');
  }
}

async function caseDeclaredPageSizeIsConsumedWithoutFrontendClamping(): Promise<void> {
  const limits: number[] = [];
  await loadHierarchicalWorksheet(
    sheetGroupsHierarchy,
    { ...sheet, page_size: 9999 },
    {},
    { list: limitsSource(1, limits) as never, drainPageLimit: 5, drainBatchYieldMs: 0 },
  );
  assert.equal(limits[0], 9999, 'the frontend consumes the declared value verbatim instead of clamping it');
  assert.equal(limits.length, 1, 'a declared page larger than the table finishes in one batch');
}

async function caseFirstBatchFailureDoesNotDeclareUsable(): Promise<void> {
  let usable = 0;
  await assert.rejects(
    loadHierarchicalWorksheet(
      sheetGroupsHierarchy,
      sheet,
      { onUsable: () => { usable += 1; } },
      {
        list: (async () => { throw new Error('list failed'); }) as never,
        firstPageLimit: 2,
        drainPageLimit: 2,
        drainBatchYieldMs: 0,
      },
    ),
    /list failed/,
  );
  assert.equal(usable, 0, 'a failed first batch must not declare the surface usable');
}

await caseFirstBatchIsReadyBeforeWholeTable();
await caseUsableFiresOnceWhileDraining();
await caseRelationModeWaitsForBothFirstBatches();
await caseEmptySheetDeclaresEmptyUsable();
await caseBackgroundDrainYieldsBetweenBatches();
await caseDeclaredPageSizeDrivesFirstBatch();
await caseMissingDeclaredPageSizeStopsTheSurface();
await caseInvalidDeclaredPageSizeStopsTheSurface();
await caseDeclaredPageSizeIsConsumedWithoutFrontendClamping();
await caseFirstBatchFailureDoesNotDeclareUsable();

console.log('[hierarchical_worksheet_load_stage_test] PASS cases=10');
