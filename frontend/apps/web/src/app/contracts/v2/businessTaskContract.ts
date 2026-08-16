import type {
  BusinessTaskContractV1,
  BusinessTaskV1Blocker,
  BusinessTaskV1Capability,
  BusinessTaskV1Evidence,
  BusinessTaskV1Fact,
  BusinessTaskV1Input,
  BusinessTaskV1Relation,
  ContractV2Dictionary,
} from './types';

export type BusinessTaskDecodeIssue = { path: string; message: string };

const forbiddenTerminalKeys = new Set([
  'model', 'resmodel', 'viewtype', 'viewid', 'xmlid', 'notebook', 'modifier',
  'modifiers', 'odooaction', 'serveractionid',
]);

function record(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as ContractV2Dictionary
    : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function boolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function stringList(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) return null;
  return value.map((item) => item.trim()).filter(Boolean);
}

function terminalKeyToken(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function collectForbiddenKeys(value: unknown, path: string, issues: BusinessTaskDecodeIssue[]): void {
  if (Array.isArray(value)) {
    value.forEach((item, index) => collectForbiddenKeys(item, `${path}[${index}]`, issues));
    return;
  }
  if (!value || typeof value !== 'object') return;
  Object.entries(value as ContractV2Dictionary).forEach(([key, nested]) => {
    const nestedPath = `${path}.${key}`;
    if (forbiddenTerminalKeys.has(terminalKeyToken(key))) {
      issues.push({ path: nestedPath, message: 'native adapter vocabulary is forbidden' });
    }
    collectForbiddenKeys(nested, nestedPath, issues);
  });
}

function requiredText(source: ContractV2Dictionary, key: string, path: string, issues: BusinessTaskDecodeIssue[]): string {
  const value = text(source[key]);
  if (!value) issues.push({ path: `${path}.${key}`, message: 'is required' });
  return value;
}

function requiredBoolean(source: ContractV2Dictionary, key: string, path: string, issues: BusinessTaskDecodeIssue[]): boolean {
  const value = boolean(source[key]);
  if (value === null) issues.push({ path: `${path}.${key}`, message: 'must be a boolean' });
  return value === true;
}

function rows(source: ContractV2Dictionary, section: string, issues: BusinessTaskDecodeIssue[]): ContractV2Dictionary[] {
  const value = source[section];
  if (!Array.isArray(value) || value.some((item) => !item || typeof item !== 'object' || Array.isArray(item))) {
    issues.push({ path: `businessTaskContract.${section}`, message: 'must be an object array' });
    return [];
  }
  const seen = new Set<string>();
  return value.map((item, index) => {
    const row = record(item);
    const key = requiredText(row, 'key', `businessTaskContract.${section}[${index}]`, issues);
    if (key && seen.has(key)) {
      issues.push({ path: `businessTaskContract.${section}[${index}].key`, message: 'must be unique' });
    }
    seen.add(key);
    return row;
  });
}

function optionalCount(value: unknown, path: string, issues: BusinessTaskDecodeIssue[]): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    issues.push({ path, message: 'must be a non-negative number when present' });
    return null;
  }
  return value;
}

function optionalRequired(value: unknown, path: string, issues: BusinessTaskDecodeIssue[]): boolean | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'boolean') {
    issues.push({ path, message: 'must be a boolean when present' });
    return null;
  }
  return value;
}

