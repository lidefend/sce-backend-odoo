# P1 Role Capability Authority 2026-11-26

## Ownership

- Formal Product Layer: P1 construction industry standard product
- Layer Target: construction role, capability and entry-visibility authority graph
- Module: `smart_construction_core`
- Standard vs User-Specific: construction industry standard
- Why Here: the faulty role-to-entry edges are standard P1 security declarations.
- Why Not Elsewhere: P2/P3 cannot repair standard permission semantics, P4 must remain evidence tooling, and P0 must not acquire construction role names.
- Blast Radius: role groups, 14 generic entry carriers, 68 cross-domain menu rebindings, role-surface guards and affected role tests.
- Exclusions: no frontend, no business model/ACL/state changes, no customer preference, and no persistent database migration before separate confirmation.

## Finding

Thirteen role identity groups currently imply `group_sc_entry_pXX` directly.
That bypasses the approved chain:

```text
role group -> capability group -> entry visibility carrier -> menu/action
```

The acceptance projection later showed that this direct graph also competes
with per-page `role_authority`, producing 221 authorized-but-unprojected pages
and 31 projected-but-not-authorized pages.

The page-level mismatch was also traceable to 68 rebound menus: their runtime
menu group is `group_sc_entry_pXX`, while the acceptance rows still declared
the superseded domain groups. The acceptance rows are now aligned to the
rebinding fact while action-level capability declarations remain unchanged.

## Decision

Preserve existing effective visibility while correcting ownership:

1. Add one explicit entry-visibility capability for each existing visibility
   carrier.
2. Make each entry-visibility capability imply only its matching carrier.
3. Replace role-to-carrier implications with role-to-capability implications.
4. Explicitly remove the old role-to-carrier edges during module replay.
5. Add a static guard forbidding role groups from directly implying any
   entry/menu/action/native permission group.

This is a graph correction, not a parallel permission engine and not a change
to ACLs, record rules or business actions.

The role exposure declaration was recomputed from the corrected menu authority;
the restricted identity's explicit narrowing set shrank from 42 to 23 pages.

## Verification Responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | identity preflight | always |
| owning module baseline coverage | deferred_remote | `verify.smart_construction_core.module_baseline` | P1 permission behavior; exact-head remote CI owns full module coverage |
| existing affected test families | required | changed-test selector and named role tests | role/group graph and role-surface consumers change |
| focused changed tests | required | `verify.role_capability_group_authority.unit` | new invariant |
| contract/schema/consumer | required | fact-layer and role-surface guards | role graph is consumed by role projection |
| frontend lint/type/build | excluded | n/a | no frontend source change |
| runtime/browser journey | deferred | governed local.dev verification | requires separately confirmed module replay/migration |
| remote required gates | required | exact-head PR CI | integration and merge authority |

## Migration Boundary

Source changes are deterministic and include explicit removal commands for the
old edges. No persistent database action is authorized by this record.

Before any module upgrade or ORM execution, create and confirm:

- exact database `sc_dev_demo` or isolated `local.test` attempt;
- module version and replay file;
- expected role/group relation removals and additions;
- authoritative pre/post closure readback;
- backup/restore or transaction rollback method.

Prepared module replay identity:

- module: `smart_construction_core`;
- target version: `17.0.0.187`;
- source data order: entry carriers before capability groups;
- expected role-to-entry direct-edge removals: the historical 13 role groups;
- expected capability additions: 14 per-scope capabilities plus one full-scope capability;
- expected postcondition: every affected role retains exactly the same
  `group_sc_entry_pXX` closure recorded in the focused static test.

## Result

## Source Validation

- `verify.role_capability_group_authority.unit`: PASS, 12 tests; graph direction,
  closure equivalence, load order and 68 acceptance rebindings checked.
- `verify.frontend.business_entry.matrix.universe`: PASS.
- `verify.frontend.role_surface_exposure_declaration.guard`: PASS,
  12 roles / 23 narrowings.
- `verify.role_surface.landing.contract.unit`: PASS, 35 tests.
- `verify.nav01.native_authority.unit`: PASS.
- `verify.frontend.dev.incremental.unit`: PASS, 245 tests.

Source result:

- `sc_entry_groups.xml` now loads before capability groups and is explicitly
  documented as resource-level carriers.
- `sc_capability_groups.xml` adds 14 entry-visibility capabilities and one
  full-scope composition capability.
- `sc_role_entry_groups.xml` removes 13 historical role-to-carrier paths and
  selects the corresponding capabilities instead; all effective role-to-carrier
  closures are unchanged.
- `sc_role_groups.xml` keeps role-identity inheritance while removing direct
  permission carriers.
- `sc_discover_entry_groups.xml` is retired; its removals and the experience
  capability selection live in `sc_role_entry_groups.xml`.
- `menu_entry_group_rebinding.json` remains the single declaration for the 68
  cross-domain menus; the acceptance CSV now consumes the same entry-carrier
  identities in its menu-chain authority.
- The role exposure narrowing declaration was reduced from 42 stale pages to the
  23 pages actually reachable by the restricted role.

