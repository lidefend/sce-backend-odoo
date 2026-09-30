import tempfile
import unittest
from pathlib import Path
from gitee_published_branch_sync import git, out, sync, CONFIRM, CONFIRM_UNPUBLISHED, sync_local_main, discard_local, retain_main_only

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

class DiscardLocalTests(unittest.TestCase):
    setUp = SyncTests.setUp
    commit = SyncTests.commit
    def discard(self, **kw):
        target_head = self.head
        git(self.root,"switch","-c","fix/cleanup",self.main)
        args = dict(root=self.root, branch="fix/cleanup",head=self.main,main=self.main,
                    target="fix/test",target_head=target_head,
                    bundle=str(Path(self.tmp.name)/"recovery.bundle"))
        args.update(kw)
        return discard_local(**args)
    def test_abandoned_local_ref_deleted_remote_and_worktree_preserved(self):
        result=self.discard(apply=True,confirm="DISCARD_EXACT_LOCAL_BRANCH_KEEP_RECOVERY")
        self.assertEqual(result["remote_writes"],0)
        self.assertNotEqual(git(self.root,"show-ref","--verify","refs/heads/fix/test",check=False).returncode,0)
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror","refs/heads/fix/test").split()[0],self.head)
        recovered=Path(self.tmp.name)/"recovered"
        git(self.root,"clone","--branch","fix/test",result["bundle"],str(recovered))
        self.assertEqual(out(recovered,"rev-parse","fix/test"),self.head)
        self.assertEqual(out(self.root,"status","--porcelain"),"")
    def test_preview_retains_ref_and_no_bundle(self):
        result=self.discard()
        self.assertEqual(result["writes"],0)
        self.assertFalse(Path(result["bundle"]).exists())
        self.assertEqual(out(self.root,"rev-parse","fix/test"),self.head)
    def test_wrong_confirmation_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"confirmation"):
            self.discard(apply=True,confirm=CONFIRM)
    def test_drift_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"drift"):
            self.discard(target_head=self.main)
    def test_protected_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"unprotected"):
            self.discard(target="main")
    def test_occupied_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"occupied"):
            self.discard(target="fix/cleanup",target_head=self.main)
    def test_dirty_refuses(self):
        (self.root/"dirty").write_text("x")
        with self.assertRaisesRegex(RuntimeError,"clean"):
            self.discard()
    def test_foreign_bundle_refuses(self):
        bundle=Path(self.tmp.name)/"other.bundle"
        git(self.root,"bundle","create",str(bundle),"main")
        with self.assertRaisesRegex(RuntimeError,"bundle target mismatch"):
            self.discard(bundle=str(bundle),apply=True,confirm="DISCARD_EXACT_LOCAL_BRANCH_KEEP_RECOVERY")
    def test_symbolic_refuses(self):
        git(self.root,"symbolic-ref","refs/heads/fix/alias","refs/heads/fix/test")
        with self.assertRaisesRegex(RuntimeError,"symbolic"):
            self.discard(target="fix/alias")
    def test_internal_archive_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"external"):
            self.discard(bundle=str(self.root/"recovery.bundle"))

    def test_incremental_bundle_refuses_before_deletion(self):
        bundle=Path(self.tmp.name)/"incremental.bundle"
        base=out(self.root,"merge-base","main","fix/test")
        git(self.root,"bundle","create",str(bundle),"refs/heads/fix/test","^"+base)
        with self.assertRaisesRegex(RuntimeError,"incremental"):
            self.discard(bundle=str(bundle),apply=True,confirm="DISCARD_EXACT_LOCAL_BRANCH_KEEP_RECOVERY")
        self.assertEqual(out(self.root,"rev-parse","fix/test"),self.head)

