const REQUIRED_BUNDLE_ASSETS = [
  { key: 'entry', pattern: /\/assets\/index-[^/]+\.js(?:[?#]|$)/u },
  { key: 'route', pattern: /\/assets\/ContractFormRoute-[^/]+\.js(?:[?#]|$)/u },
  { key: 'form', pattern: /\/assets\/ContractFormPage-[^/]+\.js(?:[?#]|$)/u },
];

function text(value) {
  return String(value || '').trim();
}

function isSha256(value) {
  return /^[0-9a-f]{64}$/iu.test(text(value));
}

export function validateRecordDeepLinkEvidence({
  expectedBuildSha,
  servedBuildInfo,
  bundleAssets,
}) {
  const findings = [];
  const expected = text(expectedBuildSha);
  const served = text(servedBuildInfo?.sha);
  if (!expected) {
    findings.push('served_build_sha_expected_missing');
  } else if (!/^[0-9a-f]{40}$/iu.test(expected)) {
    findings.push('served_build_sha_expected_invalid');
  }
  if (!served) {
    findings.push('served_build_info_missing');
  } else if (expected && served !== expected) {
    findings.push('served_build_sha_mismatch');
  }

  const assets = Array.isArray(bundleAssets) ? bundleAssets : [];
  if (!assets.length) findings.push('bundle_assets_missing');
  for (const requirement of REQUIRED_BUNDLE_ASSETS) {
    const matches = assets.filter(asset => requirement.pattern.test(text(asset?.resource_url)));
    if (!matches.length) {
      findings.push(`bundle_asset_missing:${requirement.key}`);
      continue;
    }
    if (!matches.some(asset => isSha256(asset?.resource_sha256)
      && Number(asset?.decoded_body_size || 0) > 0)) {
      findings.push(`bundle_asset_hash_missing:${requirement.key}`);
    }
  }
  return findings;
}
