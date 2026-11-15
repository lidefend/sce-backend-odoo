export const STARTUP_PHASES = [
  'boot_start',
  'skeleton_shown',
  'session_ready',
  'contract_loaded',
  'record_ready',
] as const;

export type StartupPhase = typeof STARTUP_PHASES[number];

export type StartupTimingMarks = Partial<Record<StartupPhase, number>>;

const markedPhases = new Set<StartupPhase>();

export function readStartupTimingMarks(): StartupTimingMarks {
  if (typeof performance === 'undefined' || typeof performance.getEntriesByName !== 'function') {
    return {};
  }
  const marks: StartupTimingMarks = {};
  for (const phase of STARTUP_PHASES) {
    const entry = performance.getEntriesByName(phase, 'mark')[0];
    if (entry) marks[phase] = entry.startTime;
  }
  return marks;
}

export function markStartupPhase(phase: StartupPhase, source = ''): boolean {
  if (markedPhases.has(phase)) return false;
  if (typeof performance === 'undefined' || typeof performance.mark !== 'function') return false;
  performance.mark(phase, source ? { detail: { source } } : undefined);
  markedPhases.add(phase);
  if (typeof window !== 'undefined') {
    (window as Window & { __SC_STARTUP_TIMING__?: StartupTimingMarks })
      .__SC_STARTUP_TIMING__ = readStartupTimingMarks();
  }
  return true;
}

export function startupTimingOrderIssues(marks: StartupTimingMarks): string[] {
  const issues: string[] = [];
  if (marks.boot_start === undefined) issues.push('boot_start_missing');
  if (marks.record_ready === undefined) issues.push('record_ready_missing');
  for (const phase of ['session_ready', 'contract_loaded', 'record_ready'] as const) {
    if (marks[phase] === undefined) continue;
    if (marks.boot_start !== undefined && marks[phase]! < marks.boot_start!) {
      issues.push(`${phase}_before_boot_start`);
    }
  }
  if (
    marks.session_ready !== undefined
    && marks.contract_loaded !== undefined
    && marks.contract_loaded < marks.session_ready
  ) {
    issues.push('contract_loaded_before_session_ready');
  }
  if (
    marks.contract_loaded !== undefined
    && marks.record_ready !== undefined
    && marks.record_ready < marks.contract_loaded
  ) {
    issues.push('record_ready_before_contract_loaded');
  }
  return issues;
}

export function shouldPreloadWorkspaceHomeAtStartup(routeName: unknown): boolean {
  const name = String(routeName || '').trim();
  return name !== 'record' && name !== 'model-form';
}
