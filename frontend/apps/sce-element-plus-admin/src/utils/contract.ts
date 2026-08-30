import type {
  BusinessAction,
  Dictionary,
  FieldSpec,
  PageContract,
  SemanticFormModel,
  SemanticFormNode,
} from "@/types/contracts";
import type { ActionResolutionOptions } from "@/utils/action";
import { fieldLabel } from "@/utils/format";

function object(value: unknown): Dictionary {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Dictionary)
    : {};
}

function section(source: Dictionary, camel: string, snake: string): Dictionary {
  return object(source[camel] ?? source[snake]);
}

export function decodePageContract(payload: unknown): PageContract {
  const envelope = object(payload);
  const raw = object(
    envelope.unified_page_contract_v2 ??
      envelope.__unified_page_contract_v2 ??
      envelope.contract ??
      envelope.page_contract ??
      envelope,
  );
  return {
    raw,
    pageInfo: section(raw, "pageInfo", "page_info"),
    layoutContract: section(raw, "layoutContract", "layout_contract"),
    statusContract: section(raw, "statusContract", "status_contract"),
    actionContract: section(raw, "actionContract", "action_contract"),
    dataContract: section(raw, "dataContract", "data_contract"),
    runtimeContract: section(raw, "runtimeContract", "runtime_contract"),
    searchContract: section(raw, "searchContract", "search_contract"),
    workflowContract: section(raw, "workflowContract", "workflow_contract"),
  };
}

function normalizeSelection(
  value: unknown,
): Array<{ label: string; value: unknown }> {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (Array.isArray(item) && item.length >= 2)
      return [{ value: item[0], label: String(item[1]) }];
    if (item && typeof item === "object") {
      const row = item as Dictionary;
      return [
        {
          value: row.value ?? row.key,
          label: String(row.label ?? row.name ?? row.value ?? ""),
        },
      ];
    }
    return [];
  });
}

function normalizeField(item: Dictionary, fallbackCode = ""): FieldSpec | null {
  const componentConfig = object(item.componentConfig ?? item.component_config);
  const config = {
    ...componentConfig,
    ...object(item.config ?? item.props ?? item.fieldInfo ?? item.field_info),
  };
  const descriptor = object(item.fieldDescriptor ?? item.field_descriptor ?? config.fieldDescriptor ?? config.field_descriptor);
  const fieldInfo = object(
    config.fieldInfo ?? config.field_info ?? item.fieldInfo ?? item.field_info ?? descriptor,
  );
  const capabilities = item.capabilities ?? config.capabilities ?? fieldInfo.capabilities;
  const sortable =
    item.sortable === false || config.sortable === false || fieldInfo.sortable === false
      ? false
      : item.sortable === true || config.sortable === true || fieldInfo.sortable === true ||
          (Array.isArray(capabilities) && capabilities.some((value) => String(value).toLowerCase() === "sortable"))
        ? true
        : undefined;
  const code = String(
    item.code ?? item.name ?? item.field ?? item.fieldCode ?? item.field_code ?? fieldInfo.name ?? descriptor.fieldCode ?? descriptor.field_code ?? fallbackCode,
  ).trim();
  if (!code || ["id", "__last_update"].includes(code)) return null;
  const nodeType = String(item.type ?? "").toLowerCase();
  const hidden = [
    item.invisible,
    item.hidden,
    item.ui_hidden,
    config.invisible,
    config.hidden,
    config.ui_hidden,
    fieldInfo.invisible,
    fieldInfo.hidden,
  ].some((value) => value === true || value === 1 || value === "1" || value === "true");
  return {
    code,
    label: fieldLabel(
      code,
      item.label ?? item.string ?? item.title ?? fieldInfo.label ?? fieldInfo.string ?? code,
    ),
    type: String(
      (nodeType && nodeType !== "field" ? nodeType : undefined) ??
      item.fieldType ?? item.field_type ?? item.ttype ??
        fieldInfo.type ??
        fieldInfo.ttype ??
        config.fieldType ??
        config.field_type ??
        "char",
    ).toLowerCase(),
    hidden,
    sortable,
    required:
      item.required === true ||
      config.required === true ||
      fieldInfo.required === true,
    readonly:
      item.readonly === true ||
      config.readonly === true ||
      fieldInfo.readonly === true,
    relation: String(
      item.relation ?? config.relation ?? fieldInfo.relation ?? "",
    ),
    selection: normalizeSelection(
      item.selection ?? config.selection ?? fieldInfo.selection,
    ),
    config: { ...fieldInfo, ...config, ...descriptor, ...item, componentConfig, fieldDescriptor: descriptor },
    semanticRole: String(
      item.semanticRole ?? item.semantic_role ?? config.semanticRole ?? config.semantic_role ?? fieldInfo.semanticRole ?? fieldInfo.semantic_role ?? "",
    ).trim().toLowerCase() as FieldSpec["semanticRole"],
    semanticSlot: String(item.semanticSlot ?? item.semantic_slot ?? config.semanticSlot ?? config.semantic_slot ?? "").trim(),
    semanticGroup: String(item.semanticGroup ?? item.semantic_group ?? config.semanticGroup ?? config.semantic_group ?? "").trim(),
    span: Number(item.span ?? config.span ?? fieldInfo.span ?? 12) || 12,
    hideLabel: Boolean(item.hideLabel ?? item.hide_label ?? config.hideLabel ?? config.hide_label ?? false),
    widgetKey: String(item.componentKey ?? item.component_key ?? config.componentKey ?? config.component_key ?? "").trim(),
  };
}

