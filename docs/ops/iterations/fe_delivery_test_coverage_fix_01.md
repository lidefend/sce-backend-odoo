# FE-DELIVERY-TEST-COVERAGE-FIX-01

P4-only coverage bookkeeping for PR #721 at
`aef7ae51c656db05ade90ca1b485dc417c5c571a`.

The three runtime acceptance receipts are retained. This task changes only
`scripts/verify/test_coverage_registry.yaml` and the formally exported
`docs/audit/test_coverage_registry/test_coverage_registry.json`.

## Execution record

### Reviewed dispositions

| Group | Disposition | Evidence |
| --- | --- | --- |
| `company_project_refund_feedback` | class-selected | Generic tag spans the ORM and HTTP classes; both specific governed lanes select them |
| `company_project_refund_feedback_orm` | class-selected | `make verify.company_project_refund.feedback.orm` selects `TestCompanyProjectRefundFeedback` |
| `company_project_refund_feedback_http` | class-selected | `make verify.company_project_refund.feedback.http` selects the HTTP class |
| `company_project_refund_feedback_restore` | class-selected | `make verify.company_project_refund.feedback.restore` selects restoration cleanup |
| `feedback_evaluation_rt_http` | class-selected | `make verify.feedback_evaluation.rt.http.orm` selects authenticated HTTP feedback evaluation |
| `feedback_evaluation_rt_restore` | class-selected | `make verify.feedback_evaluation.rt.restore` selects fixture restoration |
| `native_advisory_draft` | class-selected | `make verify.native_advisory_draft.orm` selects the native advisory draft fixture/state tests |

No disposition claims that a test passed. The registry records how each group is
selected; execution evidence remains owned by its gate.

### Verification

- `make test.coverage.registry.export`: PASS; 197 tag groups, 47 on-demand, 16 wired CI unit scripts.
- Repeated export produced identical SHA-256 `af59fc5f6e43c5ee738315318cb60940ae57a24438f910778afc3b5fd3e2744e`.
- `make verify.test.coverage.registry`: PASS, 18 tests; all declared groups gated or dispositioned.
- The generated snapshot also captures the already-present `uc4_native_lowcode`
  status change from the current tree; it is generator output, not a manual edit.

### Candidate commit

Pending exact staging and commit identity.
