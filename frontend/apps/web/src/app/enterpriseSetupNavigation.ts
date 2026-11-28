type Query = Record<string, unknown>;

export function withEnterpriseSetupReturnTarget(
  query: Query,
  target: {
    sourceSceneKey: string;
    sourcePath: string;
    sourceLabel: string;
  },
): Query {
  const next = { ...query };
  if (target.sourceSceneKey !== 'enterprise.setup') return next;
  const sourcePath = String(target.sourcePath || '').trim();
  if (!sourcePath.startsWith('/') || sourcePath.startsWith('//')) return next;
  next.return_url = sourcePath;
  return next;
}
