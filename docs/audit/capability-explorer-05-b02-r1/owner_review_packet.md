# CAP05-B02 Owner Review Packet

Status: `BLOCKED_PENDING_OWNER_REVIEW`

This packet adds a three-state, read-only review of the original recovery
point, the paired pre-rebuild snapshot, and the current rebuilt `sc_dev_demo`
baseline. It makes no restore, cleanup or business-state decision.

## Fixed Objects

| Object | Identity |
| --- | --- |
| Original recovery point | `artifacts/local-dev/snapshots/20261115T082948Z` |
| Original dump SHA256 | `0f416a23009a1e0678fa5e0a71eb19972854112bd112f2525bf03e6a790544b4` |
| Pre-rebuild snapshot | `artifacts/local-dev/snapshots/20261115T163419Z` |
| Pre-rebuild dump SHA256 | `b361b210ba9c7437f46cf5954ccf7cecff680a6cab757f9423ba39ae355b86ff` |
| Current database | `sc_dev_demo`, read-only repeatable-read capture |
| Current module | `smart_construction_core 17.0.0.182 / installed` |

## Focused Findings

| Item | Original recovery point | Pre-rebuild snapshot | Current rebuilt baseline |
| --- | --- | --- | --- |
| `database.uuid` value SHA256 | `955a24d6…` | `955a24d6…` | `ac229bea…` |
| `database.secret` value SHA256 | `129ea5f6…` | `129ea5f6…` | `53082a81…` |
| `sc_entitlement` rows | 1 | 1 | 0 |
| BOQ import wizard | 0 | 0 | 1, state `done` |
| Database attachment rows | 929 | 929 | 930 |
| Physical filestore files | 1,755 | 1,755 | 1,862 |

The database identity change belongs to the current rebuilt baseline. It is not
a difference between the original recovery point and the pre-rebuild snapshot.
The original UUID and secret remain preserved in both old snapshots.

The entitlement row and BOQ wizard are also rebuild-baseline differences:

- The same `sc_entitlement` row existed in both older snapshots and is absent
  from the current rebuilt baseline.
- The BOQ wizard did not exist in either older snapshot and now exists once as
  `DEMO-CONTRACT-V1 / done / contract_boq.csv`.
- Its linked attachment is 251 bytes with SHA1
  `68364e2bb6de0a751686d721dda008356ca3efa3`.

## Seed Relative Dates

The rebuilt demo baseline refreshes relative dates:

| Field | Original max | Pre-rebuild max | Current max |
| --- | --- | --- | --- |
| `construction_contract.date_contract` | `2026-11-14` | `2026-11-14` | `2026-11-16` |
| `payment_request.date_request` | `2026-11-14` | `2026-11-15` | `2026-11-16` |
| `project_project.initiation_date` | `2026-11-14` | `2026-11-14` | `2026-11-16` |
| `tier_review.reviewed_date` | `2026-11-13 16:06:03` | `2026-11-15 08:34:57` | `2026-11-15 17:49:16` |

These values prove relative demo-date replay. They do not prove business intent
or authorize a timestamp edit.

## Filestore

The pre-rebuild filestore was path- and content-identical to the original
recovery point. The rebuilt baseline contains:

- 107 added physical files and 33,931 added bytes;
- zero modified files and zero deleted files;
- 929 stored-file attachment rows, all matching the physical SHA1 checksums;
- 930 total attachment rows, including one attachment without a stored file.

The owner must decide whether the 107 added files and BOQ attachment are
accepted as demo fixture residue or require a separately authorized cleanup.

## Capability and Scenario Catalog

Both `sc_product_scenario` and `sc_product_scenario_entry` remain at 17 and 78
rows respectively in all three states. Current row fingerprints changed,
however, so equal counts are not proof of byte-identical configuration. This
does not authorize changes to capability identity, scenes, qualification or
release.

## Decisions Required

1. Accept or reject the rebuilt database's new UUID, secret and create date.
2. Accept the missing `sc_entitlement` demo row or authorize a separately
   scoped reseed.
3. Accept the BOQ wizard and attachment as demo fixture residue or authorize a
   separately scoped cleanup.
4. Accept relative demo-date refresh or require a deterministic demo-date
   policy.
5. Decide whether B02 closes as remediation by rebuild, explicitly not as a
   strict-isolation PASS for the earlier upgrade.

## Boundary

- No restore, cleanup, table edit, version edit or business-state change was
  performed.
- `CAP05-B01` is now merged through PR #893; that does not erase the earlier B02
  environment deviation.
- `CAP05-B02` remains `BLOCKED_PENDING_OWNER_REVIEW`.
- R2 and R3 remain on hold.
