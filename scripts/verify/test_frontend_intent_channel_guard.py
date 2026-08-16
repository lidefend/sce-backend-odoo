#!/usr/bin/env python3
from __future__ import annotations

import unittest

import frontend_intent_channel_guard as guard


ACTIVATION_SERVICE = "frontend/apps/web/src/services/accountActivation.ts"


class FrontendIntentChannelGuardTest(unittest.TestCase):
    def test_repository_paths_satisfy_the_transport_boundary(self):
        violations, found_paths, used_exceptions = guard.scan_api_paths()
        self.assertEqual([], violations)
        self.assertIn(guard.INTENT_ENDPOINT, found_paths)
        self.assertEqual(
            {
                (rel, api_path)
                for rel, api_paths in guard.DIRECT_TRANSPORT_EXCEPTIONS.items()
                for api_path in api_paths
            },
            used_exceptions,
        )

    def test_intent_endpoint_is_the_only_general_frontend_api_path(self):
        self.assertTrue(guard.is_allowed_api_path("frontend/apps/web/src/api/intents.ts", guard.INTENT_ENDPOINT))
        self.assertFalse(guard.is_allowed_api_path("frontend/apps/web/src/api/example.ts", "/api/v1/example"))

    def test_activation_routes_are_bound_to_the_exact_adapter(self):
        for api_path in guard.DIRECT_TRANSPORT_EXCEPTIONS[ACTIVATION_SERVICE]:
            self.assertTrue(guard.is_allowed_api_path(ACTIVATION_SERVICE, api_path))
            self.assertFalse(guard.is_allowed_api_path("frontend/apps/web/src/api/intents.ts", api_path))

    def test_auth_prefix_is_not_wildcard_allowed(self):
        self.assertFalse(
            guard.is_allowed_api_path(ACTIVATION_SERVICE, "/api/v1/auth/password-recovery/complete")
        )
        self.assertFalse(guard.is_allowed_api_path(ACTIVATION_SERVICE, "/api/v1/auth/login"))


if __name__ == "__main__":
    unittest.main()
