export type TemplateSectionKind = 'default' | 'header' | 'sheet' | 'group' | 'notebook' | 'page';

export type TemplateSectionInput = {
  title: string;
  kind: TemplateSectionKind;
};

export type TemplateSectionPresentation = {
  title: string;
  hint: string;
  tone: 'core' | 'advanced';
  isAdvanced: boolean;
};

export function resolveTemplateSectionPresentation(
  section: TemplateSectionInput,
  _options?: Record<string, unknown>,
): TemplateSectionPresentation {
  const rawTitle = String(section.title || '').trim();
  return {
    title: rawTitle || '信息分组',
    hint: '',
    tone: 'core',
    isAdvanced: false,
  };
}
