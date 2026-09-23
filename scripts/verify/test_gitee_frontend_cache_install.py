import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.ops.gitee_frontend_cache_install import install,digest,key,trusted_parent

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'cache'
        self.data=b'fixture public dependency archive'
        self.m={'status':'prepared','dependency_inputs':{'files':{}},'archive_sha256':digest(self.data)}
        self.m['dependency_key']=key(self.m['dependency_inputs'])
    def run_install(self):
        with patch('scripts.ops.gitee_frontend_cache_install.os.geteuid',return_value=0),patch('scripts.ops.gitee_frontend_cache_install.trusted_parent'):
            return install(self.m,self.data,digest(self.data),self.root)
    def test_append_and_idempotent_readback(self):
        self.assertEqual(self.run_install()['status'],'installed')
        self.assertEqual(self.run_install()['status'],'already_installed')
        p=self.root/self.m['dependency_key']/'dependencies.tar.gz'
        self.assertEqual(p.read_bytes(),self.data);self.assertEqual(p.stat().st_mode&0o777,0o644)
    def test_digest_mismatch_writes_nothing(self):
        self.m['archive_sha256']='0'*64
        with self.assertRaises(ValueError):self.run_install()
        self.assertFalse(self.root.exists())
    def test_input_identity_rejected(self):
        self.m['dependency_key']='0'*64
        with self.assertRaises(ValueError):self.run_install()
        self.assertFalse(self.root.exists())
    def test_existing_changed_cache_not_overwritten(self):
        self.run_install();p=self.root/self.m['dependency_key']/'dependencies.tar.gz';p.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.run_install()
        self.assertEqual(p.read_bytes(),b'changed')
    def test_existing_symlink_rejected(self):
        self.root.mkdir();(self.root/self.m['dependency_key']).symlink_to('/tmp')
        with self.assertRaises(ValueError):self.run_install()
    def test_broken_parent_symlink_rejected(self):
        self.root.symlink_to('absent')
        with self.assertRaises(ValueError):trusted_parent(self.root)
    def test_program_does_not_extract_archive(self):
        result=self.run_install();self.assertFalse(result['services_changed'])
        self.assertEqual(len(list((self.root/self.m['dependency_key']).iterdir())),2)

if __name__=='__main__':unittest.main()
