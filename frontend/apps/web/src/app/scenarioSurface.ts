import { routeAuthorityEntries, type RouteAuthorityContract } from './routeAuthority';

export interface ScenarioNavEntry {
  menu_xmlid: string;
  menu_id: number;
  action_id: number;
  action_xmlid: string;
  model: string;
  view_modes: string[];
  route: string;
  label: string;
  intent: string;
  intent_label: string;
  configured: boolean;
}

export interface ScenarioNode {
  key: string;
  name: string;
  sequence: number;
  entries: ScenarioNavEntry[];
}

export interface ScenarioCenterNode {
  key: string;
  name: string;
  sequence: number;
  scenarios: ScenarioNode[];
  entries: ScenarioNavEntry[];
}

export interface ScenarioNavigationModel {
  centers: ScenarioCenterNode[];
}

export interface ScenarioSearchHit {
  entry: ScenarioNavEntry;
  centerName: string;
  scenarioName: string;
}

export class ScenarioSurfaceError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
    this.name = 'ScenarioSurfaceError';
  }
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function parseEntry(raw: unknown): ScenarioNavEntry | null {
  const row = asRecord(raw);
  const menuId = positiveInteger(row.menu_id);
  const route = text(row.route);
  const menuXmlid = text(row.menu_xmlid);
  if (menuId <= 0 || !route || !menuXmlid) return null;
  return {
    menu_xmlid: menuXmlid,
    menu_id: menuId,
    action_id: positiveInteger(row.action_id),
    action_xmlid: text(row.action_xmlid),
    model: text(row.model),
    view_modes: asList(row.view_modes).map((item) => text(item)).filter(Boolean),
    route,
    label: text(row.label) || menuXmlid,
    intent: text(row.intent),
    intent_label: text(row.intent_label),
    configured: row.configured === true,
  };
}

function parseScenario(raw: unknown): ScenarioNode | null {
  const row = asRecord(raw);
  const key = text(row.key);
  if (!key) return null;
  const entries = asList(row.entries)
    .map(parseEntry)
    .filter((entry): entry is ScenarioNavEntry => entry !== null);
  if (!entries.length) return null;
  return {
    key,
    name: text(row.name) || key,
    sequence: positiveInteger(row.sequence),
    entries,
  };
}

function parseCenter(raw: unknown): ScenarioCenterNode | null {
  const row = asRecord(raw);
  const key = text(row.key);
  if (!key) return null;
  const scenarios = asList(row.scenarios)
    .map(parseScenario)
    .filter((scenario): scenario is ScenarioNode => scenario !== null);
  const entries = asList(row.entries)
    .map(parseEntry)
    .filter((entry): entry is ScenarioNavEntry => entry !== null);
  return {
    key,
    name: text(row.name) || key,
    sequence: positiveInteger(row.sequence),
    scenarios,
    entries,
  };
}

/**
 * Parse the server-owned scenario-center navigation projection.
 *
 * Returns `null` for a missing/malformed contract. A valid empty projection is
 * authoritative (for example after entry revocation) and must not trigger any
 * other navigation fallback: the unified navigation shows its own empty state.
 */
export function parseScenarioSurface(raw: unknown): ScenarioNavigationModel | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const contract = raw as Record<string, unknown>;
  if (contract.ok !== true) return null;
  const tree = asRecord(contract.tree);
  if (!Array.isArray(tree.centers)) return null;
  const centers = asList(tree.centers)
    .map(parseCenter)
    .filter((center): center is ScenarioCenterNode => center !== null);
  return { centers };
}

/**
 * Search the authorized scenario-center surface by familiar business names.
 * It never resolves actions or routes; it only narrows already-authorized
 * entries and keeps center/scenario attribution for the result list.
 */
export function searchScenarioSurface(
  model: ScenarioNavigationModel,
  query: string,
): ScenarioSearchHit[] {
  const term = query.trim().toLowerCase();
  if (!term) return [];
  const matchesEntry = (entry: ScenarioNavEntry): boolean => (
    entry.label.toLowerCase().includes(term)
    || entry.menu_xmlid.toLowerCase().includes(term)
  );
  const hits: ScenarioSearchHit[] = [];
  for (const center of model.centers) {
    for (const entry of center.entries) {
      if (matchesEntry(entry)) {
        hits.push({ entry, centerName: center.name, scenarioName: '' });
      }
    }
    for (const scenario of center.scenarios) {
      for (const entry of scenario.entries) {
        if (matchesEntry(entry)) {
          hits.push({ entry, centerName: center.name, scenarioName: scenario.name });
        }
      }
    }
  }
  return hits;
}

/** Snapshot only an exact entry still present in the current principal authority. */
export function createScenarioSelectionSnapshot(entry: ScenarioNavEntry, authority: RouteAuthorityContract | null) {
  const row = routeAuthorityEntries(authority).find((candidate) => (
    candidate.menu_id === entry.menu_id && candidate.action_id === entry.action_id
    && candidate.menu_xmlid === entry.menu_xmlid && candidate.route === entry.route
  ));
  if (!row || !entry.route) return null;
  const snapshot = JSON.parse(JSON.stringify({ route: row.route, authority: row }));
  const freeze = (value: Record<string, unknown>): void => {
    Object.values(value).forEach((child) => {
      if (child && typeof child === 'object') freeze(child as Record<string, unknown>);
    });
    Object.freeze(value);
  };
  freeze(snapshot);
  return snapshot as Readonly<{ route: string; authority: typeof row }>;
}
