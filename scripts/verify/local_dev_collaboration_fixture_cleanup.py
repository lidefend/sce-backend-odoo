"""Remove only temporary collaboration fixtures created by the governed browser journey."""

prefix = "codex-delete-journey-"
fixtures = env["ir.attachment"].sudo().search([("name", "like", prefix + "%")])
removed = fixtures.ids
fixtures.unlink()
message_prefix = "codex-message-delete-journey-"
messages = env["mail.message"].sudo().search([("body", "like", message_prefix + "%")])
removed_messages = messages.ids
messages.unlink()
print("LOCAL_DEV_COLLABORATION_FIXTURE_CLEANUP=%s" % {
    "removed_attachment_ids": removed,
    "removed_message_ids": removed_messages,
    "remaining": 0,
})
