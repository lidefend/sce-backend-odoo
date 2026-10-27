// One-shot, short-lived authority for navigation initiated by an authorized
// button execution. A form `type="action"` button and an object method that
// returns a window action are authorized by the button itself, not by being a
// released menu leaf, so the router guard cannot resolve them from the static
// route authority. The grant is bound to the exact destination route and the
// returned action id, consumed on first use, and expires quickly so a stale
// grant cannot be replayed through a URL.

interface ButtonNavigationGrant {
  actionId: number;
  route: string;
  expiresAt: number;
}

const GRANT_TTL_MS = 30_000;
const MAX_PENDING = 32;

const pending: ButtonNavigationGrant[] = [];

function pruneExpired(now: number): void {
  for (let index = pending.length - 1; index >= 0; index -= 1) {
    if (pending[index].expiresAt < now) pending.splice(index, 1);
  }
}

export function grantButtonNavigationAuthority(actionId: number, route: string): void {
  if (!Number.isSafeInteger(actionId) || actionId <= 0 || !route) return;
  pruneExpired(Date.now());
  pending.push({ actionId, route, expiresAt: Date.now() + GRANT_TTL_MS });
  if (pending.length > MAX_PENDING) pending.splice(0, pending.length - MAX_PENDING);
}

export function consumeButtonNavigationAuthority(actionId: number, route: string): boolean {
  if (!Number.isSafeInteger(actionId) || actionId <= 0 || !route) return false;
  const now = Date.now();
  for (let index = 0; index < pending.length; index += 1) {
    const grant = pending[index];
    if (grant.actionId !== actionId || grant.route !== route) continue;
    pending.splice(index, 1);
    return now <= grant.expiresAt;
  }
  pruneExpired(now);
  return false;
}

export function pendingButtonNavigationAuthorityCount(): number {
  pruneExpired(Date.now());
  return pending.length;
}
