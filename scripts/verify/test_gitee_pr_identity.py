import copy
import io
import json
import unittest
from unittest.mock import Mock
from scripts.ci.gitee_pr_identity import ReadAPI, ReportError, observe, REPOSITORY, REPOSITORY_ID

HEAD = "a" * 40
BASE = "b" * 40
SOURCE = "fix/test"


def rows():
    repo = {"id": REPOSITORY_ID, "full_name": REPOSITORY}
    pr = {"id": 123, "number": 7, "state": "open",
          "head": {"repo": repo, "ref": SOURCE, "sha": HEAD},
          "base": {"repo": repo, "ref": "main", "sha": BASE}}
    return [pr, {"name": SOURCE, "commit": {"sha": HEAD}},
            {"name": "main", "commit": {"sha": BASE}, "protected": True}]


class IdentityTests(unittest.TestCase):
    def run_observe(self, data=None, **kwargs):
        api = Mock()
        api.get.side_effect = data if data is not None else rows() + rows()
        args = dict(number=7, source=SOURCE, head=HEAD, base=BASE, clock=lambda: 100)
        args.update(kwargs)
        return observe(api, **args), api

    def test_two_passes_no_merge_eligibility(self):
        result, api = self.run_observe()
        self.assertTrue(result["pr_identity_verified"])
        self.assertFalse(result["atomic_merge_guarantee"])
        self.assertFalse(result["integration_eligible"])
        self.assertEqual(result["pr_id"], 123)
        self.assertEqual([x.args[0] for x in api.get.call_args_list],
            ["/pulls/7", "/branches/fix%2Ftest", "/branches/main"] * 2)

    def test_closed_and_merged(self):
        for state in ["closed", "merged", None]:
            data = rows(); data[0]["state"] = state
            with self.subTest(state=state), self.assertRaises(ReportError):
                self.run_observe(data)

    def test_fork_or_missing_repository_rejected(self):
        for side in ["head", "base"]:
            for value in [None, {}, {"id": REPOSITORY_ID, "full_name": "other/fork"},
                          {"id": 1, "full_name": REPOSITORY}]:
                data = copy.deepcopy(rows()); data[0][side]["repo"] = value
                with self.subTest(side=side, value=value), self.assertRaises(ReportError):
                    self.run_observe(data)

    def test_head_and_base_changes_rejected(self):
        for side in ["head", "base"]:
            data = copy.deepcopy(rows()); data[0][side]["sha"] = "c" * 40
            with self.subTest(side=side), self.assertRaises(ReportError):
                self.run_observe(data)

    def test_ref_drift_on_second_pass(self):
        for index in [1, 2]:
            data = rows() + rows(); data[3 + index]["commit"]["sha"] = "c" * 40
            with self.subTest(index=index), self.assertRaises(ReportError):
                self.run_observe(data)

    def test_pr_replacement_rejected(self):
        data = rows() + rows(); data[3]["id"] = 124
        with self.assertRaises(ReportError): self.run_observe(data)

    def test_unprotected_main_rejected(self):
        for value in [False, None, 1, "true"]:
            data = rows(); data[2]["protected"] = value
            with self.subTest(value=value), self.assertRaises(ReportError): self.run_observe(data)

    def test_malformed_pr_rejected(self):
        for key, value in [("id", True), ("number", True), ("number", 8), ("id", 0)]:
            data = rows(); data[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ReportError): self.run_observe(data)

    def test_bad_expected_values_do_not_query(self):
        for kw in [dict(number=True), dict(number=0), dict(source="main"), dict(source="fix/../x"),
                   dict(head=BASE), dict(base="0" * 40), dict(head="main")]:
            api = Mock()
            args = dict(number=7, source=SOURCE, head=HEAD, base=BASE); args.update(kw)
            with self.subTest(kw=kw), self.assertRaises(ReportError): observe(api, **args)
            api.get.assert_not_called()

    def test_expired_or_backwards_window(self):
        for end in [99, 191]:
            ticks = iter([100, end])
            with self.subTest(end=end), self.assertRaises(ReportError):
                self.run_observe(clock=lambda: next(ticks))



class MergedIdentityTests(unittest.TestCase):
    def test_historical_snapshot_does_not_read_live_branches_or_authorize_execution(self):
        from scripts.ci.gitee_pr_identity import observe_merged
        from scripts.ci.gitee_formal_executor import verify_snapshot
        row=rows()[0];row.update(state='merged',merged_at='2026-09-23T09:00:00Z')
        p=dict(pr_number=7,source_branch=SOURCE,head_sha=HEAD,base_sha=BASE,
               repository=REPOSITORY,target_branch='main',platform_snapshot={'pr_id':123})
        api=Mock();api.get.side_effect=[row,copy.deepcopy(row)]
        result=observe_merged(api,p)
        self.assertTrue(result['historical_merged'])
        self.assertEqual([c.args[0] for c in api.get.call_args_list],['/pulls/7']*2)
        with self.assertRaises(ValueError): verify_snapshot(p,result)

    def test_merged_identity_rejects_drift_closed_fork_and_wrong_sha(self):
        from scripts.ci.gitee_pr_identity import observe_merged
        p=dict(pr_number=7,source_branch=SOURCE,head_sha=HEAD,base_sha=BASE,platform_snapshot={'pr_id':123})
        good=rows()[0];good.update(state='merged',merged_at='2026-09-23T09:00:00Z')
        variants=[]
        for key,value in [('state','closed'),('state','open'),('merged_at',None),('id',999),('number',8)]:
            r=copy.deepcopy(good);r[key]=value;variants.append(r)
        for side in ['head','base']:
            r=copy.deepcopy(good);r[side]['sha']='c'*40;variants.append(r)
            r=copy.deepcopy(good);r[side]['repo']['id']=999;variants.append(r)
        for r in variants:
            api=Mock();api.get.side_effect=[good,r]
            with self.subTest(row=r),self.assertRaises(ReportError):observe_merged(api,p)


class ReadAPITests(unittest.TestCase):
    def api(self):
        api = object.__new__(ReadAPI)
        api.token = "synthetic-unit-token"
        api.opener = Mock()
        return api

    def test_no_writes_or_arbitrary_endpoints(self):
        api = self.api()
        for path in ["/check-runs", "/pulls/7/merge", "https://example.invalid/", "/branches/..",
                     "/branches/fix/test", "/branches/fix%252Ftest", "/pulls/7?access_token=x"]:
            with self.subTest(path=path), self.assertRaises(ReportError): api.get(path)
        with self.assertRaises(ReportError): api.request("POST", "/check-runs", {})
        api.opener.open.assert_not_called()

    def test_get_only(self):
        api = self.api()
        api.opener.open.return_value = io.BytesIO(b'{"id":123}')
        self.assertEqual(api.get("/pulls/7"), {"id": 123})
        req = api.opener.open.call_args.args[0]
        self.assertEqual(req.get_method(), "GET")
        self.assertIsNone(req.data)
        self.assertNotIn(api.token, req.full_url)

    def test_bounded_shape(self):
        for body in [b"[]", b"not-json", b"x" * 1048577]:
            api = self.api(); api.opener.open.return_value = io.BytesIO(body)
            with self.subTest(size=len(body)), self.assertRaises(ReportError): api.get("/pulls/7")

    def test_transport_error_sanitized(self):
        api = self.api(); api.opener.open.side_effect = OSError("do not expose this")
        with self.assertRaisesRegex(ReportError, "^api_read_failed$"): api.get("/pulls/7")


if __name__ == "__main__": unittest.main()
