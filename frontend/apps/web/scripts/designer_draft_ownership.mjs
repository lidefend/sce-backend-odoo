// Ownership and authorization rules for the configuration drafts a designer run touches.
//
// The product resumes whichever draft its own scope rule finds. A runner therefore may
// neither assume that a draft it saved into was authored by this run, nor treat "an
// `open` request was emitted" as proof that a draft was created: `open` returns an
// existing draft by design. Ownership is proved by inventory exclusion only, and every
// operation on a draft that pre-existed the run needs an authorization that names that
// draft id and the operation.
export const DRAFT_OPERATIONS = ['stage', 'preview', 'publish', 'rollback', 'discard'];

const asPositiveId = (value) => {
  const id = Number.parseInt(String(value ?? '').trim(), 10);
  return Number.isInteger(id) && id > 0 ? id : 0;
};

// `FORM_LOWCODE_AUTHORIZED_DRAFT="163:stage,publish;192:discard"` binds an explicit draft
// id to the exact operations the operator authorizes. Anything unparsable is a refusal,
// never a silent default.
export function parseDraftAuthorization(raw) {
  const text = String(raw ?? '').trim();
  if (!text) return { entries: new Map(), error: null };
  const entries = new Map();
  for (const clause of text.split(';')) {
    const piece = clause.trim();
    if (!piece) continue;
    const [rawId, rawOps] = piece.split(':');
    const id = asPositiveId(rawId);
    if (!id) return { entries: new Map(), error: `invalid_authorized_draft_id:${piece}` };
    // A separator with nothing between it is a typo, not an empty grant: accepting it
    // would silently widen an authorization the operator never spelled out.
    const operations = String(rawOps ?? '').split(',').map((op) => op.trim());
    if (!operations.length || operations.some((op) => !op)) {
      return { entries: new Map(), error: `missing_authorized_operations:${piece}` };
    }
    const unknown = operations.filter((op) => !DRAFT_OPERATIONS.includes(op));
    if (unknown.length) return { entries: new Map(), error: `unknown_authorized_operation:${unknown.join(',')}` };
    entries.set(id, new Set(operations));
  }
  return { entries, error: null };
}

// A run may only write configuration when the inventory is present and every draft the
// product could resume is either authorized for this run or absent. A missing inventory
// is a refusal: unknown ownership must never degrade into "assume it is ours".
export function resolveDesignerDraftPolicy({ inventory, authorization } = {}) {
  const parsed = parseDraftAuthorization(authorization);
  if (parsed.error) {
    return { decision: 'fail_closed', reason: parsed.error, inventoryIds: [], blocking: [], allowed: {} };
  }
  if (!Array.isArray(inventory)) {
    return { decision: 'fail_closed', reason: 'designer_draft_inventory_missing', inventoryIds: [], blocking: [], allowed: {} };
  }
  const inventoryIds = inventory.map((row) => asPositiveId(row?.id)).filter(Boolean);
  const blocking = [];
  const allowed = {};
  for (const id of inventoryIds) {
    const operations = parsed.entries.get(id);
    if (!operations) blocking.push(id);
    else allowed[id] = [...operations];
  }
  const unmatched = [...parsed.entries.keys()].filter((id) => !inventoryIds.includes(id));
  if (unmatched.length) {
    return { decision: 'fail_closed', reason: `authorized_draft_not_in_inventory:${unmatched.join(',')}`,
      inventoryIds, blocking, allowed };
  }
  if (blocking.length) {
    return { decision: 'fail_closed', reason: `preexisting_designer_draft:${blocking.join(',')}`,
      inventoryIds, blocking, allowed };
  }
  return { decision: 'proceed', reason: null, inventoryIds, blocking, allowed };
}

// A draft that shows up after the inventory was taken belongs to somebody else: the run
// must stop before it writes into it.
export function resolvePreexistingDraftProbe({ existingIds = [], inventoryIds = [] } = {}) {
  const appeared = existingIds.map(asPositiveId).filter(Boolean).filter((id) => !inventoryIds.includes(id));
  if (appeared.length) return { decision: 'fail_closed', reason: `preexisting_designer_draft_appeared:${appeared.join(',')}`, ids: appeared };
  const resumed = existingIds.map(asPositiveId).filter(Boolean);
  return { decision: 'proceed', reason: null, ids: resumed };
}