function walkFields(value: unknown, output: FieldSpec[], seen: Set<string>) {
  if (Array.isArray(value)) {
    for (const item of value) walkFields(item, output, seen);
    return;
  }
  if (!value || typeof value !== "object") return;
  const row = value as Dictionary;
  const kind = String(
    row.kind ?? row.type ?? row.nodeType ?? row.node_type ?? "",
  ).toLowerCase();
  if (
    kind === "field" ||
    row.field ||
    row.fieldCode ||
    row.field_code ||
    row.fieldDescriptor ||
    row.field_descriptor ||
    row.widgetId ||
    row.widget_id ||
    row.fieldInfo ||
    row.field_info ||
    (row.name && row.ttype)
  ) {
    const field = normalizeField(row);
    if (field && !seen.has(field.code)) {
      seen.add(field.code);
      output.push(field);
    }
  }
  for (const key of [
    "fields",
    "children",
    "items",
    "nodes",
    "containers",
    "tabs",
    "groups",
    "widgetList",
    "widget_list",
    "containerTree",
    "container_tree",
  ]) {
    walkFields(row[key], output, seen);
  }
}

export function resolveFieldSpecs(contract: PageContract): FieldSpec[] {
  const output: FieldSpec[] = [];
  const seen = new Set<string>();
  const meta = object(
    contract.dataContract.dataMeta ?? contract.dataContract.data_meta,
  );
  const candidates = [
    meta.fields,
    meta.fieldSpecs,
    meta.field_specs,
    contract.dataContract.fields,
    contract.layoutContract.fields,
    contract.layoutContract.containerTree,
    contract.layoutContract.container_tree,
    contract.raw.fields,
  ];
  candidates.forEach((candidate) => {
    if (
      candidate &&
      typeof candidate === "object" &&
      !Array.isArray(candidate)
    ) {
      for (const [code, value] of Object.entries(candidate)) {
        const field = normalizeField(object(value), code);
        if (field && !seen.has(field.code)) {
          seen.add(field.code);
          output.push(field);
        }
      }
    } else {
      walkFields(candidate, output, seen);
    }
  });
  const visible = object(meta.visibleFields ?? meta.visible_fields).fields;
  if (Array.isArray(visible) && visible.length) {
    const order = visible.map(String);
    return output
      .filter((field) => order.includes(field.code))
      .sort((a, b) => order.indexOf(a.code) - order.indexOf(b.code));
  }
  return output;
}

