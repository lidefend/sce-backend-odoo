import { onScopeDispose } from 'vue';
import {
  createContextRequestOwner,
  type ContextRequestIdentity,
} from '../../app/contextEpoch';

export type BusinessConfigEditorIntentOwner = ReturnType<typeof createContextRequestOwner>;

export function useBusinessConfigEditorIntent(
  requestIdentity: () => ContextRequestIdentity,
): BusinessConfigEditorIntentOwner {
  const owner = createContextRequestOwner(requestIdentity);
  onScopeDispose(() => owner.dispose());
  return owner;
}
