import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from scripts.ops.gitee_formal_pr import ensure, select

class PRTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ledger=Path(self.tmp.name)/'ledger'
        self.api=Mock();self.api.call.return_value=[];self.reader=Mock()
        self.reader.get.side_effect=[{'commit':{'sha':'a'*40}},{'commit':{'sha':'b'*40},'protected':True}]
    def test_preview_never_creates(self):
        result=ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger)
        self.assertEqual(result['writes'],0);self.assertFalse(self.ledger.exists());self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')
    def test_changed_sha_stops_before_create(self):
        with self.assertRaises(ValueError):ensure(self.api,self.reader,'c'*40,'b'*40,self.ledger,True)
        self.api.call.assert_not_called()
    def test_uncertain_create_has_durable_no_retry_marker(self):
        self.api.call.side_effect=[[],RuntimeError('lost response')]
        with self.assertRaises(RuntimeError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.assertTrue(self.ledger.exists())
    @patch('scripts.ops.gitee_formal_pr.os.fsync',side_effect=OSError('disk failure'))
    def test_failed_ledger_sync_prevents_post(self,sync):
        with self.assertRaises(OSError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')

    def test_previous_uncertain_create_not_posted_again(self):
        self.ledger.write_text('creating')
        with self.assertRaises(ValueError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')
    def test_incomplete_listing_rejected(self):
        with self.assertRaises(ValueError):select([{}]*100)

if __name__=='__main__':unittest.main()
