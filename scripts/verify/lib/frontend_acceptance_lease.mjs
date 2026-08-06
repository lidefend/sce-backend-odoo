import crypto from 'node:crypto';
import fsSync from 'node:fs';
import fs from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

function hash(value) { return crypto.createHash('sha256').update(String(value)).digest('hex'); }

async function processIdentity(pid) {
  if (process.platform !== 'linux') return { starttime: '', cmdline_hash: '' };
  const stat = await fs.readFile(`/proc/${pid}/stat`, 'utf8');
  const tail = stat.slice(stat.lastIndexOf(')') + 2).split(' ');
  const cmdline = await fs.readFile(`/proc/${pid}/cmdline`).catch(() => Buffer.from(''));
  return { starttime: tail[19] || '', cmdline_hash: hash(cmdline) };
}

async function bootId() {
  return (await fs.readFile('/proc/sys/kernel/random/boot_id', 'utf8').catch(() => '')).trim();
}

async function holdFlock(lockFile, shared) {
  await fs.mkdir(path.dirname(lockFile), { recursive: true });
  const args = [shared ? '-s' : '-x', '-n', lockFile, 'sh', '-c', 'printf READY; cat >/dev/null'];
  const child = spawn('flock', args, { stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk; });
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`acceptance lease timed out: ${lockFile}`)), 3000);
    const poll = () => {
      if (stdout.includes('READY')) { clearTimeout(timer); resolve(); }
      else if (child.exitCode !== null) { clearTimeout(timer); reject(new Error(`acceptance lease conflict: ${stderr.trim() || lockFile}`)); }
      else setTimeout(poll, 10);
    };
    poll();
  }).catch((error) => { child.kill(); throw error; });
  return child;
}

export async function acquireAcceptanceLease({ environment, root, mode = 'shared-read', owner = {} }) {
  if (!['shared-read', 'exclusive-write', 'exclusive-service'].includes(mode)) throw new Error(`unknown lease mode: ${mode}`);
  const leaseRoot = environment?.concurrency?.leaseRoot || path.join(os.tmpdir(), 'sce-frontend-acceptance', 'leases');
  const targetKey = environment?.concurrency?.targetKey || hash(path.resolve(root || '.'));
  const runId = environment?.artifacts?.runId || `${process.pid}-${crypto.randomUUID()}`;
  const artifactDir = environment?.artifacts?.runRoot || path.resolve(root || '.', runId);
  await fs.mkdir(artifactDir, { recursive: true });
  await fs.mkdir(leaseRoot, { recursive: true });
  const lockFile = path.join(leaseRoot, `${targetKey}.lock`);
  const holder = await holdFlock(lockFile, mode === 'shared-read');
  const metadataPath = path.join(leaseRoot, `${targetKey}-${runId}.json`);
  const identity = await processIdentity(process.pid).catch(() => ({ starttime: '', cmdline_hash: '' }));
  const metadata = {
    schema: 'frontend_acceptance_lease.v1', run_id: runId, mode, pid: process.pid,
    boot_id: await bootId(), process_starttime: identity.starttime, cmdline_hash: identity.cmdline_hash,
    target_key: targetKey, artifact_dir: artifactDir, created_at: new Date().toISOString(), ...owner,
  };
  await fs.writeFile(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
  let released = false;
  const exitCleanup = () => {
    try { holder.stdin.end(); } catch {}
    try { holder.kill('SIGKILL'); } catch {}
    try { fsSync.unlinkSync(metadataPath); } catch {}
  };
  process.once('exit', exitCleanup);
  const resource = {
    id: runId, runId, mode, artifactDir, metadataPath,
    async release() {
      if (released) return;
      released = true;
      process.removeListener('exit', exitCleanup);
      holder.stdin.end();
      if (holder.exitCode === null) await new Promise((resolve) => { holder.once('exit', resolve); setTimeout(() => { holder.kill('SIGKILL'); resolve(); }, 1000); });
      await fs.unlink(metadataPath).catch((error) => { if (error?.code !== 'ENOENT') throw error; });
    },
  };
  return resource;
}

export async function reserveDynamicPort(host = '127.0.0.1') {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, host, resolve); });
  const address = server.address();
  let released = false;
  return {
    host, port: address.port,
    async release() {
      if (released) return;
      released = true;
      await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    },
  };
}

export async function startOwnedProcess({ command, args = [], cwd, env = process.env, logFile, ready, timeoutMs = 30_000, lease }) {
  if (lease?.mode !== 'exclusive-service') throw new Error(`owned service requires an exclusive-service lease`);
  await fs.mkdir(path.dirname(logFile), { recursive: true });
  const handle = await fs.open(logFile, 'a');
  const child = spawn(command, args, { cwd, env, detached: true, stdio: ['ignore', handle.fd, handle.fd] });
  const identity = await processIdentity(child.pid);
  let stopped = false;
  const exitCleanup = () => {
    try {
      if (process.platform !== 'linux') return;
      const stat = fsSync.readFileSync(`/proc/${child.pid}/stat`, 'utf8');
      const tail = stat.slice(stat.lastIndexOf(')') + 2).split(' ');
      const cmdline = fsSync.readFileSync(`/proc/${child.pid}/cmdline`);
      if ((tail[19] || '') === identity.starttime && hash(cmdline) === identity.cmdline_hash) process.kill(-child.pid, 'SIGKILL');
    } catch {}
  };
  process.once('exit', exitCleanup);
  const resource = {
    pid: child.pid, identity,
    async stop() {
      if (stopped) return;
      stopped = true;
      process.removeListener('exit', exitCleanup);
      const current = await processIdentity(child.pid).catch(() => null);
      if (!current) { await handle.close(); return; }
      if (current.starttime !== identity.starttime || current.cmdline_hash !== identity.cmdline_hash) throw new Error(`managed service ownership changed; refusing to kill pid ${child.pid}`);
      process.kill(-child.pid, 'SIGTERM');
      await new Promise((resolve) => {
        const timer = setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL'); } catch {} resolve(); }, 2000);
        child.once('exit', () => { clearTimeout(timer); resolve(); });
      });
      await handle.close();
    },
  };
  const deadline = Date.now() + timeoutMs;
  try {
    let readyObserved = false;
    while (Date.now() < deadline) {
      if (child.exitCode !== null) throw new Error(`managed service exited before readiness: ${child.exitCode}`);
      if (await ready()) { readyObserved = true; break; }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (!readyObserved) throw new Error(`managed service readiness timed out`);
  } catch (error) {
    await resource.stop().catch(() => {});
    throw error;
  }
  return resource;
}
