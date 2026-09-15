import type {
  CanonicalFormAction,
  CanonicalFormNode,
  CanonicalFormRenderModel,
  CanonicalFormSemanticRole,
} from './canonicalFormRenderModel';

export type CanonicalFormFloorplan = {
  summaryNodes: CanonicalFormNode[];
  decisionInputNodes: CanonicalFormNode[];
  taskNodes: CanonicalFormNode[];
  coreInputNodes: CanonicalFormNode[];
  conditionInputNodes: CanonicalFormNode[];
  preExecutionInputNodes: CanonicalFormNode[];
  preExecutionInputTitle: string;
  supplementaryInputNodes: CanonicalFormNode[];
  postRelationInputNodes: CanonicalFormNode[];
  postRelationInputTitle: string;
  contextNodes: CanonicalFormNode[];
  overflowContextNodes: CanonicalFormNode[];
  riskNodes: CanonicalFormNode[];
  auditNodes: CanonicalFormNode[];
  auditDeclared: boolean;
  relationNodes: CanonicalFormNode[];
  subordinateNodes: CanonicalFormNode[];
  blockedActions: CanonicalFormAction[];
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
  decisionMode: boolean;
};

export type CanonicalFormFloorplanOptions = {
  /** Exact native node already rendered by the product header. */
  claimedStatusbarNodeIdentity?: string;
  /** Exact field whose workflow fact is already rendered by the product header. */
  claimedStatusbarFieldCode?: string;
};

function hasEditableField(node: CanonicalFormNode): boolean {
  return node.fields.some((field) => field.visible && !field.readonly && !field.disabled)
    || node.children.some(hasEditableField);
}

function hasPresentableValue(field: CanonicalFormNode['fields'][number]): boolean {
  if (field.fieldType.trim().toLowerCase() === 'boolean') return true;
  if (field.value === null || field.value === undefined || field.value === false) return false;
  if (typeof field.value === 'string') return field.value.trim().length > 0;
  if (Array.isArray(field.value)) return field.value.length > 0;
  if (typeof field.value === 'object') {
    const relation = field.value as { displayName?: unknown };
    if (Object.prototype.hasOwnProperty.call(relation, 'displayName')) {
      return String(relation.displayName || '').trim().length > 0;
    }
    return Object.keys(field.value).length > 0;
  }
  return true;
}

function nodeHasContent(node: CanonicalFormNode): boolean {
  if (!node.visible) return false;
  if (node.fields.some((field) => field.visible)) return true;
  if (['chatter', 'activity', 'attachment'].includes(node.kind.trim().toLowerCase())) return true;
  return node.children.some(nodeHasContent);
}

function punctuationOnly(value: string): boolean {
  return /^[\s.·•:_-]+$/.test(value);
}

function createNodeHasContent(node: CanonicalFormNode): boolean {
  if (!node.visible) return false;
  if (node.fields.some((field) => field.visible)) return true;
  if (node.action || node.nativeWidget) return true;
  if (node.text.trim() && !punctuationOnly(node.text)) return true;
  if (['chatter', 'activity', 'attachment'].includes(node.kind.trim().toLowerCase())) return true;
  return node.children.some(createNodeHasContent);
}

function unresolvedCreateIdentity(field: CanonicalFormNode['fields'][number]): boolean {
  const code = field.fieldCode.trim().toLowerCase();
  const value = String(field.value ?? '').trim().toLowerCase();
  return field.readonly && ['name', 'display_name'].includes(code) && ['new', '/'].includes(value);
}

function createReadyNode(node: CanonicalFormNode, readonlyTitleAncestor = false): CanonicalFormNode {
  const shellOwnsReadonlyTitle = readonlyTitleAncestor || node.kind.trim().toLowerCase() === 'h1';
  const projected = {
    ...node,
    text: punctuationOnly(node.text) ? '' : node.text,
    fields: node.fields.filter((field) => (
      !unresolvedCreateIdentity(field)
      && !(shellOwnsReadonlyTitle && field.readonly)
      && (
        !field.visible
        || !field.readonly
        || field.required
        || Boolean(field.reasonCode)
        || hasPresentableValue(field)
      )
    )),
    children: node.children.map((child) => createReadyNode(child, shellOwnsReadonlyTitle)),
  };
  return {
    ...projected,
    children: projected.children.filter(createNodeHasContent),
  };
}

