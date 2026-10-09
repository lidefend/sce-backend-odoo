#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_published_face_converge.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_published_face_converge", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40
OLD_SHA = "b" * 40
TREE_IDS = {"smart_core": "c" * 40}
PRODUCTS = ["construction.standard", "construction.preview"]
MODULES = ["smart_core"]


def product(key: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "product_key": key,
        "snapshot_id": 40,
        "snapshot_version": f"daily-navigation-{key.split('.')[-1]}-{SHA[:12]}",
        "policy_released_menu_count": 90,
        "snapshot_released_page_count": 90,
        "gate_page_count": 90,
    }
    payload.update(overrides)
    return payload


def evidence_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "PASS",
        "reason": "",
        "expected_sha": SHA,
        "head": SHA,
        "remote_root": module.REMOTE_ROOT,
        "product_keys": PRODUCTS,
        "products": [product(key) for key in PRODUCTS],
        "refreshes": {},
        "guard_status": "PASS",
        "modules": MODULES,
        "upgrade_mode": "run",
        "module_tree_ids": dict(TREE_IDS),
        "converge_returncode": 0,
        "converge_tail": "",
    }
    payload.update(overrides)
    return payload


def evidence(**overrides: object) -> bytes:
    return (json.dumps(evidence_payload(**overrides)) + "\n").encode()