## Runtime Validation

Not run. No persistent or isolated test database was upgraded because the
module replay plan above has not received a separate migration confirmation.

## Takeover continuation

Candidate: `fix/p1-role-capability-authority-20261126` at
`169531b07224db6913c5655e02c067a50d7632cc`, plus explicit uncommitted changes.
P1 owns the six new ORM regression methods. P4 changes only repair run target
registration, deleted-security-file test routing, and coverage bookkeeping.
The deleted `sc_discover_entry_groups.xml` now selects the same guards as its
replacement. Full-scope ORM assertions compare exact capability membership;
missing capability declarations cannot pass vacuously.

Evidence is under `.runtime/agent-runs/P1-ROLE-CAPABILITY-AUTHORITY-20261126/`:

- `takeover-role-guard.log`: passed, 12 tests.
- `takeover-planner-unit.log`: passed, 245 tests.
- `takeover-resume.json`: run resolved; no scope escape.
- `takeover-iteration.log`: failed before runtime execution on the deleted path;
  routing has since been repaired and the final plan has no unmapped paths.
- `takeover-coverage-final.log`: 19 tool tests pass; audit still fails on two
  pre-existing unregistered groups, `p0_contract_descriptor_conformance_evidence`
  and `workflow_contract_platform`. This task registers only its own new group.
- `takeover-offline.log`: affected offline consumer checks; use the command exit
  status and original per-target results, not this narrative, as evidence.
- Python syntax and `git diff --check` pass. Static changed-test discovery selects
  9 core classes (including `TestRoleCapabilityAuthority`) and 3 bundle classes;
  discovery is not ORM execution.
- `local.test.prepare` passed identity validation without runtime writes.
- ORM, remote integration, deployed behavior and user acceptance remain not run.
  Full core module coverage remains deferred to exact-head remote CI.

### Proposed isolated execution for owner confirmation

Migration/install is needed only to validate loaded Odoo relations; source tests
cannot prove installed permissions. Proposed first execution:

```sh
make local.test.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestRoleCapabilityAuthority LOCAL_TEST_REUSE_DATABASE=0
```

Target: existing project `sc-local-test-6b0769da09e2`, database role
`sc_test_odoo`, runner-allocated unique `sc_test_6b0769da09e2_<attempt-digest>`.
The exact attempt name is allocated by the registered runner and must be retained
in its receipt. Module: `smart_construction_core` version `17.0.0.187` from this
candidate; runner and source hashes are recorded in `takeover-candidate.json`.
This explicit template-free diagnostic preserves all existing templates and
persistent databases. Expected writes are fresh module/dependency installation,
14 scope capabilities plus full composition, and test transactions; this does
not rehearse upgrading existing user data or authorize `sc_dev_demo` changes.

Preflight/dry-run is the completed read-only `local.test.prepare`, static XML
closure validation and class selection. There is no claim of a database dry-run.
Before execution recheck source hashes and profile identity. Postconditions are
all six tests actually executed, zero failures, exact 14 capability memberships,
unchanged role-entry closures, correct identity codes and all 68 menu bindings;
verify unchanged source/profile and transient-carrier cleanup in the receipt.

Backup/recovery: this attempt is newly allocated synthetic data, so there is no
existing database content to back up. Preserve existing template and persistent
volumes. Test transactions roll back, the runner cleans its transient application
carrier, and failed attempt data is isolated and not promoted. Do not perform
manual/global database or volume cleanup; inspect the receipt on failure.
Subsequent affected ORM families and any actual upgrade rehearsal require their
own exact target/source authority; this focused run cannot establish upgrade or
full-module acceptance.

Status remains `verification_pending`. No remote mutation or database migration
has occurred. Local source rollback is limited to the listed takeover diff;
code rollback must never be represented as database restoration.

## Disposable test authorization

On 2026-11-26 the owner explicitly instructed: “一次性测试 可以直接执行”.
This supersedes the earlier confirmation requirement for disposable isolated
tests in this task. Governed local.test execution is authorized; persistent
database migration remains excluded. The pending migration-approval blocker
is removed. P1 scope and three-lane verification responsibilities are unchanged.

## Rule synchronization and first ORM result

The owner's follow-up explicitly requested recording the rule change. `AGENTS.md`,
`.agent/context.yaml` and the execution allowlist now permit governed disposable
synthetic tests without per-attempt confirmation, including required installation,
upgrade, fixtures and template preparation. Persistent/real-data migration rules
remain in force. Earlier confirmation requests in this record are historical and
superseded for disposable tests.

The focused ORM execution passed all 6 methods with 0 failures/errors. Receipt:
`.runtime/test-baseline/1795637553697716498/receipt.json`; original log beside it.
Database: `sc_test_6b0769da09e2_f8fd05c4fb07`. This is fresh-install evidence,
not a persistent-database upgrade rehearsal or full module baseline. Rule-file
edits were applied after the receipt completed to preserve its source identity.

Changed-test attempt `.runtime/test-baseline/1795637702907636352/receipt.json`
failed in the bundle negative principal setup: unlinking an implying capability
left its materialized entry membership. Classified as `validation_tool_defect`.
The test now resets exact data-only groups and asserts both entry capability
and carrier are absent before checking denial. The denial assertion is retained.

