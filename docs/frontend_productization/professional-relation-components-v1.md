# Professional Relation Components v1

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: registry-authorized many2one/many2many presentation adapter.
- Module: `frontend/apps/web` and generic Contract V2 field component projection.
- Standard vs User-Specific: platform standard.

This batch establishes one semantic relation wrapper while retaining the existing authoritative relation runtime for search, selection, record opening, create modes, dialog settlement, and permission checks. One2many line editing remains Phase 7D.

## Rules

- Generic many2one fields resolve to `sc.relation.many2one`.
- Generic many2many fields resolve to `sc.relation.many2many`; declared tag widgets retain `sc.select.tags`.
- Currency, user, and company relations remain Phase 7B business-value presentations because their formal relation model is the declared semantic authority.
- `relation_entry`, capabilities, action/menu identity, and record permissions remain server-owned.
- The wrapper adds semantic DOM identity but does not duplicate relation search or dialog state.
- Missing or mismatched component/type pairs fail closed in the professional registry.