function semanticNode(
  value: unknown,
  zone: 'primary' | 'subordinate',
  key: string,
  roleByField: Record<string, string> = {},
  slotByField: Record<string, string> = {},
  containerStatusById: Map<string, Dictionary> = new Map(),
): SemanticFormNode | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const row = value as Dictionary;
  const kind = String(row.kind ?? row.type ?? row.containerType ?? row.container_type ?? 'group').trim().toLowerCase();
  const nodeKey = String(row.containerId ?? row.container_id ?? row.widgetId ?? row.widget_id ?? row.name ?? key).trim() || key;
  const info = object(row.fieldInfo ?? row.field_info);
  const ownField = (row.fieldCode || row.field_code || row.field || kind === 'field')
    ? normalizeField({ ...row, ...info, name: row.fieldCode ?? row.field_code ?? row.field ?? row.name }, String(row.fieldCode ?? row.field_code ?? row.field ?? row.name ?? ''))
    : null;
  const fieldRows = Array.isArray(row.fields) ? row.fields : Array.isArray(row.widgetList) ? row.widgetList : [];
  const fields = [ownField, ...fieldRows.map((item: unknown, index: number) => normalizeField(object(item), `${nodeKey}.field.${index}`))]
    .filter((field): field is FieldSpec => Boolean(field))
    .map((field) => ({
      ...field,
      semanticRole: (field.semanticRole || roleByField[field.code] || '') as FieldSpec['semanticRole'],
      semanticSlot: field.semanticSlot || slotByField[field.code] || '',
    } as FieldSpec));
  // Native form payloads may carry an empty `children` placeholder beside
  // the real notebook `tabs`/page collection. Use the first non-empty carrier
  // so tab content is not silently dropped or rendered outside its page.
  const childRows: unknown[] = ([row.children, row.pages, row.tabs, row.items, row.nodes] as unknown[])
    .find((candidate): candidate is unknown[] => Array.isArray(candidate) && candidate.length > 0) || [];
  const children = childRows.map((item: unknown, index: number) => semanticNode(item, zone, `${nodeKey}.${index}`, roleByField, slotByField, containerStatusById)).filter((item): item is SemanticFormNode => Boolean(item));
  const containerStatus = containerStatusById.get(nodeKey);
  const visible = ![row.invisible, row.hidden, row.ui_hidden].some((v) => v === true || v === 1 || v === '1' || v === 'true')
    && containerStatus?.visible !== false;
  const role = String(row.semanticRole ?? row.semantic_role ?? row.formStructureRole?.role ?? row.form_structure_role?.role ?? '').trim().toLowerCase() as FieldSpec['semanticRole'];
  const actionRow = object(row.action);
  const actionKey = String(actionRow.actionKey ?? actionRow.action_key ?? actionRow.key ?? actionRow.name ?? '').trim();
  const action = actionKey
    ? {
        key: actionKey,
        label: String(actionRow.label ?? actionRow.string ?? actionRow.title ?? actionKey),
        type: 'primary' as const,
        intent: String(actionRow.intent ?? actionRow.backend_intent ?? ''),
        button: object(actionRow.button ?? actionRow),
        params: object(actionRow.params),
        enabled: actionRow.enabled !== false && containerStatus?.disabled !== true && containerStatus?.visible !== false,
        reasonCode: String(actionRow.reasonCode ?? actionRow.reason_code ?? containerStatus?.reasonCode ?? containerStatus?.reason_code ?? ''),
        target: object(actionRow.target),
        actionId: String(actionRow.actionId ?? actionRow.action_id ?? ''),
        backendIdentity: String(actionRow.backendIdentity ?? actionRow.backend_identity ?? ''),
        sourceWidgetId: String(actionRow.sourceWidgetId ?? actionRow.source_widget_id ?? nodeKey),
        targetScope: String(actionRow.targetScope ?? actionRow.target_scope ?? '').trim().toLowerCase(),
        sourceChannel: String(actionRow.sourceChannel ?? actionRow.source_channel ?? '').trim(),
        triggerType: String(actionRow.triggerType ?? actionRow.trigger_type ?? '').trim().toLowerCase(),
        presentationTier: 'secondary' as const,
      }
    : undefined;
  const rawClasses = String(row.class ?? row.classes ?? row.className ?? '').trim().toLowerCase();
  const rawWidget = String(row.nativeWidget ?? row.native_widget ?? row.widget ?? '').trim().toLowerCase();
  const nativeActionContainer = [kind, rawClasses, rawWidget].some((value) =>
    /(?:button[_-]?box|stat[_-]?buttons?|oe_stat_button)/.test(value),
  );
  const explicitZone = String(row.zoneRole ?? row.zone_role ?? row.zone ?? '').trim().toLowerCase();
  const rowZone = explicitZone === 'subordinate' || nativeActionContainer ? 'subordinate' : zone;
  return {
    key: nodeKey,
    kind,
    title: String(row.title ?? row.string ?? row.label ?? row.name ?? '').trim(),
    text: String(row.text ?? '').trim(),
    role,
    zone: rowZone,
    columns: Math.max(1, Math.min(3, Number(row.columns ?? row.cols ?? 2) || 2)),
    span: Number(row.span ?? 24) || 24,
    visible,
    fields,
    children,
    action,
    nativeWidget: String(row.nativeWidget ?? row.native_widget ?? row.widget ?? '').trim(),
  };
}

