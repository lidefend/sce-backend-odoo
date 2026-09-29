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
