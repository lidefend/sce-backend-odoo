#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    event = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalAuditEvent.vue")
    timeline = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalAuditTimeline.vue")
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalAuditModel.ts")
    driver = read_text("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    task = read_text("frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue")
    collaboration = read_text("frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue")
    for marker in ("data-professional-audit-event", "data-audit-event-name", "data-audit-result", "data-audit-actor", "data-audit-time"):
        if marker not in event: failures.append(f"audit event missing {marker}")
    for marker in ("data-professional-audit-timeline", "ScEmptyState", "data-audit-readable-fallback"):
        if marker not in timeline: failures.append(f"audit timeline missing {marker}")
    if "resolveProfessionalAuditEvents" not in driver or "ProfessionalAuditTimeline" not in task:
        failures.append("task audit surface bypasses professional audit authority")
    if "ProfessionalAuditTimeline" not in collaboration or "resolveProfessionalAuditEvents" not in collaboration:
        failures.append("workspace collaboration hides or bypasses professional audit events")
    if ':show-audit-timeline="false"' not in driver or ':show-audit-timeline="true"' not in driver:
        failures.append("task and workspace do not prevent duplicate audit timelines")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in model or forbidden in event or forbidden in timeline:
            failures.append(f"audit components contain forbidden product special case {forbidden}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_audit_guard] FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("[frontend_professional_audit_guard] PASS components=2")
    return 0

if __name__ == "__main__": raise SystemExit(main())
