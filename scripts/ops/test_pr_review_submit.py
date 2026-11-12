from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ops.pr_review_submit import (
    CONFIRMATION,
    REQUIRED_CHECKS,
    ReviewError,
    load_reviewer_token,
    submit_review,
)


HEAD = "a" * 40
MAIN = "b" * 40


class FakeClient:
    def __init__(self, *, reviewer="review-bot", author="author", head=HEAD, checks=None):
        self.calls = []
        self.reviewer = reviewer
        self.author = author
        self.head = head
        self.checks = checks

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path == "/user":
            return {"login": self.reviewer}
        if method == "GET" and path == "/repos/owner/repo/pulls/878":
            return {
                "state": "open",
                "draft": False,
                "user": {"login": self.author},
                "head": {"sha": self.head},
                "base": {"sha": MAIN, "ref": "main"},
            }
        if method == "GET" and path == f"/repos/owner/repo/commits/{HEAD}/check-runs?per_page=100":
            if self.checks is not None:
                return {"check_runs": self.checks}
            return {
                "check_runs": [
                    {"name": name, "status": "completed", "conclusion": "success", "started_at": "2026-11-13T00:00:00Z"}
                    for name in REQUIRED_CHECKS
                ]
            }
        if method == "GET" and path == "/repos/owner/repo/pulls/878/reviews?per_page=100":
            return []
        if method == "POST" and path == "/repos/owner/repo/pulls/878/reviews":
            return {
                "id": 901,
                "user": {"login": self.reviewer},
                "state": "APPROVED",
                "commit_id": payload["commit_id"],
            }
        raise AssertionError((method, path, payload))


def review_kwargs(**overrides):
    values = {
        "repository": "owner/repo",
        "pr_number": 878,
        "expected_head": HEAD,
        "expected_main": MAIN,
        "expected_login": "review-bot",
        "action": "APPROVE",
        "body": "Independent review passed.",
        "require_ci": True,
        "apply": False,
        "confirmation": "",
    }
    values.update(overrides)
    return values


class ReviewerCredentialTest(unittest.TestCase):
    def test_loads_named_reviewer_token_from_private_config(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            config.chmod(0o700)
            hosts = config / "hosts.yml"
            hosts.write_text(
                "github.com:\n"
                "  user: other\n"
                "  users:\n"
                "    review-bot:\n"
                "      oauth_token: reviewer-token\n",
                encoding="utf-8",
            )
            hosts.chmod(0o600)
            self.assertEqual(load_reviewer_token(config, "Review-Bot"), "reviewer-token")

    def test_rejects_config_with_group_access(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            config.chmod(0o755)
            hosts = config / "hosts.yml"
            hosts.write_text("github.com:\n  oauth_token: token\n", encoding="utf-8")
            hosts.chmod(0o600)
            with self.assertRaisesRegex(ReviewError, "group or other access"):
                load_reviewer_token(config, "review-bot")


class SubmitReviewTest(unittest.TestCase):
    def test_dry_run_validates_without_posting(self):
        client = FakeClient()
        result = submit_review(client, **review_kwargs())
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertEqual(result["review_id"], 0)
        self.assertFalse(any(method == "POST" for method, _path, _payload in client.calls))

    def test_approve_posts_exact_head(self):
        client = FakeClient()
        result = submit_review(
            client,
            **review_kwargs(apply=True, confirmation=CONFIRMATION),
        )
        self.assertEqual(result["status"], "PASS")
        post = [row for row in client.calls if row[0] == "POST"]
        self.assertEqual(len(post), 1)
        self.assertEqual(post[0][2]["commit_id"], HEAD)
        self.assertEqual(post[0][2]["event"], "APPROVE")

    def test_rejects_author_self_approval(self):
        client = FakeClient(reviewer="author", author="author")
        with self.assertRaisesRegex(ReviewError, "differ from the PR author"):
            submit_review(client, **review_kwargs(expected_login="author"))

    def test_rejects_head_mismatch(self):
        client = FakeClient(head="c" * 40)
        with self.assertRaisesRegex(ReviewError, "does not match expected head"):
            submit_review(client, **review_kwargs())

    def test_rejects_missing_required_check(self):
        client = FakeClient(
            checks=[
                {"name": name, "status": "completed", "conclusion": "success", "started_at": "2026-11-13T00:00:00Z"}
                for name in REQUIRED_CHECKS[:-1]
            ]
        )
        with self.assertRaisesRegex(ReviewError, "required checks are not successful"):
            submit_review(client, **review_kwargs())

    def test_apply_requires_confirmation(self):
        client = FakeClient()
        with self.assertRaisesRegex(ReviewError, "requires confirmation"):
            submit_review(client, **review_kwargs(apply=True))

    def test_existing_exact_head_approval_is_idempotent(self):
        client = FakeClient()
        original = client.request

        def request(method, path, payload=None):
            if method == "GET" and path.endswith("/reviews?per_page=100"):
                client.calls.append((method, path, payload))
                return [
                    {
                        "id": 777,
                        "user": {"login": "review-bot"},
                        "state": "APPROVED",
                        "commit_id": HEAD,
                    }
                ]
            return original(method, path, payload)

        client.request = request
        result = submit_review(
            client,
            **review_kwargs(apply=True, confirmation=CONFIRMATION),
        )
        self.assertTrue(result["idempotent"])
        self.assertEqual(result["review_id"], 777)
        self.assertFalse(any(method == "POST" for method, _path, _payload in client.calls))


if __name__ == "__main__":
    unittest.main()