function createFieldOccurrenceSignature(field: CanonicalFormNode['fields'][number]): string {
  const occurrenceIdentityKeys = new Set([
    'native_locator', 'nativeLocator', 'occurrence_index', 'occurrenceIndex', 'source_position', 'sourcePosition',
  ]);
  function occurrenceNeutral(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(occurrenceNeutral);
    if (!value || typeof value !== 'object') return value;
    return Object.fromEntries(Object.entries(value as Record<string, unknown>)
      .filter(([key]) => !occurrenceIdentityKeys.has(key))
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, occurrenceNeutral(item)]));
  }
  return [
    field.fieldCode, field.label, field.fieldType, field.componentKey, String(field.span), String(field.hideLabel),
    String(field.visible), String(field.readonly), String(field.required), String(field.disabled),
    field.reasonCode, field.semanticRole,
    JSON.stringify(occurrenceNeutral(field.componentConfig)), JSON.stringify(occurrenceNeutral(field.fieldDescriptor)),
  ].join('|');
}

function deduplicateEquivalentCreateFields(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  const retainedWidgetBySignature = new Map<string, string>();
  function collect(node: CanonicalFormNode) {
    node.fields.forEach((field) => {
      if (field.visible) retainedWidgetBySignature.set(createFieldOccurrenceSignature(field), field.widgetId);
    });
    node.children.forEach(collect);
  }
  nodes.forEach(collect);
  function project(node: CanonicalFormNode): CanonicalFormNode {
    const projected = {
      ...node,
      fields: node.fields.filter((field) => (
        !field.visible || retainedWidgetBySignature.get(createFieldOccurrenceSignature(field)) === field.widgetId
      )),
      children: node.children.map(project),
    };
    return {
      ...projected,
      children: projected.children.filter(createNodeHasContent),
    };
  }
  return nodes.map(project).filter(createNodeHasContent);
}

function productFieldPriority(field: CanonicalFormNode['fields'][number]): number {
  return Number(Boolean(field.semanticRole)) * 16
    + Number(!field.readonly && !field.disabled) * 8
    + Number(field.required) * 4
    + Number(hasPresentableValue(field)) * 2
    + Number(Boolean(field.semanticSlot || field.semanticGroup));
}

function deduplicateProductFields(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  const retainedByIdentity = new Map<string, CanonicalFormNode['fields'][number]>();
  function collect(node: CanonicalFormNode) {
    node.fields.forEach((field) => {
      if (!field.visible) return;
      const identity = String(field.fieldCode || field.widgetId).trim();
      const retained = retainedByIdentity.get(identity);
      if (!retained || productFieldPriority(field) > productFieldPriority(retained)) {
        retainedByIdentity.set(identity, field);
      }
    });
    node.children.forEach(collect);
  }
  nodes.forEach(collect);
  const retained = new Set(retainedByIdentity.values());
  function project(node: CanonicalFormNode): CanonicalFormNode {
    const projected = {
      ...node,
      fields: node.fields.filter((field) => !field.visible || retained.has(field)),
      children: node.children.map(project),
    };
    return { ...projected, children: projected.children.filter(nodeHasContent) };
  }
  return nodes.map(project).filter(nodeHasContent);
}

function fieldNodes(
  nodes: CanonicalFormNode[],
  predicate: (field: CanonicalFormNode['fields'][number]) => boolean,
  suppressTitles = false,
): CanonicalFormNode[] {
  function project(node: CanonicalFormNode): CanonicalFormNode {
    return {
      ...node,
      ...(suppressTitles ? { title: '' } : {}),
      text: '',
      fields: node.fields.filter((field) => field.visible && predicate(field)),
      children: node.children.map(project),
    };
  }
  return nodes.map(project).filter(nodeHasContent);
}

function collectVisibleFields(node: CanonicalFormNode): CanonicalFormNode['fields'] {
  return [
    ...node.fields.filter((field) => field.visible),
    ...node.children.flatMap(collectVisibleFields),
  ];
}

