#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify.docs_links import resolve_link


class DocsLinksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "docs" / "page.md"
        self.source.parent.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_percent_encoded_space_resolves_to_literal_space(self) -> None:
        resolved = resolve_link(self.source, "../source/parsers%20Kanban%20Pivot.py#L127")
        self.assertEqual(resolved, self.root / "source" / "parsers Kanban Pivot.py")

    def test_angle_destination_with_space_resolves(self) -> None:
        resolved = resolve_link(self.source, "<../source/parsers Calendar Gantt.py#L79>")
        self.assertEqual(resolved, self.root / "source" / "parsers Calendar Gantt.py")

    def test_encoded_hash_remains_part_of_the_path(self) -> None:
        resolved = resolve_link(self.source, "../source/file%23name.md#L2")
        self.assertEqual(resolved, self.root / "source" / "file#name.md")

    def test_angle_external_url_is_not_a_local_path(self) -> None:
        self.assertIsNone(resolve_link(self.source, "<https://example.com/a b>"))

    def test_fragment_only_link_requires_no_file(self) -> None:
        self.assertIsNone(resolve_link(self.source, "#section"))


if __name__ == "__main__":
    unittest.main()
