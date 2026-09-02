"""Remove only temporary collaboration fixtures created by the governed browser journey."""

prefix = "codex-delete-journey-"
upload_prefix = "codex-upload-journey-"
fixtures = env["ir.attachment"].sudo().search([
    "|",
    ("name", "like", prefix + "%"),
    ("name", "like", upload_prefix + "%"),
])
removed = fixtures.ids
fixtures.unlink()
message_prefix = "codex-message-delete-journey-"
create_prefix = "codex-create-action-journey-"
messages = env["mail.message"].sudo().search([
    "|",
    ("body", "like", message_prefix + "%"),
    ("body", "like", create_prefix + "%"),
])
removed_messages = messages.ids
messages.unlink()
activity_prefix = "codex-activity-cancel-journey-"
activities = env["mail.activity"].sudo().search([
    "|",
    ("summary", "like", activity_prefix + "%"),
    ("summary", "like", create_prefix + "%"),
])
removed_activities = activities.ids
activities.unlink()
print("LOCAL_DEV_COLLABORATION_FIXTURE_CLEANUP=%s" % {
    "removed_attachment_ids": removed,
    "removed_message_ids": removed_messages,
    "removed_activity_ids": removed_activities,
    "remaining": 0,
})
