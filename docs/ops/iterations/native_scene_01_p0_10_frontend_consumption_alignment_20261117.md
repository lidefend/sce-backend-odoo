# NATIVE-SCENE-01 / P0-10 Frontend Consumption Alignment

Status: verification_pending

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: Unified Page Contract V2 decoder and custom frontend consumption.
- Module: `frontend/apps/web`.
- Standard vs User-Specific: platform-neutral contract consumption.
- Why Here: Action View Set, Search identity, native occurrence identity and
  embedded Widget nodes are P0 contracts consumed by the generic frontend.
- Why Not Elsewhere: no industry/customer semantics or Renderer-specific business
  behavior is required; the backend has already published the facts.
- Blast Radius: Action-bound Search decoding and the declared contract-basis
  bindings for Native Action, occurrence and Widget consumers.

## Scope

- reject `nativeActionContract.search` when `searchContract.nativeIdentity` is
  present but the Action contract omits the Search reference;
- compare `viewId`, `viewXmlId` and `authority` across both contract carriers;
- register Native Action View Set, native occurrence identity and embedded
  native Widget consumption in the frontend contract-basis ledger;
- add focused non-zero regression evidence.

## Exclusions

- backend ActionResolver or PageAssembler changes;
- same-type multiple View selection UX;
- professional Renderer or industry Widget implementation;
- database, deployment, product acceptance or production mutation.

## Baseline

- Source branch: `main`
- Exact baseline: `e890568b9c75bcf8059c5ea67030992492dbd440`
- Worktree state before edits: clean

## Evidence

Implemented:

- `nativeActionContract.search` now must exist whenever
  `searchContract.nativeIdentity` exists;
- the two carriers must agree on `viewId`, `viewXmlId` and `authority`;
- a present Native Action Contract with an empty `orderedViews` stops through
  `ContractGapError` instead of reopening implicit view inference;
- the Native Action View Set, Search identity, occurrence identity, embedded
  Widget node and Widget provenance surfaces are explicitly registered in
  `frontend_contract_basis_ledger.json`;
- the new consumption gate is referenced by the frontend quick, PR and release
  lanes.
- the source-derived complexity, split-plan and component-driver inventory
  reports were refreshed deterministically by the repository commit hook.

Verification:

| Check | Result |
| --- | --- |
| `make verify.frontend.native_action_contract_consumption.unit` | PASS, 7 cases |
| `make verify.frontend.canonical_form_presenter.unit` | PASS, primary suite 177 cases plus declared auxiliary suites |
| `make verify.frontend.contract_basis.unit` | PASS, 15 tests; 20 bindings, 0 open defects |
| `make verify.frontend.contract_basis.enforce` | PASS |
| `make verify.frontend.native_widget_provenance.unit` | PASS |
| `make verify.frontend.node_component.unit` | PASS, 48 cases |
| `make ci.local.iteration` | PASS; strict typecheck and source lint passed, with 4 pre-existing warnings |

The original logs and source-bound receipts are under
`.runtime/agent-runs/NATIVE-SCENE-01-P0-10-FRONTEND-CONSUMPTION-ALIGNMENT/`.
This page is not a substitute for those receipts or remote CI.

## Boundary Result

- Backend contract source was not modified.
- No database, runtime, deployment or production mutation was performed.
- Same-type multiple View selection UX and professional Renderer behavior remain
  outside this batch.
- Current state is a verified dirty candidate, not a reviewed or published PR.
