#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    panel = read_text("frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue")
    timeline = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue")
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts")
    for marker in ('data-professional-collaboration-component="timeline"', "data-collaboration-entry-type", "update-activity", "open-attachment"):
        if marker not in timeline: failures.append(f"collaboration timeline missing {marker}")
    if "<ProfessionalCollaborationTimeline" not in panel or "visibleCollaborationTimeline" not in panel:
        failures.append("native collaboration panel bypasses shared timeline")
    for marker in ('data-professional-collaboration-component="panel"', 'data-professional-collaboration-component="composer"', ":data-follower-readiness"):
        if marker not in panel: failures.append(f"collaboration panel missing {marker}")
    if "follower: 'fail_closed'" not in model:
        failures.append("undeclared follower runtime must fail closed")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in model or forbidden in timeline: failures.append(f"collaboration components contain forbidden product special case {forbidden}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_collaboration_guard] FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("[frontend_professional_collaboration_guard] PASS components=1 follower=fail_closed")
    return 0

if __name__ == "__main__": raise SystemExit(main())
