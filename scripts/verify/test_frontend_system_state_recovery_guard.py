import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify.frontend_system_state_recovery_guard import validate


class FrontendSystemStateRecoveryGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_sensitive_redirect_query_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "client.ts":
                return value + "\nconst leak = '/login?reason=session_expired&redirect=';"
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("must not expose" in item for item in validate()))

    def test_missing_login_notice_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "LoginView.vue":
                return value.replace("data-session-expired-notice", "data-removed-notice")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("data-session-expired-notice" in item for item in validate()))

    def test_missing_single_redirect_guard_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "sessionExpiredRecovery.ts":
                return value.replace("sessionExpiredRedirectScheduled", "redirectState")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("sessionExpiredRedirectScheduled" in item for item in validate()))


if __name__ == "__main__":
    unittest.main()
