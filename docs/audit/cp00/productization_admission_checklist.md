# CP-00 productization admission checklist

Baseline: `1bfe1f500320a35d59bef156db3c5ba746735668`

This is an admission checklist for later work. It is not authorization to
implement any item.

## 1. Lifecycle stage gates

| Stage | Admission condition | Current status | Evidence boundary |
| --- | --- | --- | --- |
| Native Entry | Odoo Menu and Action exist with stable XMLIDs and a valid target | PASS for read-time discovery | Explorer native projection |
| Capability identity | One accepted identity contract relates semantic capability, provider and native entry without treating them as the same fact | GAP | Three capability representations |
| Scene composition | Scene references only backend-approved capability records and publishes a versioned composition | PARTIAL | `sc.scene` works; its artifact is not wired to product Scene snapshot delivery |
| Qualification | Preview/Standard is derived from declared criteria and verified evidence | GAP | 8 contracts, 0 evidence bundles, evaluator not integrated |
| Product Release | Released snapshot freezes the complete product dependency graph and qualification evidence | GAP | Policy/page projection is frozen; Scene bytes and evidence are not |
| Tenant enablement | Company can enable only an exact released product and the decision is independently stored | PARTIAL | Released prerequisite works; partial-member business release and dual carrier remain |
| Authorization | Native ACL, rules, company scope and business operation decide execution | PASS | Effective route authority plus native ORM |
| User delivery | Real role opens and executes the released/enabled product; denial path is proven | NOT_VERIFIED | No CP-08 pilot |

## 2. Architecture admission rules

Before CP-01 or any later implementation:

1. Approve the relationship between semantic capability identity and native
   entry identity.
2. Decide whether `menu_xmlid + action_xmlid` is a capability binding, an entry
   alias, or both with an explicit typed relation.
3. Prohibit a second editable capability registry.
4. Decide the owner of maturity evidence and its link to releases.
5. Decide the immutable boundary of a release snapshot.
6. Decide whether release approval is one-person or independent review.
7. Decide whether native release forms remain a supported write path.
8. Decide the sole tenant-enablement carrier and migration path.
9. Define whether a business Scenario release requires all declared members or
   a separately qualified subset.
10. Define the cross-principal handoff record without merging authorization.

## 3. Required proof before CP-08

The end-to-end pilot must prove:

- one accepted capability identity;
- one accepted native `(menu_xmlid, action_xmlid)` entry identity;
- provider and dependency closure;
- Preview and/or Standard evidence with digests;
- Scene version selection and content hash;
- Product Release containing all dependency digests;
- tenant enablement pointing to the exact Release;
- role assignment using native groups and rules;
- allowed user opens and executes the capability;
- unauthorized user is denied by the backend;
- disabling the tenant Scene prevents subsequent access;
- no manual JSON patch, SQL repair or permission bypass is needed.

## 4. Immediate implementation hold

The following remain on hold until the owner reviews CP-00:

- CP-01 identity ADR and schema;
- CP-02 capability-native binding;
- CP-03 Scene combination governance;
- CP-04 Qualification implementation;
- CP-05 Release snapshot redesign;
- CP-06 Tenant enablement migration;
- CP-07 Product Assembly Workspace;
- CP-08 end-to-end pilot.

The existing Explorer, Release Operator and Scene package components may be
reused. They are not proof that the lifecycle is complete.