class DailyRuntimePublishedFaceConvergeTests(unittest.TestCase):
    def test_preflight_requires_confirmation(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(module.ConvergeError, "confirmation"):
                module.preflight(SHA, "sc-root", "wutao", PRODUCTS, MODULES)

    def test_preflight_rejects_unbound_inputs(self) -> None:
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE": module.CONFIRMATION}
        ):
            with self.assertRaisesRegex(module.ConvergeError, "commit SHA"):
                module.preflight("HEAD", "sc-root", "wutao", PRODUCTS, MODULES)
            with self.assertRaisesRegex(module.ConvergeError, "host alias"):
                module.preflight(SHA, "sc-root; rm -rf /", "wutao", PRODUCTS, MODULES)
            with self.assertRaisesRegex(module.ConvergeError, "principal"):
                module.preflight(SHA, "sc-root", "wutao; whoami", PRODUCTS, MODULES)
            with self.assertRaisesRegex(module.ConvergeError, "product keys"):
                module.preflight(SHA, "sc-root", "wutao", [], MODULES)
            with self.assertRaisesRegex(module.ConvergeError, "module name list"):
                module.preflight(SHA, "sc-root", "wutao", PRODUCTS, ["smart_core; rm -rf /"])

    def test_product_keys_reject_duplicates_and_invalid_keys(self) -> None:
        with self.assertRaisesRegex(module.ConvergeError, "unique"):
            module.parse_product_keys("construction.standard,construction.standard")
        with self.assertRaisesRegex(module.ConvergeError, "product key list"):
            module.parse_product_keys("construction.standard,../../etc/passwd")
        with self.assertRaisesRegex(module.ConvergeError, "product key list"):
            module.parse_product_keys("")

    def test_modules_reject_duplicates_and_invalid_names(self) -> None:
        with self.assertRaisesRegex(module.ConvergeError, "unique"):
            module.parse_modules("smart_core,smart_core")
        with self.assertRaisesRegex(module.ConvergeError, "module name list"):
            module.parse_modules("smart_core,../../etc/passwd")
        self.assertEqual(module.parse_modules(""), [])
        self.assertEqual(module.parse_modules("smart_core"), ["smart_core"])

    def test_remote_command_binds_exact_revision_and_declared_scope(self) -> None:
        command = module.remote_command(
            SHA, "dev", ".env.dev", "sc_demo", "wutao", PRODUCTS, MODULES, dict(TREE_IDS)
        )
        self.assertEqual(
            shlex.split(command),
            [
                "python3",
                "-c",
                module.REMOTE_CONVERGE,
                SHA,
                "dev",
                ".env.dev",
                "sc_demo",
                "wutao",
                ",".join(PRODUCTS),
                ",".join(MODULES),
                "smart_core=" + TREE_IDS["smart_core"],
                module.REMOTE_ROOT,
            ],
        )

    def test_remote_command_declares_no_reuse_without_a_hint(self) -> None:
        command = module.remote_command(
            SHA, "dev", ".env.dev", "sc_demo", "wutao", PRODUCTS, MODULES, {}
        )
        self.assertEqual(shlex.split(command)[-2], "")

    def test_converge_requires_the_upgrade_mode_when_modules_are_declared(self) -> None:
        incomplete = dict(evidence_payload())
        incomplete.pop("upgrade_mode")
        with self.assertRaisesRegex(module.ConvergeError, "declared scope"):
            self._converge((json.dumps(incomplete) + "\n").encode())

    def test_converge_rejects_an_unproven_reuse_claim(self) -> None:
        # A remote that skips the upgrade must prove it against the tree identity
        # the caller declared; a different tree is an unproven claim.
        claim = evidence(upgrade_mode="reused", module_tree_ids={"smart_core": "d" * 40})
        with self.assertRaisesRegex(module.ConvergeError, "unproven"):
            self._converge(claim, reuse_tree_ids=dict(TREE_IDS))
        honest = evidence(upgrade_mode="reused", module_tree_ids=dict(TREE_IDS))
        self.assertEqual(self._converge(honest, reuse_tree_ids=dict(TREE_IDS))["status"], "PASS")

    def test_reuse_hint_requires_an_exact_verified_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "published-face-converge.json"
            payload = {
                "status": "PASS",
                "guard_status": "PASS",
                "remote_root": module.REMOTE_ROOT,
                "database": "sc_demo",
                "upgrade_modules": list(MODULES),
                "module_tree_ids": dict(TREE_IDS),
            }
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(module.reuse_hint(str(report), "sc_demo", MODULES, dict(TREE_IDS)), TREE_IDS)
            self.assertEqual(module.reuse_hint(str(report), "other_db", MODULES, dict(TREE_IDS)), {})
            self.assertEqual(module.reuse_hint(str(report), "sc_demo", [], dict(TREE_IDS)), {})
            self.assertEqual(module.reuse_hint(str(report), "sc_demo", MODULES, {"smart_core": "d" * 40}), {})
            self.assertEqual(module.reuse_hint(str(report), "sc_demo", MODULES, None), {})
            payload["status"] = "FAIL"
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(module.reuse_hint(str(report), "sc_demo", MODULES, dict(TREE_IDS)), {})
            self.assertEqual(module.reuse_hint(str(Path(directory) / "absent.json"), "sc_demo", MODULES, dict(TREE_IDS)), {})
        self.assertEqual(module.reuse_hint("", "sc_demo", [], {}), {})

    def test_module_tree_ids_binds_real_module_trees_or_refuses(self) -> None:
        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(module.module_tree_ids(ROOT, head, []), {})
        resolved = module.module_tree_ids(ROOT, head, ["smart_core"])
        self.assertIsNotNone(resolved)
        self.assertRegex(resolved["smart_core"], r"^[0-9a-f]{40}$")
        self.assertEqual(module.module_tree_ids(ROOT, head, ["smart_core", "absent_module_xyz"]), None)
        self.assertEqual(module.module_tree_ids(ROOT, "f" * 40, ["smart_core"]), None)

    def test_force_upgrade_ignores_a_matching_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text(json.dumps(evidence_payload()), encoding="utf-8")
            captured = {}

            def fake_converge(*args, **kwargs):
                captured["reuse"] = args[8]
                return {"status": "PASS"}

            argv = [
                "daily_runtime_published_face_converge",
                "--expected-sha", SHA, "--ssh-host", "sc-root", "--login", "wutao",
                "--report", str(report), "--repository", str(ROOT),
            ]
            with mock.patch.dict(os.environ, {"CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE": module.CONFIRMATION}), \
                    mock.patch.object(module, "module_tree_ids", return_value=dict(TREE_IDS)), \
                    mock.patch.object(module, "reuse_hint", return_value=dict(TREE_IDS)), \
                    mock.patch.object(module, "converge", side_effect=fake_converge), \
                    mock.patch.object(sys, "argv", argv):
                self.assertEqual(module.main(), 0)
            self.assertEqual(captured["reuse"], TREE_IDS)

            with mock.patch.dict(os.environ, {"CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE": module.CONFIRMATION}), \
                    mock.patch.object(module, "module_tree_ids", return_value=dict(TREE_IDS)), \
                    mock.patch.object(module, "reuse_hint", return_value=dict(TREE_IDS)), \
                    mock.patch.object(module, "converge", side_effect=fake_converge), \
                    mock.patch.object(sys, "argv", argv + ["--force-upgrade"]):
                self.assertEqual(module.main(), 0)
            self.assertEqual(captured["reuse"], {})

    def _converge(
        self, stdout: bytes, returncode: int = 0, reuse_tree_ids: dict[str, str] | None = None
    ) -> dict[str, object]:
        completed = mock.Mock(returncode=returncode, stdout=stdout, stderr=b"")
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE": module.CONFIRMATION}
        ), mock.patch.object(module, "run", return_value=completed):
            return module.converge(
                SHA, "sc-root", "dev", ".env.dev", "sc_demo", "wutao", PRODUCTS, MODULES,
                reuse_tree_ids,
            )

    def test_converge_accepts_matching_evidence(self) -> None:
        result = self._converge(evidence())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["expected_sha"], SHA)

    def test_converge_rejects_face_scope_drift(self) -> None:
        drift = evidence(
            products=[
                product("construction.standard"),
                product("construction.preview", snapshot_released_page_count=89),
            ]
        )
        with self.assertRaisesRegex(module.ConvergeError, "declared scope"):
            self._converge(drift)

    def test_converge_rejects_missing_declared_product(self) -> None:
        narrowed = evidence(
            product_keys=["construction.standard"],
            products=[product("construction.standard")],
        )
        with self.assertRaisesRegex(module.ConvergeError, "declared scope"):
            self._converge(narrowed)

    def test_converge_rejects_guard_not_pass(self) -> None:
        with self.assertRaisesRegex(module.ConvergeError, "did not converge"):
            self._converge(evidence(status="FAIL", reason="RELEASE_GATE_GUARD_NOT_PASS", guard_status="FAIL"))

    def test_converge_rejects_module_scope_drift(self) -> None:
        with self.assertRaisesRegex(module.ConvergeError, "declared scope"):
            self._converge(evidence(modules=["smart_construction_core"]))

    def test_converge_reports_invalid_evidence(self) -> None:
        with self.assertRaisesRegex(module.ConvergeError, "invalid"):
            self._converge(b"", returncode=1)

    def test_converge_surfaces_the_module_upgrade_tail(self) -> None:
        # A bare reason code costs another full diagnostic round trip: the entry
        # must carry the upgrade output that explains the failure.
        failed = evidence(
            status="FAIL",
            reason="MODULE_UPGRADE_FAILED",
            module_upgrade_tail="guard.codex.fast.upgrade: mode=fast blocked the upgrade",
        )
        with self.assertRaisesRegex(module.ConvergeError, "codex.fast.upgrade"):
            self._converge(failed)


