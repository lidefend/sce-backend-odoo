import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.dev import acceptance_artifact as artifact


class ArtifactTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git('init', '-q')
        self.run_git('config', 'user.email', 'synthetic@example.invalid')
        self.run_git('config', 'user.name', 'Synthetic Test')
        (self.root / 'addons').mkdir()
        (self.root / 'addons/test.py').write_text('original\n')
        (self.root / 'VERSION').write_text('1\n')
        for name in artifact.MOUNTS:
            file = self.root / (name if '.' in Path(name).name or name == 'VERSION' else name + '/.keep')
            file.parent.mkdir(parents=True, exist_ok=True)
            if not file.exists(): file.write_text('fixture\n')
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'fixture')
        self.sha = self.run_git('rev-parse', 'HEAD').strip()

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def test_export_ignores_dirty_and_untracked_source(self):
        (self.root / 'addons/test.py').write_text('dirty\n')
        (self.root / 'addons/untracked.py').write_text('not reviewed\n')
        target, _ = artifact.build(self.root, self.sha)
        self.assertEqual((target / 'addons/test.py').read_text(), 'original\n')
        self.assertFalse((target / 'addons/untracked.py').exists())
        self.assertEqual(artifact.build(self.root, self.sha)[0], target)

    def test_mutation_cannot_be_hidden_by_rewriting_manifest(self):
        target, _ = artifact.build(self.root, self.sha)
        file = target / 'addons/test.py'
        file.chmod(0o644)
        file.write_text('tampered')
        file.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'content changed'):
            artifact.verify(self.root, self.sha)
        manifest = target / 'manifest.json'
        manifest.chmod(0o644)
        data = json.loads(manifest.read_text())
        data['files']['addons/test.py']['blob'] = '0'*40
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Git authority'):
            artifact.verify(self.root, self.sha)

    def test_extra_file_and_symlink_rejected(self):
        target, _ = artifact.build(self.root, self.sha)
        extra = target / 'unexpected'
        extra.write_text('extra')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            artifact.verify(self.root, self.sha)
        extra.unlink()
        extra.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            artifact.verify(self.root, self.sha)

    def test_same_artifact_across_worktrees(self):
        linked = self.root / 'linked'
        self.run_git('worktree', 'add', '--detach', str(linked), self.sha)
        target, _ = artifact.build(self.root, self.sha)
        self.assertEqual(artifact.verify(linked, self.sha)[0], target)

    def test_mutable_ref_and_source_symlink_rejected(self):
        with self.assertRaisesRegex(ValueError, 'immutable'):
            artifact.build(self.root, 'HEAD')
        (self.root / 'addons/link').symlink_to('/etc/passwd')
        self.run_git('add', 'addons/link')
        self.run_git('commit', '-qm', 'invalid fixture')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            artifact.build(self.root, self.run_git('rev-parse','HEAD').strip())

    def test_compose_mounts_are_explicit_readonly_and_cannot_create_paths(self):
        artifact.build(self.root, self.sha)
        config = json.loads(artifact.compose_override(self.root, self.sha).read_text())
        mounts = config['services']['odoo']['volumes']
        self.assertEqual({m['target'] for m in mounts}, set(artifact.MOUNTS.values()))
        self.assertTrue(all(m['read_only'] is True and m['bind']['create_host_path'] is False for m in mounts))

    def test_writable_artifact_rejected(self):
        target, _ = artifact.build(self.root, self.sha)
        (target / 'addons/test.py').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'permissions'):
            artifact.verify(self.root, self.sha)

class BackendReplacementTest(unittest.TestCase):
    def run_case(self, *, artifact_ok=True, healthy=True):
        import os
        root_repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            (root / 'VERSION').write_text('1')
            (root / 'scripts/dev').mkdir(parents=True)
            (root / 'scripts/dev/acceptance_source_fingerprint.sh').write_text(
                (root_repo / 'scripts/dev/acceptance_source_fingerprint.sh').read_text())
            artifact_root = root / 'artifact'
            for item in ['addons', 'demo_addons', 'addons_external', 'scripts', 'docs', 'config']:
                (artifact_root / item).mkdir(parents=True)
            for item in ['VERSION', 'config/odoo.conf.template', 'scripts/render_odoo_conf.py', 'scripts/odoo-entrypoint.sh']:
                (artifact_root / item).touch()
            trace = root / 'trace'
            stubs = {
                'git': '#!/bin/sh\ncase "$*" in *rev-parse*) printf "%040d\\n" 1;; esac\n',
                'python3': '#!/bin/sh\n' + ('printf "%s\\n" "$ARTIFACT_ROOT"\n' if artifact_ok else 'exit 2\n'),
                'curl': '#!/bin/sh\nexit '+('0' if healthy else '1')+'\n',
                'sleep': '#!/bin/sh\nexit 0\n',
                'docker': '''#!/bin/sh
printf '%s\n' "$*" >> "$TRACE"
case "$1" in
 inspect)
  case "$2" in *rollback*) exit 1;; esac
  case "$*" in *'.Id'*) printf '%064d\n' 1;; *'.State.Running'*) echo false;; *'.RW'*) printf 'false\nfalse\nfalse\n';; esac
  ;;
esac
''',
            }
            for name, source in stubs.items():
                file = bin_dir / name
                file.write_text(source)
                file.chmod(0o755)
            result = subprocess.run(['bash', str(root_repo / 'scripts/dev/backend_acceptance_up.sh')],
                env={'PATH':str(bin_dir)+':'+os.environ['PATH'], 'ROOT_DIR':str(root),
                     'ARTIFACT_ROOT':str(artifact_root), 'TRACE':str(trace),
                     'XDG_RUNTIME_DIR':str(root / 'leases')}, capture_output=True, text=True)
            return result, trace.read_text() if trace.exists() else ''

    def test_invalid_artifact_causes_no_docker_mutation(self):
        result, trace = self.run_case(artifact_ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, '')

    def test_success_preserves_stopped_previous_carrier(self):
        result, trace = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('rename sc-backend-odoo-acceptance sc-backend-odoo-acceptance-rollback-', trace)
        self.assertNotIn('rm -f', trace)
        self.assertIn('compose -f ', trace)
        self.assertLess(trace.index('rename '), trace.index('compose -f '))

    def test_failed_start_restores_previous_without_starting_stopped_service(self):
        result, trace = self.run_case(healthy=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rm -f sc-backend-odoo-acceptance', trace)
        self.assertIn('rename sc-backend-odoo-acceptance-rollback-', trace)
        self.assertNotIn('start sc-backend', trace)
        self.assertIn('restored prior carrier', result.stderr)
