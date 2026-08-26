from __future__ import annotations

import unittest

from scripts.verify.frontend_inline_state_guard import FILES, validate


class FrontendInlineStateGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}

    def altered(self, key: str, marker: str) -> dict[str, str]:
        values = dict(self.sources)
        values[key] = values[key].replace(marker, "")
        return values

    def test_current_sources_pass(self) -> None:
        self.assertEqual(validate(self.sources), [])

    def test_loading_busy_semantics_are_required(self) -> None:
        self.assertTrue(any("aria-busy" in error for error in validate(self.altered("inline", ":aria-busy=\"state === 'loading' || undefined\""))))

    def test_reduced_motion_is_required(self) -> None:
        self.assertTrue(any("reduced-motion" in error for error in validate(self.altered("inline", "prefers-reduced-motion: reduce"))))

    def test_error_heading_must_not_be_fixed(self) -> None:
        values = dict(self.sources)
        values["error"] = values["error"].replace('<component :is="titleTag"', '<h2').replace('</component>', '</h2>')
        self.assertTrue(any("fixed heading" in error for error in validate(values)))

    def test_business_identity_is_rejected(self) -> None:
        values = dict(self.sources)
        values["inline"] += "<!-- payment.request -->"
        self.assertTrue(any("business identity" in error for error in validate(values)))


if __name__ == "__main__":
    unittest.main()
