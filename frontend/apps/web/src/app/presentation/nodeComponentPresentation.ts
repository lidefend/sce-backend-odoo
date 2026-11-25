import { contractGapError, frontendCapabilityGap } from '../contract/contractGap';
import { NODE_COMPONENT_REGISTRY } from './semantic_registry.generated';
import type { ContractV2Container, ContractV2Snapshot } from '../contracts/v2/types';

export type NodeComponentPresentation = {
  kind: 'feedback' | 'anchor' | 'ribbon' | 'insight_summary' | 'action_list';
  purpose?: 'advisory' | 'error' | 'warning' | 'explanation';
  content: string;
  visible: boolean;
  role?: 'alert' | 'status';
  targetContainerId?: string;
  styleClass?: string;
  visibilityOwner?: 'feedback_evaluation';
  parentVisible?: boolean;
  insight?: Readonly<{
    tone: 'success' | 'warning' | 'info';
    title: string;
    message: string;
    detail: string;
  }>;
  actionList?: Readonly<{
    title: string;
    emptyText: string;
    items: ReadonlyArray<Readonly<{
      id: string;
      title: string;
      description: string;
      state: 'done' | 'required' | 'available';
      tone: 'success' | 'warning' | 'info';
      actionType: '' | 'act_window_xmlid' | 'object_method';
      actionRef: string;
      actionLabel: string;
      actionPayload: Readonly<Record<string, unknown>>;
      enabled: boolean;
    }>>;
  }>;
};
function reject(path: string): never {
  throw contractGapError({ kind: 'contract_defect', missing: path,
    requiredDeclarationLayer: 'P0: verified node component contract' }, 'Invalid explicit node component');
}
function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}
function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function keys(value: unknown, expected: string[]): Record<string, unknown> {
  const row = object(value);
  if (Object.keys(row).length !== expected.length || expected.some((key) => !Object.hasOwn(row, key))) reject('componentConfig');
  return row;
}

function nodePayloadSource(value: unknown): boolean {
  const row = object(value);
  return Object.keys(row).length === 4
    && row.kind === 'smart_construction_core_native_view_widget_payload'
    && row.module === 'smart_construction_core'
    && row.projectionOnly === false
    && row.noBusinessFactAuthority === false;
}

