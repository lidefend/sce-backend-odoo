"""Bounded read-only Gitee PR snapshots; never authorizes a merge or ref write."""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from scripts.ci.gitee_ci_checks import API, BASE, ReportError

REPOSITORY = "leegege/sce-product-odoo"
REPOSITORY_ID = 49219677
SHA = re.compile(r"[0-9a-f]{40}")
BRANCH = re.compile(r"(?:feature|fix|refactor|audit|release|codex)/[A-Za-z0-9_./-]+")


def valid_branch(value):
    return (isinstance(value, str) and BRANCH.fullmatch(value) and
            not any(x in value for x in ("..", "//", "@{")) and
            not value.endswith(("/", ".", ".lock")))


class ReadAPI(API):
    # Reuse no-follow owner-only token loading and redirect rejection. Do not
    # broaden the reporter's write API or expose its inherited write methods.
    def request(self, *args, **kwargs):
        raise ReportError("read_only_api")

    def get(self, suffix):
        if not re.fullmatch(r"/(?:pulls/[1-9][0-9]*|branches/(?:main|[A-Za-z0-9_.%/-]+))", suffix):
            raise ReportError("endpoint_rejected")
        if suffix.startswith("/branches/"):
            branch = urllib.parse.unquote(suffix[len("/branches/"):])
            if branch != "main" and not valid_branch(branch):
                raise ReportError("branch_rejected")
            if urllib.parse.quote(branch, safe="") != suffix[len("/branches/"):]:
                raise ReportError("noncanonical_branch")
        req = urllib.request.Request(BASE + suffix, method="GET",
                                     headers={"Authorization": "token " + self.token})
        try:
            with self.opener.open(req, timeout=10) as response:
                data = response.read(1048577)
            if len(data) > 1048576:
                raise ReportError("response_too_large")
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ReportError("invalid_response")
            return value
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ReportError("api_read_failed") from None


def pr_identity(row, *, number, source, head, base):
    if not isinstance(row, dict) or row.get("state") != "open":
        raise ReportError("pr_not_open")
    if type(row.get("number")) is not int or row["number"] != number:
        raise ReportError("pr_number_mismatch")
    if type(row.get("id")) is not int or row["id"] < 1:
        raise ReportError("pr_id_missing")
    for side, ref, sha in (("head", source, head), ("base", "main", base)):
        obj = row.get(side)
        if not isinstance(obj, dict) or obj.get("ref") != ref or obj.get("sha") != sha:
            raise ReportError("pr_ref_mismatch")
        repo = obj.get("repo")
        if (not isinstance(repo, dict) or repo.get("full_name") != REPOSITORY or
                type(repo.get("id")) is not int or repo["id"] != REPOSITORY_ID):
            raise ReportError("pr_repository_mismatch")
    return {"pr_id": row["id"], "pr_number": number, "repository": REPOSITORY,
            "source_branch": source, "target_branch": "main", "head_sha": head, "base_sha": base}


def observe(api, *, number, source, head, base, clock=time.time):
    if (type(number) is not int or number < 1 or not valid_branch(source) or
            not isinstance(head, str) or not SHA.fullmatch(head) or
            not isinstance(base, str) or not SHA.fullmatch(base) or
            head == base or "0" * 40 in (head, base)):
        raise ReportError("invalid_expected_identity")
    started = clock()
    first = None
    for _ in range(2):
        identity = pr_identity(api.get(f"/pulls/{number}"), number=number,
                               source=source, head=head, base=base)
        for ref, sha in ((source, head), ("main", base)):
            row = api.get("/branches/" + urllib.parse.quote(ref, safe=""))
            if (not isinstance(row, dict) or row.get("name") != ref or
                    not isinstance(row.get("commit"), dict) or row["commit"].get("sha") != sha):
                raise ReportError("branch_drift")
            if ref == "main" and row.get("protected") is not True:
                raise ReportError("main_not_protected")
        if first is not None and identity != first:
            raise ReportError("pr_identity_drift")
        first = identity
    ended = clock()
    if ended < started or ended - started > 90:
        raise ReportError("observation_window_exceeded")
    return {**first, "observed_started_at": started, "observed_finished_at": ended,
            "pr_identity_verified": True, "remote_refs_verified": True,
            "atomic_merge_guarantee": False, "integration_eligible": False}



def observe_merged(api, plan):
    """Historical reporting only: never produces an execution snapshot."""
    first = None
    for _ in range(2):
        row = api.get('/pulls/' + str(plan['pr_number']))
        if row.get('state') != 'merged' or not row.get('merged_at'):
            raise ReportError('pr_not_merged')
        # Reuse exact PR/repository/ref/SHA validation, without testing mutable
        # live branch refs: main advances and source branches may be deleted.
        identity = pr_identity({**row, 'state': 'open'}, number=plan['pr_number'],
                               source=plan['source_branch'], head=plan['head_sha'],
                               base=plan['base_sha'])
        if identity['pr_id'] != plan['platform_snapshot']['pr_id']:
            raise ReportError('pr_id_mismatch')
        current = {**identity, 'merged_at': row['merged_at']}
        if first is not None and current != first:
            raise ReportError('merged_identity_drift')
        first = current
    return {**first, 'historical_merged': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    try:
        result = observe(ReadAPI(args.token_file), number=args.pr_number,
                         source=args.source_branch, head=args.head, base=args.base)
        print(json.dumps(result, sort_keys=True))
    except ReportError as exc:
        raise SystemExit("PR identity verification refused: " + str(exc)) from None
    except OSError:
        raise SystemExit("PR identity verification refused: local_credential_unavailable") from None


if __name__ == "__main__":
    main()
