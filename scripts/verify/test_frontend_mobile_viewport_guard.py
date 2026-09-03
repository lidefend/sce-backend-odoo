import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import frontend_mobile_viewport_guard as guard  # noqa: E402

GOOD_META = (
    '<meta name="viewport" content="width=device-width, '
    'initial-scale=1.0, viewport-fit=cover" />'
)
MISSING_COVER = (
    '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
)
NO_META = "<html><head><title>x</title></head></html>"
ZOOM_DISABLED = (
    '<meta name="viewport" content="width=device-width, '
    'initial-scale=1.0, viewport-fit=cover, user-scalable=no" />'
)


class MobileViewportGuardTest(unittest.TestCase):
    def test_compliant_meta_passes(self) -> None:
        failures = guard.validate(GOOD_META, style_sources={})
        self.assertEqual(failures, [])

    def test_missing_viewport_fit_cover_fails(self) -> None:
        failures = guard.validate(MISSING_COVER, style_sources={})
        self.assertTrue(
            any("viewport-fit=cover" in f for f in failures), failures
        )

    def test_missing_meta_tag_fails(self) -> None:
        failures = guard.validate(NO_META, style_sources={})
        self.assertTrue(
            any("viewport meta" in f for f in failures), failures
        )

    def test_disabled_zoom_fails(self) -> None:
        failures = guard.validate(ZOOM_DISABLED, style_sources={})
        self.assertTrue(
            any("accessibility floor" in f for f in failures), failures
        )

    def test_safe_area_without_cover_fails(self) -> None:
        failures = guard.validate(
            MISSING_COVER,
            style_sources={
                "a.vue": "padding-bottom: calc(8px + env(safe-area-inset-bottom));"
            },
        )
        self.assertTrue(
            any("safe-area" in f for f in failures), failures
        )

    def test_safe_area_with_cover_passes(self) -> None:
        failures = guard.validate(
            GOOD_META,
            style_sources={
                "a.vue": "padding-bottom: calc(8px + env(safe-area-inset-bottom));"
            },
        )
        self.assertEqual(failures, [])

    def test_repo_baseline_is_compliant(self) -> None:
        failures = guard.validate()
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
