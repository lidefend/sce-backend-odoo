import assert from 'node:assert/strict';
import {
  relationCreateMode,
  relationEntry,
  relationInlineCreate,
  relationModel,
  relationOptionFromRow,
  relationOptionsLimit,
  relationOptionsFromRecords,
  relationOptionsSearchLimit,
  relationOptionsWithSelectedFallback,
} from '../src/pages/contractForm/relationDescriptor';
import { parseMany2oneDisplay } from '../src/pages/contractForm/fieldUtils';
import { useRelationRuntime } from '../src/pages/contractForm/useRelationRuntime';
import { nativeNodeFieldDescriptor } from '../src/pages/contractForm/nativeLayoutUtils';
import { resolveContractV2FormFieldMap } from '../src/app/contracts/v2/store';
import { isContractGapError } from '../src/app/contract/contractGap';
import type { ContractGapError } from '../src/app/contract/contractGap';

// Behaviour lock for relation-entry option-volume consumption.
//
// Contract rule: `relation_entry.options_limit` / `options_search_limit` are
// declared by the backend assembler (page_assembler._build_relation_entry_for_field)
// and the frontend only projects/consumes them. The projection (`relationEntry`)
// must carry the declared values verbatim so the consumers stop with a
// ContractGapError when the declaration is missing. This test does NOT accept a
// string/constant appearing in the source as proof of correctness: it asserts the
// projected value equals the declaration and that a removed declaration is
// detected by the fail-closed stop.
//
// Baseline must be green first (declaration present → declared value consumed);
// only then do the removal cases prove the injection (a dropped declaration) is
// actually detected.

function descriptorWith(relationEntryShape: Record<string, unknown> | undefined) {
  return {
    name: 'project_id',
    type: 'many2one',
    relation: 'project.project',
    ...(relationEntryShape ? { relationEntry: relationEntryShape } : {}),
  } as never;
}

// Keys the options-volume consumers read off the projected relation entry.
// Kept explicit so the hand-maintained projection cannot silently drop one again.
const REQUIRED_PROJECTED_KEYS = ['options_limit', 'options_search_limit'] as const;

let checked = 0;

// ---- Baseline (declaration present, non-default values so a frontend fallback
// constant cannot masquerade as the declaration). -----------------------------
const DECLARED_LIMIT = 33;
const DECLARED_SEARCH_LIMIT = 17;
const baselineDescriptor = descriptorWith({
  model: 'project.project',
  can_read: true,
  options_limit: DECLARED_LIMIT,
  options_search_limit: DECLARED_SEARCH_LIMIT,
});

const baselineEntry = relationEntry(baselineDescriptor);
assert.ok(baselineEntry, 'baseline: a declared relation entry must project to a non-null entry');
assert.equal(relationModel(baselineDescriptor), 'project.project', 'matching relation target declarations must resolve once');
for (const key of REQUIRED_PROJECTED_KEYS) {
  assert.ok(
    Object.prototype.hasOwnProperty.call(baselineEntry as Record<string, unknown>, key),
    `baseline: projection must carry the consumed declaration key ${key}`,
  );
}
assert.equal(
  relationOptionsLimit(baselineEntry as Record<string, unknown>),
  DECLARED_LIMIT,
  'baseline: options_limit must equal the declared value, not a frontend constant',
);
assert.equal(
  relationOptionsSearchLimit(baselineEntry as Record<string, unknown>),
  DECLARED_SEARCH_LIMIT,
  'baseline: options_search_limit must equal the declared value, not a frontend constant',
);
checked += 1;

const conflictingTargetDescriptor = descriptorWith({
  model: 'res.partner',
  can_read: true,
  options_limit: DECLARED_LIMIT,
  options_search_limit: DECLARED_SEARCH_LIMIT,
});
let conflictingTargetError: unknown;
try {
  relationModel(conflictingTargetDescriptor);
} catch (error) {
  conflictingTargetError = error;
}
assert.ok(
  isContractGapError(conflictingTargetError),
  'conflicting relation target declarations must stop with ContractGapError',
);
assert.equal(
  (conflictingTargetError as ContractGapError).defect.missing,
  'field.project_id.relation_model_consistency',
  'the stop must name the conflicting relation target identity',
);
checked += 1;

