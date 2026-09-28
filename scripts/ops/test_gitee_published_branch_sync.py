import tempfile
import unittest
from pathlib import Path
from gitee_published_branch_sync import git, out, sync, CONFIRM, CONFIRM_UNPUBLISHED, sync_local_main

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
    def unpublish(self):
        git(self.root,"push","gitee-mirror","--delete","fix/test")
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror","refs/heads/fix/test"),"")
    def run_sync_unpublished(self, **kw):
        return sync(self.root,"fix/test",self.head,self.main,allowed_urls={self.remote},allow_absent=True,**kw)
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

    def test_unpublished_appends_main_and_stays_absent(self):
        self.unpublish()
        r=self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED)
        self.assertEqual(r["mode"],"unpublished")
        self.assertEqual(out(self.root,"show","-s","--format=%P",r["head"]),self.head+" "+self.main)
        self.assertEqual(out(self.root,"status","--porcelain"),"")
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror","refs/heads/fix/test"),"")
        self.assertTrue(Path(r["recovery_bundle"]).exists())
    def test_unpublished_preview_leaves_candidate(self):
        self.unpublish()
        self.assertEqual(self.run_sync_unpublished()["writes"],0)
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
    def test_unpublished_dirty_refused(self):
        self.unpublish()
        (self.root/"dirty").write_text("x")
        with self.assertRaisesRegex(RuntimeError,"clean"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED)
    def test_unpublished_main_drift_refused(self):
        self.unpublish()
        self.main="a"*40
        with self.assertRaisesRegex(RuntimeError,"drift"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED)
    def test_unpublished_existing_remote_branch_refused(self):
        with self.assertRaisesRegex(RuntimeError,"already exists"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED)
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror","refs/heads/fix/test").split()[0],self.head)
    def test_unpublished_conflict_restores(self):
        self.unpublish()
        git(self.root,"switch","main")
        self.main=self.commit("topic","conflict")
        git(self.root,"push","gitee-mirror","main")
        git(self.root,"switch","fix/test")
        with self.assertRaisesRegex(RuntimeError,"conflict"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED)
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
        self.assertEqual(out(self.root,"status","--porcelain"),"")
    def test_unpublished_confirmation_required(self):
        self.unpublish()
        with self.assertRaisesRegex(RuntimeError,"confirmation"):
            self.run_sync_unpublished(apply=True)
    def test_unpublished_rejects_remote_head_pin(self):
        self.unpublish()
        with self.assertRaisesRegex(RuntimeError,"cannot pin"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM_UNPUBLISHED,remote_head=self.head)
    def test_published_confirmation_rejected_in_unpublished_mode(self):
        self.unpublish()
        with self.assertRaisesRegex(RuntimeError,"confirmation"):
            self.run_sync_unpublished(apply=True,confirm=CONFIRM)

class LocalMainTests(unittest.TestCase):
    setUp = SyncTests.setUp
    commit = SyncTests.commit
    def local_sync(self, **kw):
        old = out(self.root, "rev-parse", "main")
        return sync_local_main(self.root, "fix/test", self.head, self.main, old,
                               allowed_urls={self.remote}, **kw)
    def advance_remote(self):
        old = self.main
        git(self.root, "switch", "main")
        self.main = self.commit("next", "next")
        git(self.root, "push", "gitee-mirror", "main")
        git(self.root, "switch", "fix/test")
        git(self.root, "update-ref", "refs/heads/main", old)
        return old
    def test_local_main_preview_and_apply(self):
        old = self.advance_remote()
        self.assertEqual(self.local_sync()["writes"], 0)
        self.assertEqual(out(self.root, "rev-parse", "main"), old)
        r = self.local_sync(apply=True, confirm="FAST_FORWARD_EXACT_LOCAL_GITEE_MAIN")
        self.assertTrue(r["changed"])
        self.assertEqual(out(self.root, "rev-parse", "main"), self.main)
        self.assertEqual(out(self.root, "rev-parse", "HEAD"), self.head)
        self.assertEqual(out(self.root, "status", "--porcelain"), "")
    def test_local_main_divergence_refused(self):
        git(self.root, "update-ref", "refs/heads/main", self.head)
        with self.assertRaisesRegex(RuntimeError, "fast-forward"):
            self.local_sync(apply=True, confirm="FAST_FORWARD_EXACT_LOCAL_GITEE_MAIN")
    def test_local_main_occupied_refused(self):
        git(self.root, "worktree", "add", str(Path(self.tmp.name)/"other"), "main")
        with self.assertRaisesRegex(RuntimeError, "occupied"):
            self.local_sync()
    def test_local_main_dirty_refused(self):
        (self.root/"dirty").write_text("x")
        with self.assertRaisesRegex(RuntimeError, "clean"):
            self.local_sync()
    def test_local_main_drift_refused(self):
        with self.assertRaisesRegex(RuntimeError, "local main drift"):
            sync_local_main(self.root,"fix/test",self.head,self.main,self.head,allowed_urls={self.remote})
    def test_local_main_confirmation_refused(self):
        with self.assertRaisesRegex(RuntimeError, "confirmation"):
            self.local_sync(apply=True, confirm=CONFIRM)
    def test_local_main_remote_drift_refused(self):
        self.main = "a"*40
        with self.assertRaisesRegex(RuntimeError, "remote identity drift"):
            self.local_sync()

    def test_symbolic_main_never_rewrites_other_topic(self):
        old = self.advance_remote()
        git(self.root, "branch", "fix/retained", old)
        git(self.root, "symbolic-ref", "refs/heads/main", "refs/heads/fix/retained")
        with self.assertRaisesRegex(RuntimeError, "symbolic"):
            self.local_sync(apply=True, confirm="FAST_FORWARD_EXACT_LOCAL_GITEE_MAIN")
        self.assertEqual(out(self.root,"rev-parse","fix/retained"),old)
        self.assertEqual(out(self.root,"symbolic-ref","refs/heads/main"),"refs/heads/fix/retained")
        self.assertEqual(out(self.root,"rev-parse","HEAD"),self.head)
        self.assertEqual(out(self.root,"status","--porcelain"),"")

if __name__=="__main__": unittest.main()
