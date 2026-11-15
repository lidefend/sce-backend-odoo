# CAP05-B01-R1 Migration Lifecycle Repair

Status: `IN_PROGRESS`

## Scope

Repair only the two pre-migration precondition checks:

- `smart_construction_core/migrations/17.0.0.180/pre-migrate.py`
- `smart_construction_core/migrations/17.0.0.181/pre-migrate.py`

The repair distinguishes a valid pre-174 schema from an invalid modern or
unknown-version state. It does not move migration stages, refactor the
migration framework, or modify capability, ACL, scene, release or enterprise
state.

## Research Basis

- Research branch: `audit/capability-explorer-05-b01-migration-20261116`
- Research HEAD: `50a2eb1c2913b62027a990682aa54e45ab9585ad`
- Research tree: `defa41be6082a572e0a7fef69f2aaa528e1783bd`
- Product baseline: `main@96c42ab35550d4807d3bc070e75a06555c57de6f`

## Implementation

Both pre-migrations first test for
`public.sc_product_scenario_entry`. If the table exists, the original
operation runs unchanged. If it is absent:

- a recognized version below `17.0.0.174` is a compatible no-op;
- a recognized version at or above `17.0.0.174` raises;
- a missing or unparsable version raises.

Version ordering uses `odoo.tools.parse_version`.

## Verification

Pending focused tests and the isolated 172/174/179-to-182 upgrade matrix.

## Stop Boundary

Stop before merge or deployment after exact-head CI and independent review.
