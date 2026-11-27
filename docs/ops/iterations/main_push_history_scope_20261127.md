# Main push history scope

Baseline: `09c95df6b2d0dad6c841d86b0b4a6d1435dcf094`.

P4 standard CI workflow routing; no product, database, scanner rule or exemption changes.

Confirmed failure: public_guard run 45955910221 scanned unrelated preserved #1022 history and reported RH018 on blob `1582beb6a28df0d8f550a87ebff8f24c41b4d70f`; merge_policy_gate run 45955910131 failed downstream. Frontend and professional checks passed. Original logs remain on GitHub.

Owner approved ordinary push and PR exact-commit full-ancestry scanning. Schedule and workflow_dispatch retain all public refs; #1022 and original history remain untouched.

Required: workflow shell routing regression, existing scanner negative tests and local incremental checks; new exact-head PR CI. R3, merge and deployment excluded. Local receipts under `.runtime/frontend-dev-validation/executions/`; current result indexed by this run.

Local pre-commit validation: 36 workflow tests and 42 scanner tests passed; workflow shell event routing regression had 3 failures before repair. `make ci.local.iteration` passed all 4 selected targets. Exact-HEAD receipt and remote checks remain required. Rollback: revert this isolated workflow/test change through protected review; no data migration.

Owner authorized synchronization and merge after renewed validation. Updated baseline: `9395d93f92badffc87d32c5979cf7c70e374e975` (#1026); appended by governed sync without conflicts. Local and remote evidence must bind the new candidate; original results remain historical.
