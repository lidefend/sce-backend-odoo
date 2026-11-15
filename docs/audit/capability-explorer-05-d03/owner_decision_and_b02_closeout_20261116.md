# CAP05-D03 Owner Decision and B02 Closeout

Status: `OWNER_APPROVED_PENDING_AUDIT_PR`

## Decision

CAP05-B02 is closed as:

`REMEDIATED_BY_OWNER_AUTHORIZED_REBUILD`

It is not a `STRICT_ISOLATION_PASS`. The earlier persistent database upgrade
deviation occurred, the original recovery point was not restored, and the
owner later authorized a rebuild of the demo-only database.

## Owner Decisions

| Decision | Ruling | Operational effect |
| --- | --- | --- |
| D02-01 Database identity | ACCEPT | Keep the rebuilt Demo UUID, secret and create date. Do not restore old identity. External connection updates are separate. |
| D02-02 Entitlement absence | NOT ACCEPTED PENDING INVESTIGATION | `ENTITLEMENT-01` must investigate meaning, identity, company, seed source, validity and authorization consumers. No database mutation. |
| D02-03 BOQ residue | RETAIN AS DEMO RESIDUE | Keep `DEMO-CONTRACT-V1 / done / contract_boq.csv` and its 251-byte attachment. Do not treat it as formal business delivery. |
| D02-04 Relative dates | ACCEPT AS DEMO BEHAVIOR | Refreshed seed dates are demo-only and are not real business event dates. A future Demo data standard must state this. |
| D02-05 B02 closeout | REMEDIATED BY OWNER-AUTHORIZED REBUILD | Close B02 without asserting that the original upgrade was strictly isolated. |

## Preserved History

- `CAP05-D01` remains `superseded`; its historical record is not rewritten.
- `CAP05-D02` remains the owner authorization for the demo rebuild.
- PR #894 contains the original owner-review evidence at
  `e873a9abfdce65fc284ea0bdb0a91d8d7fcbcab4`.
- PR #893 contains the separate B01 migration repair at
  `6d5e1bee3b55bea549cda723958a54a0ef90674a`.
- The current decision does not claim that missing entitlement is correct.

## Entitlement Follow-up

`ENTITLEMENT-01` is authorized as a read-only investigation. It must determine:

- the `sc.entitlement` model definition and fields;
- the original row identity and company;
- the seed or creation source;
- effective dates and renewal semantics;
- current API, handler, UI and authorization consumers;
- whether the Demo environment requires the row for product-access behavior.

It may not reseed, insert, update or delete `sc_entitlement`.

## Boundary

- No database restore or write was performed by CAP05-D03.
- The BOQ wizard and attachment remain untouched.
- Demo dates remain unchanged.
- Capability, scene, qualification, release and tenant-enablement state remain
  unchanged.
- CP-01 through CP-08 remain on hold.
- Deployment and user acceptance were not performed.
