#!/usr/bin/env python3
"""Regression tests for shared JavaScript contract-consumer markers."""

from __future__ import annotations

import unittest

from js_contract_consumer_markers import has_contract_page_info_view_type_access


class ContractPageInfoViewTypeMarkerTests(unittest.TestCase):
    def test_accepts_semantically_equivalent_optional_chains(self) -> None:
        accepted = (
            "contract?.snapshot.pageInfo.viewType",
            "contract?.snapshot?.pageInfo?.viewType",
            "const mode = contract?.snapshot.pageInfo?.viewType;",
            "return contract?.snapshot?.pageInfo.viewType ?? 'list';",
        )
        for source in accepted:
            with self.subTest(source=source):
                self.assertTrue(has_contract_page_info_view_type_access(source))

    def test_rejects_different_or_weakened_consumption_paths(self) -> None:
        rejected = (
            "contract.snapshot.pageInfo.viewType",
            "other?.snapshot?.pageInfo?.viewType",
            "contract?.pageInfo?.viewType",
            "contract?.snapshot?.other?.viewType",
            "contract?.snapshot?.pageInfo?.view_type",
            "contract?.snapshot?.pageInfo?.details?.viewType",
            "contract?.snapshot?.pageInfo?.['viewType']",
            "contract?.snapshot?.pageInfo?.viewType.extra",
            "contract?.snapshot?.pageInfo?.viewType['name']",
            "snapshot?.pageInfo?.viewType",
            "contract?.snapshot?.viewType",
            "contract?.pageInfo?.viewType",
            "viewType",
            "const snapshot = contract?.snapshot; const viewType = snapshot?.pageInfo?.viewType;",
        )
        for source in rejected:
            with self.subTest(source=source):
                self.assertFalse(has_contract_page_info_view_type_access(source))

    def test_ignores_comments_and_literal_text(self) -> None:
        rejected = (
            "// contract?.snapshot?.pageInfo?.viewType\nconst mode = 'list';",
            "/* contract?.snapshot?.pageInfo?.viewType */ const mode = 'list';",
            "const value = 'contract?.snapshot?.pageInfo?.viewType';",
            'const value = "contract?.snapshot?.pageInfo?.viewType";',
            "const value = `contract?.snapshot?.pageInfo?.viewType`;",
            "const value = `${contract?.snapshot?.pageInfo?.viewType}`;",
            "const value = /contract?.snapshot?.pageInfo?.viewType/;",
        )
        for source in rejected:
            with self.subTest(source=source):
                self.assertFalse(has_contract_page_info_view_type_access(source))

    def test_rejects_distributed_tokens(self) -> None:
        rejected = (
            "const contract = source; const snapshot = source; const pageInfo = source; const viewType = source;",
            "contract?.snapshot; pageInfo?.viewType;",
            "contract?.snapshot?.pageInfo; other?.viewType;",
        )
        for source in rejected:
            with self.subTest(source=source):
                self.assertFalse(has_contract_page_info_view_type_access(source))

    def test_fails_closed_for_lexically_damaged_source(self) -> None:
        rejected = (
            "const mode = contract?.snapshot?.pageInfo?.viewType; /*",
            "const mode = 'contract?.snapshot?.pageInfo?.viewType;",
            "const mode = `contract?.snapshot?.pageInfo?.viewType;",
            "if (ready) { contract?.snapshot?.pageInfo?.viewType;",
            "if (ready]) contract?.snapshot?.pageInfo?.viewType;",
        )
        for source in rejected:
            with self.subTest(source=source):
                self.assertFalse(has_contract_page_info_view_type_access(source))


if __name__ == "__main__":
    unittest.main(verbosity=2)
