from __future__ import annotations

import unittest

from scripts.quota_digitization.build_release import verify_release
from scripts.quota_digitization.parser import parse_page


def line(text, x, y, confidence=0.99):
    return {
        "text": text,
        "confidence": confidence,
        "box": [[x - 20, y - 5], [x + 20, y - 5], [x + 20, y + 5], [x - 20, y + 5]],
    }


class TableSegmentationTest(unittest.TestCase):
    def _page(self):
        lines = [
            line("C.1.1预制方桩（编码：010301001）", 800, 60),
            line("工作内容：准备、定位、打桩。", 500, 80),
            line("单位：100m", 300, 100),
            line("AC0001", 1000, 140), line("AC0002", 1200, 140),
            line("打预制方桩", 1100, 170),
            line("250×250", 1000, 190), line("300×300", 1200, 190),
            line("综合", 240, 230), line("基价（元）", 320, 230),
            line("100.00", 1000, 230), line("120.00", 1200, 230),
            line("人工费（元）", 300, 250), line("20.00", 1000, 250), line("25.00", 1200, 250),
            line("材料费（元）", 300, 270), line("60.00", 1000, 270), line("70.00", 1200, 270),
            line("机械费（元）", 300, 290), line("10.00", 1000, 290), line("12.00", 1200, 290),
            line("名称", 300, 330), line("单位", 700, 330), line("单价（元）", 850, 330),
            line("混凝土", 300, 370), line("m3", 700, 370), line("500", 850, 370),
            line("1.2", 1000, 370), line("1.4", 1200, 370),
            line("单位：100m", 300, 430),
            line("AC0003", 1000, 460), line("AC0004", 1200, 460),
            line("静力压桩", 1100, 490),
            line("综合基价（元）", 300, 530), line("200.00", 1000, 530), line("220.00", 1200, 530),
            line("名称", 300, 570), line("单位", 700, 570), line("单价（元）", 850, 570),
        ]
        return {
            "book_id": "building_1", "discipline": "房屋建筑与装饰工程", "volume": "一",
            "source_file": "building.pdf", "pdf_page": 1, "width_px": 1600, "height_px": 800,
            "line_count": len(lines), "mean_confidence": 0.99, "lines": lines,
        }

    def test_two_vertical_tables_do_not_cross_assign_costs(self):
        items, _, issues = parse_page(self._page())
        by_code = {row["code"]: row for row in items}
        self.assertEqual(set(by_code), {"AC0001", "AC0002", "AC0003", "AC0004"})
        self.assertEqual(by_code["AC0001"]["price_total"], 100.0)
        self.assertEqual(by_code["AC0002"]["price_total"], 120.0)
        self.assertEqual(by_code["AC0003"]["price_total"], 200.0)
        self.assertEqual(by_code["AC0004"]["price_total"], 220.0)
        self.assertFalse([row for row in issues if row["severity"] == "error"])

    def test_resource_quantities_are_attached_to_the_correct_item(self):
        items, _, _ = parse_page(self._page())
        by_code = {row["code"]: row for row in items}
        self.assertEqual(by_code["AC0001"]["resources"][0]["name"], "混凝土")
        self.assertEqual(by_code["AC0001"]["resources"][0]["quantity"], 1.2)
        self.assertEqual(by_code["AC0002"]["resources"][0]["quantity"], 1.4)


class RulePageTest(unittest.TestCase):
    def test_installation_rule_page_is_not_silently_dropped(self):
        lines = [line("A.7 风机安装（编码:030108）", 800, 80), line("说明", 800, 120)]
        lines.extend(line(f"{index}. 风机安装规则内容", 700, 150 + index * 20) for index in range(1, 8))
        page = {
            "book_id": "installation_1", "discipline": "通用安装工程", "volume": "一",
            "source_file": "installation.pdf", "pdf_page": 38, "width_px": 1600, "height_px": 800,
            "line_count": len(lines), "mean_confidence": 0.97, "lines": lines,
        }
        items, rules, issues = parse_page(page)
        self.assertFalse(items)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["chapter_code"], "INSTALL-030108")
        self.assertFalse([row for row in issues if row["severity"] == "error"])


class ReleaseGateTest(unittest.TestCase):
    def test_cost_component_mismatch_fails_closed(self):
        dataset = {
            "source_books": [
                {"book_id": book_id, "source_sha256": "a" * 64}
                for book_id in (
                    "building_1", "building_2", "installation_1", "installation_2",
                    "installation_3", "installation_4",
                )
            ],
            "rules": [{"book_id": "installation_1"}],
            "items": [{
                "code": "AA0001", "price_total": 100.0, "cost_labor": 20.0,
                "cost_material": 30.0, "cost_machine": 10.0, "cost_misc": 5.0,
            }],
            "metrics": {"page_count": 1218, "item_count": 1, "error_count": 0},
        }
        errors = verify_release(dataset, require_source_hashes=True)
        self.assertTrue(any("price component integrity" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
