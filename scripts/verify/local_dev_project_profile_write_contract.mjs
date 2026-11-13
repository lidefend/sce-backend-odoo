function fail(message) {
  throw new Error(`[DENY] ${message}`);
}

export function appPathname(value, basePath = '/t/demo') {
  const pathname = value instanceof URL ? value.pathname : new URL(String(value)).pathname;
  return pathname === basePath
    ? '/'
    : pathname.startsWith(`${basePath}/`)
      ? pathname.slice(basePath.length)
      : pathname;
}

export function projectRecordTarget(value, basePath = '/t/demo') {
  const match = appPathname(value, basePath).match(
    /^\/(f|r)\/project\.project\/([1-9][0-9]*)\/?$/,
  );
  return match ? { surface: match[1], projectId: Number(match[2]) } : null;
}

export function assertExpectedProjectRecord(value, expectedProjectId, label = 'project record') {
  const target = projectRecordTarget(value);
  if (!target) fail(`${label} did not open a project record route: ${String(value)}`);
  if (target.projectId !== Number(expectedProjectId)) {
    fail(`${label} opened project ${target.projectId}, expected ${expectedProjectId}`);
  }
  return target;
}

export function targetInitiationDate(existingValue, preferredDay = 10, now = new Date()) {
  const existing = String(existingValue || '').trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const year = existing ? Number(existing[1]) : now.getFullYear();
  const month = existing ? Number(existing[2]) : now.getMonth() + 1;
  const existingDay = existing ? Number(existing[3]) : 0;
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  let day = Math.max(1, Math.min(Number(preferredDay), daysInMonth));
  if (day === existingDay) day = day === daysInMonth ? day - 1 : day + 1;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export function assertDateSelection({ before, target, after, writeValue }) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(target || ''))) fail('target date must be a full YYYY-MM-DD value');
  if (String(before || '') === String(target)) fail('target date must differ from the original date');
  if (String(after || '') !== String(target)) {
    fail(`date control value ${String(after)} did not become ${String(target)}`);
  }
  if (String(writeValue || '') !== String(target)) {
    fail(`date write value ${String(writeValue)} did not equal ${String(target)}`);
  }
}