export function resolveSemanticFormModel(contract: PageContract): SemanticFormModel {
  const layout = contract.layoutContract || {};
  const status = contract.statusContract || {};
  const containerStatusRows = Array.isArray(status.containerStatus)
    ? status.containerStatus
    : Array.isArray(status.container_status)
      ? status.container_status
      : [];
  const containerStatusById = new Map<string, Dictionary>();
  containerStatusRows.forEach((value) => {
    const row = object(value);
    const id = String(row.containerId ?? row.container_id ?? '').trim();
    if (id) containerStatusById.set(id, row);
  });
  const structure = object(layout.formStructureContract ?? layout.form_structure_contract ?? contract.raw.formStructureContract ?? contract.raw.form_structure_contract);
  const mode = String(structure.presentationMode ?? structure.presentation_mode ?? layout.presentationMode ?? layout.presentation_mode ?? 'workspace').toLowerCase() === 'task' ? 'task' : 'workspace';
  const roleByField: Record<string, string> = {};
  const slotByField: Record<string, string> = {};
  const structureRoles = object(structure.fieldRoles ?? structure.field_roles);
  Object.entries(structureRoles).forEach(([code, value]) => {
    const row = object(value);
    roleByField[code] = String(row.role ?? '').trim().toLowerCase();
    slotByField[code] = String(row.slot ?? '').trim();
  });
  const slots = Array.isArray(structure.slots) ? structure.slots : [];
  slots.forEach((slot: unknown) => {
    const row = object(slot);
    const slotName = String(row.slot ?? '').trim();
    const roleName = String(row.role ?? '').trim().toLowerCase();
    const refs = Array.isArray(row.fieldRefs ?? row.field_refs) ? (row.fieldRefs ?? row.field_refs) as unknown[] : [];
    refs.forEach((code) => {
      const key = String(code).trim();
      if (key && !roleByField[key]) roleByField[key] = roleName;
      if (key && !slotByField[key]) slotByField[key] = slotName;
    });
  });
  const authoritativeActions = resolveActions(contract, 'form');
  function bindActions(node: SemanticFormNode): SemanticFormNode {
    const candidate = node.action;
    const authoritative = candidate && authoritativeActions.find((action) => (
      (candidate.backendIdentity && action.backendIdentity === candidate.backendIdentity)
      || (candidate.actionId && action.actionId === candidate.actionId)
      || action.key === candidate.key
    ));
    const action = authoritative || (
      candidate && candidate.label.trim().toLowerCase() !== candidate.key.trim().toLowerCase()
        ? candidate
        : undefined
    );
    const actionOnly = Boolean(action && !node.fields.length && !node.children.length);
    const actionSource = String(action?.sourceWidgetId || '').trim().toLowerCase();
    const actionScope = String(action?.targetScope || '').trim().toLowerCase();
    const isHeaderAction = actionSource === 'page.header'
      || (actionSource === 'page.root' && ['header', 'page'].includes(actionScope));
    return {
      ...node,
      zone: node.zone === 'subordinate' || (actionOnly && !isHeaderAction) ? 'subordinate' : node.zone,
      // Action-only native button nodes are already represented by the
      // contract action surface. Do not inject them back into the form tree.
      action: actionOnly ? undefined : action,
      children: node.children.map(bindActions),
    };
  }
  const rows = Array.isArray(layout.containerTree) ? layout.containerTree : Array.isArray(layout.container_tree) ? layout.container_tree : [];
  const parsedNodes = rows.map((row: unknown, index: number) => semanticNode(row, 'primary', `primary.${index}`, roleByField, slotByField, containerStatusById)).filter((item): item is SemanticFormNode => Boolean(item));
  const boundNodes = parsedNodes.map(bindActions);
  const rawPrimaryNodes = boundNodes.filter((node) => node.zone !== 'subordinate');
  function findNotebook(node: SemanticFormNode): SemanticFormNode | null {
    if (['notebook', 'notebook_block', 'tabs', 'tabset'].includes(node.kind)) return node;
    for (const child of node.children) {
      const found = findNotebook(child);
      if (found) return found;
    }
    return null;
  }
  const nativeNotebook = rawPrimaryNodes.map(findNotebook).find((node): node is SemanticFormNode => Boolean(node));
  const nativeNotebookCollectionCodes = new Set<string>();
  function collectNotebookCollections(node: SemanticFormNode) {
    node.fields.forEach((field) => {
      if (['one2many', 'many2many'].includes(field.type)) nativeNotebookCollectionCodes.add(field.code);
    });
    node.children.forEach(collectNotebookCollections);
  }
  if (nativeNotebook) collectNotebookCollections(nativeNotebook);
  const allFields = new Map<string, FieldSpec>();
  const collectFields = (node: SemanticFormNode) => {
    node.fields.forEach((field) => { if (!allFields.has(field.code)) allFields.set(field.code, field); });
    node.children.forEach(collectFields);
  };
  rawPrimaryNodes.forEach(collectFields);
  const usedFields = new Set<string>();
  const semanticSlots = slots.map((slot: unknown, slotIndex: number) => {
    const row = object(slot);
    const slotKey = String(row.slot ?? `slot-${slotIndex}`).trim();
    const slotRole = String(row.role ?? '').trim().toLowerCase();
    const groups = Array.isArray(row.groups) ? row.groups : [];
    const groupNodes = groups.map((group: unknown, groupIndex: number) => {
      const groupRow = object(group);
      const refs = Array.isArray(groupRow.fieldRefs ?? groupRow.field_refs) ? (groupRow.fieldRefs ?? groupRow.field_refs) as unknown[] : [];
      const fields = refs.map((ref) => allFields.get(String(ref).trim())).filter((field): field is FieldSpec => Boolean(field && !usedFields.has(field.code) && !field.hidden && !nativeNotebookCollectionCodes.has(field.code)));
      fields.forEach((field) => usedFields.add(field.code));
      return {
        key: `${slotKey}.group.${String(groupRow.name ?? groupIndex)}`, kind: 'group', title: String(groupRow.title ?? groupRow.label ?? '').trim(), text: '',
        role: String(groupRow.role ?? slotRole).trim().toLowerCase() as FieldSpec['semanticRole'], zone: 'primary' as const,
        columns: Math.max(1, Math.min(3, Number(groupRow.columns ?? 2) || 2)), span: 24, visible: fields.length > 0, fields, children: [],
      } as SemanticFormNode;
    }).filter((node) => node.visible);
    const directRefs = Array.isArray(row.fieldRefs ?? row.field_refs) ? (row.fieldRefs ?? row.field_refs) as unknown[] : [];
    const directFields = directRefs.map((ref) => allFields.get(String(ref).trim())).filter((field): field is FieldSpec => Boolean(field && !usedFields.has(field.code) && !field.hidden && !nativeNotebookCollectionCodes.has(field.code)));
    directFields.forEach((field) => usedFields.add(field.code));
    if (!groupNodes.length && !directFields.length) return null;
    return {
      key: `semantic.${slotKey}`, kind: 'slot', title: String(row.title ?? slotKey).trim(), text: '', role: slotRole as FieldSpec['semanticRole'], zone: 'primary',
      columns: 1, span: 24, visible: true, fields: directFields, children: groupNodes,
    } as SemanticFormNode;
  }).filter((node): node is SemanticFormNode => Boolean(node));
  const retainedRemainderFields = new Set<string>();
  function removeUsed(node: SemanticFormNode): SemanticFormNode | null {
    const fields = node.fields.filter((field) => {
      if (usedFields.has(field.code) || field.hidden || retainedRemainderFields.has(field.code)) return false;
      retainedRemainderFields.add(field.code);
      return true;
    });
    const children = node.children.map(removeUsed).filter((child): child is SemanticFormNode => Boolean(child));
    if (!fields.length && !children.length) return null;
    return { ...node, fields, children, action: undefined, nativeWidget: '', text: '' };
  }
  // Native notebook pages are authoritative for workspace forms. Semantic slot
  // projection must not consume fields such as contract_ids before their tab renders.
  const primaryNodes = mode === 'workspace' && nativeNotebook
    ? rawPrimaryNodes
    : semanticSlots.length
      ? [...semanticSlots, ...rawPrimaryNodes.map(removeUsed).filter((node): node is SemanticFormNode => Boolean(node))]
      : rawPrimaryNodes;
  const promotedSubordinateNodes: SemanticFormNode[] = [];
  function separateSubordinate(node: SemanticFormNode): SemanticFormNode | null {
    if (node.zone === 'subordinate' && !node.fields.length) {
      promotedSubordinateNodes.push(node);
      return null;
    }
    const children = node.children
      .map(separateSubordinate)
      .filter((child): child is SemanticFormNode => Boolean(child));
    return { ...node, children };
  }
  const primaryNodesWithSeparatedActions = primaryNodes
    .map(separateSubordinate)
    .filter((node): node is SemanticFormNode => Boolean(node));
  const seenFields = new Set<string>();
  const seenWidgets = new Set<string>();
  const seenActions = new Set<string>();
  function deduplicate(node: SemanticFormNode): SemanticFormNode | null {
    const fields = node.fields.filter((field) => {
      if (field.hidden) return true;
      if (seenFields.has(field.code)) return false;
      seenFields.add(field.code);
      return true;
    });
    const children = node.children.map(deduplicate).filter((child): child is SemanticFormNode => Boolean(child));
    const nativeWidget = node.nativeWidget && !/^sc_insight_banner$/i.test(node.nativeWidget)
      ? (seenWidgets.has(node.nativeWidget) ? '' : (seenWidgets.add(node.nativeWidget), node.nativeWidget))
      : '';
    const actionKey = node.action?.key || '';
    const action = actionKey && seenActions.has(actionKey)
      ? undefined
      : (actionKey ? (seenActions.add(actionKey), node.action) : node.action);
    if (!fields.length && !children.length && !node.text && !nativeWidget && !action) return null;
    return { ...node, fields, children, nativeWidget, action };
  }
  const deduplicatedPrimaryNodes = primaryNodesWithSeparatedActions.map(deduplicate).filter((node): node is SemanticFormNode => Boolean(node));
  const inlineSubordinate = boundNodes.filter((node) => node.zone === 'subordinate');
  const subordinateRows = Array.isArray(layout.subordinateNodes) ? layout.subordinateNodes : Array.isArray(layout.subordinate_nodes) ? layout.subordinate_nodes : [];
  const subordinateNodes = [
    ...promotedSubordinateNodes,
    ...inlineSubordinate,
    ...subordinateRows.map((row: unknown, index: number) => semanticNode(row, 'subordinate', `subordinate.${index}`, roleByField, slotByField, containerStatusById)).filter((item): item is SemanticFormNode => Boolean(item)).map(bindActions),
  ];
  const deduplicatedSubordinateNodes = subordinateNodes.map(deduplicate).filter((node): node is SemanticFormNode => Boolean(node));
  return {
    presentationMode: mode,
    primaryNodes: deduplicatedPrimaryNodes,
    subordinateNodes: deduplicatedSubordinateNodes,
    layoutHints: object(layout.layoutHints ?? layout.layout_hints),
    slots: semanticSlots.map((slot) => ({
      slot: slot.key.replace(/^semantic\./, ''), title: slot.title, role: slot.role || '',
      groups: slot.children.map((group) => ({ name: group.key, title: group.title, role: group.role || '', fieldRefs: group.fields.map((field) => field.code), columns: group.columns })),
    })),
  };
}

