import hashlib
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.ops import gitee_ci_publication_gate as gate
from scripts.ops.gitee_ci_rotate_secret import replacement


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.file = self.root/'artifacts/gitee-temporary-integration/scan.json'
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b'{}')
        self.data = {'head': 'a'*40, 'main': 'b'*40, 'observed_at': time.time(),
                     'platform': {'repository':'leegege/sce-product-odoo','hook_id':2106026,
                                  'events':['push','pull_request'],'active':True,
                                  'platform_mirrors':[],'gitee_go_enabled':False,
                                  'signing_secret_rotated':True},
                     'public_scope_authorized':True,
                     'evidence_files':[{'path':str(self.file),'sha256':hashlib.sha256(b'{}').hexdigest()}]}

    def verify(self):
        with patch.object(gate, 'ROOT', self.root):
            gate.verify_receipt(self.data,'a'*40,'b'*40)

    def test_valid(self): self.verify()

    def test_stale(self):
        self.data['observed_at'] -= 3601
        with self.assertRaises(ValueError): self.verify()

    def test_future(self):
        self.data['observed_at'] += 600
        with self.assertRaises(ValueError): self.verify()

    def test_head_drift(self):
        self.data['head']='c'*40
        with self.assertRaises(ValueError): self.verify()

    def test_automation_not_isolated(self):
        self.data['platform']['platform_mirrors']=['unexpected']
        with self.assertRaises(ValueError): self.verify()

    def test_evidence_tamper(self):
        self.file.write_bytes(b'changed')
        with self.assertRaises(ValueError): self.verify()

    def test_credential_path_rejected(self):
        self.data['evidence_files'][0]['path']=str(self.root/'.git/key')
        with self.assertRaises(ValueError): self.verify()

    def test_rotation_preserves_other_configuration(self):
        self.assertEqual(replacement('OTHER=x\nGITEE_WEBHOOK_SECRET=old\n','f'*64),
                         'OTHER=x\nGITEE_WEBHOOK_SECRET='+'f'*64+'\n')

    def test_rotation_ambiguity_rejected(self):
        for data in ['', 'GITEE_WEBHOOK_SECRET=a\nGITEE_WEBHOOK_SECRET=b\n']:
            with self.assertRaises(ValueError): replacement(data,'f'*64)

    def test_rotation_injection_rejected(self):
        with self.assertRaises(ValueError): replacement('GITEE_WEBHOOK_SECRET=x\n','f'*64+'\nX=1')
