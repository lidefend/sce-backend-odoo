import { listRecords } from '../../api/data';
import { requireDeclaredNumber } from '../contract/contractGap';
export { ContractGapError, isContractGapError } from '../contract/contractGap';
export type { ContractDefectRef } from '../contract/contractGap';
import type { WorksheetDomainTab } from './hierarchicalWorksheetDomainTabs';

export { resolveWorksheetDomainTabs, applyWorksheetDomainTab } from './hierarchicalWorksheetDomainTabs';
export type { WorksheetDomainTab } from './hierarchicalWorksheetDomainTabs';

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
  context?: WorksheetDict;
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
  /** 可编辑字段（G7.2 内联编辑；后端 config 未注入时前端回退默认写入面） */
  editable_fields?: string[];
  domain: unknown[];
  context?: WorksheetDict;
  /** 数据域 tab（G7.3；后端 config 未注入时前端无 tab，行为与旧契约一致） */
  domain_tabs?: WorksheetDomainTab[];
  /** 契约声明的页大小（首屏可用批次规模）；前端原样消费，缺失或非法即停机。 */
  page_size?: number;
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

/**
 * 消费契约声明的首屏页大小。声明由装配层通过受管通道发布
 * （`hierarchical_worksheet.page_size` → 上下文 `hierarchy_page_size` → native tree
 * `page_size` → 平台缺省），前端只消费声明值：不提供默认值、不夹取范围。
 * 声明缺失或非法即抛出 `ContractGapError`，由调用方进入显式停机状态。
 */
export function requireDeclaredPageSize(sheet: WorksheetSheetConfig): number {
  return requireDeclaredNumber(sheet.page_size, {
    missing: 'config.sheet.page_size',
    requiredDeclarationLayer: 'P0:smart_core:page_assembler._inject_native_hierarchical_worksheet',
  });
}

/**
 * 后台续载批次大小：登记的渲染/传输机制常量（请求分块）。它不属于产品语义，
 * 不改变用户可见集合、权限或状态，只决定整表续载的请求分块规模。
 */
export const WORKSHEET_DRAIN_PAGE_LIMIT = 5000;
/**
 * 后台续载批次之间的让渡间隔（毫秒）。整表续载不能独占连接：批次之间让出
 * 一段时间，让页面在网络批次之间沉降，而不是从首屏开始连续占满连接。
 */
export const WORKSHEET_DRAIN_BATCH_YIELD_MS = 800;

export type WorksheetLoadResult = {
  roots: WorksheetNode[];
  nodesById: Map<number, WorksheetNode>;
  recordsByNode: Map<number, WorksheetDict>;
  sourceRows: WorksheetDict[];
  recordCount: number;
};

/**
 * 首个批次已到齐、工作表可以实际使用时回调一次。之后仍会在后台续载到整表，
 * 因此“可用”不再等价于“已全量加载”。
 */
export type WorksheetLoadHooks = { onUsable?: (result: WorksheetLoadResult) => void };

export type WorksheetListSource = typeof listRecords;

export type WorksheetLoadOptions = {
  /** 数据读取入口（默认 `listRecords`）；测试注入替代实现以绑定声明消费行为。 */
  list?: WorksheetListSource;
  firstPageLimit?: number;
  drainPageLimit?: number;
  drainBatchYieldMs?: number;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

function records(value: unknown): WorksheetDict[] {
  const payload = value && typeof value === 'object' ? value as WorksheetDict : {};
  return Array.isArray(payload.records) ? payload.records as WorksheetDict[] : [];
}

export function relationId(value: unknown): number {
  return Array.isArray(value) ? Number(value[0] || 0) : Number(value || 0);
}

type LoadAllOptions = {
  list: WorksheetListSource;
  firstPageLimit: number;
  drainPageLimit: number;
  drainBatchYieldMs: number;
  onBatch?: (rows: WorksheetDict[]) => void;
};

async function loadAll(
  model: string,
  fields: string[],
  domain: unknown[],
  order: string,
  context: WorksheetDict | undefined,
  options: LoadAllOptions,
): Promise<WorksheetDict[]> {
  const output: WorksheetDict[] = [];
  let offset = 0;
  let limit = Math.max(1, options.firstPageLimit);
  for (;;) {
    const response = await options.list({ model, fields, domain, context, order, offset, limit });
    const batch = records(response);
    output.push(...batch);
    // Snapshot the arrived rows: the usable declaration must describe the first
    // batch as it was, not the array that the background drain keeps growing.
    options.onBatch?.(output.slice());
    if (batch.length < limit) return output;
    offset += limit;
    limit = Math.max(1, options.drainPageLimit);
    if (options.drainBatchYieldMs > 0) await sleep(options.drainBatchYieldMs);
  }
}

/** 由已到齐的行构建工作表结果；首屏可用与整表完成共用同一份构建语义。 */
function buildWorksheet(
  hierarchy: WorksheetHierarchyConfig,
  sheet: WorksheetSheetConfig,
  hierarchyRows: WorksheetDict[],
  sheetRows: WorksheetDict[],
): WorksheetLoadResult {
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

export async function loadHierarchicalWorksheet(
  hierarchy: WorksheetHierarchyConfig,
  sheet: WorksheetSheetConfig,
  hooks: WorksheetLoadHooks = {},
  options: WorksheetLoadOptions = {},
): Promise<WorksheetLoadResult> {
  const tuning = {
    list: options.list || listRecords,
    firstPageLimit: options.firstPageLimit ?? requireDeclaredPageSize(sheet),
    drainPageLimit: options.drainPageLimit ?? WORKSHEET_DRAIN_PAGE_LIMIT,
    drainBatchYieldMs: options.drainBatchYieldMs ?? WORKSHEET_DRAIN_BATCH_YIELD_MS,
  };
  const stage = {
    hierarchy: [] as WorksheetDict[],
    sheet: [] as WorksheetDict[],
    hierarchyUsable: hierarchy.navigation_mode === 'sheet_groups',
    sheetUsable: false,
    emitted: false,
  };
  const emitUsable = () => {
    if (stage.emitted || !stage.hierarchyUsable || !stage.sheetUsable) return;
    stage.emitted = true;
    hooks.onUsable?.(buildWorksheet(hierarchy, sheet, stage.hierarchy, stage.sheet));
  };
  const hierarchyPromise = hierarchy.navigation_mode === 'sheet_groups'
    ? Promise.resolve([] as WorksheetDict[])
    : loadAll(hierarchy.model, hierarchy.fields, hierarchy.domain, hierarchy.order, hierarchy.context, {
        ...tuning,
        onBatch: (rows) => { stage.hierarchy = rows; stage.hierarchyUsable = true; emitUsable(); },
      });
  const sheetPromise = loadAll(sheet.model, sheet.fields, sheet.domain, sheet.order, sheet.context, {
    ...tuning,
    onBatch: (rows) => { stage.sheet = rows; stage.sheetUsable = true; emitUsable(); },
  });
  const [hierarchyRows, sheetRows] = await Promise.all([hierarchyPromise, sheetPromise]);
  return buildWorksheet(hierarchy, sheet, hierarchyRows, sheetRows);
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
