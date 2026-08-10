# Product Primary-Center Baseline v1

This document records the P1 construction-product L2 target information architecture. The authoritative contract is [`config/product_primary_center_baseline_v1.json`](../../config/product_primary_center_baseline_v1.json).

The target has ten ordered business centers: Workbench, Project, Contract, Cost, Finance, Tax, Accounting, Reporting, Administration, and Product Configuration. It is intentionally separate from the deployed menu snapshot. Runtime alignment is `MIGRATION_PENDING`; no XMLID, action, permission, route, database, or current menu is changed by this baseline.

Business navigation is limited to three levels. Center names, sequence, and count are P1 product facts. Maturity labels belong to L2/L3 capabilities, never to a whole primary center. System Administration remains an internal-governance entry rather than a business primary center.

Migration may begin only after menu mapping, ADR review, native P1 menu changes, role/company/database/action/route/five-viewport validation, and an explicit release-snapshot update.
