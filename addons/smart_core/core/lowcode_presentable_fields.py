# -*- coding: utf-8 -*-
"""Fields a low-code configuration may present as business facts.

A configuration is an editing surface, not a licensing authority: it may
single out the facts the user edits, but it must not promote a field the
platform already classifies as framework/tracking plumbing into the business
body.  The declaration lives at the platform core so the field-availability
picker and the view-orchestration union consume one list instead of each
keeping its own guess about what a technical field looks like.

Only explicit names are declared here.  A name/suffix heuristic would also
match business relation carriers (``attachment_ids`` is a ``*_ids`` field but is
the canonical attachment fact), and silently dropping a canonical carrier is
worse than presenting a plumbing field: the union therefore consumes this
explicit list and never a prefix.
"""
from __future__ import annotations

LOWCODE_NON_PRESENTABLE_FIELD_NAMES = frozenset({
    "access_instruction_message",
    "access_token",
    "access_url",
    "access_warning",
    "activity_date_deadline",
    "activity_exception_decoration",
    "activity_exception_icon",
    "activity_ids",
    "activity_state",
    "activity_summary",
    "activity_type_icon",
    "activity_type_id",
    "activity_user_id",
    "alias_bounced_content",
    "alias_contact",
    "alias_defaults",
    "alias_domain",
    "alias_domain_id",
    "alias_email",
    "alias_force_thread_id",
    "alias_id",
    "alias_name",
    "alias_parent_model_id",
    "alias_parent_thread_id",
    "alias_status",
    "alias_user_id",
    "message_attachment_count",
    "message_bounce",
    "message_channel_ids",
    "message_follower_ids",
    "message_has_error",
    "message_has_error_counter",
    "message_has_sms_error",
    "message_ids",
    "message_is_follower",
    "message_main_attachment_id",
    "message_needaction",
    "message_needaction_counter",
    "message_partner_ids",
    "message_unread",
    "message_unread_counter",
    "my_activity_date_deadline",
    "rating_ids",
    "rating_last_feedback",
    "rating_last_image",
    "rating_last_value",
    "rating_percentage_satisfaction",
    "rating_status",
    "rating_status_period",
    "website_message_ids",
})
