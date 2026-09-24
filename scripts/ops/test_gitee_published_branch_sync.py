import tempfile
import unittest
from pathlib import Path
from gitee_published_branch_sync import git, out, sync, CONFIRM

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/"repo"
        self.root.mkdir()
        self.remote = str(Path(self.tmp.name)/"remote.git")
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        self.commit("base", "base")
        git(self.root, "init", "--bare", self.remote)
        git(self.root, "remote", "add", "gitee-mirror", self.remote)
        git(self.root, "push", "gitee-mirror", "main")
        git(self.root, "switch", "-c", "fix/test")
        self.head = self.commit("topic", "topic")
        git(self.root, "push", "gitee-mirror", "fix/test")
        git(self.root, "switch", "main")
        self.main = self.commit("upstream", "upstream")
        git(self.root, "push", "gitee-mirror", "main")
        git(self.root, "switch", "fix/test")
    def commit(self, file, content):
        (self.root/file).write_text(content)
        git(self.root, "add", file)
        git(self.root, "commit", "-m", content)
        return out(self.root, "rev-parse", "HEAD")
    def run_sync(self, **kw):
        return sync(self.root,"fix/test",self.head,self.main,allowed_urls={self.remote},**kw)
    def test_append_without_rewrite_or_push(self):
        r=self.run_sync(apply=True,confirm=CONFIRM)
        self.assertEqual(out(self.root,"show","-s","--format=%P",r["head"]),self.head+" "+self.main)
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror","refs/heads/fix/test").split()[0],self.head)
        self.assertTrue(Path(r["recovery_bundle"]).exists())
    def test_preview_leaves_candidate(self):
        self.assertEqual(self.run_sync()["writes"],0)
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
    def test_dirty_refused(self):
        (self.root/"dirty").write_text("x")
        with self.assertRaisesRegex(RuntimeError,"clean"): self.run_sync(apply=True,confirm=CONFIRM)
    def test_remote_drift_refused(self):
        self.main="a"*40
        with self.assertRaisesRegex(RuntimeError,"drift"): self.run_sync(apply=True,confirm=CONFIRM)
    def test_conflict_restores(self):
        git(self.root,"switch","main")
        self.main=self.commit("topic","conflict")
        git(self.root,"push","gitee-mirror","main")
        git(self.root,"switch","fix/test")
        with self.assertRaisesRegex(RuntimeError,"conflict"): self.run_sync(apply=True,confirm=CONFIRM)
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
        self.assertEqual(out(self.root,"status","--porcelain"),"")
    def test_local_unpublished_append_keeps_remote_identity(self):
        remote_head=self.head
        self.head=self.commit("extra", "extra")
        r=self.run_sync(apply=True,confirm=CONFIRM,remote_head=remote_head)
        self.assertEqual(out(self.root,"show","-s","--format=%P",r["head"]),self.head+" "+self.main)
    def test_confirmation_required(self):
        with self.assertRaisesRegex(RuntimeError,"confirmation"): self.run_sync(apply=True)

if __name__=="__main__": unittest.main()
