#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalRelationLifecycleModel.ts")
    producer = read_text("frontend/apps/web/src/pages/contractForm/useCreatedRecordNavigationRuntime.ts")
    consumer = read_text("frontend/apps/web/src/pages/contractForm/relationCreateDialogRuntime.ts")
    search = read_text("frontend/apps/web/src/pages/contractForm/RelationSearchDialog.vue")
    search_style = read_text("frontend/apps/web/src/pages/contractForm/RelationSearchDialog.css")
    visual = read_text("scripts/verify/local_dev_candidate_visual_smoke.mjs")
    create = read_text("frontend/apps/web/src/pages/contractForm/RelationCreateDialog.vue")
    for symbol in (
        "buildProfessionalRelationCreatedMessage", "buildProfessionalRelationCancelledMessage",
        "resolveProfessionalRelationLifecycleEvent", "settleProfessionalRelationLifecycle",
    ):
        if symbol not in model: failures.append(f"professional relation lifecycle model missing {symbol}")
    if "buildProfessionalRelationCreatedMessage" not in producer or "buildProfessionalRelationCancelledMessage" not in producer:
        failures.append("relation child producer bypasses professional lifecycle model")
    if "resolveProfessionalRelationLifecycleEvent" not in consumer or "settleProfessionalRelationLifecycle" not in consumer:
        failures.append("relation parent consumer bypasses professional lifecycle model")
    if 'data-professional-relation-lifecycle="search"' not in search:
        failures.append("relation search dialog missing professional lifecycle identity")
    for marker in (
        '<ScInput', '<ScLoading', 'role="listbox"', 'role="option"',
        'data-semantic-component="RelationSearchResult"', ':aria-selected=',
        '@keydown.space.prevent=', '@keydown.enter.prevent=',
        'class="relation-dialog-footer-actions"',
    ):
        if marker not in search:
            failures.append(f"relation search presentation missing {marker}")
    for forbidden in ('class="input"', '<input\n          ref="searchInputRef"'):
        if forbidden in search:
            failures.append(f"relation search presentation retains legacy control {forbidden}")
    for primitive_prefix in ('var(--sc-space-', 'var(--sc-base-'):
        if primitive_prefix in search_style:
            failures.append(f"relation search style directly consumes primitive token {primitive_prefix}")
    for marker in ('captureRelationSearchDialog', 'relationSearchDialogEvidence', 'keyboardSelected'):
        if marker not in visual:
            failures.append(f"relation search runtime evidence missing {marker}")
    if 'data-professional-relation-lifecycle="create"' not in create:
        failures.append("relation create dialog missing professional lifecycle identity")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in model: failures.append(f"relation lifecycle model contains forbidden product special case {forbidden}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_relation_lifecycle_guard] FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("[frontend_professional_relation_lifecycle_guard] PASS authority=shared exact_once=1")
    return 0

if __name__ == "__main__": raise SystemExit(main())
