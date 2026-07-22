# ADR-001: Single-Database Colocated Platform Core in Production

- Status: Accepted
- Scope: current production release
- Decision: `single_database_colocated_platform_core`
- Business database: `sc_production`
- Platform database: `sc_production`
- Future dual database: separate migration required

## Context

`smart_core` is a logical platform boundary, not a requirement for a separate physical database. Production currently has one Odoo/Nginx runtime and one database backup, restore, and permission boundary. `sc_production` already contains the installed `smart_core` module, platform models, product policies, and login routes. The previous missing-configuration fallback to `sc_platform_core` left runtime deployment and code in conflicting modes.

## Decision

Platform capabilities remain enabled. `sc_production` is authoritative for both business data and the current tenant's platform data. `smart_core.platform_release_db` must explicitly equal the server-locked current database. `system.init` reads the active release snapshot only from its current registry. Client headers, body fields, URLs, and cookies have no role in selecting either database.

The following models are physically colocated with business models for this release:

- `sc.subscription.plan`
- `sc.subscription`
- `sc.entitlement`
- `sc.usage.counter`
- `sc.ops.job`
- `sc.product.policy`
- `sc.edition.release.snapshot`
- `sc.release.action`
- `sc.login.route`
- tenant payload/import models

Repository defaults no longer guess `sc_platform_core`. Production fails closed when configuration is missing or conflicts with the current database, or when no valid active snapshot exists; it must not expose a complete ungated navigation surface. A non-production standalone platform database remains possible only through explicit configuration.

## Constraints

- No implicit fallback, dual reads, or dual writes between `sc_production` and `sc_platform_core`.
- Standalone `sc_platform_core` is development/experimental only and is not a production source of truth.
- Subscription, entitlement, plan, usage, and release-governance capabilities remain supported.
- Physical colocation does not weaken tenant, company, ACL, record-rule, or business-scope isolation.
- Snapshots are generated from version-controlled policy through the existing release service, never by direct inserts or copied development data.
- The database and matching filestore are backed up, validated, and restored as a pair in isolated containers.

## Consequences

This release does not introduce unverified dual-database permissions, consistency, backup, restore, or monitoring infrastructure. Any future dual-database architecture requires a new ADR and a separate migration project covering ownership, consistency, least privilege, backup/restore, monitoring, and rollback.

Chinese version: [ADR-001-single-database-colocated-platform-core.md](ADR-001-single-database-colocated-platform-core.md)
