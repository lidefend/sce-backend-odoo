/**
 * 产品配置能力目录的 fail-closed 消费投影。
 *
 * `product.configuration.capability.catalog` 是登录首屏 6 区块与配置工作台
 * 8 张卡片的唯一契约载体。消费规则：
 * - 声明面存在但形状非法 -> 抛 ContractGapError 停机（回声明层补齐）；
 * - 声明面为「空集合」是合法投影（例如非 business_full 账号没有 login_home
 *   区块），前端不得用默认值或特判兜底；
 * - 前端只原样透出 `key/label/status/available/reason/authority/entry`，
 *   不做任何能力推导。
 */
import type {
  ProductCapabilityConfigurationCard,
  ProductCapabilityItem,
  UserCapabilityItem,
  ProductCapabilityLoginHomeBlock,
} from '../api/productCapabilityCatalog';
import { contractGapError, type ContractGapError } from './contract/contractGap';

const REQUIRED_DECLARATION_LAYER = 'P1:smart_construction_core:product.configuration.capability.catalog';

function raiseGap(missing: string): never {
  throw contractGapError(
    { kind: 'contract_defect', missing, requiredDeclarationLayer: REQUIRED_DECLARATION_LAYER },
    `契约缺少合法声明 ${missing}：前端不停机兜底，等待声明层补齐`,
  );
}

function asObject(value: unknown, missing: string): Record<string, unknown> | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== 'object' || Array.isArray(value)) raiseGap(missing);
  return value as Record<string, unknown>;
}

function asList(value: unknown, missing: string): unknown[] {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value)) raiseGap(missing);
  return value;
}

function requiredText(value: unknown, missing: string): string {
  if (typeof value !== 'string' || !value.trim()) raiseGap(missing);
  return value;
}

function optionalText(value: unknown, missing: string): string {
  if (value === undefined || value === null) return '';
  if (typeof value !== 'string') raiseGap(missing);
  return value;
}

function declaredBoolean(value: unknown, missing: string): boolean {
  if (typeof value !== 'boolean') raiseGap(missing);
  return value;
}

function rowObject(value: unknown, missing: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) raiseGap(missing);
  return value as Record<string, unknown>;
}

/** 消费登录首屏 6 区块；非 business_full 账号的 login_home 为空投影，返回空集合。 */
export function projectLoginHomeBlocks(catalog: unknown): ProductCapabilityLoginHomeBlock[] {
  if (catalog === undefined || catalog === null) return [];
  const root = rowObject(catalog, 'product.configuration.capability.catalog');
  const home = asObject(root.login_home, 'product.configuration.capability.catalog.login_home');
  if (!home) return [];
  const blocks = asList(home.blocks, 'product.configuration.capability.catalog.login_home.blocks');
  return blocks.map((item, index) => {
    const row = rowObject(item, `product.configuration.capability.catalog.login_home.blocks[${index}]`);
    return {
      key: requiredText(row.key, `product.configuration.capability.catalog.login_home.blocks[${index}].key`),
      label: requiredText(row.label, `product.configuration.capability.catalog.login_home.blocks[${index}].label`),
      required: declaredBoolean(row.required, `product.configuration.capability.catalog.login_home.blocks[${index}].required`),
      authority: optionalText(row.authority, `product.configuration.capability.catalog.login_home.blocks[${index}].authority`),
      available: declaredBoolean(row.available, `product.configuration.capability.catalog.login_home.blocks[${index}].available`),
      reason: optionalText(row.reason, `product.configuration.capability.catalog.login_home.blocks[${index}].reason`),
    };
  });
}

