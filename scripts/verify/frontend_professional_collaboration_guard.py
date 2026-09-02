#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    panel = read_text("frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue")
    timeline = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue")
    composer = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationComposer.vue")
    attachments = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalAttachmentManager.vue")
    followers = read_text("frontend/apps/web/src/pages/contractForm/ProfessionalFollowerManager.vue")
    model = read_text("frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts")
    attachment_runtime = read_text("frontend/apps/web/src/pages/contractForm/useNativeAttachmentRuntime.ts")
    chatter_runtime = read_text("frontend/apps/web/src/pages/contractForm/useNativeChatterRuntime.ts")
    for marker in ('data-professional-collaboration-component="timeline"', "data-collaboration-entry-type", "update-activity", "open-attachment"):
        if marker not in timeline: failures.append(f"collaboration timeline missing {marker}")
    if "<ProfessionalCollaborationTimeline" not in panel or "visibleCollaborationTimeline" not in panel:
        failures.append("native collaboration panel bypasses shared timeline")
    if "<ProfessionalCollaborationComposer" not in panel or 'data-professional-collaboration-component="composer"' not in composer:
        failures.append("native collaboration panel bypasses shared composer")
    if "<ProfessionalAttachmentManager" not in panel or 'data-professional-collaboration-component="attachments"' not in attachments:
        failures.append("native collaboration panel bypasses shared attachment manager")
    if "<ScButton" not in attachments:
        failures.append("attachment settlement bypasses the governed button primitive")
    if "<ScButton" not in panel:
        failures.append("collaboration entry actions bypass the governed button primitive")
    for primitive in ("<ScButton", "<ScInput", "<ScTextarea", "<ScSelect"):
        if primitive not in composer:
            failures.append(f"collaboration composer bypasses governed primitive {primitive}")
    if "<textarea" in composer:
        failures.append("collaboration composer retains a raw textarea bypass")
    if "<ScFileField" not in attachments or 'type="file"' in attachments:
        failures.append("attachment input bypasses the governed file primitive")
    if "<ScButton" not in timeline or ':loading="timelineLoading"' not in timeline:
        failures.append("collaboration timeline does not expose governed loading actions")
    for marker in ('data-professional-collaboration-component="panel"', ":data-follower-readiness"):
        if marker not in panel: failures.append(f"collaboration panel missing {marker}")
    if "<ProfessionalFollowerManager" not in panel or 'data-professional-collaboration-component="followers"' not in followers:
        failures.append("native collaboration panel bypasses shared follower manager")
    if "<ScButton" not in followers or "<ScList" not in followers or "<ScInlineState" not in followers:
        failures.append("follower settlement bypasses governed primitives")
    if "follower: input.hasFollowerAuthority ? 'ready' : 'fail_closed'" not in model:
        failures.append("follower readiness must consume explicit authority and fail closed")
    if "contract.actions.follow.enabled === true && response.can_follow === true" not in chatter_runtime or "contract.actions.unfollow.enabled === true && response.can_unfollow === true" not in chatter_runtime:
        failures.append("follower presentation must intersect contract and record authority")
    if "contract?.actions.follow.enabled === true && canFollow.value === true" not in chatter_runtime or "contract?.actions.unfollow.enabled === true && canUnfollow.value === true" not in chatter_runtime:
        failures.append("follower update handler must independently enforce contract and record authority")
    if "@update=\"$emit('update-follower', $event)\"" not in panel:
        failures.append("professional collaboration panel must settle follower updates")
    if "canDownloadCollaborationAttachment(entry)" not in timeline:
        failures.append("collaboration attachment download bypasses the shared authority resolver")
    if "entry.attachment?.can_download !== false" in timeline:
        failures.append("collaboration attachment download retains fail-open authority")
    if "entry.attachment?.can_download === true" not in model:
        failures.append("collaboration attachment download authority does not fail closed")
    if "att.can_download !== true" not in attachment_runtime:
        failures.append("attachment open handler must independently reject missing or denied authority")
    if attachment_runtime.count("!params.canUpload()") < 2:
        failures.append("attachment upload handlers must independently reject missing or denied authority")
    if ':enabled="attachmentUploadEnabled"' not in panel:
        failures.append("attachment upload presentation must consume explicit upload authority")
    if "canUpdateCollaborationActivity(entry, action)" not in chatter_runtime:
        failures.append("activity update handler must independently enforce explicit backend authority")
    if "canReplyCollaborationMessage(entry)" not in timeline:
        failures.append("message reply presentation must consume explicit backend authority")
    if "entry.message?.can_reply !== true" not in chatter_runtime or "parent_id: replyTarget.value?.id" not in chatter_runtime:
        failures.append("message reply handler must enforce authority and preserve the parent relation")
    if "@reply=\"$emit('reply', $event)\"" not in panel:
        failures.append("professional collaboration panel must settle the reply action")
    if "canExecuteCollaborationCreateAction(action, 'activity')" not in chatter_runtime or "canExecuteCollaborationCreateAction(action, activeMode.value)" not in chatter_runtime:
        failures.append("collaboration create handlers must independently enforce the active contract action")
    if "nativeChatterActions.value.find((item) => item.mode === 'activity')" in read_text("frontend/apps/web/src/pages/contractForm/useRecordCollaborationPresentation.ts"):
        failures.append("activity composer authority must not fall back to an unrelated contract action")
    if "entry.activity?.can_complete === true" not in model or "entry.activity?.can_cancel === true" not in model:
        failures.append("activity update authority resolver must fail closed for both actions")
    if "activity.status === 'pending' || activity.status === 'overdue'" not in model or "'unknown'" not in model:
        failures.append("activity presentation must consume explicit backend status and fail closed when absent")
    if "deadline < now" in model or "new Date()" in model:
        failures.append("activity presentation must not infer business status from the client clock")
    for forbidden in ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目"):
        if forbidden in model or forbidden in timeline: failures.append(f"collaboration components contain forbidden product special case {forbidden}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_collaboration_guard] FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("[frontend_professional_collaboration_guard] PASS components=1 follower=backend_authoritative")
    return 0

if __name__ == "__main__": raise SystemExit(main())
