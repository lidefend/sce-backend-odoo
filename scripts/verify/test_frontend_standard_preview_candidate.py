from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/frontend_standard_preview.py"


def _read_constants(profile: str | None) -> dict[str, str]:
    env = dict(os.environ)
    if profile is None:
        env.pop("SC_ACCEPTANCE_RUNTIME_PROFILE", None)
    else:
        env["SC_ACCEPTANCE_RUNTIME_PROFILE"] = profile
    env["FRONTEND_ACCEPTANCE_PORT"] = "5178"
    env["VITE_API_PROXY_TARGET"] = "http://127.0.0.1:18088"
    code = (
        "import importlib.util, pathlib\n"
        f"spec = importlib.util.spec_from_file_location('fsp', {str(SCRIPT)!r})\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "print(mod.OUTPUT)\n"
        "print(mod.PREVIEW_PORT)\n"
        "print(mod.API_PROXY_TARGET)\n"
        "print(mod.DIST)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = result.stdout.splitlines()
    return {
        "output": lines[0],
        "port": lines[1],
        "proxy": lines[2],
        "dist": lines[3],
    }


class FrontendStandardPreviewProfileTests(unittest.TestCase):
    def test_local_profile_preserves_existing_identity(self) -> None:
        values = _read_constants(None)
        self.assertTrue(values["output"].endswith("config05-20260929"))
        self.assertEqual(values["port"], "5180")
        self.assertEqual(values["proxy"], "http://127.0.0.1:18082")
        self.assertTrue(values["dist"].endswith("config05-20260929/dist"))

    def test_candidate_profile_uses_isolated_identity(self) -> None:
        values = _read_constants("candidate")
        self.assertTrue(values["output"].endswith("config05-20260929-candidate"))
        self.assertEqual(values["port"], "5178")
        self.assertEqual(values["proxy"], "http://127.0.0.1:18088")
        self.assertTrue(values["dist"].endswith("config05-20260929-candidate/dist"))
        self.assertNotIn("config05-20260929/dist", values["dist"])


if __name__ == "__main__":
    unittest.main()
