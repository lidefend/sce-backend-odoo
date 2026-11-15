# ODOO-NATIVE-CAPABILITY-EXPLORER-01

## Candidate

- Baseline: `6689f601b3bcda349546b6e3814ca91fcaade346`
- Branch: `audit/platform-capability-studio-01-20261115`
- Stage: source validation complete and verified

## Scope

- Read-only discovery from installed Odoo modules and native metadata.
- Join native business entries to existing product-scenario bindings and product
  release state.
- Prove technical draft selection without creating a capability registry.

## Exclusions

- Capability Explorer UI.
- Scene editor.
- New models, migrations or database writes.
- Maturity qualification changes.

## Verification

- `verify.odoo_native_capability_explorer.unit`: PASS, 6 tests.
- `audit.odoo_native_capability_explorer.demo`: PASS against
  `sc_demo@2571346afc8c69cea20e32fcba36082c949cf825`.
- 282 native business entries discovered with 282 stable identities and zero
  technical selection blockers.
- Runtime metadata included 77 installed modules, 758 models, 776 related views,
  581 ACL rows and 348 record rules.
- Existing scene bindings classified 75 entries as bound and 207 as unbound.
- No capability row was created or persisted.
- `verify.guard.registry`: PASS, 24 tests.
- `verify.agent.ledger.unit`: PASS, 18 tests.
- `verify.local.dev.runtime.performance.unit`: PASS, 34 tests.
- `verify.verification.lane_coverage`: PASS, 74 tests.
- `make ci.local.iteration`: PASS after the new probe paths were registered in
  the incremental planner and the on-demand audit target was declared as
  `diagnostic_cli`.
- `make ci.local.iteration`: PASS with seven affected targets.
- The first incremental run correctly refused the new on-demand audit target as
  unregistered verification surface. It was registered as `diagnostic_cli` and
  the reviewed identity baseline grew from 668 to 669 zero-reference targets;
  the unregistered count remains zero.
- Raw runtime log:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-01/runtime-probe.log`,
  SHA256 `65c2b6b19bea5dc1170e1b0213024c8839e079c71c9402dd9f8e2c68d5826a18`.

## Conclusion

The Odoo-native discovery path is valid. A platform capability explorer can be
generated from Odoo metadata and joined to existing scene facts without a new
capability registry or a capability write model.
