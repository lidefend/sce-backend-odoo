import {
  ACCEPTED_CONTRACT_VERSIONS,
  CLIENT_CONTRACT_CAPABILITIES,
  CONTRACT_VERSION,
  type ContractDictionary,
} from './types';

export function contractClientDeclaration(): ContractDictionary {
  return {
    contractVersion: CONTRACT_VERSION,
    clientType: 'web_pc',
    accepted_contract_versions: [...ACCEPTED_CONTRACT_VERSIONS],
    client_contract_capabilities: [...CLIENT_CONTRACT_CAPABILITIES],
    // Keep the established snake_case keys while the backend completes v2 negotiation.
    client_type: 'web_pc',
    delivery_profile: 'full',
  };
}
