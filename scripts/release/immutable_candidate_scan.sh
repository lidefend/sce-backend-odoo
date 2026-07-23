#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
artifacts="${CANDIDATE_ARTIFACTS:-artifacts/release/immutable-production-candidate-v1}"
source_sha="${SOURCE_SHA:?SOURCE_SHA is required}"
mkdir -p "$artifacts"
artifacts="$(realpath "$artifacts")"
manifest="$artifacts/image-manifest.json"
[[ -f "$manifest" ]] || { echo "[candidate.scan] image manifest missing" >&2; exit 2; }
image="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image"])' "$manifest")"
image_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_digest"])' "$manifest")"
mkdir -p "$artifacts/trivy-cache"

docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/syft:v1.27.1@sha256:844ed6a928ef9396fac26d1de374e71dcaf80df14f05841670ed41619c5a718f \
  "$image" -o cyclonedx-json > "$artifacts/sbom.cyclonedx.json"
docker run --rm \
  anchore/syft:v1.27.1@sha256:844ed6a928ef9396fac26d1de374e71dcaf80df14f05841670ed41619c5a718f \
  version -o json > "$artifacts/syft-version.json"
docker run --rm \
  -v "$artifacts/trivy-cache:/root/.cache/" \
  aquasec/trivy:0.63.0@sha256:6fb0646988fcd2fdf7bf123f7174945ebc2c9c72d1fa1567c8d7daeeb70f8037 \
  --version --format json > "$artifacts/trivy-version.json"

set +e
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$artifacts/trivy-cache:/root/.cache/" \
  aquasec/trivy:0.63.0@sha256:6fb0646988fcd2fdf7bf123f7174945ebc2c9c72d1fa1567c8d7daeeb70f8037 \
  image --format json --scanners vuln,secret \
  --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed=false --timeout 30m --skip-version-check \
  "$image" > "$artifacts/trivy.json"
trivy_status=$?
set -e
[[ "$trivy_status" -eq 0 ]] || { echo "[candidate.scan] trivy execution failed" >&2; exit "$trivy_status"; }
trivy_db_metadata="$artifacts/trivy-cache/trivy/db/metadata.json"
[[ -f "$trivy_db_metadata" ]] || {
  echo "[candidate.scan] Trivy vulnerability DB metadata missing" >&2
  exit 2
}
cp "$trivy_db_metadata" "$artifacts/trivy-db-metadata.json"

python3 scripts/release/candidate_scan_contract.py \
  --trivy-report "$artifacts/trivy.json" \
  --trivy-version "$artifacts/trivy-version.json" \
  --trivy-db-metadata "$artifacts/trivy-db-metadata.json" \
  --syft-version "$artifacts/syft-version.json" \
  --image-manifest "$manifest" \
  --expected-source-sha "$source_sha" \
  --expected-image-digest "$image_digest" \
  --output "$artifacts/security-summary.json"

python3 scripts/release/product_release_manifest.py \
  --image-manifest "$manifest" \
  --sbom "$artifacts/sbom.cyclonedx.json" \
  --scan-summary "$artifacts/security-summary.json" \
  --archive "$artifacts/candidate-image.tar" \
  --archive-reload-digest-file "$artifacts/reloaded-image-id.txt" \
  --expected-source-sha "$source_sha" \
  --output "$artifacts/product-release-manifest.json"
