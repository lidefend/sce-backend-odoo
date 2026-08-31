import fs from 'node:fs';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

function isExecutable(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function revisionOf(dirName) {
  const match = String(dirName || '').match(/-(\d+)$/);
  return match ? Number(match[1]) : 0;
}

function resolvedRealHome() {
  return process.env.SNAP_REAL_HOME || process.env.REAL_HOME || '';
}

function browserCacheRoots() {
  const roots = [];
  const explicit = process.env.PLAYWRIGHT_BROWSERS_PATH || '';
  if (explicit) roots.push(explicit);
  roots.push(path.join(os.homedir(), '.cache', 'ms-playwright'));
  const realHome = resolvedRealHome();
  if (realHome) roots.push(path.join(realHome, '.cache', 'ms-playwright'));
  return [...new Set(roots.filter(Boolean))];
}

function cachedChromiumCandidates() {
  return browserCacheRoots().flatMap((root) => {
    let entries = [];
    try {
      entries = fs.readdirSync(root, { withFileTypes: true });
    } catch {
      return [];
    }
    return entries
      .filter((entry) => entry.isDirectory() && (entry.name.startsWith('chromium-') || entry.name.startsWith('chromium_headless_shell-')))
      .sort((a, b) => revisionOf(b.name) - revisionOf(a.name))
      .flatMap((entry) => [
        path.join(root, entry.name, 'chrome-linux64', 'chrome'),
        path.join(root, entry.name, 'chrome-headless-shell-linux64', 'chrome-headless-shell'),
      ])
      .filter(isExecutable);
  });
}

export function resolveChromiumExecutablePath() {
  const explicitKeys = [
    'CHROMIUM_EXECUTABLE_PATH',
    'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH',
    'PLAYWRIGHT_EXECUTABLE_PATH',
    'CHROMIUM_PATH',
    'PLAYWRIGHT_CHROMIUM_EXECUTABLE',
  ];
  for (const key of explicitKeys) {
    const explicit = process.env[key];
    if (explicit && isExecutable(explicit)) {
      return explicit;
    }
  }
  return cachedChromiumCandidates()[0] || '';
}

export function resolvePlaywrightEndpoint() {
  for (const key of [
    'PLAYWRIGHT_WS_ENDPOINT',
    'PLAYWRIGHT_REMOTE_WS_ENDPOINT',
    'PLAYWRIGHT_CONNECT_WS_ENDPOINT',
    'PLAYWRIGHT_CDP_ENDPOINT',
    'PLAYWRIGHT_REMOTE_DEBUG_URL',
  ]) {
    const value = String(process.env[key] || '').trim();
    if (value) {
      return { key, value };
    }
  }
  return null;
}

function loadPlaywrightChromium() {
  const modulePath = require.resolve('playwright', {
    paths: [
      path.join(repoRoot, 'frontend', 'apps', 'web', 'node_modules'),
      path.join(repoRoot, 'frontend', 'node_modules'),
    ],
  });
  return require(modulePath).chromium;
}

function mergedLaunchEnv() {
  const systemLibraryDirs = ['/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu', '/lib', '/usr/lib'];
  const ldLibraryPath = [...new Set([
    ...systemLibraryDirs,
    ...String(process.env.LD_LIBRARY_PATH || '').split(':').filter(Boolean),
  ])].join(':');
  const realHome = resolvedRealHome();
  return {
    ...process.env,
    ...(realHome ? { HOME: realHome } : {}),
    LD_LIBRARY_PATH: ldLibraryPath,
  };
}

export async function launchChromium(options = {}) {
  const chromium = loadPlaywrightChromium();
  const endpoint = resolvePlaywrightEndpoint();
  if (endpoint) {
    if (endpoint.key.includes('CDP') || endpoint.key.includes('DEBUG')) {
      return chromium.connectOverCDP(endpoint.value);
    }
    return chromium.connect(endpoint.value);
  }
  const executablePath = resolveChromiumExecutablePath();
  if (executablePath) {
    return chromium.launch({ ...options, executablePath, env: mergedLaunchEnv() });
  }
  return chromium.launch({ ...options, env: mergedLaunchEnv() });
}

export async function launchAcceptanceChromium(environment, options = {}) {
  if (!environment?.schema?.startsWith('frontend_acceptance_environment.')) {
    throw new Error('a resolved frontend acceptance environment is required');
  }
  return launchChromium(options);
}
