# Fund legacy read-only archive contract

## Scope

The `smart_construction_core` module exposes two historical archive entries on
`sc.fund.account.operation`:

- 油卡登记: `direct_acceptance:油卡登记`
- 充值登记: `direct_acceptance:充值登记`

Both require the source model
`online_old_legacy_direct:direct_acceptance`. The pair of source model and
source table is the archive classifier; menu, action, view, context, or numeric
database IDs are not trusted as record identity.

## Security boundary

The two entries have separate XML actions, menus, search views, list views,
form views, and fixed domains. They are visible to the existing
`smart_construction_core.group_sc_cap_finance_read` capability (including its
implying finance roles). All records remain restricted to the user's allowed
companies.

The model rejects runtime creation of either archive identity and rejects
write, unlink, confirm, complete, cancel, and reset operations on existing
archive records. This server-side protection is exact to the two approved
source identities and does not change ordinary fund-operation workflows.
Business initiators and industry configuration administrators do not gain
read access to these finance archives merely through their existing generic
fund-operation ACLs.

## Data lifecycle

This change does not import, copy, repair, or delete historical data. Any
future historical import must be separately designed as an offline, audited
and idempotent migration; the runtime model intentionally exposes no context
flag or public bypass for creating archive records.
