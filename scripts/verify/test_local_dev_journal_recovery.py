"""Bounded owned-recovery policy; no database connection."""
import copy
import unittest
from local_dev_journal_recovery import validate_run_ref, validate_snapshot, validate_identity, journal_actor_identity


class RecoveryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.ref = 'P4-JOURNAL-' + self.head + '-' + 'b' * 32
        self.snapshot = dict(id=17, ref=self.ref, creator=40, company=1, journal=3,
                             currency=6, state='draft', posted_before=False, name='/', lines=[
            dict(id=30, move=17, account=49, company=1, currency=6, debit=100, credit=0,
                 balance=100, amount_currency=100, matched_debit=[], matched_credit=[]),
            dict(id=31, move=17, account=48, company=1, currency=6, debit=0, credit=100,
                 balance=-100, amount_currency=-100, matched_debit=[], matched_credit=[]),
        ])

    def test_exact_candidate_and_nonce(self):
        validate_run_ref(self.ref, self.head)
        for ref, head in [(self.ref, 'c'*40), (self.ref+'x', self.head),
                          ('P4-JOURNAL-'+self.head+'-13', self.head), (None, self.head), (self.ref, '')]:
            with self.subTest(ref=ref, head=head), self.assertRaises(AssertionError): validate_run_ref(ref, head)

    def test_balanced_owned_draft(self):
        validate_snapshot(self.snapshot, self.ref)

    def test_clerk_requires_exact_creator(self):
        self.snapshot['creator'] = 1988
        validate_snapshot(self.snapshot, self.ref, 'sc_demo_accounting_user', 1988)
        with self.assertRaises(AssertionError): validate_snapshot(self.snapshot, self.ref)
        self.snapshot['creator'] = 40
        with self.assertRaises(AssertionError):
            validate_snapshot(self.snapshot, self.ref, 'sc_demo_accounting_user', 1988)

    def test_unknown_or_mismatched_actor_rejected(self):
        for login, uid in [('sc_demo_accounting_read', 1987), ('sc_demo_accounting_user', 40),
                           ('demo_full', 1988), ('sc_demo_accounting_user', 1), ('demo_full', True)]:
            with self.subTest(login=login, uid=uid), self.assertRaises(AssertionError):
                journal_actor_identity(login, uid)

    def test_prior_zero_amount_defect_still_cleanable(self):
        for line in self.snapshot['lines']:
            for key in ('debit', 'credit', 'balance', 'amount_currency'): line[key] = 0
        validate_snapshot(self.snapshot, self.ref)

    def test_foreign_or_posted_record_rejected(self):
        for key, value in [('ref', 'another'), ('creator', 1), ('company', 2), ('journal', 4),
                           ('currency', 1), ('state', 'posted'), ('posted_before', True), ('name', 'ENTRY/17'), ('id', False)]:
            snapshot = copy.deepcopy(self.snapshot); snapshot[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): validate_snapshot(snapshot, self.ref)

    def test_foreign_or_reconciled_lines_rejected(self):
        for key, value in [('id', False), ('move', 19), ('account', 50), ('company', 2), ('currency', 1),
                           ('matched_debit', [1]), ('matched_credit', [1]), ('debit', 200), ('credit', 100),
                           ('balance', -100), ('amount_currency', '100')]:
            snapshot = copy.deepcopy(self.snapshot); snapshot['lines'][0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): validate_snapshot(snapshot, self.ref)

    def test_unexpected_line_cardinality_rejected(self):
        for lines in [[], self.snapshot['lines'][:1], self.snapshot['lines']*2,
                      [self.snapshot['lines'][0], self.snapshot['lines'][0]]]:
            snapshot = copy.deepcopy(self.snapshot); snapshot['lines'] = lines
            with self.subTest(lines=lines), self.assertRaises(AssertionError): validate_snapshot(snapshot, self.ref)


class IdentityTests(unittest.TestCase):
    def test_hidden_or_marker_changed_cannot_mean_absent(self):
        for visible, audited, known in [([], [17], None), ([], [], [17]), ([18], [18], [17]),
                                        ([17,18], [17,18], None)]:
            with self.subTest(visible=visible, audited=audited, known=known), self.assertRaises(AssertionError):
                validate_identity(visible, audited, known)
        validate_identity([], [], [])
        validate_identity([17], [17], [17])


