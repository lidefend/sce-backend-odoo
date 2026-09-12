function deny(message) {
  throw new Error(`[DENY] ${message}`);
}

export function assertRuntimeWriterIdentity(identity, authority) {
  const loginUser = identity.login?.user || {};
  const initUser = identity.init?.user || {};
  const loginEntitlement = identity.login?.entitlement || {};
  const initRole = String(identity.init?.role_surface?.role_code || '');
  if (String(loginUser.login || '') !== authority.writer.login || Number(loginUser.id) !== authority.writer.id) {
    deny('authenticated session user does not match the governed project manager');
  }
  if (Number(loginUser.company_id) !== authority.project.company_id || Number(initUser.company_id) !== authority.project.company_id) {
    deny('authenticated session company does not match the governed project company');
  }
  if (loginEntitlement.is_internal_user !== true || String(loginEntitlement.role_code || '') !== 'internal_user') {
    deny('authenticated project manager is not an internal user');
  }
  if (!authority.writer.role_code || initRole !== authority.writer.role_code) {
    deny('system.init role does not match the governed project manager role');
  }
  if (Number(initUser.id) !== authority.writer.id) deny('system.init principal does not match the authenticated project manager');
}