function fieldNames(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map(String).filter((field) => field && field !== "id")
    : [];
}

export function resolveListFieldSpecs(contract: PageContract): FieldSpec[] {
  const parsed = resolveFieldSpecs(contract);
  const parsedByCode = new Map(parsed.map((field) => [field.code, field]));
  const meta = object(
    contract.dataContract.dataMeta ?? contract.dataContract.data_meta,
  );
  const source = object(
    contract.dataContract.dataSource ?? contract.dataContract.data_source,
  );
  const primary = object(source.primary ?? source);
  const params = object(primary.params);
  const visible = fieldNames(
    object(meta.visibleFields ?? meta.visible_fields).fields,
  );
  const requested = fieldNames(params.fields);
  const listOrder = requested.length
    ? requested
    : visible.length
      ? visible
      : parsed.map((field) => field.code);
  const operationProfile = object(
    meta.businessOperationProfile ?? meta.business_operation_profile,
  );
  const labels = object(
    operationProfile.field_labels ?? operationProfile.fieldLabels,
  );
  const listProfile = object(contract.layoutContract.listProfile ?? contract.layoutContract.list_profile);
  const hiddenByProfile = new Set(
    (Array.isArray(listProfile.hidden_columns) ? listProfile.hidden_columns : []).map(String),
  );
  const customFilters = object(object(contract.searchContract.custom).filters);
  const searchFields = [
    ...(Array.isArray(customFilters.fields) ? customFilters.fields : []),
    ...(Array.isArray(contract.searchContract.group_by)
      ? contract.searchContract.group_by
      : []),
  ] as Dictionary[];
  const searchByCode = new Map(
    searchFields
      .map((field) => [String(field.field ?? field.name ?? ""), field] as const)
      .filter(([code]) => Boolean(code)),
  );

  return listOrder.map((code) => {
    const existing = parsedByCode.get(code);
    if (existing) {
      return { ...existing, defaultVisible: !hiddenByProfile.has(existing.code) };
    }
    const search = searchByCode.get(code) || {};
    return {
      code,
      label: fieldLabel(code, search.label ?? search.string ?? labels[code] ?? code),
      type: String(search.type ?? "char").toLowerCase(),
      hidden: [search.invisible, search.hidden, search.ui_hidden].some((value) => value === true || value === 1 || value === "1" || value === "true"),
      defaultVisible: !hiddenByProfile.has(code),
      sortable: search.sortable === false ? false : undefined,
      required: false,
      readonly: true,
      relation: String(search.relation ?? ""),
      selection: normalizeSelection(search.choices ?? search.selection),
      config: { ...search, source: "data_source_field_fallback" },
    };
  });
}

