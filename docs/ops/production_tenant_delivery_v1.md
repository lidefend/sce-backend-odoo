# Production tenant delivery v1

The production tenant-delivery path is separate from development and rehearsal
helpers. It accepts one external, immutable release-set lock and fails closed
unless all of these identities agree:

- product release version, full commit/tree, and digest-addressed image;
- customer repository commit/tree and signed customer archive digest;
- exact customer module allowlist from the signed external lock, with legacy
  modules rejected;
- locked tenant payload id, schema, checksum, and tenant identity;
- `sc_production` database and matching application filestore scope;
- protected legacy attachment path `/data/odoo/legacy_attachments`.

`release.production.customer_package.preflight` and
`release.production.tenant_payload.plan` are dry-run entry points.
Preparation, module installation, and import use separate exact confirmation
phrases and the production danger guard. The customer archive and payload are
mounted read-only. The legacy attachment tree is neither an application
filestore nor an accepted package/payload location.

The release-set lock is generated outside Git after the immutable image and
signed customer package exist. It contains identifiers and checksums only,
never credentials or customer records. Production execution must use the
digest-addressed image and exact external files recorded in that lock.

The generic importer continues to enforce its exclusive lock, tenant/database
binding, normal ORM authorization, two-phase archived dependency restoration,
final payload parity, and strict identical-import no-op behavior.
