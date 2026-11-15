# Recovery-Point Integrity

Status: `PASS`

## Authorized Recovery Point

`artifacts/local-dev/snapshots/20261115T082948Z/`

| Artifact | Bytes | SHA256 | Result |
| --- | ---: | --- | --- |
| `manifest.txt` | 517 | `bf9db35d4715f656521f9e5964fcdfdb905b3b7820958f5648d561769d08d316` | match |
| `sc_dev_demo.dump` | 12,288,190 | `0f416a23009a1e0678fa5e0a71eb19972854112bd112f2525bf03e6a790544b4` | match |
| `sc_dev_demo-filestore.tar.gz` | 11,596,714 | `90ae7b1ce8bdb3829ca08e84ff0a370862eaf7662bed1221a2acc70f0e539686` | match |

The manifest identifies source SHA
`d176e2fd67fec87257114b207cec655ec8fa6e9d`, database `sc_dev_demo`,
dbfilter `^sc_dev_demo$`, and a paired filestore rooted at
`odoo_data:/var/lib/odoo/filestore/sc_dev_demo`.

## Structural Validation

- The dump is PostgreSQL custom format `v1.14-0`, created at
  `2026-11-15 08:29:48 UTC` by PostgreSQL `15.19`.
- The dump header names database `sc_dev_demo`.
- `pg_restore --list` read 22,781 TOC lines and 838 table-data entries.
- The filestore archive contains one top-level database directory,
  `sc_dev_demo`.
- The archive contains 2,269 members: 1,755 files and 514 directories.
- Uncompressed file bytes total 52,733,406.
- The archive has zero duplicate members, zero unsafe paths, zero links,
  zero device entries, and passes `gzip -t`.
- The two checksum entries embedded in `manifest.txt` pass `sha256sum -c`.

## Boundary

`pg_restore --list` and data streaming were performed with the PostgreSQL
client from the existing `sc-local-dev` container. No database was created
or restored and no persistent table was changed by integrity validation.

The recovery point is complete and readable. This result does not itself
authorize restoring it.
