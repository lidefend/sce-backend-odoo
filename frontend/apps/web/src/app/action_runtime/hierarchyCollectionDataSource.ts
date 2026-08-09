import { listRecords } from '../../api/data';
import { executeButton } from '../../api/executeButton';

export type HierarchyDict = Record<string, unknown>;
export type HierarchyLevelConfig = {
  key: string;
  model: string;
  fields: string[];
  label_field: string;
  code_field: string;
  parent_key?: string;
  parent_field?: string;
  self_parent_field?: string;
  order?: string;
  domain?: unknown[];
};
export type HierarchyTreeNode = {
  key: string;
  id: number;
  levelKey: string;
  code: string;
  label: string;
  children: HierarchyTreeNode[];
};
export type HierarchyListConfig = {
  model: string;
  fields: string[];
  bindings: HierarchyDict;
  order: string;
  pageSize: number;
  domain?: unknown[];
};
export type HierarchyCommand = {
  key: string;
  label: string;
  method: string;
  placement?: 'toolbar' | 'overflow';
  group?: string;
  availability_field?: string;
};

function normalizeRows(value: unknown): HierarchyDict[] {
  const payload = value && typeof value === 'object' ? value as HierarchyDict : {};
  return Array.isArray(payload.records) ? payload.records as HierarchyDict[] : [];
}

function relationId(value: unknown): number {
  return Array.isArray(value) ? Number(value[0] || 0) : Number(value || 0);
}

export async function loadHierarchyTree(levels: HierarchyLevelConfig[]): Promise<HierarchyTreeNode[]> {
  const nodeMaps = new Map<string, Map<number, HierarchyTreeNode>>();
  let roots: HierarchyTreeNode[] = [];
  for (const level of levels) {
    const levelRows: HierarchyDict[] = [];
    const batchSize = 5000;
    for (let offset = 0; ; offset += batchSize) {
      const result = await listRecords({ model: level.model, fields: level.fields, domain: level.domain || [], offset, limit: batchSize, order: level.order });
      const batch = normalizeRows(result);
      levelRows.push(...batch);
      if (batch.length < batchSize) break;
    }
    const nodes = new Map<number, HierarchyTreeNode>();
    levelRows.forEach((row) => {
      const id = Number(row.id || 0);
      if (id) nodes.set(id, { key: `${level.key}:${id}`, id, levelKey: level.key, code: String(row[level.code_field] || ''), label: String(row[level.label_field] || ''), children: [] });
    });
    nodeMaps.set(level.key, nodes);
    const nestedNodeIds = new Set<number>();
    if (level.self_parent_field) {
      levelRows.forEach((row) => {
        const node = nodes.get(Number(row.id));
        const parent = nodes.get(relationId(row[level.self_parent_field || '']));
        if (node && parent && node !== parent) {
          parent.children.push(node);
          nestedNodeIds.add(node.id);
        }
      });
    }
    if (!level.parent_key) roots = [...nodes.values()].filter((node) => !nestedNodeIds.has(node.id));
    else {
      const parents = nodeMaps.get(level.parent_key);
      levelRows.forEach((row) => {
        const node = nodes.get(Number(row.id));
        const parent = parents?.get(relationId(row[level.parent_field || '']));
        if (node && parent && !nestedNodeIds.has(node.id)) parent.children.push(node);
      });
    }
  }
  return roots;
}

export async function loadHierarchyRows(options: {
  config: HierarchyListConfig;
  selectedNode: HierarchyTreeNode | null;
  keyword: string;
  offset: number;
}): Promise<{ rows: HierarchyDict[]; total: number }> {
  const domain: unknown[] = [...(options.config.domain || [])];
  if (options.selectedNode) {
    const rawBinding = options.config.bindings[options.selectedNode.levelKey];
    const binding = rawBinding && typeof rawBinding === 'object'
      ? rawBinding as HierarchyDict
      : { field: rawBinding, operator: '=' };
    const field = String(binding.field || '');
    const operator = String(binding.operator || '=');
    if (field) domain.push([field, operator, options.selectedNode.id]);
  }
  const result = await listRecords({
    model: options.config.model,
    fields: options.config.fields,
    domain,
    search_term: options.keyword,
    need_total: true,
    offset: options.offset,
    limit: options.config.pageSize,
    order: options.config.order,
  });
  const rows = normalizeRows(result);
  return { rows, total: Number((result as unknown as HierarchyDict).total ?? rows.length) };
}

export async function executeHierarchyCommand(options: {
  model: string;
  recordId: number;
  command: HierarchyCommand;
}): Promise<void> {
  await executeButton({
    model: options.model,
    res_id: options.recordId,
    button: { name: options.command.method, type: 'object' },
    context: {},
  });
}
