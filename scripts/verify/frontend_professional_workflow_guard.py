#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    action_bar = read_text("frontend/apps/web/src/pages/contractForm/CanonicalActionBar.vue")
    driver = read_text("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    header = read_text("frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue")
    confirm = read_text("frontend/apps/web/src/components/business/IntentConfirmationDialog.vue")
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalWorkflowModel.ts")
    for marker in ('data-professional-workflow-component="action-bar"', ':data-disabled-reason', ':data-workflow-primary-key'):
        if marker not in action_bar: failures.append(f"workflow action bar missing {marker}")
    if driver.count("<CanonicalActionBar") < 2: failures.append("task and workspace do not share CanonicalActionBar")
    if 'data-professional-workflow-component="statusbar"' not in header: failures.append("workflow statusbar lacks semantic identity")
    if "<ScDialog" not in confirm or 'data-professional-workflow-component="confirm-dialog"' not in confirm: failures.append("workflow confirmation bypasses the dialog primitive")
    if "当前操作不可用" not in model: failures.append("disabled workflow action lacks a fail-closed reason")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in model or forbidden in action_bar: failures.append(f"workflow components contain forbidden product special case {forbidden}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_workflow_guard] FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("[frontend_professional_workflow_guard] PASS components=3")
    return 0

if __name__ == "__main__": raise SystemExit(main())
