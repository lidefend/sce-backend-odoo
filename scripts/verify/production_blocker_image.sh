#!/usr/bin/env bash
set -euo pipefail

# Verifies the split production-blocker carriers:
#   * ODOO_IMAGE_REF     -> backend-only image built from ./Dockerfile
#   * FRONTEND_IMAGE_REF -> static nginx image built from
#     Dockerfile.production-frontend using the dist exported from
#     Dockerfile.production-frontend-builder.
# The two assertion groups are deliberately separate: the Odoo image must
# prove the absence of frontend/nginx, the frontend image must prove their
# presence plus the exact build fingerprint.

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

image="${BLOCKER_RUNTIME_IMAGE:-sce-blocker-runtime:test}"
image_a="${image%:*}:repro-a"
image_b="${image%:*}:repro-b"
frontend_image="${BLOCKER_FRONTEND_IMAGE:-sce-blocker-frontend:test}"
expected_image_digest="${EXPECTED_IMAGE_DIGEST:-}"
expected_frontend_digest="${EXPECTED_FRONTEND_IMAGE_DIGEST:-}"
artifacts="${BLOCKER_IMAGE_ARTIFACTS:-artifacts/production-blocker/image}"
frontend_dist="$artifacts/frontend-dist"
frontend_context="$artifacts/frontend-context"
trivy_cache="$artifacts/trivy-cache"
source_sha="$(git rev-parse HEAD)"
build_time="$(git log -1 --format=%cI)"
mkdir -p "$artifacts" "$trivy_cache"

# Frontend static artifact, exported from the dedicated builder stage. The
# fingerprint algorithm is the unified contract shared with CI:
#   find -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
rm -rf "$frontend_dist"
mkdir -p "$frontend_dist"
DOCKER_BUILDKIT=1 docker build \
  --file Dockerfile.production-frontend-builder \
  --target frontend-dist \
  --output "type=local,dest=$frontend_dist" \
  --build-arg VITE_ODOO_DB=sc_prod \
  .
test -s "$frontend_dist/index.html"
frontend_sha="$(cd "$frontend_dist" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
printf '%s\n' "$frontend_sha" > "$artifacts/frontend-build.sha256"

build_image() {
  local tag="$1"
  docker build --pull --no-cache \
    --build-arg "SOURCE_SHA=$source_sha" \
    -t "$tag" .
}

build_image "$image_a"
build_image "$image_b"
docker tag "$image_b" "$image"

# Frontend image from an isolated context whose dist-production-candidate is
# exactly the exported artifact the production Dockerfile copies.
rm -rf "$frontend_context"
mkdir -p "$frontend_context/frontend/apps/web/dist-production-candidate" \
  "$frontend_context/config/nginx/conf.d" \
  "$frontend_context/scripts"
cp Dockerfile.production-frontend "$frontend_context/Dockerfile.production-frontend"
cp config/nginx/conf.d/production-candidate.conf "$frontend_context/config/nginx/conf.d/"
cp scripts/render_nginx_conf.sh "$frontend_context/scripts/"
cp -a "$frontend_dist/." "$frontend_context/frontend/apps/web/dist-production-candidate/"
docker build --pull \
  --file "$frontend_context/Dockerfile.production-frontend" \
  --build-arg "FRONTEND_BUILD_SHA256=$frontend_sha" \
  --build-arg "SOURCE_SHA=$source_sha" \
  --build-arg "BUILD_TIME=$build_time" \
  --build-arg PRODUCT_VERSION=production-blocker-candidate \
  --build-arg NODE_VERSION=22.17.0-build-only \
  --build-arg PNPM_VERSION=9.12.3-build-only \
  -t "$frontend_image" "$frontend_context"

assert_expected_digest() {
  local tag="$1"
  local expected="$2"
  local expected_hex
  local actual_id
  [[ -n "$expected" ]] || return 0
  expected_hex="${expected#*@}"
  expected_hex="${expected_hex#sha256:}"
  actual_id="$(docker image inspect "$tag" --format '{{.Id}}')"
  actual_id="${actual_id#sha256:}"
  [[ "$actual_id" == "$expected_hex" ]] && return 0
  # Pulled images carry a registry repo digest instead of the config ID.
  if docker image inspect "$tag" --format '{{range .RepoDigests}}{{println .}}{{end}}' \
    | grep -q "@sha256:${expected_hex}$"; then
    return 0
  fi
  echo "[production-blocker-image] digest mismatch for $tag: expected $expected actual id $actual_id" >&2
  return 1
}

