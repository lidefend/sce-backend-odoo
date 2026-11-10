# Systemic Convergence Independent Review R1

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: numeric presentation and released navigation action authorization
- Module: one2many presentation, menu fact projection and action-spec routes
- Database, fixture, ACL broadening and deployment are excluded

## Findings Closed

### S1: one2many integer rounding regression

The shared formatter defaulted to `Intl.NumberFormat` rounding. Integer values now
retain the previous truncation contract before formatting:

- `2.7 -> 2`
- `-2.7 -> -2`
- `null/false -> empty`

### S2: native-tree test used an unprojected action_model

`_menu_fact_tree_as_native` now carries `action_model` on the native node and its
meta. The test enters through the real projection instead of injecting a field
that production did not publish.

### S2: action-spec route publication bypassed action groups

`_route_entry_from_action_spec` now applies the same action-group intersection as
menu-backed route publication. The test covers denied and allowed action groups.

## Validation

- `make verify.backend.navigation_delivery.unit`: PASS, 51 + 10 + 3 tests.
- `make verify.frontend.business_semantics.unit`: PASS.
- `make verify.frontend.collection_view_semantics.unit`: PASS, 43 tests.

## Result

Completed on clean candidate `915644ab3c00e8cfafc94646079d90f599251c67`.

- Clean iteration: PASS, 10 targets.
- Runtime authorization: 2 authorized entries, `problems=0`,
  `console_errors=0`, PM `leaked_entries=[]`, `uncovered=0`.

Runtime evidence:
`.runtime/m9-authority-r1/summary.json`, SHA-256
`d449edcfd8c1cc0d60e8e4fd4cf5a214b119ebc5a16befa37092512aa97ae9cf`.
