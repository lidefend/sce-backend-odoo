# Batch-2A Personnel Profile and Authorization Boundary

[中文](business_entry_surface_normalization_batch_2a_20260913.md)

## 1. Product Boundary

- Formal Product Layer: P1 construction-industry standard product.
- Layer Target: action-scoped `res.users` list/form/search configuration for the
  personnel-profile and data-permission entries in `smart_construction_core`, plus
  the governed write adapter for existing project-member authorization.
- The batch reorganizes responsibilities of two existing formal entries. Business
  semantics remain in P1; ACLs, record rules, group membership, and low-code
  runtime configuration are unchanged. The live journey exposed two generic P0
  contract-consumption gaps, fixed narrowly by carrying formal-action read context
  and applying row modifiers in desktop/mobile one2many editors. Neither fix adds
  a model, action, or field special case.
- P1 blast radius is limited to
  `action_sc_runtime_user_management/menu_sc_runtime_user_management` and
  `action_sc_product_data_permission_v1/menu_sc_product_data_permission_v1`, plus
  their shared `sc.project.member.assignment` write path. P0 blast radius is the
  formal-action read context and the shared desktop/mobile one2many editor; generic
  targeted tests prove that neither change is business-specific.
  The 89-entry catalog is an inventory scope, not a list of 89 pages to change;
  wording differences alone are not defects.

## 2. Carryover Decision

The personnel entry is available to business-configuration administrators and
platform administrators. The data-permission entry is available to industry
configuration administrators. Industry configuration implies business
configuration, but the reverse is false. Moving company, role, and project
authorization exclusively to the data-permission entry would therefore remove
an existing capability from some administrators.

Both actions use `res.users`, the same `sc_runtime_company_maintainable` domain,
the same assignable `res.groups` facts, and the same
`sc.project.member.assignment` facts. Until product governance explicitly
authorizes either a capability removal or wider entry access, the personnel form
keeps a clearly labelled compatibility authorization tab. No permission is
changed by this batch.

A focused runtime menu-projection test confirms the carryover boundary directly:
a transactional user holding only the business-configuration administrator group
sees Personnel Profile but not Data Permission, while a user explicitly assigned
the industry-configuration administrator group sees both through the existing
inheritance. Data Permission therefore cannot yet replace the compatibility entry
without a separate product authorization decision.

Managed account creation still requires an explicit initial password, consistent
main/allowed companies, and the existing internal-user seed. Because the model is
`res.users`, this batch does not claim coverage of employees without accounts.

## 3. Implementation

- The personnel entry is titled “人员档案”; profile/contact/organization/job
  information leads the list and form.
- Profile documents, login/account controls, and compatibility authorization
  controls are separated. Login, activation, password, main company, and allowed
  companies remain available under their existing authority.
- The data-permission form keeps read-only identity and concentrates editable
  main/allowed company, business-role, and project-member authorization facts.
- Both actions retain dedicated tree/form/search views. Shared `res.users` views,
  ACLs, record rules, and group inheritance are unchanged.
- The managed `res.users.write` path previously filtered out the project-member
  one2many commands submitted by both forms, leaving an editable control that did
  not persist. The commands are now separated from the privileged user-field write
  and executed as the current administrator through the existing assignment ACL
  and company record rule. A new assignment requires a valid project readable by
  the current actor.
- An established assignment has immutable project identity. Omitting the project
  or supplying the existing project permits note updates, deactivation, and
  reactivation; clearing or changing it is rejected server-side. Reassignment is
  represented by deactivating the old assignment and creating one for the target
  project. Both forms also render the project control read-only on existing rows.
- All assignment commands are prevalidated before ordinary profile fields are
  written, so a mixed invalid authorization/profile update rolls back as a unit.
  Creating a person with inline authorization now explicitly requires saving the
  person first instead of silently dropping the commands.
- Cross-user changes, physical deletion, and unreadable cross-company projects
  remain rejected. Account creation, activation, and password behavior are unchanged.
- P0 now consumes two existing generic contract semantics correctly: main/relation
  reads use only server-projected formal-action context and preserve explicit
  `active_test=false`; one2many editors apply the current row's modifier so an
  established assignment project is read-only while a new row remains selectable.
  No URL/arbitrary client context is forwarded, `active_test` is not disabled
  globally, and no `sudo` or business-model exception was added.

## 4. Layered Verification

- Static: business-entry ownership 7 tests, administration-wave guard 1 test,
  and configuration-wave guard 1 test passed; XML/Python/diff checks passed.
