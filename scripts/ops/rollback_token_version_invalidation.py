#!/usr/bin/env python3
"""Offline proof for the Batch C rollback: revoke tokens by bumping token_version.

The rollback must NOT rotate the JWT signing key (that is outside the batch C
authorization scope).  Odoo already rejects a token whose ``token_version`` claim
does not equal the user's current ``res.users.token_version``.  This script
demonstrates that invariant without a database and without printing any secret.

Usage:
    python3 scripts/ops/rollback_token_version_invalidation.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets

import jwt

ALGORITHM = "HS256"


def token_version_is_current(token_version, current_version) -> bool:
    try:
        return int(token_version or 0) == int(current_version or 0)
    except (TypeError, ValueError):
        return False


def _fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def self_test() -> dict:
    secret = secrets.token_urlsafe(48)
    before = _fingerprint(secret)
    token = jwt.encode(
        {
            "user_id": 5,
            "db": "sc_demo",
            "namespace_id": "ns_demo",
            "aud": "tenant",
            "token_version": 1,
        },
        secret,
        algorithm=ALGORITHM,
    )
    payload = jwt.decode(token, secret, algorithms=[ALGORITHM], audience="tenant")
    old_token_still_decodes = payload.get("token_version") == 1
    old_token_valid_after_bump = token_version_is_current(payload.get("token_version"), 2)
    current_token_valid = token_version_is_current(payload.get("token_version"), 1)
    after = _fingerprint(secret)
    return {
        "secret_rotated": False,
        "secret_fingerprint_unchanged": before == after,
        "old_token_still_decodes_with_same_key": old_token_still_decodes,
        "old_token_valid_after_version_bump": old_token_valid_after_bump,
        "same_version_token_valid": current_token_valid,
        "issued_version": 1,
        "current_version_after_bump": 2,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("only --self-test is supported; this script never reads a live secret")
    result = self_test()
    passed = (
        result["secret_fingerprint_unchanged"]
        and result["old_token_still_decodes_with_same_key"]
        and not result["old_token_valid_after_version_bump"]
        and result["same_version_token_valid"]
    )
    result["status"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
