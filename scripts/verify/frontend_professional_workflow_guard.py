#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def shared_action_bar_errors(driver: str, surface: str) -> list[str]:
    """Follow task/workspace action inputs through the extracted native surface."""
    def template(source):
        return re.sub(r"<!--[\s\S]*?-->", "", source.split("<script", 1)[0])

    def has_binding(source, tag, expected):
        calls = re.findall(r"<" + tag + r"\b[\s\S]*?/>", source)
        if len(calls) != 1:
            return False
        attrs = {key: value for key, _, value in re.findall(r'''([:@\w-]+)\s*=\s*(["'])(.*?)\2''', calls[0], re.S)}
        return all(attrs.get(key) == value for key, value in expected.items())

    errors = []
    action_bindings = {f":{name}": value for name, value in (
        ("direct-actions", "directActions"), ("overflow-actions", "overflowActions"),
        ("effective-primary-key", "effectivePrimaryKey"),
    )}
    action_bindings["@action-ref"] = "emit('action-ref', $event)"
    source = template(driver)
    for pattern in ("TaskFormPattern", "WorkspaceFormPattern"):
        branch = re.search(r"<" + pattern + r"\b[\s\S]*?</" + pattern + r">", source)
        expected = {**action_bindings, ":effective-primary-key": "floorplan.effectivePrimaryKey",
                    ":visible-actions": "visibleActions", ":actions-in-header": "actionsInHeader"}
        if not branch or not has_binding(branch[0], "CanonicalNativeFormSurface", expected):
            errors.append(f"{pattern} must forward shared workflow actions to the native surface")
    legacy = {key: "floorplan." + value if key.startswith(":") else value for key, value in action_bindings.items()}
    if not has_binding(source, "CanonicalActionBar", legacy):
        errors.append("task compatibility path must retain shared workflow actions")
    expected = {**action_bindings, "v-if": "visibleActions.length && !actionsInHeader"}
    if not has_binding(template(surface), "CanonicalActionBar", expected):
        errors.append("native surface must retain shared workflow actions and header ownership")
    for source, component in ((driver, "CanonicalNativeFormSurface"), (driver, "CanonicalActionBar"), (surface, "CanonicalActionBar")):
        if f"import {component} from './{component}.vue'" not in source:
            errors.append(f"shared workflow component import missing: {component}")
    return errors

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    action_bar = read_text("frontend/apps/web/src/pages/contractForm/CanonicalActionBar.vue")
    driver = read_text("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    surface = read_text("frontend/apps/web/src/pages/contractForm/CanonicalNativeFormSurface.vue")
    header = read_text("frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue")
    confirm = read_text("frontend/apps/web/src/components/business/IntentConfirmationDialog.vue")
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalWorkflowModel.ts")
    for marker in ('data-professional-workflow-component="action-bar"', ':data-disabled-reason', ':data-workflow-primary-key'):
        if marker not in action_bar: failures.append(f"workflow action bar missing {marker}")
    failures.extend(shared_action_bar_errors(driver, surface))
    if 'data-professional-workflow-component="statusbar"' not in header: failures.append("workflow statusbar lacks semantic identity")
    for marker in ('<ScStatusBadge', '<ScSelect', 'aria-label="编辑业务状态"', ':disabled="busy"', ':readonly="statusbar.readonly"', '@change="activateStatus(String($event))"'):
        if marker not in header: failures.append(f"selection status control bypasses canonical field state {marker}")
    if '<ScSteps' in header or 'native-statusbar-track' in header:
        failures.append("selection status must not imply ordered workflow topology")
    for marker in (":data-professional-workflow-component", "canonicalWorkflowAuthority", "workflowDisabledReason(action)"):
        if marker not in header: failures.append(f"header workflow actions bypass shared authority {marker}")
    if "<ScDialog" not in confirm or 'data-professional-workflow-component="confirm-dialog"' not in confirm: failures.append("workflow confirmation bypasses the dialog primitive")
    if 'data-dialog-purpose="intent-confirmation"' not in confirm: failures.append("workflow confirmation lacks a non-conflicting dialog purpose")
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