Core changed-test receipt `.runtime/test-baseline/1795637906529464675/receipt.json`
reports 150 executed, 13 failures and 1 error. Affected contract test callers
omitted mandatory accepted-version negotiation, returning
`CONTRACT_VERSION_UNSUPPORTED` before their business assertions. Added explicit
`accepted_contract_versions: ["2.7.x"]` to these callers without weakening the
contract gate or original assertions. Bundle rerun passed 5 methods in receipt
`.runtime/test-baseline/1795637880079058733/receipt.json`.

## Authorized ORM verification result

Final `make verify.changed_tests.orm`: PASS. Core executed 150 methods in nine
classes, zero failures/errors, receipt
`.runtime/test-baseline/1795638216346755241/receipt.json`. Bundle's unchanged
five-method receipt was validated and reused by the governed selector from
`.runtime/test-baseline/1795637880079058733/receipt.json`. All 155 selected methods
are covered; the six new authority methods are included in the core result.

The two customer-form callers also needed explicit `client_type` and client
capabilities; both now declare them, with an explicit successful-envelope
assertion before inspecting form structure. Original business assertions remain.
Failed attempts are retained, including
`.runtime/test-baseline/1795638123580470653/receipt.json`.

Rule YAML parsing, disposable-authorization assertions and `git diff --check`
pass. Required full module coverage remains remote; existing coverage-registry
omissions and remaining local iteration checks are not claimed passed. Changes
remain uncommitted; no PR, merge, persistent-data migration or deployment occurred.

## Local iteration closure

The two existing coverage omissions are now dispositioned using their real owning
entries, without claiming standalone gate wiring or execution. Coverage audit
passes (19 tool tests). `make ci.local.iteration` passed all 18 selected targets;
receipt `.runtime/frontend-dev-validation/executions/20261125T203144Z-2554244-644322999/receipt.json`.
Additional runtime evidence includes 84 permission-truth methods, 2 real extension
lifecycle methods, payment isolation and 11 workspace-authority methods. Full
module coverage remains deferred to remote integration. No persistent migration
or deployment was performed. Next: generated evidence, clean commit, independent
review and exact-head remote checks.

`make ci.delivery.freeze.prepare` passed; generated complexity reports were
reviewed and only reflect the owned test/registry changes. Log:
`.runtime/agent-runs/P1-ROLE-CAPABILITY-AUTHORITY-20261126/freeze-prepare.log`.
Remote main was read back at the unchanged baseline
`487a3d8497cd89841e1954d164e0e11d79742d81`. Independent review and exact-head PR
CI remain pending; author self-check is not independent review.

Public scanning initially rejected the changed payment permission test blob
`ed8f1aaa4953693e9d502bce2871a038524791a5` (PD003/RH018). A byte comparison
against the previously reviewed `578ab14089ea852ce60f7fa96da3f27eec3f4b96`
proves the only change is the entry-group reference; synthetic fixture values
are unchanged. Added the exact rule/path/blob/classification exemption under
the existing registry, with no wildcard or scan weakening. This P4 evidence
change does not alter product or ORM test inputs.

## REQUEST_CHANGES remediation: preserve experience business authorization

Independent review of `6a548785dbc1ca544f871235e7f607e19a855026` found that
routing experience identity through `group_sc_internal_user` added P1 business
ACLs despite unchanged entry closure. This was a genuine authorization regression.
The role now uses `group_sc_cap_internal_identity`, which implies only
`base.group_user` and owns no model ACL. The P1 module version is `17.0.0.188`.
Entry visibility still flows through its existing explicit scope capabilities.

New static and loaded-ORM assertions compare the complete non-entry closure with
native internal identity. A real user carrying only the experience role is compared
against a base.group_user-only control over every active ACL model granted to the
industry internal group (at least 21), for read/create/write/unlink. Labor, equipment
and subcontract prices plus request/plan models are explicitly required and denied.
Neither the industry internal group nor data_operator may enter experience groups.

Governed isolated ORM passed 14 methods with zero failures/errors. Receipt:
`.runtime/test-baseline/1795641281717555660/receipt.json`; source, test surface and
profile remained unchanged, and the transient application carrier is absent.
Exact attempt: `sc_test_6b0769da09e2_cf54e9a34ec0`, project
`sc-local-test-6b0769da09e2`, role `sc_test_odoo`. The runner rebuilt the changed
synthetic template. This is disposable test evidence, not a persistent upgrade
or deployment. No real business data or persistent database was modified.

P1 owns this safety correction; P0, frontend and customer configuration remain
excluded. Local checks cover the role graph, role consumers and the named ORM
classes; owning-module baseline remains remote. Re-review and exact-head required
CI remain pending. Following #1003 integration, use governed main synchronization
and reconcile the two coverage-registry collisions against the actual merged Make
entries; generated reports must be regenerated, not chosen by text conflict side.
Rollback is the bounded source commit, never an assertion of database restoration.
