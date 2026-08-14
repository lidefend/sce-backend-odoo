# P0 authentication credential framework v1

Status: implementation candidate. This contract belongs to `smart_core`; P4 only injects
test credentials and redacts evidence, while business modules consume the resulting
principal without branching on credential type.

## Authority and boundaries

- `res.users` remains the user, company and role authority.
- Odoo `res.users.apikeys` remains the API-key secret, hash, generation and revocation
  authority. `smart_core` must never copy cleartext keys or their hashes.
- `sc.auth.credential.policy` stores only product policy and usage projection for an
  Odoo key: stable key ID, allowed scopes and companies, expiry, rotation link, last use
  and revocation projection.
- Password and API-key credentials are explicit and mutually exclusive. Password
  authentication always calls Odoo with `interactive=True`; machine key validation uses
  the dedicated native API-key model with scope `smart_core.machine`.
- Human login issues an interactive JWT. Machine exchange issues a short-lived scoped
  JWT and never grants a browser session by default.

Odoo 17 source authority:
<https://github.com/odoo/odoo/blob/17.0/odoo/addons/base/models/res_users.py>

## Credential and principal contracts

```text
credential = {
  type: password | api_key,
  login?: string,       # password only
  secret: string,
  requested_scope?: string[]
}

principal = {
  user_id, database, company_id, allowed_company_ids, role_xmlids,
  principal_type: human | machine,
  auth_method: password | api_key,
  credential_id, scope, token_version, credential_epoch
}
```

JWTs carry the same identity boundary plus `iat`, `exp` and `jti`. Current Odoo ACLs,
record rules, company rules and entitlements remain authoritative; a credential can only
reduce access. Machine scope is checked before the existing permission pipeline. Every
handler defaults to machine denial and must publish authoritative `MACHINE_ACCESS`
metadata to opt in. Dynamic handlers such as `api.data` classify their own explicit
operation contract; unknown operations deny, and the central gate never infers access
from an intent's name.
JWT signing is fail-closed: `SC_JWT_SECRET` or the corresponding protected Odoo
configuration must provide at least 32 bytes. There is no built-in or development
fallback signing value.

## Lifecycle

1. An authenticated human re-enters their password to generate a machine key.
2. Odoo generates and hashes the key. Creation is serialized per user/native scope and
   the policy is bound only when exactly one new native record and one matching index
   exist. The cleartext value is returned exactly once.
3. `smart_core` records the native key ID and restrictive policy, never the key.
4. A machine exchanges an explicit API key for a short JWT after native validation,
   policy/expiry/company checks and rate limiting.
5. Successful exchange and lifecycle events record only credential ID, user, scope,
   company and trace. The anonymous rate limiter stores an HMAC of the client identity,
   never the key or key fingerprint. Product evidence must not retain the key.
6. Revocation removes the native key and increments the policy epoch. Existing machine
   JWTs fail immediately when their credential ID/epoch is revalidated.
7. Rotation creates a new native key and policy, then revokes the predecessor.
8. Expiry is projected by a locked service transaction from both authentication and
   listing. The active-to-expired transition emits one immutable audit event.

## Frontend boundary

The normal login screen remains password/SSO oriented. API-key management is an
explicit `/account/api-keys` integration surface. It lists only policy projections and
requires password confirmation for create/rotate. The returned key exists only in the
one-time dialog's transient component state and is cleared on close/unmount.

The one-time response declares `meta.evidence_policy.classification=one_time_secret`,
and the visible secret region carries `data-evidence-sensitive=api_key`. Controlled
browser evidence tooling must refuse screenshots/traces while that marker is present,
and evidence-bundle secret scanning rejects serialized `api_key` values. The UI itself
guarantees transient state, clearing and no browser-storage/log persistence; capture
prevention remains an explicit responsibility of the controlled evidence workflow.

The machine exchange contract is the anonymous intent `auth.machine.token`, requires
`X-Anonymous-Intent: true`, an explicit `credential.type=api_key`, and the same database
as the routed request. It returns a 15-minute restricted bearer token. Key exchange for
a full browser session remains a separate product decision and is not enabled by this
version. Keys are never written to local storage. Browser traces and screenshots are
forbidden while the one-time secret marker is present and must be enforced by the
controlled evidence workflow rather than inferred from ordinary DOM rendering.
