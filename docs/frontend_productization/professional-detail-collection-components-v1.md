# Professional Detail Collection Components v1

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: registry-authorized one2many detail collection adapter.
- Module: `frontend/apps/web` and generic Contract V2 field component projection.
- Standard vs User-Specific: platform standard.

This batch establishes the formal one2many presentation family while retaining the existing governed x2many runtime for readonly facts, editable rows, line validation, summaries, removal settlement, and server-owned create policies. It does not introduce business-model layouts or Phase 8 lifecycle behavior.

## Rules

- Generic one2many fields resolve to `sc.relation.table`.
- The professional wrapper exposes row, column, creation, validation, summary, and removal state as semantic DOM evidence.
- Row commands and mutation settlement remain owned by the existing relation adapter.
- Missing or mismatched component/type pairs fail closed in the professional registry.
