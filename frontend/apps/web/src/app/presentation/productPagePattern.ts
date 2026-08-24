import type { ProductPageRenderProfile } from './productPageHeader';

export type ProductPagePatternKey = 'task-form' | 'workspace-form' | 'collection' | 'dashboard';

export type ProductPagePatternModel = {
  key: ProductPagePatternKey;
  presentationMode: 'task' | 'workspace' | 'collection' | 'dashboard';
  renderProfile: ProductPageRenderProfile;
};

export function resolveProductPagePatternModel(input: ProductPagePatternModel): ProductPagePatternModel {
  const expectedMode = input.key === 'task-form' ? 'task'
    : input.key === 'workspace-form' ? 'workspace'
      : input.key;
  if (input.presentationMode !== expectedMode) {
    throw new Error(`PRODUCT_PAGE_PATTERN_MODE_MISMATCH:${input.key}:${input.presentationMode}`);
  }
  if ((input.key === 'collection' || input.key === 'dashboard') && input.renderProfile !== 'readonly') {
    throw new Error(`PRODUCT_PAGE_PATTERN_PROFILE_MISMATCH:${input.key}:${input.renderProfile}`);
  }
  return { ...input };
}