const relationEntryContract = {
  model: 'res.partner',
  can_read: true,
  can_create: true,
  create_mode: 'quick',
  options_limit: DECLARED_LIMIT,
  options_search_limit: DECLARED_SEARCH_LIMIT,
  inline_create: {
    enabled: true,
    create_on_no_match: true,
    name_field: 'name',
    match: 'exact_label',
  },
};
const store = {
  widgetsByFieldCode: new Map([
    ['owner_id', {
      widgetId: 'field.owner_id',
      widgetType: 'many2one',
      fieldCode: 'owner_id',
      label: '负责人',
      semanticType: 'relation',
      componentConfig: {
        fieldType: 'many2one',
        relation: 'res.partner',
        relationEntry: relationEntryContract,
        widgetOptions: { color_field: 'color' },
      },
      fieldDescriptor: {
        fieldCode: 'owner_id',
        label: '负责人',
        fieldType: 'many2one',
        widgetType: 'many2one',
        semanticType: 'relation',
        relation: 'res.partner',
        relationEntry: relationEntryContract,
        widgetOptions: { color_field: 'color' },
      },
    }],
  ]),
} as never;
const storeField = resolveContractV2FormFieldMap(store).owner_id;
const storeEntry = relationEntry(storeField);
assert.ok(storeEntry, 'store projection: canonical relationEntry must survive the Store field map');
assert.equal(storeEntry.canRead, true, 'store projection: canRead must survive');
assert.equal(storeEntry.canCreate, true, 'store projection: canCreate must survive');
assert.equal(relationOptionsLimit(storeEntry as Record<string, unknown>), DECLARED_LIMIT);
assert.equal(relationOptionsSearchLimit(storeEntry as Record<string, unknown>), DECLARED_SEARCH_LIMIT);
assert.equal(relationCreateMode(storeField), 'quick', 'store projection: quick create must remain available');
assert.equal(relationInlineCreate(storeField).enabled, true, 'store projection: inline create must remain available');
assert.deepEqual(
  relationOptionsWithSelectedFallback([]),
  [],
  'store projection: selected IDs without authoritative labels must not synthesize a #id label',
);
const missingRelationLabel = (() => {
  try {
    relationOptionFromRow({ id: 42 }, descriptorWith({ model: 'project.project', can_read: true }));
  } catch (error) {
    return error;
  }
  return null;
})();
assert.ok(isContractGapError(missingRelationLabel), 'relation rows without an authoritative label must stop');
assert.equal(
  (missingRelationLabel as ContractGapError).defect.missing,
  'relation_option.42.label',
  'the stop must name the missing relation display label',
);
assert.equal(parseMany2oneDisplay(42), null, 'a bare many2one identity has no display label');
assert.equal(parseMany2oneDisplay([42, '']), null, 'an empty many2one display label is not a business label');
const relationRuntime = useRelationRuntime();
await assert.rejects(
  relationRuntime.queryRelationOptions({
    fieldName: 'project_id',
    keyword: '',
    relation: 'project.project',
    canRead: true,
    hasDynamicFallback: false,
    currentValue: null,
    optionsLimit: DECLARED_LIMIT,
    optionsSearchLimit: DECLARED_SEARCH_LIMIT,
    fetchOptions: async () => relationOptionsFromRecords(
      [{ id: 42 }],
      descriptorWith({ model: 'project.project', can_read: true }),
    ),
    isDeniedError: () => false,
  }),
  { name: 'ContractGapError' },
  'candidate loading must surface a missing relation label instead of swallowing the contract defect',
);
assert.equal(
  Object.prototype.hasOwnProperty.call(storeField as object, 'relation_entry'),
  false,
  'store projection: the canonical map must not emit a duplicate snake_case relation entry',
);
checked += 1;

