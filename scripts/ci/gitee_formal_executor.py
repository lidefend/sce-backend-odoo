"""Trusted-parent execution for ordinary PR static gates, never a merge authority.

Used by the formal-static worker. Candidate/full lanes remain fail-closed.
Frontend standard execution requires a separately verified offline dependency cache.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from scripts.ci.gitee_ci_acceptance import Executor, Interrupted, REMOTE
from scripts.ci.gitee_gate_plan import CHECKS, digest, plan as build_plan, changed_paths

PUBLIC_TESTS = (
    "scripts/verify/test_repository_clean_history_guard.py",
    "scripts/verify/test_github_actions_security_guard.py",
    "scripts/ci/test_ci_risk_classifier.py",
    "scripts/ci/test_ci_risk_workflow_contract.py",
    "scripts/ci/test_merge_policy_gate.py",
    "scripts/ci/test_release_candidate_gate.py",
    "scripts/ci/test_select_authoritative_workflow_run.py",
    "scripts/ci/test_frontend_professional_extension_guard.py",
    "scripts/verify/test_frontend_release_evidence_bundle.py",
)
PUBLIC_COMPILE = ('scripts/verify/repository_clean_history_guard.py', 'scripts/verify/test_repository_clean_history_guard.py', 'scripts/verify/github_actions_security_guard.py', 'scripts/verify/test_github_actions_security_guard.py', 'scripts/ci/ci_risk_classifier.py', 'scripts/ci/test_ci_risk_classifier.py', 'scripts/ci/test_ci_risk_workflow_contract.py', 'scripts/ci/test_merge_policy_gate.py', 'scripts/ci/test_release_candidate_gate.py', 'scripts/ci/select_authoritative_workflow_run.py', 'scripts/ci/test_select_authoritative_workflow_run.py', 'scripts/ci/frontend_professional_extension_guard.py', 'scripts/ci/test_frontend_professional_extension_guard.py', 'scripts/release/frontend_release_evidence.py', 'scripts/release/generate_frontend_release_evidence_bundle.py', 'scripts/verify/frontend_release_evidence_bundle.py', 'scripts/verify/test_frontend_release_evidence_bundle.py')
FAST_TESTS = PUBLIC_TESTS[:4] + ("scripts/ci/test_select_authoritative_workflow_run.py",)
NODE_PATH = '/opt/gitee-ci/node-v22.17.0/bin/node'
NODE_SHA256 = '8071ae0fca095a272ad698a90c7061801a86fb6392ddb81e922b68a91a4374b9'
# Trusted, fixed tuning for the small shared CI host. Go's limit is a soft GC
# target, not a cgroup cap; gate failures and deadlines remain authoritative.
RESOURCE_ENV = {'GOMEMLIMIT':'256MiB', 'GOGC':'50', 'GOMAXPROCS':'2',
                'NODE_OPTIONS':'--max-old-space-size=2048', 'UV_THREADPOOL_SIZE':'2',
                'MAKEFLAGS':'-j1'}

IDENTITY_KEYS = ("repository", "source_branch", "target_branch", "head_sha", "base_sha", "pr_number")


def recipes(check, mode, base):
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("invalid_base")
    # (argv, nonzero unittest count required). Static guards legitimately have no
    # test count. A test entry reporting zero/all-skipped is always rejected.
    py = lambda p: (["python3", p], True)
    static = lambda *a: (list(a), False)
    common = [py("scripts/ci/test_ci_risk_classifier.py"),
              py("scripts/verify/test_github_actions_security_guard.py"),
              static("python3", "scripts/verify/github_actions_security_guard.py"),
              static("make", "verify.product.release.version"),
              # Container-free rejection rules of the settlement ORM lane. This
              # sandbox hosts no database, so the lane itself stays GitHub-only.
              static("bash", "scripts/ci/orm_result_guard.sh", "--self-test"),
              static("git", "diff", "--check")]
    if check == "public_guard" and mode == "required":
        return [static("python3", "-m", "py_compile", *PUBLIC_COMPILE)] + [py(p) for p in PUBLIC_TESTS] + [
            # Candidate PRs on Gitee resolve to this lane, and the sandbox hosts
            # no database: execute the container-free rejection rules here so the
            # settlement ORM lane cannot silently lose its zero-test, failure and
            # timeout guards.
            static("bash", "scripts/ci/orm_result_guard.sh", "--self-test"),
            static("python3", "scripts/ci/frontend_professional_extension_guard.py"),
            static("python3", "scripts/verify/repository_clean_history_guard.py", "--trusted-base", base),
            static("python3", "scripts/verify/clean_product_release_scan.py", "--report", "/tmp/clean-product.json"),
            static("python3", "scripts/verify/github_actions_security_guard.py")]
    if check == "public_guard" and mode == "skip_fast": return []
    if check == "merge_policy_gate" and mode == "fast":
        return [py(p) for p in FAST_TESTS] + [
            static("python3", "scripts/verify/github_actions_security_guard.py"),
            static("make", "verify.product.release.version"), static("git", "diff", "--check")]
    if check == "merge_policy_gate" and mode == "required": return []
    if check == "frontend_release_gate" and mode == "skip": return []
    if check == "frontend_release_gate" and mode == "standard":
        return [static("python3", "scripts/ci/frontend_professional_extension_guard.py"),
                static("pnpm", "-C", "frontend/apps/web", "lint:src"),
                static("pnpm", "-C", "frontend/apps/web", "typecheck:strict"),
                (["pnpm", "-C", "frontend/apps/web", "test"], True),
                static("pnpm", "-C", "frontend/apps/web", "build")]
    if check == "professional_quality_gate" and mode == "fast": return common
    if check == "professional_quality_gate" and mode == "governance":
        return common + [py("scripts/ci/test_ci_risk_workflow_contract.py"),
                         static("make", "ci.generated_reports.guard", "architecture.complexity_baseline_lock")]
    if check == "professional_quality_gate" and mode == "standard_frontend":
        return [static("python3", "scripts/ci/frontend_professional_extension_guard.py")] + common + [
            static("make", "ci.generated_reports.guard", "architecture.complexity_baseline_lock")]
    if check == "professional_quality_gate" and mode == "standard_backend":
        return [(["make", "test.unit"], True), static("make", "test.contract", "test.e2e.preflight"),
                static("make", "verify.tenant.data_responsibility_boundary", "verify.tenant.module_set_matrix",
                       "verify.tenant.payload_boundary", "verify.tenant.product_legacy_boundary",
                       "verify.tenant.legacy_xmlid_boundary"),
                static("make", "ci.generated_reports.guard", "architecture.complexity_baseline_lock"),
                static("git", "diff", "--check")]
    raise ValueError("unsupported_lane_requires_runtime_preparation")


def nonzero_tests(output):
    counts = [int(x) for x in re.findall(r"^Ran (\d+) tests? in ", output, re.MULTILINE)]
    if not counts or any(n == 0 for n in counts):
        raise ValueError("missing_or_zero_tests")
    skipped = sum(int(x) for x in re.findall(r"skipped=(\d+)", output))
    count = sum(counts) - skipped
    if count <= 0: raise ValueError("all_tests_skipped")
    return count


def verify_snapshot(plan, current):
    if (not isinstance(current, dict) or current.get("pr_identity_verified") is not True or
            current.get("remote_refs_verified") is not True or
            any(current.get(k) != plan.get(k) for k in IDENTITY_KEYS)):
        raise ValueError("live_identity_mismatch")


class FormalExecutor(Executor):
    def __init__(self, artifacts, *, timeout=5400):
        super().__init__(artifacts, timeout=timeout)

    def checkout(self, workspace, sha, log, cancelled, deadline):
        env={'PATH':'/usr/bin:/bin','HOME':str(workspace),'GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
        if os.environ.get('GIT_SSH_COMMAND'): env['GIT_SSH_COMMAND']=os.environ['GIT_SSH_COMMAND']
        for args in [['git','clone','--origin','gitee-mirror','--no-checkout','--no-tags',REMOTE,str(workspace/'repo')],
                     ['git','-C',str(workspace/'repo'),'fetch','--no-tags','gitee-mirror',sha],
                     ['git','-C',str(workspace/'repo'),'checkout','--detach',sha]]:
            if self.command(args,workspace,log,cancelled,deadline,env): raise RuntimeError('checkout failed')
        return (workspace/'repo/.git/HEAD').read_text().strip()

    def sandbox_command(self, workspace, command):
        node=[]
        frontend=[]
        if getattr(self,'needs_frontend',False):
            frontend=['--ro-bind',str(workspace/'tools'),'/tools',
                      '--ro-bind',str(workspace/'pnpm'),'/pnpm']
        if getattr(self,'needs_node',False):
            path=Path(NODE_PATH); info=path.stat()
            if path.is_symlink() or info.st_uid!=0 or info.st_mode & 0o022 or hashlib.sha256(path.read_bytes()).hexdigest()!=NODE_SHA256:
                raise ValueError('untrusted_node_runtime')
            node=['--ro-bind',NODE_PATH,'/usr/bin/node']
        git_metadata = ['--ro-bind', str(workspace/'repo/.git'), '/work/.git'] if (workspace/'repo/.git').is_dir() else []
        return ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
                '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
                '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
                '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                '--bind', str(workspace/'repo'), '/work', *git_metadata, *node, *frontend, '--chdir', '/work', *command]

    def validate_selection(self, candidate):
        expected = build_plan(head=candidate['head_sha'], base=candidate['base_sha'],
            source_branch=candidate['source_branch'], pr_number=candidate['pr_number'],
            paths=candidate['paths'], candidate=candidate['candidate_requested'])
        for key in ('checks', 'source_hashes', 'toolchain', 'lane', 'repository', 'target_branch'):
            if candidate.get(key) != expected[key]:
                raise ValueError('untrusted_gate_selection')

    def validate_paths(self, workspace, candidate):
        actual = changed_paths(workspace/'repo', candidate['base_sha'], candidate['head_sha'])
        if sorted(set(actual)) != candidate['paths']:
            raise ValueError('changed_path_manifest_mismatch')

    def execute_plan(self, plan, refresh_identity, cancelled=lambda: False):
        original = dict(plan); expected = original.pop("plan_sha256", None)
        if digest(original) != expected: raise ValueError("plan_digest_mismatch")
        if tuple(x["name"] for x in plan["checks"]) != CHECKS:
            raise ValueError("required_check_set_mismatch")
        # This is a trusted in-process controller API, not a candidate-provided
        # JSON admission endpoint. Re-derive plans from trusted policy before use.
        self.validate_selection(plan)
        verify_snapshot(plan, refresh_identity())
        command_sets = [recipes(c["name"], c["mode"], plan["base_sha"]) for c in plan["checks"]]
        self.artifacts.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix="formal-", dir=self.artifacts))
        receipt = {k: plan[k] for k in IDENTITY_KEYS}
        receipt.update(plan_sha256=expected, checks=[], status="environment_error", integration_eligible=False)
        env = {"PATH": "/tools:/usr/bin:/bin", "HOME": "/tmp", "ENV": "test", "CI": "1",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "PYTHONDONTWRITEBYTECODE": "1", "XDG_CACHE_HOME": "/tmp/cache"}
        env.update(RESOURCE_ENV)
        receipt["resource_environment"] = dict(RESOURCE_ENV)
        deadline = time.monotonic() + self.timeout
        try:
            with tempfile.TemporaryDirectory(prefix="formal-checkout-") as temp, (attempt/'checkout.log').open('wb') as log:
                workspace = Path(temp)
                if self.checkout(workspace, plan['head_sha'], log, cancelled, deadline) != plan['head_sha']:
                    raise ValueError("checkout_identity_mismatch")
                # The trusted base must be present and an ancestor before scanning.
                for cmd in [["git", "merge-base", "--is-ancestor", plan['base_sha'], plan['head_sha']]]:
                    if self.command(cmd, workspace/'repo', log, cancelled, deadline, env):
                        raise ValueError("base_not_available_or_not_ancestor")
                self.validate_paths(workspace, plan)
                for path, expected_hash in plan['source_hashes'].items():
                    rel = Path(path)
                    if rel.is_absolute() or '..' in rel.parts: raise ValueError("invalid_policy_path")
                    source = workspace/'repo'/rel
                    if not source.resolve().is_relative_to((workspace/'repo').resolve()):
                        raise ValueError("policy_path_escape")
                    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
                        raise ValueError("policy_source_mismatch")
                frontend_required = any(c['name']=='frontend_release_gate' and c['mode']=='standard' for c in plan['checks'])
                self.needs_frontend = False
                self.needs_node = frontend_required or any(c['mode'] == 'standard_backend' for c in plan['checks'])
                if self.needs_node:
                    node_log = attempt/'node.log'
                    with node_log.open('wb') as stream:
                        code = self.command(self.sandbox_command(workspace, ['node','--version']), workspace,
                                            stream, cancelled, deadline, env)
                    if code or node_log.read_text().strip() != 'v22.17.0':
                        raise ValueError("pinned_node_unavailable_in_sandbox")
                for check, commands in zip(plan['checks'], command_sets):
                    reuse = None
                    if check['name']=='frontend_release_gate' and check['mode']=='standard':
                        from scripts.ci.gitee_frontend_reuse import consume
                        reuse = consume(workspace/'repo', plan)
                        receipt['frontend_reuse'] = reuse
                        if reuse['status'] == 'verified_local_execution':
                            # The cheap policy guard still executes remotely. Only
                            # four exact, authenticated local steps are reused.
                            commands = commands[:1]
                        else:
                            from scripts.ops.gitee_frontend_cache import runtime_cache, isolate_package_manager
                            receipt['frontend_cache']=runtime_cache(workspace/'repo')
                            isolate_package_manager(workspace/'repo', workspace/'pnpm')
                            (workspace/'tools').mkdir()
                            launcher=workspace/'tools/pnpm'
                            launcher.write_text('#!/bin/sh\nexec node /pnpm/bin/pnpm.cjs "$@"\n')
                            launcher.chmod(0o755)
                            self.needs_frontend=True
                    check_deadline = min(deadline, time.monotonic() + {
                        'public_guard':900, 'merge_policy_gate':1800,
                        'professional_quality_gate':5400, 'frontend_release_gate':7200}[check['name']])
                    row = {'name':check['name'], 'mode':check['mode'], 'status':'success', 'tests':0}
                    for index, (cmd, require_tests) in enumerate(commands):
                        path = attempt/(check['name']+'-'+str(index)+'.log')
                        with path.open('wb') as stream:
                            code = self.command(self.sandbox_command(workspace, cmd), workspace,
                                                stream, cancelled, check_deadline, env)
                        if code:
                            row.update(status='failed', failed_step=index, exit_code=code); break
                        if require_tests:
                            if path.stat().st_size > 16 * 1024 * 1024: raise ValueError('test_log_too_large')
                            row['tests'] += nonzero_tests(path.read_text(errors='replace'))
                    if reuse and reuse['status'] == 'verified_local_execution' and row['status'] == 'success':
                        row.update(tests=reuse['tests'], execution='verified_local_execution',
                                   attestation_sha256=reuse['attestation_sha256'])
                    receipt['checks'].append(row)
                verify_snapshot(plan, refresh_identity())
                receipt['status'] = 'success' if all(c['status']=='success' for c in receipt['checks']) else 'failed'
        except Interrupted as exc:
            receipt['status'] = exc.status
        except (OSError, ValueError, KeyError, RuntimeError):
            receipt['status'] = 'environment_error'
        if cancelled(): receipt['status'] = 'cancelled'
        (attempt/'receipt.json').write_text(json.dumps(receipt, sort_keys=True)+'\n')
        return receipt
