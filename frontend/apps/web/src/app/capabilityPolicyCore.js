import { getRequiredCapabilities, normalizeCapabilities } from './capabilityCore.js';

// Contract-2.0-Spec section 2.0: `system.init` capabilities/tiles publish the
// unified capability availability (`capability_state` + `capability_state_reason`)
// and the renderer must not infer that state.  The vocabulary below is therefore
// the authority; the renderer state names are only a presentation mapping of it.
export const CONTRACT_CAPABILITY_STATES = Object.freeze([
  'allow',
  'readonly',
  'deny',
  'pending',
  'coming_soon',
]);

// Total, declared mapping from the contract vocabulary to the renderer states.
export const CONTRACT_STATE_TO_POLICY_STATE = Object.freeze({
  allow: 'enabled',
  readonly: 'enabled',
  deny: 'disabled_permission',
  pending: 'disabled_capability',
  coming_soon: 'disabled_capability',
});

const POLICY_STATE_SEVERITY = Object.freeze({
  enabled: 0,
  disabled_capability: 1,
  disabled_permission: 2,
});

export function normalizeContractCapabilityState(value) {
  const state = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return Object.prototype.hasOwnProperty.call(CONTRACT_STATE_TO_POLICY_STATE, state) ? state : '';
}

// Read the projected capability state for one capability key from the runtime
// capability catalog that the contract published in `system.init`.
export function projectedCapabilityMeta(capability, catalog) {
  const key = typeof capability === 'string' ? capability.trim() : '';
  if (!key || !catalog || typeof catalog !== 'object') return null;
  const meta = catalog[key];
  if (!meta || typeof meta !== 'object') return null;
  const state = normalizeContractCapabilityState(meta.capability_state)
    || normalizeContractCapabilityState(meta.state);
  if (!state) return null;
  return {
    state,
    reasonCode: String(meta.reason_code || meta.capability_state_reason || '').trim(),
    reason: String(meta.reason || '').trim(),
  };
}

function resolveCapability(capability, options) {
  const projected = projectedCapabilityMeta(capability, options.catalog);
  if (projected) {
    return {
      key: capability,
      state: projected.state,
      reasonCode: projected.reasonCode,
      reason: projected.reason,
      authority: 'contract',
    };
  }
  // Residual path: the capability is not in the runtime catalog, so the
  // contract grant set itself is the authority ("not granted to this
  // principal").  This preserves the historic "capability not opened"
  // presentation instead of turning an absent grant into a permission error.
  const available = Array.isArray(options.available) ? options.available : [];
  return {
    key: capability,
    state: available.includes(capability) ? 'allow' : 'deny_ungranted',
    reasonCode: '',
    reason: '',
    authority: 'contract-grant',
  };
}

function rendererStateFor(row) {
  if (row.state === 'deny_ungranted') return 'disabled_capability';
  return CONTRACT_STATE_TO_POLICY_STATE[row.state] || 'enabled';
}

export function evaluateCapabilityPolicy(options = {}) {
  const required = normalizeCapabilities(
    options.required ?? getRequiredCapabilities(options.source),
  );
  const rows = required.map((capability) => resolveCapability(capability, options));

  const groups = Array.isArray(options.groups) ? options.groups : [];
  const userGroups = Array.isArray(options.userGroups) ? options.userGroups : [];
  const groupDenied = groups.length > 0 && !groups.some((group) => userGroups.includes(group));

  let state = 'enabled';
  for (const row of rows) {
    const rowState = rendererStateFor(row);
    if (POLICY_STATE_SEVERITY[rowState] > POLICY_STATE_SEVERITY[state]) state = rowState;
  }
  if (groupDenied && POLICY_STATE_SEVERITY.disabled_permission > POLICY_STATE_SEVERITY[state]) {
    state = 'disabled_permission';
  }

  const blocking = rows.filter((row) => rendererStateFor(row) !== 'enabled');
  const reasonRow = blocking.find((row) => row.state === 'deny') || blocking[0] || null;
  return {
    state,
    missing: blocking.map((row) => row.key),
    reason_code: reasonRow ? reasonRow.reasonCode : '',
    reason: reasonRow ? reasonRow.reason : '',
    authority: blocking.some((row) => row.authority === 'contract-grant')
      ? 'contract-grant'
      : 'contract',
  };
}

export function capabilityTooltip(policy) {
  const contractReason = String((policy && (policy.reason_code || policy.reason)) || '').trim();
  if (policy && policy.state === 'disabled_capability') {
    if (contractReason) return contractReason;
    return `Missing capabilities: ${(policy.missing || []).join(', ')}`;
  }
  if (policy && policy.state === 'disabled_permission') {
    return contractReason || 'Permission required';
  }
  return '';
}