COUPLE_TARGET = "daily.runtime.candidate.release:"
FACE_TARGET = "daily.runtime.published_face.converge:"
GUARD_TARGET = "verify.daily_dev.product_menu_release_gate.guard"


class DailyRuntimeCandidateReleaseCouplingTests(unittest.TestCase):
    """The code face and the published face must stay in one governed entry.

    A published face that is not re-frozen from the locked contract silently
    drops declared entries from the gated navigation, so decoupling the two faces
    again would reintroduce exactly that user-visible failure. Guard the coupling
    and the proof step, not merely the entry names.
    """

    def _makefile_text(self) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8") for path in sorted((ROOT / "make").glob("*.mk"))
        )

    def test_candidate_release_entry_owns_both_faces(self) -> None:
        text = self._makefile_text()
        lines = [line for line in text.splitlines() if line.startswith(COUPLE_TARGET)]
        self.assertEqual(len(lines), 1, "daily.runtime.candidate.release must exist exactly once")
        prerequisites = lines[0].split(":", 1)[1]
        self.assertIn("daily.runtime.candidate.bundle_sync", prerequisites)
        self.assertIn("daily.runtime.published_face.converge", prerequisites)
        # The served identity must be declared before the face is frozen, because
        # the face is projected through the module code at that exact revision.
        self.assertIn("daily.runtime.source_revision.align", prerequisites)

    def test_published_face_refresh_upgrades_projection_code_before_freezing(self) -> None:
        recipe = self._recipe(FACE_TARGET)
        self.assertIn("--upgrade-modules", recipe)
        self.assertRegex(recipe, r"--upgrade-modules \"\$\(DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES\)\"")
        self.assertRegex(
            self._makefile_text(),
            r"DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES \?= smart_core",
        )

    def test_face_freeze_declares_the_intentional_module_upgrade(self) -> None:
        # ``guard.codex.fast.upgrade`` blocks an undeclared upgrade, so a freeze that
        # cannot declare its own upgrade intent can never make new projection code
        # live and silently re-freezes the previous contract.
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"CODEX_NEED_UPGRADE": "1"', source)
        self.assertIn('"CODEX_MODULES": ",".join(modules)', source)

    def _recipe(self, target: str) -> str:
        lines = self._makefile_text().splitlines()
        starts = [index for index, line in enumerate(lines) if line.startswith(target)]
        self.assertEqual(len(starts), 1, f"{target} must exist exactly once")
        start = starts[0]
        body = [lines[start]]
        for line in lines[start + 1:]:
            if line.startswith("\t") or not line.strip():
                body.append(line)
                continue
            break
        return "\n".join(body)

    def test_published_face_refresh_is_proved_by_the_release_gate_guard(self) -> None:
        # A refresh without the guard could freeze a face nobody proved, so the
        # proof step must stay inside the refresh entry itself.
        self.assertIn(GUARD_TARGET, self._recipe("release.daily_product_navigation.converge:"))
        self.assertEqual(len([line for line in self._makefile_text().splitlines() if line.startswith(FACE_TARGET)]), 1)


if __name__ == "__main__":
    unittest.main()
