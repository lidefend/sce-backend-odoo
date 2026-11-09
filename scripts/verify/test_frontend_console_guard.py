from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_console_guard as guard


class FrontendConsoleGuardTest(unittest.TestCase):
    LOGGER = (
        "const env = { VITE_DEBUG_LOGS: '' };"
        "console.debug(); console.info(); console.warn(); console.error();"
        "sink.debug(); sink.info(); sink.warn(); sink.error();"
    )

    def make_root(self, files: dict[str, str]) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "frontend/apps/web/src").mkdir(parents=True)
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_logger_owner_passes(self) -> None:
        root = self.make_root({guard.ALLOWED: self.LOGGER})
        self.assertEqual(guard.inspect(root)["errors"], [])

    def test_scattered_console_fails(self) -> None:
        root = self.make_root({
            guard.ALLOWED: self.LOGGER,
            "frontend/apps/web/src/Probe.ts": "console.warn('noise');\n",
        })
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("outside shared logger" in error for error in errors))

    def test_missing_debug_gate_fails(self) -> None:
        root = self.make_root({guard.ALLOWED: self.LOGGER.replace("VITE_DEBUG_LOGS", "UNUSED")})
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("policy marker" in error for error in errors))

    def test_too_many_console_calls_fails(self) -> None:
        root = self.make_root({
            guard.ALLOWED: self.LOGGER + "console.error('extra');console.warn('extra');",
        })
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("too many console calls" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
