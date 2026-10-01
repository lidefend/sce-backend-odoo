/**
 * Contract V2 publishes two independent authority dimensions on every action
 * rule:
 *
 * - `authorizationAllowed` — whether the *actor* is authorized;
 * - `businessAvailable` — whether the *business state* permits the action.
 *
 * A producer may fold those dimensions into `allowed` / `enabled` / `disabled`,
 * but the fold is an implementation convenience, not a contract guarantee: the
 * live payload already publishes them apart (`authorizationAllowed: true`
 * together with `businessAvailable: false`).  A renderer that only trusted the
 * folded flags would silently ignore a declared deny, so the declared evidence
 * is consumed directly and fail-closed.
 *
 * Only an explicit `false` denies.  An absent field leaves the existing
 * projection untouched, so contracts that do not publish the dimension keep
 * their current behaviour.
 */
export type DeclaredAuthoritySource = {
  authorizationAllowed?: unknown;
  businessAvailable?: unknown;
};

export const DECLARED_DENIAL_NOT_AUTHORIZED = 'ACTION_NOT_AUTHORIZED';
export const DECLARED_DENIAL_NOT_BUSINESS_AVAILABLE = 'ACTION_NOT_BUSINESS_AVAILABLE';

export function declaredActionAuthorityDenial(rule: DeclaredAuthoritySource | null | undefined): string {
  if (!rule) return '';
  if (rule.authorizationAllowed === false) return DECLARED_DENIAL_NOT_AUTHORIZED;
  if (rule.businessAvailable === false) return DECLARED_DENIAL_NOT_BUSINESS_AVAILABLE;
  return '';
}