/** 消费配置工作台 8 张卡；非 business_config_admin 账号的 configuration_cards 为空集合。 */
export function projectConfigurationCards(catalog: unknown): ProductCapabilityConfigurationCard[] {
  if (catalog === undefined || catalog === null) return [];
  const root = rowObject(catalog, 'product.configuration.capability.catalog');
  const cards = asList(root.configuration_cards, 'product.configuration.capability.catalog.configuration_cards');
  return cards.map((item, index) => {
    const row = rowObject(item, `product.configuration.capability.catalog.configuration_cards[${index}]`);
    return {
      key: requiredText(row.key, `product.configuration.capability.catalog.configuration_cards[${index}].key`),
      label: requiredText(row.label, `product.configuration.capability.catalog.configuration_cards[${index}].label`),
      status: optionalText(row.status, `product.configuration.capability.catalog.configuration_cards[${index}].status`),
      available: declaredBoolean(row.available, `product.configuration.capability.catalog.configuration_cards[${index}].available`),
      reason: optionalText(row.reason, `product.configuration.capability.catalog.configuration_cards[${index}].reason`),
      entry: optionalText(row.entry, `product.configuration.capability.catalog.configuration_cards[${index}].entry`),
      authority: optionalText(row.authority, `product.configuration.capability.catalog.configuration_cards[${index}].authority`),
    };
  });
}

/** 消费能力清单（后端已按账号投影，前端不得再按角色/菜单/模型过滤）。 */
export function projectCapabilities(catalog: unknown): ProductCapabilityItem[] {
  if (catalog === undefined || catalog === null) return [];
  const root = rowObject(catalog, 'product.configuration.capability.catalog');
  const rows = asList(root.capabilities, 'product.configuration.capability.catalog.capabilities');
  return rows.map((item, index) => {
    const row = rowObject(item, `product.configuration.capability.catalog.capabilities[${index}]`);
    return {
      key: requiredText(row.key, `product.configuration.capability.catalog.capabilities[${index}].key`),
      label: requiredText(row.label, `product.configuration.capability.catalog.capabilities[${index}].label`),
      audience: optionalText(row.audience, `product.configuration.capability.catalog.capabilities[${index}].audience`),
      status: optionalText(row.status, `product.configuration.capability.catalog.capabilities[${index}].status`),
      available: declaredBoolean(row.available, `product.configuration.capability.catalog.capabilities[${index}].available`),
      reason: optionalText(row.reason, `product.configuration.capability.catalog.capabilities[${index}].reason`),
      entry: optionalText(row.entry, `product.configuration.capability.catalog.capabilities[${index}].entry`),
      authority: optionalText(row.authority, `product.configuration.capability.catalog.capabilities[${index}].authority`),
      description: optionalText(row.description, `product.configuration.capability.catalog.capabilities[${index}].description`),
    };
  });
}

/** 判定一个错误是否为本投影的契约缺陷停机错误。 */
export function isProductCapabilityCatalogGap(error: unknown): error is ContractGapError {
  return typeof error === 'object' && error !== null
    && (error as { name?: string }).name === 'ContractGapError';
}

/**
 * 渲染层对「已声明的状态枚举」的展示文案映射（renderer dispatch，不是语义推导）：
 * 仅映射后端已声明的 available/partial/planned，未知声明值原样回显。
 */
export function capabilityStatusLabel(status: string): string {
  if (status === 'available') return '可用';
  if (status === 'partial') return '部分可用';
  if (status === 'planned') return '未发布';
  return status;
}


export function projectUserCapabilities(catalog: unknown): { items: UserCapabilityItem[]; empty_message: string } {
  const root = rowObject(catalog, 'user_capabilities.catalog');
  const surface = rowObject(root.user_capabilities, 'user_capabilities');
  if (!Array.isArray(surface.items)) raiseGap('user_capabilities.items');
  const base = projectCapabilities({ capabilities: surface.items });
  const items = base.map((row, index) => {
    const source = rowObject((surface.items as unknown[])[index], 'user_capabilities.item');
    return { ...row,
      status_label: requiredText(source.status_label, 'user_capabilities.status_label'),
      reason_code: optionalText(source.reason_code, 'user_capabilities.reason_code'),
    };
  });
  return { items, empty_message: requiredText(surface.empty_message, 'user_capabilities.empty_message') };
}

export function requireStructuredStartupCapabilities(value: unknown): asserts value is (Record<string, unknown> & { key: string; state: string; capability_state: string })[] {
  if (!Array.isArray(value)) raiseGap('system.init.capabilities');
  for (const item of value) {
    const row = rowObject(item, 'system.init.capabilities.item');
    requiredText(row.key, 'system.init.capabilities.key');
    requiredText(row.state, 'system.init.capabilities.state');
    requiredText(row.capability_state, 'system.init.capabilities.capability_state');
  }
}