function nodeDeclaresRole(node: CanonicalFormNode, role: CanonicalFormSemanticRole): boolean {
  return node.semanticRole === role
    || node.fields.some((field) => field.semanticRole === role)
    || node.children.some((child) => nodeDeclaresRole(child, role));
}

function projectNodeRoles(
  node: CanonicalFormNode,
  roles: ReadonlySet<CanonicalFormSemanticRole>,
  includeUnassigned = false,
  onlyPresentable = false,
  suppressTitles = false,
  inheritedRole = '',
): CanonicalFormNode {
  const effectiveNodeRole = node.semanticRole || inheritedRole;
  const nodeTextBelongsToProjection = roles.has(effectiveNodeRole as CanonicalFormSemanticRole)
    || (includeUnassigned && !effectiveNodeRole);
  return {
    ...node,
    ...(suppressTitles ? { title: '' } : {}),
    text: nodeTextBelongsToProjection ? node.text : '',
    fields: node.fields.filter((field) => {
      const effectiveFieldRole = field.semanticRole || effectiveNodeRole;
      return (
        (roles.has(effectiveFieldRole as CanonicalFormSemanticRole)
          || (includeUnassigned && !effectiveFieldRole))
        && (!onlyPresentable || hasPresentableValue(field))
      );
    }),
    children: node.children.map((child) => projectNodeRoles(
      child, roles, includeUnassigned, onlyPresentable, suppressTitles, effectiveNodeRole,
    )),
  };
}

function roleNodes(
  nodes: CanonicalFormNode[],
  roles: CanonicalFormSemanticRole[],
  includeUnassigned = false,
  onlyPresentable = false,
  suppressTitles = false,
): CanonicalFormNode[] {
  const roleSet = new Set(roles);
  return nodes
    .map((node) => projectNodeRoles(node, roleSet, includeUnassigned, onlyPresentable, suppressTitles))
    .filter(nodeHasContent);
}

function nodeHasRelationCapability(node: CanonicalFormNode): boolean {
  const kind = node.kind.trim().toLowerCase();
  return ['notebook', 'relation'].includes(kind)
    || node.semanticRole === 'relation'
    || node.fields.some((field) => (
      field.semanticRole === 'relation'
      || ['one2many', 'many2many'].includes(field.fieldType.trim().toLowerCase())
    ))
    || node.children.some(nodeHasRelationCapability);
}

function fieldHasRelationCapability(field: CanonicalFormNode['fields'][number]): boolean {
  return field.semanticRole === 'relation'
    || ['one2many', 'many2many'].includes(field.fieldType.trim().toLowerCase());
}

function fieldHasAttachmentCapability(field: CanonicalFormNode['fields'][number]): boolean {
  const config = field.componentConfig;
  const descriptor = field.fieldDescriptor;
  const tokens = [
    field.componentResolution.componentKey,
    field.componentResolution.renderer,
    field.componentResolution.contractAdapter,
    config.widget, config.widgetType, config.widget_type,
    descriptor.widget, descriptor.widgetType, descriptor.widget_type,
  ].map((value) => String(value || '').trim().toLowerCase());
  const relation = String(descriptor.relation || '').trim().toLowerCase();
  return field.semanticRole === 'activity'
    || relation === 'ir.attachment'
    || tokens.some((value) => value === 'many2many_binary' || value.includes('attachment'));
}

function fieldHasBusinessRelationCapability(field: CanonicalFormNode['fields'][number]): boolean {
  return fieldHasRelationCapability(field) && !fieldHasAttachmentCapability(field);
}

export function fieldIsBusinessRelationCollection(field: CanonicalFormNode['fields'][number]): boolean {
  return ['one2many', 'many2many'].includes(field.fieldType.trim().toLowerCase())
    && !fieldHasAttachmentCapability(field);
}

function fieldIsDecisionMoney(field: CanonicalFormNode['fields'][number]): boolean {
  return field.semanticRole === 'summary'
    && field.fieldType.trim().toLowerCase() === 'monetary'
    && !field.readonly
    && !field.disabled;
}