// `ui.business_config.change_set.open` answers with the serialized draft when it resumes
// or creates one, and with `{change_set: null}` only when a read-only probe found
// nothing. Reading only `data.change_set` turned "a draft was found" into "no draft",
// so an unrecognised shape must be an error rather than an empty result.
export function resolveChangeSetOpenResponse({ body, intent = 'open' } = {}) {
  const data = body?.data ?? {};
  if (data.change_set === null) return { draft: null, shape: 'resume_only_miss', error: null };
  if (data.change_set && typeof data.change_set === 'object') return { draft: data.change_set, shape: 'nested_change_set', error: null };
  if (asPositiveId(data.id)) return { draft: data, shape: 'serialized_change_set', error: null };
  return { draft: null, shape: 'unrecognised', error: `unrecognised_change_set_open_shape:${intent}` };
}

// A run may only write configuration for a draft the product already holds. The probe
// tells us which draft the save will stage into, so the operation must be authorized
// *before* the save is clicked: refusing afterwards would already have written.
export function resolvePreWriteDraftGate({ probedIds = [], policy } = {}) {
  const ids = probedIds.map(asPositiveId).filter(Boolean);
  const unauthorized = ids.filter((id) => !isDraftOperationAllowed({ policy, changeSetId: id, operation: 'stage' }));
  if (unauthorized.length) {
    return { decision: 'fail_closed', reason: `probed_designer_draft_stage_not_authorized:${unauthorized.join(',')}`, ids: unauthorized };
  }
  return { decision: 'proceed', reason: null, ids };
}

// Ownership needs a positive credential from the side that made the decision: the
// product asked for a fresh draft (`fresh: true`) and the handler reports that it
// created one (`created: true`). Exclusion from the inventory is then only a
// consistency check, never the proof itself.
export function resolveDesignerDraftOwnership({ changeSetId, inventoryIds = [], created = false, freshRequested = false } = {}) {
  const id = asPositiveId(changeSetId);
  if (!id) return { release: false, reason: 'unidentified_change_set', created: Boolean(created), fresh_requested: Boolean(freshRequested) };
  if (created !== true || freshRequested !== true) {
    return { release: false, reason: 'creation_not_proven_by_this_run', created: Boolean(created), fresh_requested: Boolean(freshRequested) };
  }
  if (inventoryIds.includes(id)) {
    return { release: false, reason: 'preexisting_designer_draft_not_authored_by_run', created: true, fresh_requested: true };
  }
  return { release: true, reason: 'created_by_this_run', created: true, fresh_requested: true };
}

// A resumed draft must have been known before the save. One that the probe never saw
// cannot be proved to be ours, even though it is absent from the inventory.
export function resolveResumedDraftDecision({ changeSetId, probedIds = [], policy } = {}) {
  const id = asPositiveId(changeSetId);
  if (!id) return { decision: 'fail_closed', reason: 'unidentified_change_set' };
  if (!probedIds.map(asPositiveId).includes(id)) {
    return { decision: 'fail_closed', reason: `resumed_designer_draft_not_probed:${id}` };
  }
  for (const operation of ['stage', 'preview', 'publish', 'rollback']) {
    if (!isDraftOperationAllowed({ policy, changeSetId: id, operation })) {
      return { decision: 'fail_closed', reason: `resumed_designer_draft_${operation}_not_authorized:${id}` };
    }
  }
  return { decision: 'proceed', reason: null };
}

// Cleanup releases only ids this run authored; a set that still holds a foreign id is a
// refusal, because silently skipping it would hide the boundary that was crossed.
export function resolveCleanupRelease({ heldIds = [], inventoryIds = [] } = {}) {
  const foreign = heldIds.map(asPositiveId).filter(Boolean).filter((id) => inventoryIds.includes(id));
  if (foreign.length) return { decision: 'fail_closed', reason: `foreign_draft_in_cleanup_set:${foreign.join(',')}`, release: [], foreign };
  return { decision: 'proceed', reason: null, release: heldIds.map(asPositiveId).filter(Boolean), foreign: [] };
}

export function isDraftOperationAllowed({ policy, changeSetId, operation } = {}) {
  const id = asPositiveId(changeSetId);
  if (!id) return false;
  const operations = policy?.allowed?.[id];
  if (!operations) return false;
  return operations.includes(operation);
}
