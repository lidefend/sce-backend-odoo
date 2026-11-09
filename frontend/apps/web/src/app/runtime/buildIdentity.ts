export interface FrontendBuildIdentity {
  sha: string;
  builtAt: string;
  environment: string;
  version: string;
}

export const FRONTEND_BUILD_IDENTITY: Readonly<FrontendBuildIdentity> = Object.freeze({
  sha: String(__SC_BUILD_SHA__ || '').trim().toLowerCase(),
  builtAt: String(__SC_BUILD_TIME__ || '').trim(),
  environment: String(__SC_BUILD_ENV__ || '').trim(),
  version: String(__SC_BUILD_VERSION__ || '').trim(),
});

const FULL_SHA = /^[0-9a-f]{40}$/;
const SEMVER_RELEASE = /^(\d+\.\d+\.\d+)-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)(?:\+[0-9A-Za-z.-]+)?$/;

export function shortBuildRevision(value: string): string {
  const revision = String(value || '').trim().toLowerCase();
  return FULL_SHA.test(revision) ? revision.slice(0, 9) : 'unknown';
}

export function compactProductVersion(value: string): string {
  const version = String(value || '').trim();
  const prerelease = version.match(SEMVER_RELEASE);
  return prerelease ? prerelease[2] : (version || 'unknown');
}

export function productIdentityLabel(productVersion: string, sourceRevision: string): string {
  return `${compactProductVersion(productVersion)} · ${shortBuildRevision(sourceRevision)}`;
}

export function buildIdentityTitle(
  productVersion: string,
  sourceRevision: string,
  build: FrontendBuildIdentity = FRONTEND_BUILD_IDENTITY,
): string {
  return [
    compactProductVersion(productVersion),
    `源代码 ${String(sourceRevision || '').trim() || 'unknown'}`,
    `构建时间 ${build.builtAt || 'unknown'}`,
    `构建环境 ${build.environment || 'unknown'}`,
  ].join(' · ');
}

export function buildIdentityCopyText(
  productVersion: string,
  sourceRevision: string,
  build: FrontendBuildIdentity = FRONTEND_BUILD_IDENTITY,
): string {
  return [
    `product_version=${String(productVersion || '').trim() || 'unknown'}`,
    `source_revision=${String(sourceRevision || '').trim() || 'unknown'}`,
    `frontend_build_sha=${String(build.sha || '').trim() || 'unknown'}`,
    `frontend_build_time=${String(build.builtAt || '').trim() || 'unknown'}`,
    `frontend_build_environment=${String(build.environment || '').trim() || 'unknown'}`,
  ].join('\n');
}