function projectRelationNode(node: CanonicalFormNode): CanonicalFormNode {
  const directRelation = node.semanticRole === 'relation' || node.kind.trim().toLowerCase() === 'relation';
  const revealRelationIdentity = (field: CanonicalFormNode['fields'][number]) => (
    fieldHasBusinessRelationCapability(field) ? { ...field, hideLabel: false } : field
  );
  if (directRelation) {
    const projected = {
      ...node,
      fields: node.fields.map(revealRelationIdentity),
      children: node.children.map(projectRelationNode).filter(nodeHasContent),
    };
    const relationFields = collectVisibleFields(projected).filter(fieldHasBusinessRelationCapability);
    const onlyRelationLabel = relationFields.length === 1 ? relationFields[0].label.trim().toLocaleLowerCase() : '';
    return projected.title.trim().toLocaleLowerCase() === onlyRelationLabel
      ? { ...projected, title: '' }
      : projected;
  }
  const projected = {
    ...node,
    fields: node.fields.filter(fieldHasBusinessRelationCapability).map(revealRelationIdentity),
    children: node.children.map(projectRelationNode).filter(nodeHasContent),
  };
  const relationFields = collectVisibleFields(projected).filter(fieldHasBusinessRelationCapability);
  const onlyRelationLabel = relationFields.length === 1 ? relationFields[0].label.trim().toLocaleLowerCase() : '';
  return projected.title.trim().toLocaleLowerCase() === onlyRelationLabel
    ? { ...projected, title: '' }
    : projected;
}

function relationRoleNodes(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  return nodes.map(projectRelationNode).filter(nodeHasContent);
}

function suppressRepeatedTitles(nodes: CanonicalFormNode[], seen: Set<string>): CanonicalFormNode[] {
  function project(node: CanonicalFormNode): CanonicalFormNode {
    const titleIdentity = node.title.trim().toLocaleLowerCase();
    const repeated = Boolean(titleIdentity && seen.has(titleIdentity));
    if (titleIdentity && !repeated) seen.add(titleIdentity);
    return {
      ...node,
      ...(repeated ? { title: '' } : {}),
      children: node.children.map(project),
    };
  }
  return nodes.map(project);
}

function authoritativeSectionTitle(nodes: CanonicalFormNode[]): string {
  const titles = [...new Set(nodes.map((node) => node.title.trim()).filter(Boolean))];
  return titles.length === 1 ? titles[0] : '';
}

function projectContextNode(node: CanonicalFormNode): CanonicalFormNode {
  const nodeKind = node.kind.trim().toLowerCase();
  if ((node.semanticRole && !['context', 'risk', 'activity'].includes(node.semanticRole)) || nodeKind === 'relation') {
    return { ...node, fields: [], children: [] };
  }
  return {
    ...node,
    fields: node.fields.filter((field) => (
      !fieldHasRelationCapability(field)
      && (!field.semanticRole || ['context', 'risk', 'activity'].includes(field.semanticRole))
    )),
    children: node.children.map(projectContextNode),
  };
}

function contextRoleNodes(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  return nodes.map(projectContextNode).filter(nodeHasContent);
}

function flattenPresentableFields(nodes: CanonicalFormNode[], region: string): CanonicalFormNode[] {
  const projected: CanonicalFormNode[] = [];
  const seenFields = new Set<string>();
  function visit(node: CanonicalFormNode) {
    node.fields.filter((field) => field.visible && hasPresentableValue(field)).forEach((field) => {
      const fieldIdentity = String(field.fieldCode || field.widgetId).trim();
      if (fieldIdentity && seenFields.has(fieldIdentity)) return;
      if (fieldIdentity) seenFields.add(fieldIdentity);
      projected.push({
        ...node,
        nodeId: `${node.nodeId}.${region}.${field.widgetId}`,
        title: '',
        columns: 1,
        fields: [field],
        children: [],
      });
    });
    node.children.forEach(visit);
  }
  nodes.forEach(visit);
  return projected;
}

function visibleNodes(nodes: CanonicalFormNode[], mode: CanonicalFormRenderModel['identity']['mode']): CanonicalFormNode[] {
  return nodes
    .map((node) => mode === 'create' ? createReadyNode(node) : node)
    .filter((node) => node.visible && nodeHasContent(node));
}

