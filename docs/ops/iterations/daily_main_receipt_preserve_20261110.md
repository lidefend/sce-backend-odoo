# Preserve deployment receipt during daily main sync

Status: active

- Formal Product Layer: P4
- Layer Target: daily runtime main bundle synchronization
- Baseline: `main@bdb2d770876eb1603b6ea32bf9d958aa2100a205`
- Exclusion: no product, contract, ACL, data or topology change

## Defect

The detached candidate ignored `.deployed.json`, so it was clean. Main sync then
checked out the older main commit before fast-forwarding, where that ignore rule
did not yet exist. The valid runtime receipt became an unexpected untracked file
and blocked synchronization after checkout.

## Rule

Main sync may defer exactly the sole untracked root `.deployed.json` across
checkout. Before fast-forward, it must prove the target main `.gitignore`
explicitly ignores that path. Every other dirty path and every target main that
does not ignore the receipt remain fail-closed. Post-sync cleanliness remains
mandatory.
