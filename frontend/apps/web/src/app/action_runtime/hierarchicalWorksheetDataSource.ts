import { listRecords } from '../../api/data';

export type WorksheetDict = Record<string, unknown>;
export type WorksheetHierarchyConfig = {
  navigation_mode: string;
  navigation_groups: Array<{ field: string; label: string; empty_label: string }>;
  model: string;
  fields: string[];
  parent_field: string;
  project_field: string;
  code_field: string;
  label_field: string;
  type_field: string;
  leaf_values: string[];
  group_field_map: Record<string, string>;
  domain: unknown[];
  order: string;
  navigation_depth: number;
};
export type WorksheetSheetConfig = {
  model: string;
  fields: string[];
  binding_field: string;
  ordinal_field: string;
  presentation_mode: string;
  row_kind_field: string;
  item_values: string[];
  heading_values: string[];
  summary_values: string[];
  variance_field: string;
  variance_tolerance: number;
  blank_fields_by_kind: Record<string, string[]>;
  domain: unknown[];
  order: string;
};
export type WorksheetNode = {
  key: string;
  id: number;
  code: string;
  label: string;
  kind: string;
  depth: number;
  raw: WorksheetDict;
  children: WorksheetNode[];
  recordIds?: number[];
};

function records(value: unknown): WorksheetDict[] {
  const payload = value && typeof value === 'object' ? value as WorksheetDict : {};
  return Array.isArray(payload.records) ? payload.records as WorksheetDict[] : [];
}

export function relationId(value: unknown): number {
  return Array.isArray(value) ? Number(value[0] || 0) : Number(value || 0);
}

async function loadAll(model: string, fields: string[], domain: unknown[], order: string): Promise<WorksheetDict[]> {
  const output: WorksheetDict[] = [];
  const limit = 5000;
  for (let offset = 0; ; offset += limit) {
    const response = await listRecords({ model, fields, domain, order, offset, limit });
    const batch = records(response);
    output.push(...batch);
    if (batch.length < limit) return output;
  }
}

export async function loadHierarchicalWorksheet(
  hierarchy: WorksheetHierarchyConfig,
  sheet: WorksheetSheetConfig,
): Promise<{
  roots: WorksheetNode[];
  nodesById: Map<number, WorksheetNode>;
  recordsByNode: Map<number, WorksheetDict>;
  sourceRows: WorksheetDict[];
  recordCount: number;
}> {
  const sheetPromise = loadAll(sheet.model, sheet.fields, sheet.domain, sheet.order);
  const hierarchyPromise = hierarchy.navigation_mode === 'sheet_groups'
    ? Promise.resolve([] as WorksheetDict[])
    : loadAll(hierarchy.model, hierarchy.fields, hierarchy.domain, hierarchy.order);
  const [hierarchyRows, sheetRows] = await Promise.all([hierarchyPromise, sheetPromise]);
  const nodes = new Map<number, WorksheetNode>();
  hierarchyRows.forEach((row) => {
    const id = Number(row.id || 0);
    if (!id) return;
    nodes.set(id, {
      key: `node:${id}`,
      id,
      code: String(row[hierarchy.code_field] || ''),
      label: String(row[hierarchy.label_field] || ''),
      kind: String(row[hierarchy.type_field] || ''),
      depth: 0,
      raw: row,
      children: [],
    });
  });
  const roots: WorksheetNode[] = [];
  hierarchyRows.forEach((row) => {
    const node = nodes.get(Number(row.id || 0));
    if (!node) return;
    const parent = nodes.get(relationId(row[hierarchy.parent_field]));
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  });
  const setDepth = (node: WorksheetNode, depth: number) => {
    node.depth = depth;
    node.children.forEach((child) => setDepth(child, depth + 1));
  };
  roots.forEach((root) => setDepth(root, 0));
  if (hierarchy.navigation_mode === 'sheet_groups') {
    let virtualId = -1;
    const groupNodes = new Map<string, WorksheetNode>();
    const displayGroupValue = (value: unknown, emptyLabel: string) => {
      if (Array.isArray(value)) return String(value[1] || value[0] || emptyLabel);
      return String(value || emptyLabel);
    };
    sheetRows.forEach((row) => {
      let parent: WorksheetNode | null = null;
      let path = '';
      (hierarchy.navigation_groups || []).forEach((group, depth) => {
        const label = displayGroupValue(row[group.field], group.empty_label);
        path = `${path}/${group.field}:${label}`;
        let node = groupNodes.get(path);
        if (!node) {
          node = {
            key: `group:${path}`,
            id: virtualId--,
            code: '',
            label,
            kind: group.field,
            depth,
            raw: { group_field: group.field, group_label: group.label },
            children: [],
            recordIds: [],
          };
          groupNodes.set(path, node);
          if (parent) parent.children.push(node); else roots.push(node);
        }
        const recordId = Number(row.id || 0);
        if (recordId && !node.recordIds?.includes(recordId)) node.recordIds?.push(recordId);
        parent = node;
      });
    });
  }
  const recordsByNode = new Map<number, WorksheetDict>();
  sheetRows.forEach((row) => {
    const nodeId = relationId(row[sheet.binding_field]);
    if (nodeId && !recordsByNode.has(nodeId)) recordsByNode.set(nodeId, row);
  });
  const itemValues = new Set(sheet.item_values || []);
  const recordCount = itemValues.size && sheet.row_kind_field
    ? sheetRows.filter((row) => itemValues.has(String(row[sheet.row_kind_field] || ''))).length
    : sheetRows.length;
  return { roots, nodesById: nodes, recordsByNode, sourceRows: sheetRows, recordCount };
}

export function collectNodeIds(node: WorksheetNode): Set<number> {
  const ids = new Set<number>();
  const visit = (current: WorksheetNode) => {
    ids.add(current.id);
    current.children.forEach(visit);
  };
  visit(node);
  return ids;
}