function excludeClaimedHeaderStatus(
  nodes: CanonicalFormNode[],
  claimedNodeId: string,
  claimedFieldCode: string,
): CanonicalFormNode[] {
  if (!claimedNodeId && !claimedFieldCode) return nodes;
  function project(node: CanonicalFormNode): CanonicalFormNode {
    return {
      ...node,
      fields: node.fields.filter((field) => (
        !claimedFieldCode || field.fieldCode !== claimedFieldCode
      )),
      children: node.children.filter((child) => child.nodeId !== claimedNodeId).map(project),
    };
  }
  return nodes.filter((node) => node.nodeId !== claimedNodeId).map(project);
}

function orderedVisibleFields(nodes: CanonicalFormNode[]): CanonicalFormNode['fields'] {
  const out: CanonicalFormNode['fields'] = [];
  function collect(node: CanonicalFormNode) {
    out.push(...node.fields.filter((field) => field.visible));
    node.children.forEach(collect);
  }
  nodes.forEach(collect);
  return out;
}

function fieldsDeclaredAfterFirstRelation(nodes: CanonicalFormNode[]): Set<CanonicalFormNode['fields'][number]> {
  const fields = orderedVisibleFields(nodes);
  const relationFields = fields.filter(fieldHasBusinessRelationCapability);
  if (!relationFields.length) return new Set();
  const declaredRelationOrders = relationFields
    .map((field) => field.semanticOrder)
    .filter((order): order is number => Number.isInteger(order) && order >= 0);
  if (declaredRelationOrders.length) {
    const boundary = Math.min(...declaredRelationOrders);
    return new Set(fields.filter((field) => Number.isInteger(field.semanticOrder) && field.semanticOrder! > boundary));
  }
  const relationIndex = fields.findIndex(fieldHasBusinessRelationCapability);
  return new Set(fields.slice(relationIndex + 1));
}

/**
 * Pure, ephemeral floorplan projection. It groups canonical nodes without
 * changing field/action identity, visibility, authority, order, or values.
 */
