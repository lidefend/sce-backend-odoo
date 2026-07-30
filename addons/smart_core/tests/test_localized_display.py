# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

from ..utils.localized_display import localized_display_value


class TestLocalizedDisplay(TransactionCase):
    def test_requested_language_and_fallbacks(self):
        value = {"zh_CN": "项目甲", "en_US": "Project A"}
        self.assertEqual(localized_display_value(value, lang="zh-CN"), "项目甲")
        self.assertEqual(localized_display_value(value, lang="en-US"), "Project A")
        self.assertEqual(localized_display_value({"fr_FR": "Projet"}, lang="de_DE"), "Projet")

    def test_legacy_mapping_literal_is_safe_and_plain_text_is_unchanged(self):
        value = "{'zh_CN': '合同甲', 'en_US': 'Contract A'}"
        self.assertEqual(localized_display_value(value, lang="zh_CN"), "合同甲")
        self.assertEqual(localized_display_value("普通文本", lang="zh_CN"), "普通文本")

    def test_empty_and_malformed_mapping_never_expose_object_literal(self):
        self.assertEqual(localized_display_value({}, lang="zh_CN", empty="--"), "--")
        self.assertEqual(localized_display_value("{broken}", lang="zh_CN", empty="--"), "--")
