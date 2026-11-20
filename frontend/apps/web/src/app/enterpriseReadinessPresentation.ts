import type { ReadinessRule } from '../composables/useEnterpriseReadiness';

export type EnterpriseReadinessSection = {
  key: string;
  label: string;
  sequence: number;
  rules: ReadinessRule[];
};

export function groupEnterpriseReadinessRules(rules: ReadinessRule[]): EnterpriseReadinessSection[] {
  const sections = new Map<string, EnterpriseReadinessSection>();
  rules.forEach((rule) => {
    const section = sections.get(rule.section_key) || {
      key: rule.section_key,
      label: rule.section_label,
      sequence: rule.section_sequence,
      rules: [],
    };
    section.rules.push(rule);
    sections.set(rule.section_key, section);
  });
  return [...sections.values()].sort((left, right) => left.sequence - right.sequence);
}
