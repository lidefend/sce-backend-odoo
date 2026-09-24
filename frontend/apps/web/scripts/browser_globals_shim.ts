/**
 * Minimal browser globals for node-run frontend unit tests.
 *
 * `src/config.ts` and `src/api/client.ts` read `window.location`, `localStorage`
 * and `sessionStorage` while their modules are evaluated. Import this module
 * before anything from `src/` so those reads see a deterministic stub.
 */
const memory = new Map<string, string>();
const storage = {
  getItem: (key: string) => (memory.has(key) ? memory.get(key)! : null),
  setItem: (key: string, value: string) => { memory.set(key, String(value)); },
  removeItem: (key: string) => { memory.delete(key); },
  clear: () => { memory.clear(); },
};
const globalScope = globalThis as unknown as Record<string, unknown>;
globalScope.window = {
  location: { href: 'http://localhost/', origin: 'http://localhost', pathname: '/', search: '', hash: '' },
};
globalScope.localStorage = storage;
globalScope.sessionStorage = storage;
export {};