export function decodeBusinessTaskContractV1(
  value: unknown,
  issues: BusinessTaskDecodeIssue[] = [],
): BusinessTaskContractV1 | null {
  const source = record(value);
  if (!Object.keys(source).length) {
    issues.push({ path: 'businessTaskContract', message: 'must be an object' });
    return null;
  }
  collectForbiddenKeys(source, 'businessTaskContract', issues);
  if (source.profile_version !== 'v1') {
    issues.push({ path: 'businessTaskContract.profile_version', message: 'must equal v1' });
  }

  const taskSource = record(source.task);
  const task = {
    key: requiredText(taskSource, 'key', 'businessTaskContract.task', issues),
    goal: requiredText(taskSource, 'goal', 'businessTaskContract.task', issues),
    outcome: requiredText(taskSource, 'outcome', 'businessTaskContract.task', issues),
    mode: requiredText(taskSource, 'mode', 'businessTaskContract.task', issues),
    stage: requiredText(taskSource, 'stage', 'businessTaskContract.task', issues),
    state: requiredText(taskSource, 'state', 'businessTaskContract.task', issues),
  };

  const facts: BusinessTaskV1Fact[] = rows(source, 'facts', issues).map((row, index) => ({
    key: text(row.key), label: text(row.label), importance: text(row.importance), group: text(row.group),
    presentation: row.presentation, value: row.value, valueState: text(row.value_state),
    sourceAuthority: requiredText(row, 'source_authority', `businessTaskContract.facts[${index}]`, issues),
    applicability: requiredText(row, 'applicability', `businessTaskContract.facts[${index}]`, issues),
  }));

  const inputs: BusinessTaskV1Input[] = rows(source, 'inputs', issues).map((row, index) => {
    const path = `businessTaskContract.inputs[${index}]`;
    const visible = requiredBoolean(row, 'visible', path, issues);
    const readonly = requiredBoolean(row, 'readonly', path, issues);
    const required = requiredBoolean(row, 'required', path, issues);
    if (required && !visible) issues.push({ path, message: 'a hidden input cannot be required' });
    return {
      key: text(row.key), label: text(row.label), group: text(row.group), inputKind: text(row.input_kind),
      help: text(row.help), value: row.value, visible, readonly, required,
      sourceAuthority: requiredText(row, 'source_authority', path, issues),
      applicability: requiredText(row, 'applicability', path, issues),
    };
  });

  const blockers: BusinessTaskV1Blocker[] = rows(source, 'blockers', issues).map((row, index) => {
    const path = `businessTaskContract.blockers[${index}]`;
    const active = requiredBoolean(row, 'active', path, issues);
    const reasonCode = text(row.reason_code);
    const message = text(row.message);
    const repairCapabilityKey = text(row.repair_capability_key);
    const missingItems = stringList(row.missing_items);
    if (active && !reasonCode) issues.push({ path: `${path}.reason_code`, message: 'is required for an active blocker' });
    if (active && !message) issues.push({ path: `${path}.message`, message: 'is required for an active blocker' });
    if (active && !repairCapabilityKey) issues.push({ path: `${path}.repair_capability_key`, message: 'is required for an active blocker' });
    if (missingItems === null) issues.push({ path: `${path}.missing_items`, message: 'must be a string array' });
    return {
      key: text(row.key), label: text(row.label), repairCapabilityKey, owner: text(row.owner), active,
      reasonCode, message, missingItems: missingItems || [],
      sourceAuthority: requiredText(row, 'source_authority', path, issues),
    };
  });

  const blockerKeys = new Set(blockers.map((row) => row.key));
  const activeBlockers = new Set(blockers.filter((row) => row.active).map((row) => row.key));
  const capabilities: BusinessTaskV1Capability[] = rows(source, 'capabilities', issues).map((row, index) => {
    const path = `businessTaskContract.capabilities[${index}]`;
    const blockedBy = stringList(row.blocked_by);
    if (blockedBy === null) issues.push({ path: `${path}.blocked_by`, message: 'must be a string array' });
    (blockedBy || []).filter((key) => !blockerKeys.has(key)).forEach((key) => {
      issues.push({ path: `${path}.blocked_by`, message: `references unknown blocker ${key}` });
    });
    const visible = requiredBoolean(row, 'visible', path, issues);
    const businessAvailable = requiredBoolean(row, 'business_available', path, issues);
    const authorizationAllowed = requiredBoolean(row, 'authorization_allowed', path, issues);
    const enabled = requiredBoolean(row, 'enabled', path, issues);
    const expectedEnabled = visible && businessAvailable && authorizationAllowed
      && !(blockedBy || []).some((key) => activeBlockers.has(key));
    if (enabled !== expectedEnabled) issues.push({ path: `${path}.enabled`, message: 'is inconsistent with authoritative verdicts' });
    const reasonCode = text(row.reason_code);
    if (!enabled && (!reasonCode || reasonCode.toUpperCase() === 'OK')) {
      issues.push({ path: `${path}.reason_code`, message: 'must explain a disabled capability' });
    }
    ['safety', 'idempotency', 'outcome', 'source_authority'].forEach((key) => requiredText(row, key, path, issues));
    return {
      key: text(row.key), label: text(row.label), presentation: text(row.presentation), safety: text(row.safety),
      idempotency: text(row.idempotency), outcome: text(row.outcome), blockedBy: blockedBy || [],
      handoff: text(row.handoff), visible, businessAvailable, authorizationAllowed, enabled,
      reasonCode, reason: text(row.reason), sourceAuthority: text(row.source_authority),
    };
  });
  if (capabilities.filter((row) => row.enabled && row.presentation === 'primary').length > 1) {
    issues.push({ path: 'businessTaskContract.capabilities', message: 'cannot contain multiple enabled primary capabilities' });
  }
  const capabilityKeys = new Set(capabilities.map((row) => row.key));
  blockers.filter((row) => row.active && !capabilityKeys.has(row.repairCapabilityKey)).forEach((row) => {
    issues.push({ path: 'businessTaskContract.blockers', message: `repair capability ${row.repairCapabilityKey} is missing` });
  });

  const evidence: BusinessTaskV1Evidence[] = rows(source, 'evidence', issues).map((row, index) => ({
    key: text(row.key), label: text(row.label), kind: text(row.kind), group: text(row.group), state: text(row.state),
    count: optionalCount(row.count, `businessTaskContract.evidence[${index}].count`, issues),
    required: optionalRequired(row.required, `businessTaskContract.evidence[${index}].required`, issues),
    sourceAuthority: requiredText(row, 'source_authority', `businessTaskContract.evidence[${index}]`, issues),
  }));
  const relations: BusinessTaskV1Relation[] = rows(source, 'relations', issues).map((row, index) => ({
    key: text(row.key), label: text(row.label), kind: text(row.kind), group: text(row.group), state: text(row.state),
    count: optionalCount(row.count, `businessTaskContract.relations[${index}].count`, issues), summary: text(row.summary),
    sourceAuthority: requiredText(row, 'source_authority', `businessTaskContract.relations[${index}]`, issues),
  }));

  const completionSource = record(source.completion);
  const complete = requiredBoolean(completionSource, 'complete', 'businessTaskContract.completion', issues);
  const nextCapabilityKey = text(completionSource.next_capability_key);
  const outcomeCode = requiredText(completionSource, 'outcome_code', 'businessTaskContract.completion', issues);
  if (complete && nextCapabilityKey) issues.push({ path: 'businessTaskContract.completion.next_capability_key', message: 'must be empty when complete' });
  if (!complete && !nextCapabilityKey) issues.push({ path: 'businessTaskContract.completion.next_capability_key', message: 'is required while incomplete' });
  if (nextCapabilityKey && !capabilityKeys.has(nextCapabilityKey)) {
    issues.push({ path: 'businessTaskContract.completion.next_capability_key', message: 'references an unknown capability' });
  }

  const traceSource = record(source.trace);
  const sourceAuthorities = stringList(traceSource.source_authorities);
  if (sourceAuthorities === null) {
    issues.push({ path: 'businessTaskContract.trace.source_authorities', message: 'must be a string array' });
  }
  const trace = {
    compiler: requiredText(traceSource, 'compiler', 'businessTaskContract.trace', issues),
    profileKey: requiredText(traceSource, 'profile_key', 'businessTaskContract.trace', issues),
    profileSha256: requiredText(traceSource, 'profile_sha256', 'businessTaskContract.trace', issues),
    semanticSupplySha256: requiredText(traceSource, 'semantic_supply_sha256', 'businessTaskContract.trace', issues),
    sourceAuthorities: sourceAuthorities || [],
    sealedContractSha256: requiredText(traceSource, 'sealed_contract_sha256', 'businessTaskContract.trace', issues),
  };
  if (![trace.profileSha256, trace.semanticSupplySha256, trace.sealedContractSha256]
    .every((value) => /^[0-9a-f]{64}$/.test(value))) {
    issues.push({ path: 'businessTaskContract.trace', message: 'sha256 fields must contain 64 hexadecimal characters' });
  }

  if (issues.length) return null;
  return {
    profileVersion: 'v1', task, facts, inputs, blockers, capabilities, evidence, relations,
    completion: { complete, nextCapabilityKey, outcomeCode }, trace,
  };
}

