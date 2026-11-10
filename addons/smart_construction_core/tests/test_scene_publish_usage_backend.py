# -*- coding: utf-8 -*-
"""scene.action_publish must account the publish and never raise NameError.

Regression for the "name read but never bound" defect family: the publish
action referenced the usage-counter model without binding it, so publishing a
real scene raised ``NameError`` on the accounting line -- after the scene had
already been written to ``published``. The static guard catches the missing
name; this test proves the runtime path now actually increments the counter.
"""

from uuid import uuid4

from odoo.tests.common import TransactionCase, tagged


@tagged("sc_smoke", "scene_publish_usage_backend")
class TestScenePublishUsageCounter(TransactionCase):
    def _counter_value(self, usage, company, key):
        rows = usage.sudo().search(
            [("company_id", "=", company.id), ("key", "=", key)], limit=1
        )
        return rows.value if rows else 0

    def test_action_publish_binds_usage_counter_and_increments(self):
        usage = self.env.get("sc.usage.counter")
        self.assertIsNotNone(
            usage, "sc.usage.counter must be installed for publish accounting"
        )

        company = self.env.user.company_id
        scene = self.env["sc.scene"].create(
            {
                "name": f"Publish {uuid4().hex[:8]}",
                "code": f"PUB{uuid4().hex[:8].upper()}",
                "is_test": True,
            }
        )

        key = "scenes_published"
        before = self._counter_value(usage, company, key)

        scene.action_publish()

        self.assertEqual(scene.state, "published")
        self.assertEqual(
            self._counter_value(usage, company, key),
            before + 1,
            "publishing a scene must increment the scenes_published usage counter",
        )

    def test_publish_freezes_all_definitions_and_runtime_filters_user_access(self):
        restricted_group = self.env.ref("base.group_system")
        open_capability = self.env["sc.capability"].create({
            "key": "test.scene.open.%s" % uuid4().hex[:8],
            "name": "Open tile",
            "intent": "ui.contract",
            "status": "ga",
        })
        restricted_capability = self.env["sc.capability"].create({
            "key": "test.scene.restricted.%s" % uuid4().hex[:8],
            "name": "Restricted tile",
            "intent": "ui.contract",
            "status": "ga",
            "required_group_ids": [(6, 0, [restricted_group.id])],
        })
        scene = self.env["sc.scene"].create({
            "name": "Publication definition %s" % uuid4().hex[:8],
            "code": "PUBDEF%s" % uuid4().hex[:8].upper(),
            "is_test": True,
            "tile_ids": [
                (0, 0, {"capability_id": open_capability.id, "title": "Open"}),
                (0, 0, {"capability_id": restricted_capability.id, "title": "Restricted"}),
            ],
        })
        limited_user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Limited scene reader",
            "login": "scene-limited-%s@example.com" % uuid4().hex[:8],
            "groups_id": [(6, 0, [
                self.env.ref("smart_construction_core.group_sc_internal_user").id,
            ])],
        })

        frozen_definition = scene.with_user(limited_user)._build_version_payload()
        self.assertEqual(
            {tile["key"] for tile in frozen_definition["tiles"]},
            {open_capability.key, restricted_capability.key},
        )
        access_fields = {"allowed", "user_visible", "state", "reason_code", "reason"}
        self.assertFalse(any(access_fields & set(tile) for tile in frozen_definition["tiles"]))

        scene.action_publish()
        self.assertEqual(
            {tile["key"] for tile in scene.active_version_id.payload_json["tiles"]},
            {open_capability.key, restricted_capability.key},
        )
        runtime = scene.to_public_dict(limited_user)
        self.assertEqual({tile["key"] for tile in runtime["tiles"]}, {open_capability.key})
