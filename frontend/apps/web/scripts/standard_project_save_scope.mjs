export function permitsProjectNameWrite(role, body, permit) {
  const params = body?.params;
  return Boolean(permit && role === 'fixture_role_pm' && body?.intent === 'api.data'
    && params?.op === 'write' && params.model === 'project.project'
    && JSON.stringify(params.ids) === '[10]'
    && JSON.stringify(params.vals) === JSON.stringify({ name: permit.name }));
}
