"""Remove only temporary collaboration fixtures created by the governed browser journey."""

prefix = "codex-delete-journey-"
fixtures = env["ir.attachment"].sudo().search([("name", "like", prefix + "%")])
removed = fixtures.ids
fixtures.unlink()
print("LOCAL_DEV_COLLABORATION_FIXTURE_CLEANUP=%s" % {"removed_ids": removed, "remaining": 0})
