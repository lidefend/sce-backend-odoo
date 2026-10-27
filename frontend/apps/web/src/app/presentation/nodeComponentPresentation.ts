import { contractGapError } from '../contract/contractGap';
import { NODE_COMPONENT_REGISTRATIONS, SEMANTIC_REGISTRY_ROWS } from './semantic_registry.generated';
import type { ContractV2Container, ContractV2Snapshot } from '../contracts/v2/types';

export type NodeComponentPresentation = {
  kind: 'feedback' | 'anchor';
  purpose?: 'advisory' | 'error' | 'warning' | 'explanation';
  content: string;
  visible: boolean;
  role?: 'alert' | 'status';
  targetContainerId?: string;
  visibilityOwner?: 'feedback_evaluation';
  parentVisible?: boolean;
};
function reject(path: string): never {
  throw contractGapError({ kind: 'contract_defect', missing: path,
    requiredDeclarationLayer: 'P0: verified node component contract' }, 'Invalid explicit node component');
}
function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function keys(value: unknown, expected: string[]): Record<string, unknown> {
  const row = object(value);
  if (Object.keys(row).length !== expected.length || expected.some((key) => !Object.hasOwn(row, key))) reject('componentConfig');
  return row;
}

function compiledCondition(value: unknown, dynamic: boolean): boolean {
  if (typeof value === 'boolean') return !dynamic;
  const row = object(value);
  if (row.kind === 'static') return !dynamic && typeof row.value === 'boolean';
  if (row.kind === 'not') return compiledCondition(row.expr, dynamic);
  if (row.kind === 'field_truthy') return typeof row.field === 'string' && !!row.field;
  if (row.kind === 'field_compare') return typeof row.field === 'string' && !!row.field
    && ['=', '==', '!=', '>', '>=', '<', '<=', 'in', 'not in'].includes(String(row.operator)) && Object.hasOwn(row, 'value');
  if (['all', 'any'].includes(String(row.kind)) && Array.isArray(row.exprs)) return row.exprs.length > 0 && row.exprs.every((expr) => compiledCondition(expr, dynamic));
  return false;
}
function nativeIdentity(node: ContractV2Container) {
  return !!node.nativeLocator && Number.isInteger(node.occurrenceIndex) && Number(node.occurrenceIndex) > 0
    && !!node.sourceAuthority && Object.keys(node.sourceAuthority).length > 0;
}

/** Pure projection of the received snapshot; never evaluate business activation locally. */
export type FeedbackEvaluationOverride = {
  status: 'describing' | 'pending' | 'ready' | 'unavailable';
  content: string;
  visible: boolean;
  binding?: { container_id: string };
};

