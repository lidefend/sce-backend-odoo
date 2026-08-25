export type MobileFormActionAuthorityItem = Readonly<{
  key: string;
  kind: 'back' | 'return' | 'draft' | 'business' | 'canonical' | 'config' | 'discard';
  enabled: boolean;
}>;

type ActionLike = Readonly<{ key: string; enabled: boolean }>;

export function resolveMobileFormActionAuthority(input: {
  showBack: boolean;
  showReturn: boolean;
  showDraftSave: boolean;
  draftSaveDisabled: boolean;
  businessDirect: readonly ActionLike[];
  businessOverflow: readonly ActionLike[];
  canonicalDirect: readonly ActionLike[];
  canonicalOverflow: readonly ActionLike[];
  config: readonly ActionLike[];
  showDiscard: boolean;
  busy: boolean;
}) {
  const items: MobileFormActionAuthorityItem[] = [];
  if (input.showBack) items.push({ key: 'back:form.back', kind: 'back', enabled: !input.busy });
  if (input.showReturn) items.push({ key: 'return:form.return-workbench', kind: 'return', enabled: !input.busy });
  if (input.showDraftSave) items.push({ key: 'draft:form.save-draft', kind: 'draft', enabled: !input.draftSaveDisabled });
  const append = (actions: readonly ActionLike[], kind: MobileFormActionAuthorityItem['kind']) => {
    for (const action of actions) items.push({ key: `${kind}:${action.key}`, kind, enabled: !input.busy && action.enabled });
  };
  append(input.businessDirect, 'business');
  append(input.businessOverflow, 'business');
  append(input.canonicalDirect, 'canonical');
  append(input.canonicalOverflow, 'canonical');
  append(input.config, 'config');
  if (input.showDiscard) items.push({ key: 'discard:form.discard', kind: 'discard', enabled: !input.busy });
  const keys = items.map((item) => item.key);
  if (new Set(keys).size !== keys.length) throw new Error('MOBILE_FORM_ACTION_IDENTITY_DUPLICATE');
  return Object.freeze({ items: Object.freeze(items), count: items.length, keys: Object.freeze(keys) });
}
