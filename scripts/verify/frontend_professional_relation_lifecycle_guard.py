#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalRelationLifecycleModel.ts")
    producer = read_text("frontend/apps/web/src/pages/contractForm/useCreatedRecordNavigationRuntime.ts")
    consumer = read_text("frontend/apps/web/src/pages/contractForm/relationCreateDialogRuntime.ts")
    search = read_text("frontend/apps/web/src/pages/contractForm/RelationSearchDialog.vue")
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
