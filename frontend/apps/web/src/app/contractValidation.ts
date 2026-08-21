import type { FieldDescriptor } from '@sc/schema';

type ValidationIssue = {
  code: string;
  message: string;
};

function isEmpty(value: unknown) {
  if (value === null || value === undefined) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'string') return value.trim() === '';
  return false;
}

export function validateContractFormData(params: {
  fieldDescriptors: Record<string, FieldDescriptor>;
  validationRules: Array<Record<string, unknown>>;
  renderProfile: string;
  fieldLabels: Record<string, string>;
  values: Record<string, unknown>;
}): ValidationIssue[] {
  const { fieldLabels, values } = params;
  const issues: ValidationIssue[] = [];
  const renderProfile = String(params.renderProfile || '').trim().toLowerCase();
  const validationRules = params.validationRules;
  const requiredRules = validationRules.filter((rule) => String(rule?.code || '').trim().toUpperCase() === 'REQUIRED');
  requiredRules.forEach((rule) => {
    const field = String(rule.field || '').trim();
    if (!field) return;
    const whenProfiles = Array.isArray(rule.when_profiles)
      ? rule.when_profiles.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
      : [];
    if (whenProfiles.length && renderProfile && !whenProfiles.includes(renderProfile)) return;
    if (!params.fieldDescriptors[field] || !Object.prototype.hasOwnProperty.call(values, field)) return;
    if (isEmpty(values[field])) {
      issues.push({
        code: 'REQUIRED',
        message: `必填项未填写: ${fieldLabels[field] || field}`,
      });
    }
  });
  return issues;
}
