import assert from 'node:assert/strict';
import { relationEntry, relationOptionsLimit, relationOptionsSearchLimit } from '../src/pages/contractForm/relationDescriptor';
import { ContractGapError } from '../src/app/contract/contractGap';

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
    ...(relationEntryShape ? { relation_entry: relationEntryShape } : {}),
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
    thrown instanceof ContractGapError,
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
