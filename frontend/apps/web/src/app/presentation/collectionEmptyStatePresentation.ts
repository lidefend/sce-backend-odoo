/**
 * Empty-collection copy authority.
 *
 * The empty surface and the create entry describe one capability.  When the
 * entry control can create a record, the empty state has to invite the user to
 * create one; when it cannot, the empty state has to say the surface is
 * read-only.  Both consume the same resolved capability, so the copy can never
 * contradict the control the user can see on the same page.
 */
export type CollectionEmptyStateKind = 'filtered' | 'create' | 'readonly';

export function resolveCollectionEmptyStateKind(input: {
  hasActiveConditions: boolean;
  canCreateRecord: boolean;
}): CollectionEmptyStateKind {
  if (input.hasActiveConditions) return 'filtered';
  return input.canCreateRecord ? 'create' : 'readonly';
}