function relationIds(value: unknown): number[] {
  const rows = Array.isArray(value)
    ? value.length === 2 && typeof value[0] === "number" && typeof value[1] === "string"
      ? [value]
      : value
    : value === undefined || value === null || value === false || value === ""
      ? []
      : [value];
  return rows
    .flatMap((item) => {
      if (Array.isArray(item)) {
        if (item.length === 2 && typeof item[1] === "string") return [item[0]];
        const code = Number(item[0]);
        if (code === 6 && Array.isArray(item[2])) return item[2];
        if ([1, 4].includes(code) && Number.isFinite(Number(item[1]))) return [item[1]];
        if ([0, 2, 3, 5].includes(code)) return [];
        return [item[0]];
      }
      if (item && typeof item === "object")
        return [(item as Dictionary).id ?? (item as Dictionary).value];
      if (typeof item === "string" && item.includes(",")) return [item.split(",", 1)[0]];
      return [item];
    })
    .map(Number)
    .filter((id) => Number.isInteger(id) && id > 0);
}

export function normalizeFieldWriteValue(
  value: unknown,
  field: FieldSpec,
): unknown {
  if (field.type === "many2one") return relationIds(value)[0] || false;
  if (field.type === "many2many") return [[6, 0, relationIds(value)]];
  if (field.type === "one2many") {
    if (!Array.isArray(value)) return [];
    if (
      value.every((item) => Array.isArray(item) && typeof item[0] === "number")
    )
      return value;
    return value.flatMap((item) => {
      const row = object(item);
      const id = Number(row.id || row.res_id || 0);
      if (id > 0) return [[1, id, object(row.values || row)]];
      return Object.keys(row).length ? [[0, 0, object(row.values || row)]] : [];
    });
  }
  if (field.type === "boolean") return Boolean(value);
  if (["integer", "float", "monetary"].includes(field.type)) {
    if (
      value === "" ||
      value === undefined ||
      value === null ||
      value === false
    )
      return false;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : false;
  }
  return value ?? false;
}

function staticFlag(value: unknown) {
  return value === true || value === 1 || value === "1" || value === "true";
}