// Native form nodes retain producer-side snake_case evidence. The boundary
// adapter must normalize that evidence once, so a complete wire contract is not
// misreported as a missing canonical relationEntry.
const nativeDescriptor = nativeNodeFieldDescriptor({
  name: 'project_id',
  fieldInfo: {
    name: 'project_id',
    type: 'many2one',
    relation: 'project.project',
    relation_entry: {
      model: 'project.project',
      can_read: true,
      options_limit: DECLARED_LIMIT,
      options_search_limit: DECLARED_SEARCH_LIMIT,
    },
  },
} as never, undefined, (name) => name);
const nativeEntry = relationEntry(nativeDescriptor);
assert.ok(nativeEntry, 'native adapter: producer evidence must normalize to canonical relationEntry');
assert.equal(
  relationOptionsLimit(nativeEntry as Record<string, unknown>),
  DECLARED_LIMIT,
  'native adapter: options_limit must survive normalization',
);
assert.equal(
  Object.prototype.hasOwnProperty.call(nativeDescriptor as object, 'relation_entry'),
  false,
  'native adapter: the canonical descriptor boundary must not retain a duplicate snake_case carrier',
);
checked += 1;

// ---- Removed declaration must be detected (fail-closed), not backfilled. ----
function expectStop(
  label: string,
  entry: Record<string, unknown> | null,
  run: (entry: Record<string, unknown> | null) => number,
  missing: string,
) {
  let thrown: unknown;
  try {
    run(entry);
  } catch (error) {
    thrown = error;
  }
  assert.ok(
    isContractGapError(thrown),
    `${label}: a missing declaration must stop with ContractGapError, got ${String(thrown)}`,
  );
  assert.equal(
    (thrown as ContractGapError).defect.missing,
    missing,
    `${label}: the stop must name the missing declaration path`,
  );
  assert.equal(
    (thrown as ContractGapError).defect.kind,
    'contract_defect',
    `${label}: the stop must be reported as a contract defect`,
  );
  assert.ok(
    String((thrown as ContractGapError).defect.requiredDeclarationLayer || '').includes('page_assembler'),
    `${label}: the stop must point back to the declaration layer that owns relation_entry`,
  );
  checked += 1;
}

// Case A: relation_entry present but the option-volume declarations absent.
const droppedDescriptor = descriptorWith({ model: 'project.project', can_read: true });
const droppedEntry = relationEntry(droppedDescriptor) as Record<string, unknown>;
assert.ok(droppedEntry, 'dependency injection: the projection itself must still be non-null');
expectStop('dropped options_limit', droppedEntry, relationOptionsLimit, 'relation_entry.options_limit');
expectStop('dropped options_search_limit', droppedEntry, relationOptionsSearchLimit, 'relation_entry.options_search_limit');

// Case B: illegal declaration (below the legal minimum) must also stop, not clamp.
const illegalDescriptor = descriptorWith({ model: 'project.project', can_read: true, options_limit: 0, options_search_limit: -5 });
const illegalEntry = relationEntry(illegalDescriptor) as Record<string, unknown>;
expectStop('illegal options_limit', illegalEntry, relationOptionsLimit, 'relation_entry.options_limit');
expectStop('illegal options_search_limit', illegalEntry, relationOptionsSearchLimit, 'relation_entry.options_search_limit');

// Case C: no relation entry at all must still stop (never a guessed default).
expectStop('absent relation_entry', relationEntry(descriptorWith(undefined)), relationOptionsLimit, 'relation_entry.options_limit');

console.log(`[relation_entry_option_limits_test] PASS cases=${checked} declared=${DECLARED_LIMIT}/${DECLARED_SEARCH_LIMIT}`);
