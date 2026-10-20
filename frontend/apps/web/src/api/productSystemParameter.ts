import { intentRequest } from './intents';
import { PRODUCT_SYSTEM_PARAMETER_INTENTS } from '../app/businessConfigBoundaries';

export type ProductSystemParameterCategory = {
  key: string;
  label: string;
};

export type ProductSystemParameterImpact = {
  surfaces: string[];
  summary: string;
  risk_level: string;
};

export type ProductSystemParameter = {
  key: string;
  category: string;
  label: string;
  description: string;
  type: string;
  default: unknown;
  allowed_values: unknown[];
  min?: number;
  max?: number;
  scope: string;
  maintainer_role: string;
  status: string;
  available: boolean;
  authority: string;
  impact: ProductSystemParameterImpact;
  current_value?: unknown;
};

export type ProductSystemParameterCatalog = {
  schema_version: string;
  status: string;
  objective: string;
  categories: ProductSystemParameterCategory[];
  parameters: ProductSystemParameter[];
  guardrails: string[];
  success?: boolean;
  reason_code?: string;
};

export type ProductSystemParameterPreview = {
  ok: boolean;
  parameter: string;
  reason?: string;
  status?: string;
  proposed_value?: unknown;
  impact?: ProductSystemParameterImpact;
  allowed_values?: unknown[];
  min?: number;
  max?: number;
  audit_required?: boolean;
  rollback_required?: boolean;
  change_set_required?: boolean;
  success?: boolean;
  reason_code?: string;
};

export type ProductSystemParameterChange = {
  id: number;
  parameter_key: string;
  proposed_value: unknown;
  previous_value: unknown;
  state: string;
  company_id: number;
  change_reason: string;
  risk_level: string;
  published_at: string | false;
  rolled_back_at: string | false;
  audit_json: Record<string, unknown>;
};

export type ProductSystemParameterMutationResult = {
  success: boolean;
  reason_code: string;
  change: ProductSystemParameterChange;
  impact?: ProductSystemParameterImpact;
  restored_value?: unknown;
};

export function fetchProductSystemParameterCatalog() {
  return intentRequest<ProductSystemParameterCatalog>({
    intent: PRODUCT_SYSTEM_PARAMETER_INTENTS.catalog,
  });
}

export function previewProductSystemParameter(parameterKey: string, proposedValue: unknown) {
  return intentRequest<ProductSystemParameterPreview>({
    intent: PRODUCT_SYSTEM_PARAMETER_INTENTS.preview,
    params: { parameter_key: parameterKey, proposed_value: proposedValue },
  });
}

export function publishProductSystemParameter(params: {
  parameter_key: string;
  proposed_value: unknown;
  change_reason: string;
}) {
  return intentRequest<ProductSystemParameterMutationResult>({
    intent: PRODUCT_SYSTEM_PARAMETER_INTENTS.publish,
    params,
  });
}

export function rollbackProductSystemParameter(changeId: number) {
  return intentRequest<ProductSystemParameterMutationResult>({
    intent: PRODUCT_SYSTEM_PARAMETER_INTENTS.rollback,
    params: { change_id: changeId },
  });
}