assert_expected_digest "$image" "$expected_image_digest"
assert_expected_digest "$frontend_image" "$expected_frontend_digest"

for suffix in a b; do
  tag_var="image_$suffix"
  tag="${!tag_var}"
  docker image inspect "$tag" > "$artifacts/image-$suffix-inspect.json"
  docker run --rm --entrypoint sh "$tag" -c \
    "dpkg-query -W -f='\${Package}|\${Version}\n' | sort" > "$artifacts/image-$suffix-apt-packages.txt"
  docker run --rm --entrypoint python3 "$tag" -m pip freeze --all \
    | sort > "$artifacts/image-$suffix-python-packages.txt"
  # Backend boundary: no frontend payload, no nginx, no Node toolchain.
  docker run --rm --entrypoint sh "$tag" -eu -c '
    test ! -e /opt/sce/frontend
    test ! -e /usr/share/nginx/html/index.html
    ! command -v nginx
    ! command -v node
    ! command -v npm
    ! command -v lessc
    ! command -v rtlcss
    ! dpkg-query -W "node-*" "libnode*" 2>/dev/null
  '
  docker image inspect "$tag" --format '{{json .Config.Labels}}' \
    | jq -e '((. // {}) | has("io.sce.frontend.sha256")) | not' >/dev/null
  label_source_sha="$(docker image inspect "$tag" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')"
  [[ "$label_source_sha" == "$source_sha" ]]
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    anchore/syft:v1.27.1 "$tag" -o json > "$artifacts/image-$suffix-sbom.json"
  jq -S '[.artifacts[] | {name, version, type, purl}] | sort_by(.type, .name, .version, .purl)' \
    "$artifacts/image-$suffix-sbom.json" > "$artifacts/image-$suffix-sbom-core.json"
done

# Frontend boundary: static payload, fingerprint file and nginx present.
docker run --rm --entrypoint sh "$frontend_image" -eu -c '
  test -s /usr/share/nginx/html/index.html
  test -s /usr/share/nginx/html/.build-sha256
  command -v nginx
  ! command -v node
  ! command -v npm
'
internal_frontend_sha="$(docker run --rm --entrypoint sh "$frontend_image" -c 'cat /usr/share/nginx/html/.build-sha256')"
label_frontend_sha="$(docker image inspect "$frontend_image" --format '{{index .Config.Labels "io.sce.frontend.sha256"}}')"
if [[ "$internal_frontend_sha" != "$frontend_sha" ]]; then
  echo "[production-blocker-image] frontend .build-sha256 mismatch: image=$internal_frontend_sha expected=$frontend_sha" >&2
  exit 1
fi
if [[ "$label_frontend_sha" != "$frontend_sha" ]]; then
  echo "[production-blocker-image] io.sce.frontend.sha256 must equal FRONTEND_BUILD_SHA256; got '${label_frontend_sha}'" >&2
  echo "[production-blocker-image] frontend image labels: $(docker image inspect "$frontend_image" --format '{{json .Config.Labels}}')" >&2
  exit 1
fi
docker image inspect "$frontend_image" > "$artifacts/frontend-image-inspect.json"

cmp "$artifacts/image-a-apt-packages.txt" "$artifacts/image-b-apt-packages.txt"
cmp "$artifacts/image-a-python-packages.txt" "$artifacts/image-b-python-packages.txt"
cmp "$artifacts/image-a-sbom-core.json" "$artifacts/image-b-sbom-core.json"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(realpath "$trivy_cache"):/root/.cache" aquasec/trivy:0.63.0 image \
  --format json --scanners vuln,secret --severity HIGH,CRITICAL \
  --ignore-unfixed=false --timeout 30m --skip-version-check "$image" \
  > "$artifacts/trivy.json"

