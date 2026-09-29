/** Official detail reference: Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4.
 * A readonly record has one composition, with explicit collection/attachment
 * extensions. Section capabilities decide whether descriptions can carry facts.
 */
export type StandardDetailCompositionId = 'official-standard-detail' | 'legacy-detail-surface';
export type StandardDetailCompositionReason = 'standard-page-type' | 'specialized-page-type' | 'not-a-readonly-profile';
export type StandardDetailCompositionDecision = {
  composition: StandardDetailCompositionId;
  adopted: boolean;
  reason: StandardDetailCompositionReason;
};
export function resolveStandardDetailComposition(input: { pageType?: unknown; renderProfile?: unknown }): StandardDetailCompositionDecision {
  if (input.renderProfile !== 'readonly') return { composition: 'legacy-detail-surface', adopted: false, reason: 'not-a-readonly-profile' };
  return input.pageType === 'contract-record-detail'
    ? { composition: 'official-standard-detail', adopted: true, reason: 'standard-page-type' }
    : { composition: 'legacy-detail-surface', adopted: false, reason: 'specialized-page-type' };
}

export function resolveStandardDetailSection(input: {
  adopted: boolean;
  configurationMode: boolean;
  readonlyFacts: boolean;
  fields: readonly { type: string; dedicatedControl: boolean }[];
}): { adopted: boolean; reason: string } {
  if (!input.adopted) return { adopted: false, reason: 'outside-standard-detail' };
  if (input.configurationMode) return { adopted: false, reason: 'configuration-editor' };
  if (!input.readonlyFacts) return { adopted: false, reason: 'editable-section' };
  if (!input.fields.length) return { adopted: false, reason: 'empty-section' };
  if (input.fields.some((field) => ['one2many', 'many2many'].includes(field.type))) return { adopted: false, reason: 'relation-collection-extension' };
  if (input.fields.some((field) => field.type === 'binary')) return { adopted: false, reason: 'attachment-extension' };
  if (input.fields.some((field) => field.dedicatedControl)) return { adopted: false, reason: 'dedicated-control-extension' };
  const factTypes = ['char', 'text', 'selection', 'many2one', 'boolean', 'date', 'datetime', 'integer', 'float', 'monetary', 'html'];
  if (input.fields.some((field) => !factTypes.includes(field.type))) return { adopted: false, reason: 'unsupported-fact-type' };
  return { adopted: true, reason: 'standard-readonly-facts' };
}