export function buildWritableFormValues(
  fields: FieldSpec[],
  values: Dictionary,
): Dictionary {
  return fields.reduce<Dictionary>((payload, field) => {
    const config = field.config || {};
    const invisible =
      staticFlag(config.invisible) ||
      staticFlag(config.componentConfig?.invisible);
    const readonly =
      field.readonly ||
      staticFlag(config.readonly) ||
      staticFlag(config.componentConfig?.readonly);
    if (!invisible && !readonly)
      payload[field.code] = normalizeFieldWriteValue(values[field.code], field);
    return payload;
  }, {});
}

export function formSourceContext(contract: PageContract): Dictionary {
  const meta = object(
    contract.dataContract.dataMeta ?? contract.dataContract.data_meta,
  );
  const source = object(meta.sourceContext ?? meta.source_context);
  return object(source.context);
}

export function effectiveRights(contract: PageContract): Dictionary {
  const global = object(
    contract.statusContract.globalStatus ??
      contract.statusContract.global_status,
  );
  return object(
    global.effectiveRecordCapabilities ??
      global.effective_record_capabilities ??
      global.recordRights ??
      global.record_rights ??
      global.modelRights ??
      global.model_rights,
  );
}

function actionType(item: Dictionary): BusinessAction["type"] {
  const text = String(
    item.semantic ??
      item.type ??
      object(item.presentation).tier ??
      item.label ??
      "",
  ).toLowerCase();
  if (/delete|danger|cancel|reject|删除|取消|驳回/.test(text)) return "danger";
  if (/warning|archive|警告|归档/.test(text)) return "warning";
  if (/success|approve|通过|批准/.test(text)) return "success";
  return "primary";
}

function actionPresentationTier(item: Dictionary): NonNullable<BusinessAction["presentationTier"]> {
  const explicit = String(
    item.presentationTier ??
      item.presentation_tier ??
      object(item.presentation).tier ??
      object(item.actionPresentation).tier ??
      object(item.action_presentation).tier ??
      "",
  ).trim().toLowerCase();
  if (["primary", "secondary", "overflow", "configuration", "inline"].includes(explicit))
    return explicit as NonNullable<BusinessAction["presentationTier"]>;
  const intent = String(item.intent ?? item.backend_intent ?? "").trim().toLowerCase();
  if (["ui.local_mode", "ui.form_field_configuration", "ui.form_custom_field.create", "ui.business_config.lowcode.apply"].includes(intent))
    return "configuration";
  if (/setting|config|配置|字段|表单设置/.test(String(item.label ?? item.name ?? "").toLowerCase()))
    return "configuration";
  if (/submit|approve|reject|confirm|publish|rollback|validate|import|generate|execute|提交|审批|驳回|确认|发布|回滚|校验|导入|生成/.test(
    String(item.label ?? item.name ?? item.method ?? "").toLowerCase(),
  )) return "overflow";
  return "secondary";
}

