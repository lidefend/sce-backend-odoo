import { intentRequest } from './intents';
import { PRODUCT_CAPABILITY_INTENTS } from '../app/businessConfigBoundaries';

/**
 * `product.configuration.capability.catalog` 的投影形状。
 *
 * 字段与后端 `build_catalog`（P1:smart_construction_core）一一对应；前端只做
 * 原样消费，不补齐、不改写、不推导。`available` / `status` / `reason` 均由
 * 声明层给出。
 */
export type ProductCapabilityAudience = {
  key: string;
  label: string;
  description: string;
};

export type ProductCapabilityLoginHomeBlock = {
  key: string;
  label: string;
  required: boolean;
  authority: string;
  available: boolean;
  reason: string;
};

export type ProductCapabilityLoginHome = {
  audience: string;
  blocks: ProductCapabilityLoginHomeBlock[];
  empty_state_policy: Record<string, unknown>;
};

export type ProductCapabilityConfigurationCard = {
  key: string;
  label: string;
  status: string;
  available: boolean;
  reason: string;
  entry: string;
  authority: string;
};

export type ProductCapabilitySystemParameterCategory = {
  key: string;
  label: string;
  examples: string[];
};

export type ProductCapabilityItem = {
  key: string;
  label: string;
  audience: string;
  status: string;
  available: boolean;
  reason: string;
  entry: string;
  authority: string;
  description: string;
};

export type UserCapabilityItem = ProductCapabilityItem & { status_label: string; reason_code: string };

export type ProductCapabilityCatalog = {
  user_capabilities: { items: UserCapabilityItem[]; empty_message: string };
  schema_version: string;
  manifest_status: string;
  objective: string;
  primary_audience: string;
  audiences: ProductCapabilityAudience[];
  login_home: ProductCapabilityLoginHome;
  configuration_cards: ProductCapabilityConfigurationCard[];
  system_parameter_categories: ProductCapabilitySystemParameterCategory[];
  capabilities: ProductCapabilityItem[];
  guardrails: string[];
  reason: string;
  success?: boolean;
  reason_code?: string;
};

export function fetchProductCapabilityCatalog() {
  return intentRequest<ProductCapabilityCatalog>({
    intent: PRODUCT_CAPABILITY_INTENTS.catalog,
  });
}
