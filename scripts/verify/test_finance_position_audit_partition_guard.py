import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.finance_position_audit_partition_guard import detect, scan  # noqa: E402


COARSE = (
    "SELECT 1\n"
    "   GROUP BY counterparty_type, counterparty_project_id, partner_id, counterparty_name\n"
)
PARTITIONED = (
    "SELECT 1\n"
    "   GROUP BY company_id, currency_id, counterparty_type, counterparty_project_id,"
    " partner_id, counterparty_name\n"
)


class IdentityAggregationPartitionTest(unittest.TestCase):
    def test_coarse_identity_key_is_rejected(self):
        keys, errors = detect("coarse", COARSE)
        self.assertEqual(len(keys), 1)
        missing = sorted(e["missing"] for e in errors)
        self.assertEqual(missing, ["company_id", "currency_id"])

    def test_partitioned_identity_key_is_accepted(self):
        keys, errors = detect("partitioned", PARTITIONED)
        self.assertEqual(len(keys), 1)
        self.assertEqual(errors, [])

    def test_repository_sources_are_partitioned(self):
        summary, errors = scan()
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(summary), 4)
        for relative, detail in summary.items():
            self.assertTrue(
                detail["identity_grouping_keys"],
                f"{relative} no longer declares a counterparty identity aggregation",
            )


if __name__ == "__main__":
    unittest.main()