class MainOnlyTests(unittest.TestCase):
    setUp = SyncTests.setUp
    commit = SyncTests.commit
    def plan(self, **kw):
        args=dict(root=self.root,branch="fix/test",head=self.head,main=self.main,
                  bundle=str(Path(self.tmp.name)/"all.bundle"),allowed_urls={self.remote})
        args.update(kw)
        return retain_main_only(**args)
    def apply(self, **kw):
        plan=self.plan()
        return self.plan(apply=True,plan_sha256=plan['plan_sha256'],confirm="RETAIN_EXACT_MAIN_ONLY_WITH_RECOVERY",**kw)
    def test_keep_only_main_and_restore_every_branch(self):
        git(self.root,"branch","release/old",self.head)
        linked=Path(self.tmp.name)/"repo-old"
        git(self.root,"worktree","add","--detach",str(linked),self.main)
        before=out(self.root,"ls-remote","gitee-mirror")
        r=self.apply()
        self.assertEqual(out(self.root,"branch","--show-current"),"main")
        self.assertEqual(out(self.root,"for-each-ref","--format=%(refname)","refs/heads"),"refs/heads/main")
        self.assertFalse(linked.exists())
        self.assertEqual(out(self.root,"ls-remote","gitee-mirror"),before)
        restored=Path(self.tmp.name)/"restored"
        git(self.root,"clone","--bare",r['bundle'],str(restored))
        self.assertEqual(out(restored,"rev-parse","refs/heads/release/old"),self.head)
    def test_preview_no_ref_or_worktree_changes(self):
        p=self.plan();self.assertEqual(p['writes'],0)
        self.assertEqual(out(self.root,"branch","--show-current"),"fix/test")
        self.assertFalse((Path(self.tmp.name)/"all.bundle").exists())
    def test_manifest_drift_denied(self):
        p=self.plan();git(self.root,"branch","fix/new",self.main)
        with self.assertRaisesRegex(RuntimeError,"reviewed"):
            self.plan(apply=True,plan_sha256=p['plan_sha256'],confirm="RETAIN_EXACT_MAIN_ONLY_WITH_RECOVERY")
    def test_dirty_linked_denied(self):
        linked=Path(self.tmp.name)/"repo-old"
        git(self.root,"worktree","add","--detach",str(linked),self.main)
        (linked/"dirty").write_text("x")
        with self.assertRaisesRegex(RuntimeError,"dirty"):
            self.plan()
    def test_ignored_linked_denied_before_removal(self):
        linked=Path(self.tmp.name)/"repo-old"
        git(self.root,"worktree","add","--detach",str(linked),self.main)
        git(self.root,"config","core.excludesFile",str(Path(self.tmp.name)/"ignore"))
        (Path(self.tmp.name)/"ignore").write_text("ignored-file\n")
        (linked/"ignored-file").write_text("evidence")
        with self.assertRaisesRegex(RuntimeError,"preservation"):
            self.apply()
        self.assertTrue(linked.exists())
        self.assertEqual(out(self.root,"rev-parse","fix/test"),self.head)
    def test_remote_main_drift_denied(self):
        with self.assertRaisesRegex(RuntimeError,"remote main drift"):
            self.plan(main=self.head)
    def test_primary_ignored_main_path_preserved_before_worktree_removal(self):
        linked=Path(self.tmp.name)/"repo-old"
        git(self.root,"worktree","add","--detach",str(linked),self.main)
        ignore=Path(self.tmp.name)/"ignore"
        ignore.write_text("upstream\n")
        git(self.root,"config","core.excludesFile",str(ignore))
        (self.root/"upstream").write_text("local evidence must survive")
        self.assertEqual(out(self.root,"status","--porcelain"),"")
        with self.assertRaisesRegex(RuntimeError,"preservation"):
            self.apply()
        self.assertEqual((self.root/"upstream").read_text(),"local evidence must survive")
        self.assertTrue(linked.exists())
        self.assertEqual(out(self.root,"branch","--show-current"),"fix/test")
        self.assertEqual(out(self.root,"rev-parse","fix/test"),self.head)
    def test_symbolic_branch_denied(self):
        git(self.root,"symbolic-ref","refs/heads/fix/alias","refs/heads/fix/test")
        with self.assertRaisesRegex(RuntimeError,"symbolic"):
            self.plan()
    def test_incremental_bundle_denied(self):
        base=out(self.root,"merge-base",self.main,self.head)
        git(self.root,"bundle","create",str(Path(self.tmp.name)/"all.bundle"),"--branches","^"+base)
        with self.assertRaisesRegex(RuntimeError,"incremental"):
            self.apply()

if __name__=="__main__": unittest.main()
