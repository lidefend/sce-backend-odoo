# System Group Business ACL Guard

- status: PASS
- scanned_file_count: 5
- scanned_row_count: 899
- violation_count: 0

## Rule

- Forbid direct `base.group_system` ACL on `model_sc_*` business models.
- Bind business ACLs only to explicit SC business roles; never bridge `base.group_system` through implied groups.