export function projectNodeComponents(
  snapshot: Pick<ContractV2Snapshot, 'layoutContract' | 'statusContract' | 'dataContract'>,
  feedbackEvaluations?: ReadonlyMap<string, FeedbackEvaluationOverride>,
) {
  const rows: {node: ContractV2Container; ancestors: string[]; visible: boolean; parentVisible: boolean}[] = [];
  const statuses = new Map(snapshot.statusContract.containerStatus.map((s) => [s.containerId, s]));
  function visit(nodes: ContractV2Container[], ancestors: string[], parentVisible: boolean) {
    for (const node of nodes) {
      const status = statuses.get(node.containerId);
      const visible = parentVisible && node.visible !== false && status?.visible !== false;
      rows.push({node, ancestors, visible, parentVisible});
      visit(node.children || [], [...ancestors, node.containerId], visible);
    }
  }
  visit(snapshot.layoutContract.containerTree, [], true);
  const unique = (id: unknown) => {
    const found = rows.filter((r) => r.node.containerId === id);
    if (typeof id !== 'string' || !id || found.length !== 1) reject('node reference identity');
    return found[0];
  };
  const presentations = new Map<string, NodeComponentPresentation>();
  const ownedContent = new Set<string>();
  const sourceOwners = new Set<string>();
  for (const {node, visible, parentVisible} of rows) {
    const key = node.componentKey;
    if (!key) continue;
    if (!NODE_COMPONENT_REGISTRATIONS[key]) {
      if (!SEMANTIC_REGISTRY_ROWS.some((row) => row.componentKey === key)) reject(`${node.containerId}.componentKey`);
      continue;
    }
    unique(node.containerId);
    const registration = NODE_COMPONENT_REGISTRATIONS[key];
    if (!/^1\.\d+\.\d+$/.test(registration.version)
      || snapshot.layoutContract.componentRegistry[key]?.version !== registration.version) reject(`${node.containerId}.version`);
    if (key === 'sc.navigation.anchor') {
      const config = keys(node.componentConfig, ['targetContainerId']);
      const target = unique(config.targetContainerId);
      if (!nativeIdentity(node) || !nativeIdentity(target.node) || !target.visible || !['group', 'page', 'sheet', 'div', 'container'].includes(target.node.type || '')
        || !node.text?.trim() || node.children?.length
        || ['href', 'onclick', 'target'].some((attr) => node.attributes?.[attr])) reject(`${node.containerId}.navigation`);
      presentations.set(node.containerId, {kind: 'anchor', content: node.text.trim(), visible,
        targetContainerId: target.node.containerId});
      continue;
    }
    if (key !== 'sc.feedback.message') reject(`${node.containerId}.unsupported component`);
    const rawConfig = object(node.componentConfig);
    const dynamic = Object.hasOwn(rawConfig, 'evaluation');
    const config = dynamic
      ? keys(node.componentConfig, ['purpose', 'contentRef', 'evaluation'])
      : keys(node.componentConfig, ['purpose', 'contentRef']);
    if (!['advisory', 'error', 'warning', 'explanation'].includes(String(config.purpose))) reject(`${node.containerId}.purpose`);
    if (dynamic) {
      const evaluation = keys(config.evaluation, ['capability', 'visibilityOwner']);
      if (config.purpose !== 'advisory' || evaluation.capability !== 'form.feedback.draft.v1'
        || evaluation.visibilityOwner !== 'feedback_evaluation') reject(`${node.containerId}.evaluation`);
    }
    const ref = keys(config.contentRef, ['containerId']);
    const source = unique(ref.containerId);
    if (!nativeIdentity(source.node)) reject(`${node.containerId}.source authority`);
    if (sourceOwners.has(source.node.containerId)) reject(`${node.containerId}.duplicate content owner`);
    // Keep editable field maintenance outside the feedback host intact.
    const exclusivelyRendered = source.ancestors.includes(node.containerId) || source.node.type !== 'field'
      || object(source.node.fieldInfo).readonly === true;
    sourceOwners.add(source.node.containerId);
    if (!Object.hasOwn(object(node.modifiers), 'invisible') || !compiledCondition(node.modifiers?.invisible, config.purpose !== 'explanation')) reject(`${node.containerId}.condition`);
    let value: unknown;
    if (source.node.type === 'field') {
      const name = source.node.name;
      const type = object(source.node.fieldInfo).type || object(source.node.fieldInfo).ttype;
      if (!name || !['char', 'text', 'boolean', 'integer', 'float', 'monetary', 'selection', 'date', 'datetime'].includes(String(type))) reject(`${node.containerId}.source type`);
      if (config.purpose === 'error' && !['char', 'text'].includes(String(type))) reject(`${node.containerId}.error source type`);
      const data = snapshot.dataContract.mainData;
      if (!dynamic && !Object.hasOwn(data, name)) reject(`${node.containerId}.source value`);
      value = data[name];
    } else {
      if (config.purpose === 'error') reject(`${node.containerId}.error field source`);
      if (!['text', 'div', 'span', 'label', 'p'].includes(source.node.type || '') || source.node.children?.length) reject(`${node.containerId}.source type`);
      value = source.node.text;
    }
    if (value !== null && typeof value === 'object') reject(`${node.containerId}.scalar content`);
    const content = value == null || value === false ? '' : String(value).trim();
    const purpose = config.purpose as NonNullable<NodeComponentPresentation['purpose']>;
    if (dynamic) {
      const evaluated = feedbackEvaluations?.get(node.containerId);
      if (evaluated?.binding && evaluated.binding.container_id !== node.containerId) reject(`${node.containerId}.evaluation binding`);
      const ready = evaluated?.status === 'ready';
      const evaluatedContent = ready && evaluated.visible ? evaluated.content : '';
      if (ready && evaluated.visible && !evaluatedContent) reject(`${node.containerId}.source value`);
      if (exclusivelyRendered) ownedContent.add(source.node.containerId);
      presentations.set(node.containerId, {
        kind: 'feedback',
        purpose,
        content: evaluatedContent,
        visible: parentVisible && ready && evaluated.visible && !!evaluatedContent,
        role: 'status',
        visibilityOwner: 'feedback_evaluation',
        parentVisible,
      });
      continue;
    }
    if (visible && !content && ['error', 'warning'].includes(purpose)) reject(`${node.containerId}.missing content`);
    if (exclusivelyRendered) ownedContent.add(source.node.containerId);
    presentations.set(node.containerId, {kind: 'feedback', purpose, content, visible: visible && !!content,
      role: purpose === 'error' ? 'alert' : purpose === 'explanation' ? undefined : 'status'});
  }
  return {presentations, ownedContent};
}

export function navigateToDeclaredNode(root: HTMLElement, target: string) {
  const matches = Array.from(root.querySelectorAll<HTMLElement>('[data-contract-container-id]'))
    .filter((element) => element.dataset.contractContainerId === target);
  if (matches.length !== 1 || matches[0].hidden || matches[0].getAttribute('aria-hidden') === 'true'
    || matches[0].closest('[aria-hidden="true"], [hidden], [inert]') || !matches[0].getClientRects().length) reject('navigation target unavailable');
  matches[0].scrollIntoView({block: 'start'});
  matches[0].focus({preventScroll: true});
}
