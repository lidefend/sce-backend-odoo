"""Read-only resolver for the non-draft readiness-evidence carrier.

Prints the fixture-owned non-draft project id so the overview browser probe can
open it without hard-coding a database id. Never writes.
"""

non_draft = env.ref(
    "smart_construction_acceptance_fixture.fe_project_non_draft",
    raise_if_not_found=False,
)
if not non_draft or non_draft._name != "project.project":
    raise RuntimeError("non-draft completion-degree evidence carrier is missing")
if non_draft.lifecycle_state == "draft":
    raise RuntimeError("non-draft carrier is unexpectedly in draft")
print("ACCEPTANCE_NON_DRAFT_PROJECT_ID=%d" % non_draft.id)
