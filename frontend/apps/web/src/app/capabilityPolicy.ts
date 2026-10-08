import { capabilityTooltip as capabilityTooltipCore, evaluateCapabilityPolicy as evaluateCapabilityPolicyCore } from './capabilityPolicyCore';

export type CapabilityPolicyState = 'enabled' | 'disabled_capability' | 'disabled_permission';

export type CapabilityPolicy = {
  state: CapabilityPolicyState;
  missing: string[];
  /** Contract `capability_state_reason` of the blocking capability, when published. */
  reason_code: string;
  reason: string;
  /** `contract` when the state came from the projected capability_state, `contract-grant` when read from the contract grant set. */
  authority: 'contract' | 'contract-grant';
};

export type CapabilityCatalog = Record<string, { capability_state?: unknown; state?: unknown; reason_code?: unknown; capability_state_reason?: unknown; reason?: unknown }>;

export function evaluateCapabilityPolicy(options: {
  source?: unknown;
  required?: string[];
  available?: string[] | null;
  groups?: string[];
  userGroups?: string[];
  catalog?: CapabilityCatalog | null;
}): CapabilityPolicy {
  return evaluateCapabilityPolicyCore(options) as CapabilityPolicy;
}

export function capabilityTooltip(policy: CapabilityPolicy) {
  return capabilityTooltipCore(policy);
}
