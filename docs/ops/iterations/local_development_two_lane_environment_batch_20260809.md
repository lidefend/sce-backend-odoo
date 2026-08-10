# Local development two-lane environment batch — 2026-08-09

- Branch pattern: `release/tenant-rc-<tenant-key>-v1`
- Baseline SHA: `eef94ed`
- Formal Product Layer: P4 ops delivery / development tooling
- Layer Target: local Compose lifecycle, snapshot, clean-install regression
- Module: `scripts/dev`, `make/dev.mk`, `docs/ops`
- Standard vs User-Specific: repository development standard; no customer fact or preference
- Why Here: environment identity, backup and repeatable verification are operational concerns
- Why Not Elsewhere: no runtime product contract or industry business semantic is changed
- Blast Radius: local projects `sc-backend-odoo-dev` and `sc-local-clean` only; daily/UAT/prod excluded

Database identities:

- Persistent development: platform-internal demo tenant, `sc_demo`, exact filter `^sc_demo$`, fixture not added by this batch.
- Clean regression: isolated platform-internal regression tenant, `sc_clean`, exact filter `^sc_clean$`, demo/fixture disabled.
- Both environments use separate database, Redis and Odoo data volumes.

Rollback: stop `sc-local-clean`; its explicit rebuild target can remove only that project's isolated volumes.
The persistent `sc_demo` environment is never deleted by this workflow.