export function composeCanonicalFormFloorplan(
  renderModel: CanonicalFormRenderModel,
  options: CanonicalFormFloorplanOptions = {},
): CanonicalFormFloorplan {
  const visibleActions = renderModel.actionBar.filter((action) => action.visible);
  const canonicalPrimary = visibleActions.find((action) => action.tier === 'primary');
  const createSave = renderModel.identity.mode === 'create' && !canonicalPrimary
    ? visibleActions.find((action) => action.enabled && action.actionRef.actionId === 'form.save')
    : undefined;
  const effectivePrimary = canonicalPrimary?.enabled ? canonicalPrimary : createSave;
  const secondaryCandidates = visibleActions.filter((action) => (
    action.enabled
    && action !== effectivePrimary
    && !['overflow', 'configuration'].includes(action.tier)
  ));
  const directSecondary = secondaryCandidates.slice(0, 1);
  const directActions = [...(effectivePrimary ? [effectivePrimary] : []), ...directSecondary];
  const blockedActions = visibleActions.filter((action) => !action.enabled && action.tier === 'primary');

  if (renderModel.identity.structureAuthority === 'containerTree') {
    return {
      summaryNodes: [], decisionInputNodes: [], taskNodes: renderModel.zones.primary,
      coreInputNodes: [], conditionInputNodes: [], preExecutionInputNodes: [], preExecutionInputTitle: '',
      supplementaryInputNodes: [], postRelationInputNodes: [], postRelationInputTitle: '',
      contextNodes: [], overflowContextNodes: [], riskNodes: [], auditNodes: [], auditDeclared: false,
      relationNodes: [], subordinateNodes: renderModel.zones.subordinate,
      blockedActions, directActions,
      overflowActions: visibleActions.filter((action) => action.enabled && !directActions.includes(action)),
      effectivePrimaryKey: effectivePrimary?.key || '', decisionMode: false,
    };
  }
  const visiblePrimaryNodes = visibleNodes(
    excludeClaimedHeaderStatus(
      renderModel.zones.primary,
      options.claimedStatusbarNodeIdentity || '',
      options.claimedStatusbarFieldCode || '',
    ),
    renderModel.identity.mode,
  );
  const createNodes = renderModel.identity.mode === 'create'
    ? deduplicateEquivalentCreateFields(visiblePrimaryNodes)
    : visiblePrimaryNodes;
  const semanticProductMode = renderModel.identity.presentationMode === 'task';
  const writeMode = renderModel.identity.mode !== 'readonly';
  const primaryNodes = semanticProductMode && writeMode ? deduplicateProductFields(createNodes) : createNodes;
  const editableNodes = primaryNodes.filter(hasEditableField);
  const summaryNodes = semanticProductMode
    ? flattenPresentableFields(fieldNodes(primaryNodes, (field) => (
      field.semanticRole === 'summary' && field.readonly && hasPresentableValue(field)
    ), true), 'summary')
    : [];
  const decisionInputNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, fieldIsDecisionMoney, true)
    : [];
  const decisionInputFields = new Set(decisionInputNodes.flatMap((node) => collectVisibleFields(node)));
  // A generic `risk` role identifies a business fact, not its feedback scope,
  // severity, stage, or related action. Until those authorities are declared,
  // keep the field in its business section instead of manufacturing an alert.
  const riskNodes: CanonicalFormNode[] = [];
  const auditNodes = semanticProductMode ? roleNodes(primaryNodes, ['audit'], false, false, true) : [];
  const auditDeclared = semanticProductMode && primaryNodes.some((node) => nodeDeclaresRole(node, 'audit'));
  const taskNodes = semanticProductMode
    ? fieldNodes(primaryNodes, (field) => field.semanticRole === 'task' && field.readonly && hasPresentableValue(field), true)
    : (editableNodes.length ? editableNodes : primaryNodes);
  const conditionInputNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, (field) => (
      !field.readonly && !field.disabled && !fieldHasBusinessRelationCapability(field)
      && ['task', 'risk'].includes(field.semanticRole)
    ))
    : [];
  const conditionFields = new Set(conditionInputNodes.flatMap((node) => collectVisibleFields(node)));
  const coreInputNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, (field) => (
      !field.readonly && !field.disabled && !fieldHasBusinessRelationCapability(field)
      && field.required && !field.semanticSlot && !field.semanticGroup
      && !conditionFields.has(field) && !decisionInputFields.has(field)
    ))
    : [];
  const coreFields = new Set(coreInputNodes.flatMap((node) => collectVisibleFields(node)));
  // A later-stage requirement must be explicitly supplied by the normalized
  // contract. Contract V2 currently has no such authority, so this projection
  // intentionally stays empty instead of deriving a stage from names or values.
  const preExecutionInputNodes: CanonicalFormNode[] = [];
  const postRelationFields = fieldsDeclaredAfterFirstRelation(primaryNodes);
  const supplementaryInputPredicate = (field: CanonicalFormNode['fields'][number]) => (
    !field.readonly && !field.disabled && !fieldHasBusinessRelationCapability(field)
    && !conditionFields.has(field) && !coreFields.has(field) && !decisionInputFields.has(field)
  );
  const supplementaryInputNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, (field) => (
      supplementaryInputPredicate(field) && !postRelationFields.has(field)
    ))
    : [];
  const postRelationInputNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, (field) => supplementaryInputPredicate(field) && postRelationFields.has(field))
    : [];
  const subordinateNodes = visibleNodes(renderModel.zones.subordinate, renderModel.identity.mode);
  const primaryRelationNodes = semanticProductMode ? relationRoleNodes(primaryNodes.filter(nodeHasRelationCapability)) : [];
  const subordinateRelationNodes = semanticProductMode ? relationRoleNodes(subordinateNodes.filter(nodeHasRelationCapability)) : [];
  const relationNodes = [...primaryRelationNodes, ...subordinateRelationNodes];
  const allContextNodes = semanticProductMode
    ? (writeMode ? [] : deduplicateProductFields(contextRoleNodes(primaryNodes)))
    : primaryNodes.filter((node) => !taskNodes.includes(node));
  const readonlyContextNodes = semanticProductMode && writeMode
    ? fieldNodes(primaryNodes, (field) => (
      field.readonly && ['context', 'risk'].includes(field.semanticRole) && hasPresentableValue(field)
    ))
    : [];
  const emptySemanticNodes = semanticProductMode && !writeMode
    ? roleNodes(primaryNodes, ['summary', 'task'], false, false, true)
      .map((node) => ({
        ...node,
        fields: node.fields.filter((field) => !hasPresentableValue(field)),
        children: node.children.map(function emptyOnly(child): CanonicalFormNode {
          return {
            ...child,
            fields: child.fields.filter((field) => !hasPresentableValue(field)),
            children: child.children.map(emptyOnly),
          };
        }),
      }))
      .filter(nodeHasContent)
    : [];
  // Contract-declared business groups are already the information authority.
  // Readonly status and field count must not silently demote a whole business
  // group into an invented "more information" bucket.
  const contextPartition = semanticProductMode
    ? { direct: [...allContextNodes, ...readonlyContextNodes, ...emptySemanticNodes], overflow: [] as CanonicalFormNode[] }
    : { direct: allContextNodes, overflow: [] as CanonicalFormNode[] };

  const titleRegistry = new Set<string>();
  const titledSummaryNodes = suppressRepeatedTitles(summaryNodes, titleRegistry);
  const titledDecisionInputNodes = suppressRepeatedTitles(decisionInputNodes, titleRegistry);
  const titledTaskNodes = suppressRepeatedTitles(taskNodes, new Set<string>());
  const titledRiskNodes = suppressRepeatedTitles(riskNodes, new Set<string>());
  const titledCoreNodes = suppressRepeatedTitles(coreInputNodes, titleRegistry);
  const titledConditionNodes = suppressRepeatedTitles(conditionInputNodes, titleRegistry);
  const titledPreExecutionNodes = suppressRepeatedTitles(preExecutionInputNodes, titleRegistry);
  const preExecutionInputTitle = authoritativeSectionTitle(preExecutionInputNodes);
  const titledSupplementaryNodes = suppressRepeatedTitles(supplementaryInputNodes, titleRegistry);
  const titledContextNodes = suppressRepeatedTitles(contextPartition.direct, titleRegistry);
  const titledOverflowContextNodes = suppressRepeatedTitles(
    contextPartition.overflow,
    titleRegistry,
  );
  const titledRelationNodes = suppressRepeatedTitles(relationNodes, titleRegistry);
  const postRelationInputTitle = authoritativeSectionTitle(postRelationInputNodes);
  if (postRelationInputTitle) titleRegistry.add(postRelationInputTitle.trim().toLocaleLowerCase());
  const titledPostRelationInputNodes = suppressRepeatedTitles(postRelationInputNodes, titleRegistry);
  const titledSubordinateNodes = suppressRepeatedTitles(
    semanticProductMode
      ? subordinateNodes.filter((node) => !nodeHasRelationCapability(node))
      : subordinateNodes,
    titleRegistry,
  );
  const titledAuditNodes = suppressRepeatedTitles(auditNodes, titleRegistry);

  return {
    summaryNodes: titledSummaryNodes,
    decisionInputNodes: titledDecisionInputNodes,
    taskNodes: titledTaskNodes,
    coreInputNodes: titledCoreNodes,
    conditionInputNodes: titledConditionNodes,
    preExecutionInputNodes: titledPreExecutionNodes,
    preExecutionInputTitle,
    supplementaryInputNodes: titledSupplementaryNodes,
    postRelationInputNodes: titledPostRelationInputNodes,
    postRelationInputTitle,
    contextNodes: titledContextNodes,
    overflowContextNodes: titledOverflowContextNodes,
    riskNodes: titledRiskNodes,
    auditNodes: titledAuditNodes,
    auditDeclared,
    relationNodes: titledRelationNodes,
    subordinateNodes: titledSubordinateNodes,
    blockedActions,
    directActions,
    overflowActions: visibleActions.filter((action) => (
      !directActions.includes(action) && !blockedActions.includes(action) && action.enabled
    )),
    effectivePrimaryKey: effectivePrimary?.key || '',
    decisionMode: semanticProductMode,
  };
}
