export type ContractCarrierCapability =
  | 'page_block_data.v1'
  | 'attachment_fact.v1'
  | 'page_block_action.v1';

export interface ContractCarrierCapabilityRow {
  schemaVersion: '1.0.0';
  enabled: boolean;
}

export interface ContractCarrierCapabilities {
  negotiationVersion: string;
  status: 'legacy' | 'current';
  contractVersion: string;
  pageOrchestrationVersion: string;
  carriers: Record<ContractCarrierCapability, ContractCarrierCapabilityRow>;
}

const EXPECTED_CARRIERS: readonly ContractCarrierCapability[] = [
  'page_block_data.v1',
  'attachment_fact.v1',
  'page_block_action.v1',
];
const ALLOWED_KEYS = new Set([
  'negotiationVersion',
  'status',
  'clientType',
  'compatibilityMode',
  'acceptedContractVersions',
  'clientContractCapabilities',
  'contractVersion',
  'pageOrchestrationVersion',
  'carriers',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function decodeContractCarrierCapabilities(raw: unknown): ContractCarrierCapabilities {
  if (!isRecord(raw)) throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID');
  const unknownKey = Object.keys(raw).find((key) => !ALLOWED_KEYS.has(key));
  if (unknownKey) {
    throw new Error(`CONTRACT_CARRIER_CAPABILITIES_INVALID:${unknownKey}`);
  }
  const carriersRaw = raw.carriers;
  if (!isRecord(carriersRaw)) throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID');
  const keys = Object.keys(carriersRaw).sort();
  if (keys.join('|') !== [...EXPECTED_CARRIERS].sort().join('|')) {
    throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID');
  }
  const carriers = {} as Record<ContractCarrierCapability, ContractCarrierCapabilityRow>;
  EXPECTED_CARRIERS.forEach((carrier) => {
    const row = carriersRaw[carrier];
    if (
      !isRecord(row)
      || row.schemaVersion !== '1.0.0'
      || typeof row.enabled !== 'boolean'
    ) {
      throw new Error(`CONTRACT_CARRIER_CAPABILITIES_INVALID:${carrier}`);
    }
    carriers[carrier] = { schemaVersion: '1.0.0', enabled: row.enabled };
  });
  const status = raw.status;
  if (status !== 'legacy' && status !== 'current') {
    throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID:status');
  }
  if (raw.negotiationVersion !== '1.0.0') {
    throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID:negotiationVersion');
  }
  const contractVersion = String(raw.contractVersion || '').trim();
  const pageOrchestrationVersion = String(raw.pageOrchestrationVersion || '').trim();
  if (!contractVersion || !pageOrchestrationVersion) {
    throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID:version');
  }
  const expected = status === 'legacy'
    ? {
      contractVersion: '2.5.0',
      pageOrchestrationVersion: '2.0.0',
      pageBlockData: false,
    }
    : {
      contractVersion: '2.6.0',
      pageOrchestrationVersion: '2.1.0',
      pageBlockData: true,
    };
  if (
    contractVersion !== expected.contractVersion
    || pageOrchestrationVersion !== expected.pageOrchestrationVersion
    || carriers['page_block_data.v1'].enabled !== expected.pageBlockData
    || carriers['attachment_fact.v1'].enabled
    || carriers['page_block_action.v1'].enabled
  ) {
    throw new Error('CONTRACT_CARRIER_CAPABILITIES_INVALID:combination');
  }
  return {
    negotiationVersion: '1.0.0',
    status,
    contractVersion,
    pageOrchestrationVersion,
    carriers,
  };
}
