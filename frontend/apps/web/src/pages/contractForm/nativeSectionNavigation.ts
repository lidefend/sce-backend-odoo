export type NativeSectionNavigationRole = 'primary' | 'subordinate';

type NativeSectionAuthorityNode = {
  sourceAuthority?: Record<string, unknown>;
  source_authority?: Record<string, unknown>;
};

export function nativeSectionNavigationRole(node: NativeSectionAuthorityNode): NativeSectionNavigationRole {
  const authority = node?.sourceAuthority || node?.source_authority || {};
  const projectionOnly = authority.projection_only === true || authority.projectionOnly === true;
  const noBusinessAuthority = authority.no_business_fact_authority === true
    || authority.noBusinessFactAuthority === true;
  return projectionOnly && noBusinessAuthority ? 'subordinate' : 'primary';
}
