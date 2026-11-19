# SCENE-CLOSE-01 Center Publication Authority

Status: active

Base: `b974c32423d14f20960bf959c844a6b92334bc1a`

Branch: `feature/scene-close-01-center-publication-authority-20261119`

## Product result

An administrator can edit product-center names, order and entry placement;
the change remains a draft until release, runtime navigation consumes the
active released snapshot, capability diagnostics explain the same center and
version, and rollback restores the previous center definition.

## Scope

- Stable center identity from the locked ten-center product baseline.
- Center definitions and menu placement in the existing product policy and
  release snapshot chain.
- Release-operator maintenance parameters, options and authoritative readback.
- Capability-explorer center explanation from the active released policy.
- Minimal frontend consumption in the existing release operator, capability
  explorer and native scenario maintenance surfaces.

## Exclusions

- Composite scenario dependency/version convergence.
- Versioning all scenario fields or lifecycle state.
- Automatic scenario creation or business-category inference.
- Deployment or production mutation.

## Contract validation

Odoo-native menus, actions, ACLs, models and installed module facts are inputs,
not claims owned by this change. Validation therefore checks this repository's
contract boundary rather than rebuilding or retesting Odoo capabilities.

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base and dirty scope | passed | `make agent.run.resume` | Current run resolves with `outside_scope=[]` |
| Producer declaration | passed | backend capability-explorer and catalog-action unit tests | Contract declares accepted fields, release-state options, readback fields and stable intent |
| Strict consumer | passed | frontend capability-explorer contract tests | Frontend stops on missing fields, undeclared values, absent readback and identity mismatch |
| Existing contract families | passed | admin management backend, product-center policy and capability identity units | Ensure the new admission contract does not alter existing projection semantics |
| Static/frontend quality | passed | contract-basis, design-system component-driver, lint and strict typecheck | The new controls remain contract-driven and use the registered design system |
| ORM, module baseline, upgrade and browser | excluded | owner direction | They would retest Odoo-native capability existence rather than this repository's contract logic |

Observed contract results:

- backend capability explorer: 24 + 9 + 2 passed
- frontend capability explorer: 46 contract cases passed, plus platform-duty and route-access checks
- admin management backend: 90 passed
- product-center policy: 8 passed
- capability identity boundary: 12 passed
- incremental planner: 185 passed
- frontend contract basis: 15 passed; open defects 0
- design-system component driver: 18 passed; required 33, missing 0, raw 0
- lint: 0 errors
- strict typecheck: exit 0

The closed contract gaps are:

1. Release-state choices now come from the backend action declaration instead
   of a frontend constant.
2. The frontend requires every declared accepted field before sending the
   admission intent.
3. Every declared write readback field is required before success is shown.
4. Empty or identity-mismatched readback fails closed.
5. The product-draft route is consumed from the backend declaration.

ORM and baseline commands started before the owner clarified this boundary were
interrupted and are not counted as passes.
