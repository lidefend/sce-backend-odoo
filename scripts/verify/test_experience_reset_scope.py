import unittest

from scripts.verify.experience_reset_scope import ResetScopeError, plan_cleanup


class ExperienceResetScopeTest(unittest.TestCase):
    def test_experience_authored_non_baseline_is_cleaned(self):
        scope = plan_cleanup(
            baseline_fingerprints={1, 2},
            experience_user_ids={9},
            business_records=[
                {"model": "payment.request", "id": 3, "create_uid": 9, "write_uid": 9},
                {"model": "project.project", "id": 1, "create_uid": 1, "write_uid": 1},
            ],
            artifacts=[],
        )
        self.assertEqual([record["id"] for record in scope["records"]], [3])
        self.assertEqual(scope["artifacts"], [])
        self.assertEqual(scope["baseline_violations"], [])

    def test_experience_authored_baseline_fails_closed(self):
        with self.assertRaises(ResetScopeError):
            plan_cleanup(
                baseline_fingerprints={1},
                experience_user_ids={9},
                business_records=[
                    {"model": "project.project", "id": 1, "create_uid": 9, "write_uid": 1},
                ],
                artifacts=[],
            )

    def test_non_experience_and_artifacts(self):
        scope = plan_cleanup(
            baseline_fingerprints={1},
            experience_user_ids={9},
            business_records=[
                {"model": "project.project", "id": 1, "create_uid": 1, "write_uid": 1},
                {"model": "res.partner", "id": 4, "create_uid": 9, "write_uid": 9},
            ],
            artifacts=[
                {"model": "ir.attachment", "id": 10, "author_uid": 9},
                {"model": "ir.attachment", "id": 11, "author_uid": 1},
            ],
        )
        self.assertEqual([record["id"] for record in scope["records"]], [4])
        self.assertEqual([artifact["id"] for artifact in scope["artifacts"]], [10])

    def test_empty_experience_set_cleans_nothing(self):
        scope = plan_cleanup(
            baseline_fingerprints={1},
            experience_user_ids=set(),
            business_records=[
                {"model": "res.partner", "id": 4, "create_uid": 9, "write_uid": 9},
            ],
            artifacts=[],
        )
        self.assertEqual(scope["records"], [])


if __name__ == "__main__":
    unittest.main()
