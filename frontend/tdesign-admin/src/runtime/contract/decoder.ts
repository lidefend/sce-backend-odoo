import type { ContractDecodeIssue, ContractDictionary, ContractRuntimeMeta, ExecutablePageContract } from './types';
import { CONTRACT_VERSION } from './types';

function isRecord(value: unknown): value is ContractDictionary {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function record(value: unknown): ContractDictionary {
  return isRecord(value) ? value : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function aliasedRecord(source: ContractDictionary, camel: string, snake: string): ContractDictionary {
  return record(source[camel] || source[snake]);
}

function withAliases(source: ContractDictionary, aliases: Record<string, string>): ContractDictionary {
  const normalized = { ...source };
  Object.entries(aliases).forEach(([camel, snake]) => {
    if (normalized[camel] === undefined && normalized[snake] !== undefined) normalized[camel] = normalized[snake];
  });
  return normalized;
}

function addRequiredObjectIssue(
  issues: ContractDecodeIssue[],
  source: ContractDictionary,
  path: string,
  legacy: boolean,
) {
  if (Object.keys(source).length) return;
  issues.push({
    path,
    code: 'CONTRACT_SECTION_MISSING',
    message: `页面契约缺少 ${path}`,
    severity: legacy ? 'warning' : 'error',
  });
}

function addShapeIssue(
  issues: ContractDecodeIssue[],
  source: ContractDictionary,
  path: string,
  expected: 'object' | 'array' | 'array_or_object',
  legacy: boolean,
) {
  const parts = path.split('.');
  let current: unknown = source;
  for (const part of parts) {
    if (!isRecord(current)) return;
    current = current[part];
  }
  if (current === undefined || current === null) return;
  const valid =
    expected === 'array'
      ? Array.isArray(current)
      : expected === 'array_or_object'
        ? Array.isArray(current) || isRecord(current)
        : isRecord(current);
  if (valid) return;
  issues.push({
    path,
    code: 'CONTRACT_SHAPE_INVALID',
    message: `${path} 应为 ${expected}`,
    severity: legacy ? 'warning' : 'error',
  });
}

function validateContractShape(
  source: ContractDictionary,
  sections: {
    pageInfo: ContractDictionary;
    layoutContract: ContractDictionary;
    statusContract: ContractDictionary;
    actionContract: ContractDictionary;
    dataContract: ContractDictionary;
    runtimeContract: ContractDictionary;
  },
  issues: ContractDecodeIssue[],
  legacy: boolean,
) {
  addShapeIssue(issues, sections.layoutContract, 'containerTree', 'array', legacy);
  addShapeIssue(issues, sections.statusContract, 'buttonStatus', 'array', legacy);
  addShapeIssue(issues, sections.actionContract, 'actionRuleList', 'array', legacy);
  addShapeIssue(issues, sections.dataContract, 'mainData', 'object', legacy);
  // Odoo list contracts use an array when rows are embedded and an object
  // map when rows are delegated to an api.data data source. Both are valid
  // Contract v2 shapes; the runtime resolves the actual collection later.
  addShapeIssue(issues, sections.dataContract, 'tableRows', 'array_or_object', legacy);
  addShapeIssue(issues, sections.runtimeContract, 'patchOperations', 'array', legacy);

  const meta = record(source.meta);
  const lifecycle = record(meta.lifecycle || source.lifecycle);
  const definition = record(lifecycle.definition || lifecycle.contract_definition);
  if (Object.keys(lifecycle).length && !text(definition.schemaSha256 || definition.schema_sha256)) {
    issues.push({
      path: 'meta.lifecycle.definition.schemaSha256',
      code: 'CONTRACT_SCHEMA_HASH_MISSING',
      message: '契约生命周期缺少 schemaSha256，无法进行定义完整性校验',
      severity: 'warning',
    });
  }
  if (Object.keys(lifecycle).length && !text(lifecycle.sourceRevision || lifecycle.source_revision)) {
    issues.push({
      path: 'meta.lifecycle.sourceRevision',
      code: 'CONTRACT_SOURCE_REVISION_MISSING',
      message: '契约生命周期缺少 sourceRevision，无法定位后端定义版本',
      severity: 'warning',
    });
  }
}

function extractContract(payload: unknown): ContractDictionary {
  const source = record(payload);
  return record(
    source.unified_page_contract_v2 ||
      source.__unified_page_contract_v2 ||
      source.contract ||
      source.page_contract ||
      source,
  );
}

function resolveVersion(source: ContractDictionary, pageInfo: ContractDictionary): string {
  const meta = record(source.meta);
  return text(
    pageInfo.contractVersion ||
      pageInfo.contract_version ||
      source.contractVersion ||
      source.contract_version ||
      meta.contractVersion ||
      meta.contract_version,
  );
}

function resolveRuntimeMeta(
  source: ContractDictionary,
  pageInfo: ContractDictionary,
  issues: ContractDecodeIssue[],
): ContractRuntimeMeta {
  const meta = record(source.meta);
  const status = aliasedRecord(source, 'statusContract', 'status_contract');
  const globalStatus = withAliases(aliasedRecord(status, 'globalStatus', 'global_status'), {
    reasonCode: 'reason_code',
    suggestedAction: 'suggested_action',
  });
  const receivedVersion = resolveVersion(source, pageInfo);
  const major = Number(receivedVersion.split('.')[0]);
  const compatibility = !receivedVersion ? 'legacy' : major === 2 ? 'compatible' : 'unsupported';

  if (!receivedVersion) {
    issues.push({
      path: 'pageInfo.contractVersion',
      code: 'CONTRACT_VERSION_MISSING',
      message: '后端未返回契约版本，已按 legacy 模式执行并保留诊断信息',
      severity: 'warning',
    });
  } else if (major !== 2) {
    issues.push({
      path: 'pageInfo.contractVersion',
      code: 'CONTRACT_VERSION_UNSUPPORTED',
      message: `当前前端支持 2.0.x，后端返回 ${receivedVersion}`,
      severity: 'error',
    });
  }
  const lifecycle = record(meta.lifecycle || source.lifecycle);
  const definition = record(lifecycle.definition || lifecycle.contract_definition);
  const runtime = record(lifecycle.runtime);
  if (receivedVersion && lifecycle && Object.keys(lifecycle).length) {
    if (!text(definition.schemaId || definition.schema_id)) {
      issues.push({
        path: 'meta.lifecycle.definition.schemaId',
        code: 'CONTRACT_SCHEMA_ID_MISSING',
        message: '契约生命周期缺少 schemaId',
        severity: 'warning',
      });
    }
    if (!text(runtime.traceId || runtime.trace_id) && !text(meta.traceId || meta.trace_id)) {
      issues.push({
        path: 'meta.lifecycle.runtime.traceId',
        code: 'CONTRACT_TRACE_ID_MISSING',
        message: '契约生命周期缺少 traceId',
        severity: 'warning',
      });
    }
  }

  return {
    requestedVersion: CONTRACT_VERSION,
    receivedVersion,
    compatibility,
    reasonCode: text(globalStatus.reasonCode || source.reason_code || meta.reason_code),
    traceId: text(meta.traceId || meta.trace_id || source.trace_id),
    suggestedAction: text(globalStatus.suggestedAction || source.suggested_action || meta.suggested_action),
    issues,
  };
}

export class ContractDecodeError extends Error {
  readonly issues: ContractDecodeIssue[];
  readonly runtimeMeta: ContractRuntimeMeta;

  constructor(message: string, runtimeMeta: ContractRuntimeMeta) {
    super(message);
    this.name = 'ContractDecodeError';
    this.issues = runtimeMeta.issues;
    this.runtimeMeta = runtimeMeta;
  }
}

export function decodeExecutableContract(payload: unknown): ExecutablePageContract {
  const source = extractContract(payload);
  const issues: ContractDecodeIssue[] = [];
  const pageInfo = withAliases(aliasedRecord(source, 'pageInfo', 'page_info'), {
    pageId: 'page_id',
    sceneKey: 'scene_key',
    pageName: 'page_name',
    viewType: 'view_type',
    layoutType: 'layout_type',
    renderMode: 'render_mode',
    contractVersion: 'contract_version',
    clientType: 'client_type',
  });
  const layoutContract = withAliases(aliasedRecord(source, 'layoutContract', 'layout_contract'), {
    containerTree: 'container_tree',
    layoutHints: 'layout_hints',
    componentRegistry: 'component_registry',
    listProfile: 'list_profile',
  });
  const statusContract = withAliases(aliasedRecord(source, 'statusContract', 'status_contract'), {
    globalStatus: 'global_status',
    widgetStatus: 'widget_status',
    buttonStatus: 'button_status',
    containerStatus: 'container_status',
    selectorStatus: 'selector_status',
  });
  statusContract.globalStatus = withAliases(record(statusContract.globalStatus), {
    pageVisible: 'page_visible',
    pageAuth: 'page_auth',
    reasonCode: 'reason_code',
    suggestedAction: 'suggested_action',
    modelRights: 'model_rights',
    recordRights: 'record_rights',
    viewCapabilities: 'view_capabilities',
    entryCapabilities: 'entry_capabilities',
    effectiveRecordCapabilities: 'effective_record_capabilities',
    effectiveRenderProfile: 'effective_render_profile',
  });
  const actionContract = withAliases(aliasedRecord(source, 'actionContract', 'action_contract'), {
    actionRuleList: 'action_rule_list',
    dependencyGraph: 'dependency_graph',
    deletePolicy: 'delete_policy',
    surfacePolicies: 'surface_policies',
  });
  const dataContract = withAliases(aliasedRecord(source, 'dataContract', 'data_contract'), {
    mainData: 'main_data',
    tableRows: 'table_rows',
    relationRows: 'relation_rows',
    dictData: 'dict_data',
    dataSource: 'data_source',
    dataMeta: 'data_meta',
    treeData: 'tree_data',
    ganttData: 'gantt_data',
  });
  const runtimeContract = withAliases(aliasedRecord(source, 'runtimeContract', 'runtime_contract'), {
    patchStrategy: 'patch_strategy',
    cachePolicy: 'cache_policy',
    lazyContainer: 'lazy_container',
    retryPolicy: 'retry_policy',
    renderStrategy: 'render_strategy',
    patchOperations: 'patch_operations',
    tracePolicy: 'trace_policy',
    sourceContext: 'source_context',
  });
  const searchContract = withAliases(aliasedRecord(source, 'searchContract', 'search_contract'), {
    filterList: 'filter_list',
    groupByList: 'group_by_list',
  });
  const formStructureContract = aliasedRecord(source, 'formStructureContract', 'form_structure_contract');
  const workflowContract = aliasedRecord(source, 'workflowContract', 'workflow_contract');
  const runtimeMeta = resolveRuntimeMeta(source, pageInfo, issues);
  const legacy = runtimeMeta.compatibility === 'legacy';

  addRequiredObjectIssue(issues, pageInfo, 'pageInfo', legacy);
  addRequiredObjectIssue(issues, layoutContract, 'layoutContract', legacy);
  addRequiredObjectIssue(issues, statusContract, 'statusContract', legacy);
  addRequiredObjectIssue(issues, actionContract, 'actionContract', legacy);
  addRequiredObjectIssue(issues, dataContract, 'dataContract', legacy);
  addRequiredObjectIssue(issues, runtimeContract, 'runtimeContract', legacy);
  validateContractShape(
    source,
    { pageInfo, layoutContract, statusContract, actionContract, dataContract, runtimeContract },
    issues,
    legacy,
  );

  if (runtimeMeta.compatibility === 'unsupported' || issues.some((issue) => issue.severity === 'error')) {
    throw new ContractDecodeError('后端页面契约与当前前端不兼容', runtimeMeta);
  }

  return {
    ...source,
    pageInfo,
    layoutContract,
    statusContract,
    actionContract,
    dataContract,
    runtimeContract,
    searchContract,
    formStructureContract,
    workflowContract,
    __contractRuntime: runtimeMeta,
    __rawContract: source,
  };
}
