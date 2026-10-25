import copy
import io
import unittest
from scripts.verify import test_baseline_contract as baseline


class BaselineContractTest(unittest.TestCase):
    def reports(self):
        return [dict(order=order,status='passed',collected=['a','b'],outcomes={'a':'passed','b':'passed'}) for order in ('forward','reverse','random')]
    def test_same_case_results_across_orders_pass(self):
        reports=self.reports();reports[1]['collected'].reverse()
        self.assertEqual(baseline.compare(reports),2)
    def test_missing_duplicate_failed_skipped_quarantined_cases_do_not_pass(self):
        for mutation in ('empty','duplicate','missing','failed','skipped','started','different','wrong_order'):
            with self.subTest(mutation=mutation):
                reports=self.reports();r=reports[2]
                if mutation=='empty':r['collected']=[]
                elif mutation=='duplicate':r['collected']=['a','a']
                elif mutation=='missing':del r['outcomes']['b']
                elif mutation=='different':r.update(collected=['c'],outcomes={'c':'passed'})
                elif mutation=='wrong_order':r['order']='forward'
                else:r['outcomes']['a']=mutation
                with self.assertRaises(ValueError):baseline.compare(reports)
    def test_insufficient_independent_runs_do_not_pass(self):
        with self.assertRaises(ValueError):baseline.compare(self.reports()[:2])
    def test_subtest_failure_cannot_be_overwritten_by_success(self):
        class Failing(unittest.TestCase):
            def test_case(self):
                with self.subTest(value=1):self.assertEqual(1,2)
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=baseline.Results).run(unittest.defaultTestLoader.loadTestsFromTestCase(Failing))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(list(result.outcomes.values()),['failed_subtest'])
    def test_skipped_case_never_counts_as_passed(self):
        class Skipped(unittest.TestCase):
            @unittest.skip('fixture')
            def test_case(self):pass
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=baseline.Results).run(unittest.defaultTestLoader.loadTestsFromTestCase(Skipped))
        self.assertEqual(list(result.outcomes.values()),['skipped'])
    def test_seed_replays_order_and_preserves_exact_set(self):
        cases=[unittest.FunctionTestCase(lambda:None,description=str(i)) for i in range(3)]
        # FunctionTestCase IDs are duplicated: reject rather than silently collapse.
        with self.assertRaises(ValueError):baseline.ordered(cases,'random',1)
        cases=list(baseline.flatten(unittest.defaultTestLoader.loadTestsFromTestCase(BaselineContractTest)))
        first=[c.id() for c in baseline.ordered(cases,'random',42)]
        self.assertEqual(first,[c.id() for c in baseline.ordered(cases,'random',42)])
        self.assertEqual(set(first),{c.id() for c in cases})
    def test_quarantine_is_not_an_exclusion_escape_hatch(self):
        import json
        data=json.loads(baseline.MANIFEST.read_text());baseline.validate_manifest(data)
        data['quarantine']=['known_bad']
        with self.assertRaises(ValueError):baseline.validate_manifest(data)


    def test_failed_new_run_invalidates_old_passed_receipt(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as root:
            output=Path(root);(output/'receipt.json').write_text('{"status":"passed"}')
            with patch.object(baseline,'source_fingerprint',return_value='a'*64),patch.object(baseline.subprocess,'check_output',return_value='b'*40),patch.object(baseline.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
                self.assertEqual(baseline.main(['--output',str(output)]),1)
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'failed')

    def test_orm_order_validation_checks_actual_order_and_inputs(self):
        cases=['smart_core.tests.test_example:Example.test_a','smart_core.tests.test_example:Example.test_b','smart_core.tests.test_example:Example.test_c']
        reports=[]
        for order in ('forward','reverse','random'):
            execution=cases.copy()
            if order=='reverse':execution.reverse()
            elif order=='random':baseline.random.Random('20261026:odoo.addons.smart_core.tests.test_example.Example').shuffle(execution)
            reports.append(dict(order=order,seed=20261026,profile=baseline.IDENTITY,purpose='test',profile_sha256='c'*64,profile_unchanged=True,status='passed',cases=cases,count=3,execution_order=execution,source_fingerprint='source',source_unchanged=True,fresh_database=True,transient_application_state=True,image_unchanged=True,cleanup='absent',process_status=0,guard_status=0,packages_sha256='a'*64,image_id='sha256:'+'b'*64))
        self.assertEqual(baseline.verify_orm_reports(reports,cases,'source'),3)
        for key,value in [('execution_order',cases),('source_fingerprint','different'),('packages_sha256','missing'),('cleanup','failed'),('cases',cases[:2]),('seed',0),('profile',{})]:
            broken=copy.deepcopy(reports);broken[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):baseline.verify_orm_reports(broken,cases,'source')


    def test_invalid_manifest_invalidates_prior_orm_success(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            output=Path(root); (output/'orm-receipt.json').write_text('{"status":"passed"}')
            with patch.object(baseline,'MANIFEST',output/'missing-manifest.json'):
                self.assertEqual(baseline.main(['--orm','--output',str(output)]),1)
            self.assertEqual(json.loads((output/'orm-receipt.json').read_text())['status'],'failed')


    def test_verify_invalidates_old_pass_on_malformed_receipt(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        for error in (KeyError('reports'),TypeError('bad receipt'),AttributeError('bad shape')):
            with self.subTest(error=type(error).__name__),tempfile.TemporaryDirectory() as root:
                root=Path(root); target=root/'.runtime/test-baseline/baseline.json';target.parent.mkdir(parents=True);target.write_text('{"status":"passed"}')
                with patch.object(baseline,'ROOT',root),patch.object(baseline,'validate_manifest',return_value={}),patch.object(baseline,'verify_local_baseline',side_effect=error):
                    self.assertEqual(baseline.main(['--verify']),1)
                self.assertEqual(json.loads(target.read_text())['status'],'failed')


    def test_child_receipt_tampering_is_rejected_before_consumption(self):
        import tempfile,hashlib
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'child.json';path.write_text('{"status":"passed"}')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(baseline.verified_json(path,digest)['status'],'passed')
            path.write_text('{"status":"failed"}')
            with self.assertRaises(ValueError):baseline.verified_json(path,digest)

if __name__=='__main__':unittest.main()