- Targeted Odoo: `data_permission_surface` passed 5 methods / 7 Odoo statistics,
  including the runtime menu-visibility counterexample, and
  `runtime_user_management` passed 23 methods / 25 Odoo statistics. Coverage includes asymmetric group
  inheritance, identical record scope, dedicated views, read-only identity,
  compatibility controls, and profile-only safe payloads that exclude account,
  company, role, and project-authorization fields. Assignment coverage includes
  missing-project rejection, A-to-B and clear-project rejection with unchanged
  follower facts, same-project note/deactivate/reactivate, atomic rollback with a
  profile change, inline authorization rejection on user creation, cross-company
  record-rule denial, cross-user denial, and physical-deletion denial.
- Governed runtime: `smart_construction_core 17.0.0.165` passed the governed
  `local.dev` incremental upgrade, backend restart, and authority verification.
  Final assembly projects `active_test=false` and the established-row
  `project_id` `readonly=id` modifier from both formal actions. Product candidate
  `0734524b475e9c436afe8284d9cf62e8ffb2334a` consumes only those formal projections.
- Read-only browser: candidate
  `ab8827aa50d8339d5d5c777123771b14e178de0a` on
  `sc-local-dev/sc_dev_demo`, desktop 1440 and mobile 390. The system administrator
  received personnel `menu 430/action 736` and data-permission
  `menu 709/action 886`; both lists opened `res.users/39`, returned form contracts
  with HTTP 200, and rendered real fields without page/console errors.
  `demo_readonly` received neither route authority and both routes were rejected
  with `NAVIGATION_AUTHORITY_DENIED`. Every report has `mutationCount=0`.
- Focused write journey: P4 runner
  `92bef311801b0a218325bbe17bfbdbe787784059` reused managed batch
  `batch2a-auth-20260913` in the same `sc-local-dev/sc_dev_demo`, scoped to person
  445, project 427, and assignment 33. Both entries showed the inactive assignment
  with its established project read-only. One journey reactivated it, performed
  authoritative readback, refreshed, confirmed the same fact through the second
  entry, and finally deactivated it again. The browser made exactly two successful
  `api.data/write` attempts, each containing only assignment 33's `active` update.
  Final authority shows the assignment inactive, the person no longer following
  the project, and project/note/source unchanged.

The initial list row, `res.users/3` (`Default User Template`), is not a personnel
operating record. A generic first-row attempt did not reach a ready form. Reusing
the same runner with visible personnel record 39 passed, so no timeout or product
code was changed to mask the template-record distinction.

## 5. Evidence and Open Decision

- List-to-form journey:
  `artifacts/playwright/batch2a-personnel-auth-readonly-record39/summary.json`.
- Form grouping:
  `artifacts/playwright/batch2a-personnel-auth-forms/summary.json` and screenshots.
- Denied-role counterexample:
  `artifacts/playwright/batch2a-personnel-auth-denied/summary.json`.
- Browser artifacts are local runtime evidence and are not tracked in Git. The
  final documentation HEAD is bound separately by its final Quick.
- The read-only layout evidence remains bound to the earlier candidate. Later
  changes are limited to authorization writes, formal context, and row-modifier
  consumption; unaffected menus, themes, and page structure were not rematrixed.
- Authorization lifecycle evidence:
  `artifacts/p4-personnel-authorization/batch2a-auth-20260913/summary.json`. The
  managed person/project remain for audit, assignment 33 is inactive, and its
  follower relation is removed; no audit record was physically deleted.
- The journey transparently records three auxiliary `res.users api.onchange` HTTP
  500 responses caused by the baseline onchange path serializing virtual/NewId
  relations. They do not participate in the scoped assignment writes,
  authoritative reads, follower updates, or busy release. The runner classifies
  only an exact intent/model/record match as auxiliary; every other HTTP or page
  error remains blocking. This historical issue is not claimed as fixed here and
  remains separate follow-up work.
- Product decision remains open: remove the business administrator's existing
  authorization capability, or widen access to the data-permission entry. Until
  then, the compatibility tab is the lossless boundary.

## 6. Rollback

Revert the P1 view/authorization adapter, the two generic P0 contract-consumption
fixes, P4 runner, targeted tests, and documentation commits. There is no schema,
permission, or business-data migration. A governed module upgrade of the reverted
version restores the prior XML assembly. The managed audit assignment remains
inactive unless handled through its existing audit rules.

The next step is limited to independent review of the frozen candidate and Draft
PR preparation. Batch-2B is not started by this batch.