export type BusinessTaskPresentation = {
  task: BusinessTaskContractV1['task'];
  facts: BusinessTaskV1Fact[];
  inputs: BusinessTaskV1Input[];
  blockers: BusinessTaskV1Blocker[];
  capabilities: BusinessTaskV1Capability[];
  primaryCapability: BusinessTaskV1Capability | null;
  nextCapability: BusinessTaskV1Capability | null;
  evidence: BusinessTaskV1Evidence[];
  relations: BusinessTaskV1Relation[];
  completion: BusinessTaskContractV1['completion'];
};

export function presentBusinessTaskContract(contract: BusinessTaskContractV1): BusinessTaskPresentation {
  const capabilities = contract.capabilities.filter((row) => row.visible);
  const primaryCapability = capabilities.find((row) => row.enabled && row.presentation === 'primary') || null;
  const nextCapability = contract.completion.nextCapabilityKey
    ? capabilities.find((row) => row.key === contract.completion.nextCapabilityKey) || null
    : null;
  return {
    task: contract.task,
    facts: contract.facts.filter((row) => row.applicability !== 'not_applicable'),
    inputs: contract.inputs.filter((row) => row.visible),
    blockers: contract.blockers.filter((row) => row.active),
    capabilities,
    primaryCapability,
    nextCapability,
    evidence: contract.evidence,
    relations: contract.relations,
    completion: contract.completion,
  };
}
