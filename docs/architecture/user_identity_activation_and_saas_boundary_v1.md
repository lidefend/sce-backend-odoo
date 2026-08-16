# User Identity Activation and SaaS Boundary v1

Status: frozen architecture boundary
Scope: authentication bridge, enterprise activation, password recovery, future SaaS registration

## Authority and non-goals

Odoo `res.users` remains authoritative for users, password hashing and authentication.
The Smart Core extension owns policy isolation, digest-only credentials, binding checks,
delivery audit and the SPA activation protocol. It does not implement a second password
store, authentication engine or session system.

The current release enables only `enterprise_activation`. It does not enable public
signup, create SaaS tenants, provision practice workspaces or write production users.

## Separated identity flows

| Flow | Identity source | Database boundary | Admission policy |
|---|---|---|---|
| Enterprise production | approved enterprise roster | dedicated enterprise tenant database | controlled invitation and one-time activation |
| SaaS practice | public registration applicant | separate practice database | verified registration followed by idempotent provisioning |
| Platform operations | platform personnel | platform control domain | separately authorized, strongly audited administration |

The following decisions are mandatory:

```text
ENTERPRISE_AND_PUBLIC_IDENTITY_FLOWS_SEPARATED=true
PRODUCTION_AND_PRACTICE_DATABASES_SEPARATED=true
ODOO_NATIVE_AUTHORITY_REUSED=true
TENANT_NOT_EQUAL_TO_COMPANY=true
SHARED_WRITABLE_DEMO_SCOPE=false
PUBLIC_SAMPLE_DATA_READ_ONLY=true
PRACTICE_WORKSPACE_PER_TENANT=true
TENANT_CONTEXT_SERVER_RESOLVED=true
PUBLIC_SIGNUP_IN_PRODUCTION_DATABASE=false
SAAS_PROVISIONING_IDEMPOTENT=true
TENANT_DATA_LIFECYCLE_MANAGED=true
```

## Credential purposes

The credential schema supports distinct purposes:

- `enterprise_activation`;
- `password_recovery`;
- `email_verification`;
- `saas_registration_verification`;
- `tenant_invitation`.

Purpose is part of the signed policy and consumption check. Credentials cannot be
consumed across purposes. Only `enterprise_activation` is currently enabled.
Password recovery is a separate policy and remains assisted until an approved,
verified recovery channel exists. Public SaaS registration remains disabled.

## Enterprise activation protocol

1. A separately authorized activation administrator creates an approved batch.
2. The service issues at least 192 bits of random entropy and stores only SHA-256.
3. The one-time plaintext is returned exactly once to the controlled delivery process.
4. Delivery audit stores only a fingerprint and non-secret delivery metadata.
5. The SPA accepts the code in a POST body and receives a short-lived in-memory context.
6. The SPA submits the final password and context in a second POST body.
7. Binding is recomputed and password update plus token consumption occur atomically.
8. Odoo hashes and authenticates the final password.

The activation code and activation context are forbidden from query parameters,
persistent browser storage, application/access logs and audit exports.

The three activation/recovery bootstrap routes are the only SPA transport
exception to the unified intent endpoint. The exception is bound to the
dedicated activation adapter and exact route set because no authenticated
principal exists yet and the controller must enforce `save_session=False` and
no-store response headers. It is not a wildcard exception for `/api/v1/auth/*`;
all authenticated product operations continue to use `/api/v1/intent`.

## Binding and mutation boundary

Each credential binds the immutable user identity, tenant, environment, target login,
exact group snapshot, primary company, allowed companies, active/share state, expiry
and issuance batch. Any drift fails closed. Activation never repairs or overwrites
identity, role or company state and never migrates the login.

Legacy-login migration is a separately approved atomic production operation. The
credential may be issued only after the approved target login already exists.

## Future SaaS tenancy

The long-term hierarchy is:

```text
platform -> tenant -> workspace -> company -> business records
```

`tenant` is not interchangeable with `res.company`. Tenant context must be resolved
from the authenticated session and server-side membership, never trusted from a client
parameter. Public registration must use a separate practice database and an idempotent
provisioning service that creates tenant, workspace, company, owner membership and
template-derived practice data as one recoverable workflow.

The follow-up architecture task is `SAAS-P0-TENANCY-PROVISIONING-01`; the public product
flow is `SAAS-P1-SELF-SERVICE-REGISTRATION-02`. Neither is part of the enterprise user
activation release.