class WrapperLifecycleTests(unittest.TestCase):
    def run_wrapper(self, failure, actor="demo_full", uid=40):
        import os, subprocess, tempfile, json
        from pathlib import Path
        wrapper = Path(__file__).with_name('local_dev_workspace_feedback.sh').resolve()
        with tempfile.TemporaryDirectory(dir='.runtime', prefix='journal-wrapper-unit-') as directory:
            root=Path(directory).resolve(); binpath=root/'bin'; binpath.mkdir()
            events=root/'events'
            fake = r'''#!/usr/bin/env python3
import os,json,sys
from pathlib import Path
kind=Path(sys.argv[0]).name
if kind=='make' and ('ENV_FILE='+os.environ['TEST_ENVFILE']) not in sys.argv: sys.exit(2)
mode=os.environ.get('SC_RUNTIME_JOURNAL_RECOVERY') if kind=='make' else 'browser'
root=Path(os.environ['SC_RUNTIME_JOURNAL_EVIDENCE']); root.mkdir(parents=True,exist_ok=True)
with open(os.environ['TEST_EVENTS'],'a') as f: f.write(mode+'\n')
failure=os.environ['TEST_FAILURE']
if mode=='browser':
    if failure!='missing_report':
        (root/'report.json').write_text(json.dumps({'passed':False,'browserPassed':failure!='browser'}))
    sys.exit(1 if failure in ('browser','missing_report') else 0)
if failure==mode: sys.exit(1)
if mode=='cleanup' and failure=='missing_receipt': sys.exit(0)
receipt={'mode':mode,'ref':os.environ['SC_RUNTIME_JOURNAL_REF'],'head':os.environ['CANDIDATE_GIT_HEAD'],
         'record_id':None,'line_ids':[],'passed':True,'committed':True,'absent':True,'rolled_back':True,
         'actor':os.environ['SC_FEEDBACK_ACTOR'],'uid':int(os.environ['SC_FEEDBACK_EXPECTED_UID'])}
if failure=='wrong_actor' and mode=='preflight': receipt.update(actor='demo_full',uid=40)
print('JOURNAL_RECOVERY '+json.dumps(receipt))
'''
            for name in ('make','node'):
                p=binpath/name;p.write_text(fake);p.chmod(0o755)
            envfile=root/'env'; envfile.write_text('COMPOSE_PROJECT_NAME=sc-local-dev\nDB_NAME=sc_dev_demo\nNGINX_PORT=18081\nSC_DEMO_USER_PASSWORD=synthetic-test-only\nENV_FILE=.env.dev\n')
            env=dict(os.environ, PATH=str(binpath)+os.pathsep+os.environ['PATH'], ENV_FILE=str(envfile),
                     SC_FEEDBACK_SCOPE='journal-save',SC_FEEDBACK_ACTOR=actor,SC_FEEDBACK_EXPECTED_UID=str(uid),CANDIDATE_GIT_HEAD='a'*40,
                     CONFIRM_LOCAL_DEV_JOURNAL_SAVE='CREATE_READBACK_CLEANUP_ONE_DRAFT',
                     SC_LOCAL_DEV_WRITE_LEASE_TOKEN='synthetic-unit-lease',TEST_EVENTS=str(events),TEST_ENVFILE=str(envfile),TEST_FAILURE=failure)
            result=subprocess.run(['bash',str(wrapper)],cwd=root,env=env,capture_output=True,text=True)
            order=events.read_text().splitlines()
            reports=list(root.glob('.runtime/**/report.json'))
            report=json.loads(reports[0].read_text()) if reports else {}
            return result.returncode,order,report

    def test_success_requires_independent_verification(self):
        status,order,report=self.run_wrapper('')
        self.assertEqual(status,0)
        self.assertEqual(order,['preflight','browser','cleanup','verify_absent'])
        self.assertTrue(report['passed'])

    def test_clerk_identity_observed_before_browser(self):
        status,order,report=self.run_wrapper('', 'sc_demo_accounting_user', 1988)
        self.assertEqual(status,0)
        self.assertEqual(order,['preflight','browser','cleanup','verify_absent'])
        self.assertTrue(report['passed'])
        status,order,report=self.run_wrapper('wrong_actor', 'sc_demo_accounting_user', 1988)
        self.assertNotEqual(status,0)
        self.assertEqual(order,['preflight'])

    def test_browser_failure_or_missing_report_still_cleans(self):
        for failure in ('browser','missing_report'):
            status,order,report=self.run_wrapper(failure)
            self.assertNotEqual(status,0)
            self.assertEqual(order,['preflight','browser','cleanup','verify_absent'])
            self.assertFalse(report['passed'])
            self.assertTrue(report['cleanup']['absent'])

    def test_cleanup_or_receipt_or_verification_failure_never_passes(self):
        for failure in ('cleanup','missing_receipt','verify_absent'):
            status,order,report=self.run_wrapper(failure)
            self.assertNotEqual(status,0)
            self.assertIn('cleanup',order)
            self.assertFalse(report['passed'])

    def test_preflight_failure_never_launches_browser(self):
        status,order,report=self.run_wrapper('preflight')
        self.assertNotEqual(status,0)
        self.assertEqual(order,['preflight'])


if __name__ == '__main__': unittest.main()
