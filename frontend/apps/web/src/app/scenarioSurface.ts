export interface ScenarioNavEntry {
  menu_xmlid: string;
  menu_id: number;
  action_id: number;
  action_xmlid: string;
  model: string;
  view_modes: string[];
  route: string;
  label: string;
}

export interface ScenarioIntentNode {
  intent: string;
  label: string;
  entries: ScenarioNavEntry[];
}

export interface ScenarioNode {
  key: string;
  name: string;
  type: string;
  intents: ScenarioIntentNode[];
}

export interface ScenarioDomainNode {
  key: string;
  name: string;
  scenarios: ScenarioNode[];
}

export interface ScenarioNavigationModel {
  domains: ScenarioDomainNode[];
  horizontal: ScenarioNavEntry[];
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
  };
}

function parseIntent(raw: unknown): ScenarioIntentNode | null {
  const row = asRecord(raw);
  const intent = text(row.intent);
  if (!intent) return null;
  const entries = asList(row.entries)
    .map(parseEntry)
    .filter((entry): entry is ScenarioNavEntry => entry !== null);
  if (!entries.length) return null;
  return { intent, label: text(row.label) || intent, entries };
}

function parseScenario(raw: unknown): ScenarioNode | null {
  const row = asRecord(raw);
  const key = text(row.key);
  if (!key) return null;
  const intents = asList(row.intents)
    .map(parseIntent)
    .filter((intent): intent is ScenarioIntentNode => intent !== null);
  if (!intents.length) return null;
  return { key, name: text(row.name) || key, type: text(row.type), intents };
}

function parseDomain(raw: unknown): ScenarioDomainNode | null {
  const row = asRecord(raw);
  const key = text(row.key);
  if (!key) return null;
  const scenarios = asList(row.scenarios)
    .map(parseScenario)
    .filter((scenario): scenario is ScenarioNode => scenario !== null);
  if (!scenarios.length) return null;
  return { key, name: text(row.name) || key, scenarios };
}

/**
 * Parse the server-owned `navigation.scenario_surface` into a normalized model.
 *
 * Returns `null` for a missing, malformed, or incompatible contract so
 * the shell can fall back to the legacy canonical navigation. This parser is a
 * pure consumer: it never resolves actions, never constructs routes, and never
 * treats client-side data as an authorization source.
 */
export function parseScenarioSurface(raw: unknown): ScenarioNavigationModel | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const contract = raw as Record<string, unknown>;
  if (contract.ok !== true) return null;
  const tree = asRecord(contract.tree);
  if (!Array.isArray(tree.domains) || !Array.isArray(tree.horizontal)) return null;
  const domains = asList(tree.domains)
    .map(parseDomain)
    .filter((domain): domain is ScenarioDomainNode => domain !== null);
  const horizontal = asList(tree.horizontal)
    .map(parseEntry)
    .filter((entry): entry is ScenarioNavEntry => entry !== null);
  // A valid empty projection is authoritative (for example after revocation).
  // It must not trigger legacy navigation fallback.
  return { domains, horizontal };
}