export function resolveActions(
  contract: PageContract,
  scope = "",
  options: ActionResolutionOptions = {},
): BusinessAction[] {
  const source = contract.actionContract;
  const legacySource = contract.raw || {};
  const sourceGroups = [
    ...(Array.isArray(source.actionGroups) ? source.actionGroups : []),
    ...(Array.isArray(source.action_groups) ? source.action_groups : []),
    ...(Array.isArray(legacySource.actionGroups) ? legacySource.actionGroups : []),
    ...(Array.isArray(legacySource.action_groups) ? legacySource.action_groups : []),
  ];
  const grouped = sourceGroups.flatMap((group) => {
    if (!group || typeof group !== "object") return [];
    const row = group as Dictionary;
    const groupKey = String(row.key ?? row.name ?? row.label ?? "").trim();
    const groupLabel = String(row.label ?? row.title ?? row.name ?? "").trim();
    return (Array.isArray(row.actions) ? row.actions : []).map((action) => ({
      ...(action as Dictionary),
      groupKey,
      groupLabel,
    }));
  });
  const rows = [
    ...(Array.isArray(source.buttons) ? source.buttons : []),
    ...(Array.isArray(source.actions) ? source.actions : []),
    ...(Array.isArray(source.actionRuleList) ? source.actionRuleList : []),
    ...(Array.isArray(source.action_rule_list) ? source.action_rule_list : []),
    ...(Array.isArray(legacySource.buttons) ? legacySource.buttons : []),
    ...(Array.isArray(legacySource.actions) ? legacySource.actions : []),
    ...grouped,
  ] as Dictionary[];
  const statusRows = (
    Array.isArray(contract.statusContract.buttonStatus)
      ? contract.statusContract.buttonStatus
      : Array.isArray(contract.statusContract.button_status)
        ? contract.statusContract.button_status
        : []
  ) as Dictionary[];
  const containerStatusRows = (
    Array.isArray(contract.statusContract.containerStatus)
      ? contract.statusContract.containerStatus
      : Array.isArray(contract.statusContract.container_status)
        ? contract.statusContract.container_status
        : []
  ) as Dictionary[];
  const seen = new Set<string>();
  return rows.flatMap((item) => {
    const key = String(
      item.actionKey ??
        item.action_key ??
        item.key ??
        item.name ??
        item.method ??
        "",
    ).trim();
    const target = [item.targetScope, item.target_scope, item.sourceChannel, item.source_channel, item.kind, item.triggerType]
      .map((value) => String(value || "").toLowerCase())
      .join(" ");
    const identity = String(
      item.backendIdentity ?? item.backend_identity ?? "",
    );
    const status = statusRows.find((row) => {
      const statusKey = String(
        row.btnId ??
          row.btn_id ??
          row.buttonId ??
          row.button_id ??
          row.key ??
          "",
      );
      const statusIdentity = String(
        row.backendIdentity ?? row.backend_identity ?? "",
      );
      return (
        statusKey === key ||
        statusKey === `btn.${key}` ||
        Boolean(identity && statusIdentity === identity)
      );
    });
    const sourceWidgetId = String(item.sourceWidgetId ?? item.source_widget_id ?? "").trim();
    const containerStatus = sourceWidgetId
      ? containerStatusRows.find((row) => String(row.containerId ?? row.container_id ?? "").trim() === sourceWidgetId)
      : undefined;
    if (
      !key ||
      seen.has(key) ||
      item.allowed === false ||
      item.visible === false ||
      item.disabled === true ||
      status?.visible === false ||
      status?.allowed === false ||
      containerStatus?.visible === false ||
      containerStatus?.allowed === false
    )
      return [];
    if (scope === "form") {
      const label = String(item.label ?? item.string ?? item.title ?? key);
      const intentName = String(item.intent ?? item.backend_intent ?? "").toLowerCase();
      const sourceWidgetId = String(item.sourceWidgetId ?? item.source_widget_id ?? "").trim().toLowerCase();
      const targetScope = String(item.targetScope ?? item.target_scope ?? "").trim().toLowerCase();
      const triggerType = String(item.triggerType ?? item.trigger_type ?? "").trim().toLowerCase();
      if (options.intakeMode) return [];
      if (options.nativeTree && !(
        sourceWidgetId === "page.header"
        || (sourceWidgetId === "page.root" && ["header", "page"].includes(targetScope))
      )) return [];
      const formSource = /form|header|record|workflow|object|buttons/.test(target);
      if (!formSource || /row|batch|column|selector|list|tree/.test(target) || triggerType === "row_click") return [];
      if (/^(显示|隐藏)/.test(label) || /column|optional|visibility/.test(key.toLowerCase())) return [];
      if (label.trim().toLowerCase() === key.toLowerCase()) return [];
      if (intentName === "open" && !Object.keys(object(item.button)).length) return [];
    }
    if (scope === "row") {
      const sourceWidgetId = String(item.sourceWidgetId ?? item.source_widget_id ?? "").trim().toLowerCase();
      const triggerType = String(item.triggerType ?? item.trigger_type ?? "").trim().toLowerCase();
      if (sourceWidgetId !== "page.row" && triggerType !== "row_click") return [];
    }
    if (scope && scope !== "form" && target && !target.includes(scope))
      return [];
    seen.add(key);
    return [
      {
        key,
        label: String(item.label ?? item.string ?? item.title ?? key),
        type: actionType(item),
        intent: String(item.intent ?? item.backend_intent ?? ""),
        button: object(
          item.button ?? {
            name: item.name ?? item.method ?? key,
            type: item.type ?? "object",
          },
        ),
        params: object(item.params),
        target: object(item.target),
        actionId: String(item.actionId ?? item.action_id ?? "").trim(),
        backendIdentity: String(item.backendIdentity ?? item.backend_identity ?? "").trim(),
        sourceWidgetId: String(item.sourceWidgetId ?? item.source_widget_id ?? ""),
        targetScope: String(item.targetScope ?? item.target_scope ?? "").trim().toLowerCase(),
        sourceChannel: String(item.sourceChannel ?? item.source_channel ?? "").trim(),
        triggerType: String(item.triggerType ?? item.trigger_type ?? "").trim().toLowerCase(),
        presentationTier: actionPresentationTier(item),
        confirmMessage: String(
          object(item.actionSafety ?? item.action_safety).confirm_message ??
            item.confirm_message ??
            "",
        ),
        enabled:
          item.enabled !== false &&
          status?.disabled !== true &&
          status?.allowed !== false &&
          containerStatus?.disabled !== true &&
          containerStatus?.allowed !== false,
        reasonCode: String(
          status?.reasonCode ??
          status?.reason_code ??
          containerStatus?.reasonCode ??
          containerStatus?.reason_code ??
          item.reason_code ??
          "",
        ),
      },
    ];
  });
}

export function pageTitle(contract: PageContract, fallback = "业务页面") {
  return String(
    contract.pageInfo.pageName ??
      contract.pageInfo.page_name ??
      contract.pageInfo.title ??
      fallback,
  );
}
