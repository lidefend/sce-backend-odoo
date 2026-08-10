# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_regression", "norm", "boq_version")
class TestBoqNormLink(TransactionCase):

    def test_imported_norm_snapshot_links_to_selected_catalog_and_keeps_source_code(self):
        project = self.env["project.project"].create({"name": "定额匹配项目"})
        region = self.env["sc.norm.region"].create(
            {"name": "四川省测试地区", "code": "TEST-SC"}
        )
        catalog = self.env["sc.norm.catalog"].create(
            {
                "name": "四川省2015版建设工程预算定额",
                "code": "TEST-SC-2015",
                "region_id": region.id,
                "edition_year": "2015",
            }
        )
        specialty = self.env["sc.norm.specialty"].create(
            {"name": "建筑与装饰工程", "code": "BUILD", "catalog_id": catalog.id}
        )
        item = self.env["sc.norm.item"].create(
            {
                "name": "基底钎探",
                "code": "AA0096",
                "specialty_id": specialty.id,
                "unit_raw": "100㎡",
            }
        )
        version = self.env["project.boq.version"].create(
            {
                "name": "定额匹配清单",
                "code": "V1",
                "project_id": project.id,
                "source_type": "contract",
                "norm_catalog_id": catalog.id,
            }
        )
        boq_line = self.env["project.boq.line"].create(
            {
                "project_id": project.id,
                "version_id": version.id,
                "code": "010101001001",
                "name": "基底钎探",
                "uom_id": self.env.ref("uom.uom_square_meter").id,
                "quantity": 10.0,
                "price": 5.0,
            }
        )
        analysis = self.env["project.boq.analysis"].create(
            {
                "name": boq_line.name,
                "boq_line_id": boq_line.id,
                "major_name": "建筑与装饰工程",
                "norm_line_ids": [
                    (0, 0, {"norm_code": "AA0096换", "name": "基底钎探"})
                ],
            }
        )
        analysis._resolve_norm_links()
        snapshot = analysis.norm_line_ids
        self.assertEqual(snapshot.norm_code, "AA0096换")
        self.assertEqual(snapshot.norm_item_id, item)
        self.assertEqual(snapshot.norm_match_state, "matched")