jq -e '
  ([.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length) == 0 and
  ([.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length) == 0 and
  ([.Results[]?.Secrets[]?] | length) == 0
' "$artifacts/trivy.json" >/dev/null

before_save_id="$(docker image inspect "$image_a" --format '{{.Id}}')"
docker save "$image_a" -o "$artifacts/image-reload.tar"
docker image rm "$image_a" >/dev/null
docker load -i "$artifacts/image-reload.tar" > "$artifacts/image-reload.log"
after_load_id="$(docker image inspect "$image_a" --format '{{.Id}}')"
[[ "$before_save_id" == "$after_load_id" ]]

SOURCE_SHA="$source_sha" FRONTEND_SHA="$frontend_sha" IMAGE="$image" \
IMAGE_A="$image_a" IMAGE_B="$image_b" FRONTEND_IMAGE="$frontend_image" \
EXPECTED_IMAGE_DIGEST="$expected_image_digest" \
EXPECTED_FRONTEND_IMAGE_DIGEST="$expected_frontend_digest" \
BEFORE_SAVE_ID="$before_save_id" AFTER_LOAD_ID="$after_load_id" \
ARTIFACTS="$artifacts" python3 - <<'PY'
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

artifacts = Path(os.environ["ARTIFACTS"])

def command(*args):
    return subprocess.check_output(args, text=True).strip()

def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

scan = json.loads((artifacts / "trivy.json").read_text())
payload = {
    "schema_version": 2,
    "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_sha": os.environ["SOURCE_SHA"],
    "frontend_build_sha256": os.environ["FRONTEND_SHA"],
    "expected_digests": {
        "backend_image": os.environ["EXPECTED_IMAGE_DIGEST"] or None,
        "frontend_image": os.environ["EXPECTED_FRONTEND_IMAGE_DIGEST"] or None,
    },
    "base_images": {
        "odoo": "odoo:17.0@sha256:f88f646a0f5fc0b225995ee28953d9ce7367cc731b1756765114691fb97d18e5",
        "node_builder": "node:22.17.0-bookworm-slim@sha256:b04ce4ae4e95b522112c2e5c52f781471a5cbc3b594527bcddedee9bc48c03a0",
    },
    "images": {
        "backend": {
            "candidate": command("docker", "image", "inspect", os.environ["IMAGE"], "--format", "{{.Id}}"),
            "repro_a": command("docker", "image", "inspect", os.environ["IMAGE_A"], "--format", "{{.Id}}"),
            "repro_b": command("docker", "image", "inspect", os.environ["IMAGE_B"], "--format", "{{.Id}}"),
        },
        "frontend": {
            "candidate": command("docker", "image", "inspect", os.environ["FRONTEND_IMAGE"], "--format", "{{.Id}}"),
        },
    },
    "reproducibility": {
        "binary_image_id_equal": command("docker", "image", "inspect", os.environ["IMAGE_A"], "--format", "{{.Id}}") == command("docker", "image", "inspect", os.environ["IMAGE_B"], "--format", "{{.Id}}"),
        "apt_manifest_equal": True,
        "python_manifest_equal": True,
        "sbom_core_equal": True,
    },
    "save_remove_load": {
        "before_image_id": os.environ["BEFORE_SAVE_ID"],
        "after_image_id": os.environ["AFTER_LOAD_ID"],
        "identity_preserved": os.environ["BEFORE_SAVE_ID"] == os.environ["AFTER_LOAD_ID"],
    },
    "backend_runtime": {
        "frontend_dir_present": False,
        "nginx_present": False,
        "node_present": False,
        "frontend_sha256_label_present": False,
        "rtl_policy": "unsupported_ltr_only",
    },
    "frontend_runtime": {
        "index_html_present": True,
        "build_sha256_present": True,
        "nginx_present": True,
        "node_present": False,
        "label_key": "io.sce.frontend.sha256",
        "label_sha256": os.environ["FRONTEND_SHA"],
    },
    "scan": {
        "critical": sum(1 for r in scan.get("Results", []) for v in r.get("Vulnerabilities") or [] if v.get("Severity") == "CRITICAL"),
        "high": sum(1 for r in scan.get("Results", []) for v in r.get("Vulnerabilities") or [] if v.get("Severity") == "HIGH"),
        "secret": sum(1 for r in scan.get("Results", []) for _ in r.get("Secrets") or []),
    },
    "evidence_sha256": {
        "sbom": file_sha(artifacts / "image-b-sbom.json"),
        "trivy": file_sha(artifacts / "trivy.json"),
        "apt_manifest": file_sha(artifacts / "image-b-apt-packages.txt"),
        "python_manifest": file_sha(artifacts / "image-b-python-packages.txt"),
    },
}
(artifacts / "image-summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print("[production-blocker-image] " + json.dumps(payload, sort_keys=True))
if not all([
    payload["save_remove_load"]["identity_preserved"],
    payload["reproducibility"]["apt_manifest_equal"],
    payload["reproducibility"]["python_manifest_equal"],
    payload["reproducibility"]["sbom_core_equal"],
    payload["scan"] == {"critical": 0, "high": 0, "secret": 0},
    payload["frontend_runtime"]["index_html_present"],
    payload["frontend_runtime"]["nginx_present"],
]):
    raise SystemExit(1)
PY
