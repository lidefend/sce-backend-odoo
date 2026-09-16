function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

/** Read only provenance emitted by the final runtime contract, never saved-record counts. */
export function effectiveConfigurationLabel(contract: unknown, viewType: string, sources: Record<string, string> = {}): string {
  const root = object(contract);
  const form = object(object(object(root.formStructureContract).sourceAuthority).governance_source);
  const views = object(object(object(root.runtimeContract).governance).view_orchestration).views;
  const trace = object(object(views)[viewType]);
  const rows = viewType === 'form' && Array.isArray(form.businessConfigContracts)
    ? form.businessConfigContracts : trace.business_config_contracts;
  if (!Array.isArray(rows)) return '最终契约未提供配置来源，尚未核验';
  const names: Record<string, string> = { form: '表单新建态', tree: '列表', graph: '图表', pivot: '透视', kanban: '看板' };
  const prefix = names[viewType] || viewType;
  const legacyOverlay = Boolean(form.legacyFieldPolicyOverlay || trace.legacy_field_policy_overlay);
  if (!rows.length) return legacyOverlay ? `${prefix}：存在字段策略覆盖，契约未提供版本明细` : `${prefix}：使用默认配置（无覆盖配置）`;
  const onlyDefaults = rows.every((row) => sources[String(object(row).id)] === 'product_default');
  return `${prefix}：${onlyDefaults ? '使用默认配置；' : ''}${rows.map((row) => {
    const item = object(row);
    const category = sources[String(item.id)];
    const label = category === 'product_default' ? '产品默认' : category === 'enterprise_configuration' ? '企业配置' : '配置';
    return `${label} #${item.id} · v${item.version_no ?? '未知'}`;
  }).join('；')}${legacyOverlay ? '；另有字段策略覆盖（版本未提供）' : ''}`;
}
