export type ProductPagePresentationMode = 'task' | 'workspace' | 'collection' | 'dashboard';
export type ProductPageRenderProfile = 'create' | 'edit' | 'readonly';
export type ProductPageDirtyState = 'clean' | 'dirty' | 'saving' | 'error';
export type ProductPageHeaderVariant = 'standalone' | 'dialog';

export type ProductPageHeaderAction = {
  key: string;
  label: string;
  semantic: 'save' | 'submit' | 'create' | 'exit' | 'other';
  enabled: boolean;
};

export type ProductPageHeaderModel = {
  title: string;
  subtitle: string;
  breadcrumb: readonly string[];
  presentationMode: ProductPagePresentationMode;
  renderProfile: ProductPageRenderProfile;
  dirtyState: ProductPageDirtyState;
  statusbar: boolean;
  primaryAction: ProductPageHeaderAction | null;
  overflowActions: readonly ProductPageHeaderAction[];
  exitAction: ProductPageHeaderAction | null;
  variant: ProductPageHeaderVariant;
};

export function resolveProductPageHeaderModel(
  input: Omit<ProductPageHeaderModel, 'primaryAction'> & {
    primaryActions?: readonly ProductPageHeaderAction[];
  },
): ProductPageHeaderModel {
  const title = input.title.trim();
  if (!title) throw new Error('PRODUCT_PAGE_HEADER_TITLE_REQUIRED');
  const primaryActions = [...(input.primaryActions || [])];
  if (primaryActions.length > 1) throw new Error('PRODUCT_PAGE_HEADER_PRIMARY_ACTION_MULTIPLE');
  const primaryAction = primaryActions[0] || null;
  if (input.renderProfile === 'readonly' && primaryAction?.semantic === 'save') {
    throw new Error('PRODUCT_PAGE_HEADER_READONLY_SAVE_FORBIDDEN');
  }
  return {
    ...input,
    title,
    subtitle: input.subtitle.trim(),
    breadcrumb: input.breadcrumb.map((item) => item.trim()).filter(Boolean),
    primaryAction,
    overflowActions: [...input.overflowActions],
  };
}
