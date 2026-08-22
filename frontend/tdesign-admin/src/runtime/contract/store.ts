import type { ContractDictionary, ExecutablePageContract } from './types';

export interface NormalizedContractStore {
  fieldsByCode: ReadonlyMap<string, ContractDictionary>;
  widgetsById: ReadonlyMap<string, ContractDictionary>;
  actionsByKey: ReadonlyMap<string, ContractDictionary>;
  buttonStatusByKey: ReadonlyMap<string, ContractDictionary>;
  effectiveRights: ContractDictionary;
}

function dict(value: unknown): ContractDictionary {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as ContractDictionary) : {};
}

function text(value: unknown) {
  return String(value || '').trim();
}

function rows(value: unknown): ContractDictionary[] {
  return Array.isArray(value) ? value.map(dict).filter((item) => Object.keys(item).length) : [];
}

function setAliases(map: Map<string, ContractDictionary>, item: ContractDictionary, aliases: unknown[]) {
  aliases
    .map(text)
    .filter(Boolean)
    .forEach((key) => map.set(key, item));
}

export function createNormalizedContractStore(contract: ExecutablePageContract): NormalizedContractStore {
  const fieldsByCode = new Map<string, ContractDictionary>();
  const widgetsById = new Map<string, ContractDictionary>();
  const actionsByKey = new Map<string, ContractDictionary>();
  const buttonStatusByKey = new Map<string, ContractDictionary>();
  const walk = (value: unknown) => {
    rows(value).forEach((node) => {
      const info = dict(node.fieldInfo || node.field_info);
      const code = text(
        node.fieldCode || node.field_code || info.name || (text(node.type) === 'field' ? node.name : ''),
      );
      const widgetId = text(node.widgetId || node.widget_id || (code ? `field.${code}` : ''));
      if (code) fieldsByCode.set(code, node);
      if (widgetId) widgetsById.set(widgetId, node);
      ['children', 'widgetList', 'pages', 'tabs', 'nodes', 'items', 'fields', 'groups', 'sub_groups'].forEach((key) =>
        walk(node[key]),
      );
    });
  };
  const layout = contract.layoutContract;
  walk(layout.containerTree || layout.container_tree || layout.widgetList || layout.widget_list);

  const action = contract.actionContract;
  rows(action.actionRuleList || action.action_rule_list || action.actions || action.buttons).forEach((item) => {
    const key = text(
      item.actionKey || item.action_key || item.key || item.name || item.method || item.actionId || item.action_id,
    );
    const actionId = text(item.actionId || item.action_id);
    const identity = text(item.backendIdentity || item.backend_identity);
    setAliases(actionsByKey, item, [key, actionId, identity]);
  });

  const status = contract.statusContract;
  rows(status.buttonStatus || status.button_status).forEach((item) => {
    const key = text(item.btnId || item.btn_id || item.buttonId || item.button_id || item.key);
    const identity = text(item.backendIdentity || item.backend_identity);
    setAliases(buttonStatusByKey, item, [key, key.startsWith('btn.') ? key.slice(4) : `btn.${key}`, identity]);
  });

  const global = dict(status.globalStatus || status.global_status);
  const effectiveRights = dict(
    global.effectiveRecordCapabilities ||
      global.effective_record_capabilities ||
      global.recordRights ||
      global.record_rights ||
      global.modelRights ||
      global.model_rights,
  );
  return { fieldsByCode, widgetsById, actionsByKey, buttonStatusByKey, effectiveRights };
}
