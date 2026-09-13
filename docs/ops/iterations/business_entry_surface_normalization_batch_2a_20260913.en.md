# Batch-2A Personnel Profile and Authorization Boundary

[中文](business_entry_surface_normalization_batch_2a_20260913.md)

## 1. Product Boundary

- Formal Product Layer: P1 construction-industry standard product.
- Layer Target: action-scoped `res.users` list/form/search configuration for the
  personnel-profile and data-permission entries in `smart_construction_core`.
- The batch reorganizes responsibilities of two existing formal entries. It does
  not change the P0 renderer, ACLs, record rules, group membership, or low-code
  runtime configuration.
- Blast radius is limited to
  `action_sc_runtime_user_management/menu_sc_runtime_user_management` and
  `action_sc_product_data_permission_v1/menu_sc_product_data_permission_v1`.
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
  P0 code, ACLs, record rules, group inheritance, and backend account behavior are
  unchanged.

## 4. Layered Verification

- Static: business-entry ownership 7 tests, administration-wave guard 1 test,
  and configuration-wave guard 1 test passed; XML/Python/diff checks passed.
- Targeted Odoo: `data_permission_surface` passed 7 tests, including the new runtime
  menu-visibility counterexample, and
  `runtime_user_management` passed 16 tests. Coverage includes asymmetric group
  inheritance, identical record scope, dedicated views, read-only identity,
  compatibility controls, and profile-only safe payloads that exclude account,
  company, role, and project-authorization fields.
- Governed runtime: incremental `smart_construction_core` upgrade and authority
  verification passed. An old P4 guard referenced absent
  `sc.legacy.user.profile` in the current module set; it was not misclassified as
  a product failure or expanded into historical tooling work.
- Read-only browser: candidate
  `ab8827aa50d8339d5d5c777123771b14e178de0a` on
  `sc-local-dev/sc_dev_demo`, desktop 1440 and mobile 390. The system administrator
  received personnel `menu 430/action 736` and data-permission
  `menu 709/action 886`; both lists opened `res.users/39`, returned form contracts
  with HTTP 200, and rendered real fields without page/console errors.
  `demo_readonly` received neither route authority and both routes were rejected
  with `NAVIGATION_AUTHORITY_DENIED`. Every report has `mutationCount=0`.

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
- Product decision remains open: remove the business administrator's existing
  authorization capability, or widen access to the data-permission entry. Until
  then, the compatibility tab is the lossless boundary.

## 6. Rollback

Revert the P1 view/contract expression, targeted tests, and documentation commits.
There is no schema, permission, or business-data migration. A governed module
upgrade of the reverted version restores the prior XML assembly.