function nodeActionList(value: unknown) {
  const payload = keys(value, ['title', 'emptyText', 'items']);
  if (typeof payload.title !== 'string' || typeof payload.emptyText !== 'string' || !Array.isArray(payload.items)) {
    reject('action_list payload');
  }
  const items = payload.items.map((item) => {
    const row = keys(item, [
      'id', 'title', 'description', 'state', 'tone', 'actionType',
      'actionRef', 'actionLabel', 'actionPayload', 'enabled',
    ]);
    if (
      typeof row.id !== 'string' || !row.id
      || typeof row.title !== 'string' || !row.title
      || typeof row.description !== 'string'
      || !['done', 'required', 'available'].includes(String(row.state))
      || !['success', 'warning', 'info'].includes(String(row.tone))
      || !['', 'act_window_xmlid', 'object_method'].includes(String(row.actionType))
      || typeof row.actionRef !== 'string'
      || typeof row.actionLabel !== 'string'
      || !row.actionPayload || typeof row.actionPayload !== 'object' || Array.isArray(row.actionPayload)
      || typeof row.enabled !== 'boolean'
      || (row.enabled && !row.actionRef)
    ) reject('action_list item');
    return Object.freeze({
      id: row.id,
      title: row.title,
      description: row.description,
      state: row.state as 'done' | 'required' | 'available',
      tone: row.tone as 'success' | 'warning' | 'info',
      actionType: row.actionType as '' | 'act_window_xmlid' | 'object_method',
      actionRef: row.actionRef,
      actionLabel: row.actionLabel,
      actionPayload: Object.freeze({ ...row.actionPayload as Record<string, unknown> }),
      enabled: row.enabled,
    });
  });
  if (new Set(items.map((item) => item.id)).size !== items.length) reject('action_list duplicate id');
  return Object.freeze({
    title: payload.title,
    emptyText: payload.emptyText,
    items: Object.freeze(items),
  });
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
    if (String(node.type || node.containerType || '').toLowerCase() === 'field') {
      continue;
    }
    const semanticType = text(node.semanticType);
    if (!semanticType) continue;
    const key = NODE_COMPONENT_REGISTRY[semanticType];
    if (!key) {
      throw frontendCapabilityGap({
        semanticType,
        missing: `frontend.node_implementation.${semanticType}`,
        requiredImplementationLayer: 'P0:frontend:implementation_registry',
      }, `前端没有节点语义 ${semanticType} 的可用实现`);
    }
    unique(node.containerId);
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
    if (key === 'sc.unsupported.native_node') {
      const reasonCode = text(object(node.componentConfig).reasonCode);
      if (!reasonCode) reject(`${node.containerId}.componentConfig.reasonCode`);
      throw contractGapError({
        kind: 'contract_defect',
        missing: `native_view_widget.${reasonCode}`,
        requiredDeclarationLayer: 'P0: registered embedded native widget component',
      }, `Native embedded widget is not supported: ${reasonCode}`);
    }
    if (key === 'sc.insight.summary' || key === 'sc.action.list') {
      const required = [
        'nativeWidget', 'widgetStatus', 'identityComplete', 'optionsResolution',
        'payloadSchema', 'payload', 'payloadSourceAuthority',
      ];
      const rawConfig = object(node.componentConfig);
      if (
        required.some((field) => !Object.hasOwn(rawConfig, field))
        || !Object.keys(rawConfig).every((field) => required.includes(field) || ['optionsRaw', 'options'].includes(field))
        || rawConfig.widgetStatus !== 'ready'
        || rawConfig.identityComplete !== true
        || !['none', 'parsed', 'unsupported'].includes(String(rawConfig.optionsResolution))
        || node.type !== 'widget'
        || node.containerType !== 'widget'
        || node.children?.length
        || !nativeIdentity(node)
        || node.nativeIdentity?.kind !== 'widget'
        || node.nativeIdentity.name !== rawConfig.nativeWidget
        || node.nativeIdentity.nativeLocator !== node.nativeLocator
        || node.nativeIdentity.occurrenceIndex !== node.occurrenceIndex
        || !nodePayloadSource(rawConfig.payloadSourceAuthority)
      ) reject(`${node.containerId}.native payload`);
      if (key === 'sc.insight.summary') {
        if (rawConfig.payloadSchema !== 'insight_summary.v1') reject(`${node.containerId}.payloadSchema`);
        const payload = keys(rawConfig.payload, ['tone', 'title', 'message', 'detail']);
        if (
          !['success', 'warning', 'info'].includes(String(payload.tone))
          || typeof payload.title !== 'string' || !payload.title
          || typeof payload.message !== 'string'
          || typeof payload.detail !== 'string'
        ) reject(`${node.containerId}.payload`);
        presentations.set(node.containerId, {
          kind: 'insight_summary',
          content: payload.title,
          visible,
          insight: Object.freeze({
            tone: payload.tone as 'success' | 'warning' | 'info',
            title: payload.title,
            message: payload.message,
            detail: payload.detail,
          }),
        });
        continue;
      }
      if (rawConfig.payloadSchema !== 'action_list.v1') reject(`${node.containerId}.payloadSchema`);
      const actionList = nodeActionList(rawConfig.payload);
      presentations.set(node.containerId, {
        kind: 'action_list',
        content: actionList.title,
        visible,
        actionList,
      });
      continue;
    }
    if (key === 'sc.display.ribbon') {
      const required = ['nativeWidget', 'widgetStatus', 'identityComplete', 'optionsResolution'];
      const rawConfig = object(node.componentConfig);
      if (
        required.some((field) => !Object.hasOwn(rawConfig, field))
        || !Object.keys(rawConfig).every((field) => required.includes(field) || ['optionsRaw', 'options'].includes(field))
        || rawConfig.nativeWidget !== 'web_ribbon'
        || rawConfig.widgetStatus !== 'ready'
        || rawConfig.identityComplete !== true
        || !['none', 'parsed', 'unsupported'].includes(String(rawConfig.optionsResolution))
        || (
          Object.hasOwn(rawConfig, 'optionsRaw')
          && (
            typeof rawConfig.optionsRaw !== 'string'
            || rawConfig.optionsResolution === 'none'
          )
        )
        || (
          rawConfig.optionsResolution === 'parsed'
          && !Object.hasOwn(rawConfig, 'options')
        )
        || node.type !== 'widget'
        || node.containerType !== 'widget'
        || node.children?.length
        || !nativeIdentity(node)
        || node.nativeIdentity?.kind !== 'widget'
        || node.nativeIdentity.name !== 'web_ribbon'
        || node.nativeIdentity.nativeLocator !== node.nativeLocator
        || node.nativeIdentity.occurrenceIndex !== node.occurrenceIndex
      ) reject(`${node.containerId}.ribbon`);
      const content = text(node.title || node.label || node.string);
      if (!content) reject(`${node.containerId}.title`);
      presentations.set(node.containerId, {
        kind: 'ribbon',
        content,
        visible,
        styleClass: text(node.attributes?.bg_color),
      });
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
