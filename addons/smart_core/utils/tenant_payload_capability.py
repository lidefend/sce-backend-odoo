from __future__ import annotations

import hmac


def maintenance_capability_matches(actual: object, expected: object) -> bool:
    """Compare the signed maintenance capability without timing leakage."""

    expected_value = str(expected or "")
    actual_value = str(actual or "")
    return len(expected_value) == 64 and hmac.compare_digest(
        actual_value, expected_value
    )
