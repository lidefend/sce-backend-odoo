import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

async function withCoordinator(root, run) {
  const coordinator = path.join(root, '.coordinator');
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      await fs.mkdir(coordinator);
      try { return await run(); } finally { await fs.rmdir(coordinator).catch(() => {}); }
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
  }
  throw new Error(`acceptance lease coordinator timed out: ${root}`);
}

async function activeLeaseEntries(leaseRoot) {
  const entries = (await fs.readdir(leaseRoot)).filter((name) => name.endsWith('.json'));
  const active = [];
  for (const name of entries) {
    const file = path.join(leaseRoot, name);
    let descriptor;
    try {
      descriptor = JSON.parse(await fs.readFile(file, 'utf8'));
    } catch {
      active.push(name);
      continue;
    }
    const pid = Number(descriptor?.pid || 0);
    if (!Number.isSafeInteger(pid) || pid <= 0) {
      active.push(name);
      continue;
    }
    try {
      process.kill(pid, 0);
      active.push(name);
    } catch (error) {
      if (error?.code === 'ESRCH') await fs.unlink(file).catch(() => {});
      else active.push(name);
    }
  }
  return active;
}

export async function acquireAcceptanceLease({ root, mode = 'shared-read', owner = {} }) {
  if (!['shared-read', 'exclusive-write', 'exclusive-service'].includes(mode)) throw new Error(`unknown lease mode: ${mode}`);
  const leaseRoot = path.resolve(root, '.leases');
  await fs.mkdir(leaseRoot, { recursive: true });
  const id = `${process.pid}-${crypto.randomUUID()}`;
  const leaseFile = path.join(leaseRoot, `${mode}-${id}.json`);
  await withCoordinator(leaseRoot, async () => {
    const entries = await activeLeaseEntries(leaseRoot);
    const exclusive = entries.some((name) => name.startsWith('exclusive-'));
    if ((mode === 'shared-read' && exclusive) || (mode !== 'shared-read' && entries.length)) {
      throw new Error(`acceptance lease conflict: requested=${mode} active=${entries.join(',')}`);
    }
    await fs.writeFile(leaseFile, `${JSON.stringify({ schema: 'frontend_acceptance_lease.v1', id, mode, pid: process.pid, created_at: new Date().toISOString(), ...owner }, null, 2)}\n`, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
  });
  let released = false;
  return {
    id,
    mode,
    async release() {
      if (released) return;
      released = true;
      await fs.unlink(leaseFile).catch((error) => { if (error?.code !== 'ENOENT') throw error; });
    },
  };
}
