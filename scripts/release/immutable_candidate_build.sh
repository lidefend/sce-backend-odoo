#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

source_sha="${SOURCE_SHA:?SOURCE_SHA is required}"
source_ref="${CANDIDATE_SOURCE_REF:-origin/main}"
if [[ "$source_ref" == "HEAD" ]]; then
  [[ "${ALLOW_BOUNDARY_BRANCH_BUILD:-0}" == "1" ]] || {
    echo "[candidate.build] branch build requires explicit boundary authorization" >&2
    exit 2
  }
  [[ "$(git branch --show-current)" =~ ^release/tenant-rc-[a-z0-9._-]+$ ]] || {
    echo "[candidate.build] branch build is restricted to a tenant RC release branch" >&2
    exit 2
  }
  [[ -z "$(git status --short)" ]] || {
    echo "[candidate.build] branch build requires a clean worktree" >&2
    exit 2
  }
fi
python3 scripts/release/release_source_identity.py source-preflight \
  --root "$root" \
  --source-sha "$source_sha"
if [[ "$(git rev-parse "$source_ref")" != "$source_sha" ]]; then
  echo "[candidate.build] $source_ref no longer matches locked source SHA" >&2
  exit 2
fi
# Browser acceptance scripts are release evidence tooling and are not consumed by
# the Vite production build. Every actual frontend workspace/build input remains
# locked to the candidate source SHA.
locked_product_paths=(
  VERSION
  release
  addons
  addons_external
  frontend
  ':(exclude)frontend/apps/web/scripts'
  requirements-odoo.txt
  config/odoo.conf.template
  scripts/odoo-entrypoint.sh
  scripts/render_odoo_conf.py
  scripts/release
  Dockerfile.production-candidate
  Dockerfile.production-frontend-builder
  config/product_addons_allowlist.txt
  config/product_optional_addons_allowlist.txt
)
if git diff --quiet "$source_sha" -- "${locked_product_paths[@]}"; then
  :
else
  echo "[candidate.build] product/runtime files differ from locked source SHA" >&2
  git diff --name-only "$source_sha" -- "${locked_product_paths[@]}" >&2
  exit 2
fi

artifacts="${CANDIDATE_ARTIFACTS:-artifacts/release/immutable-production-candidate-v1}"
dist="frontend/apps/web/dist-production-candidate"
short_sha="${source_sha:0:12}"
product_version="$(python3 scripts/release/product_release.py --version)"
image_repository="ghcr.io/lidefend/sce-product"
expected_image="${image_repository}:${product_version}"
image="${CANDIDATE_IMAGE:-$expected_image}"
[[ "$image" == "$expected_image" ]] || {
  echo "[candidate.build] CANDIDATE_IMAGE must be $expected_image" >&2
  exit 2
}
sha_image="${image_repository}:sha-${short_sha}"
frontend_builder="sce-production-frontend-builder:${short_sha}"
build_time="${CANDIDATE_BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
source_tree_sha="$(git rev-parse "${source_sha}^{tree}")"
node_version="v22.17.0-build-only"
pnpm_version="9.12.3-build-only"
runtime_base="odoo:17.0@sha256:f88f646a0f5fc0b225995ee28953d9ce7367cc731b1756765114691fb97d18e5"
frontend_base="$(awk '$1 == "FROM" {print $2; exit}' Dockerfile.production-frontend-builder)"
[[ "$frontend_base" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "[candidate.build] frontend builder base must be digest pinned" >&2
  exit 2
}
frontend_base_digest="${frontend_base##*@}"
runtime_base_digest="${runtime_base##*@}"
baseline_checksum="$(awk 'NF {print $1; exit}' scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256)"
[[ "$baseline_checksum" =~ ^[0-9a-f]{64}$ ]] || {
  echo "[candidate.build] formal baseline checksum is invalid" >&2
  exit 2
}
python_version="$(docker run --rm --entrypoint python3 "$runtime_base" --version | awk '{print $2}')"
module_matrix="$(python3 scripts/release/product_module_matrix.py --json)"

mkdir -p "$artifacts"
rm -rf "$dist"
docker build \
  --file Dockerfile.production-frontend-builder \
  --tag "$frontend_builder" \
  --build-arg "VITE_ODOO_DB=sc_user_data_rehearsal_candidate" \
  .
builder_container="$(docker create "$frontend_builder")"
trap 'docker rm -f "$builder_container" >/dev/null 2>&1 || true' EXIT
mkdir -p "$dist"
docker cp "$builder_container:/build/frontend/apps/web/dist/." "$dist/"
docker rm "$builder_container" >/dev/null
trap - EXIT

frontend_hash="$(find "$dist" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
printf '%s\n' "$frontend_hash" > "$artifacts/frontend-build.sha256"

docker build \
  --file Dockerfile.production-candidate \
  --tag "$image" \
  --tag "$sha_image" \
  --build-arg "SOURCE_SHA=$source_sha" \
  --build-arg "PRODUCT_VERSION=$product_version" \
  --build-arg "FRONTEND_BUILD_SHA256=$frontend_hash" \
  --build-arg "BUILD_TIME=$build_time" \
  --build-arg "PYTHON_VERSION=$python_version" \
  --build-arg "NODE_VERSION=$node_version" \
  --build-arg "PNPM_VERSION=$pnpm_version" \
  .

image_id="$(docker image inspect "$image" --format '{{.Id}}')"
[[ "$(docker image inspect "$sha_image" --format '{{.Id}}')" == "$image_id" ]] || {
  echo "[candidate.build] human and source tags do not identify the same image" >&2
  exit 1
}
for label_check in \
  "org.opencontainers.image.title=sce-product" \
  "org.opencontainers.image.version=$product_version" \
  "org.opencontainers.image.revision=$source_sha" \
  "org.opencontainers.image.created=$build_time"; do
  label_name="${label_check%%=*}"
  expected_label="${label_check#*=}"
  actual_label="$(docker image inspect "$image" --format "{{index .Config.Labels \"$label_name\"}}")"
  [[ "$actual_label" == "$expected_label" ]] || {
    echo "[candidate.build] image label mismatch: $label_name" >&2
    exit 1
  }
done
odoo_version="$(docker run --rm --entrypoint odoo "$image" --version | head -1)"
image_python="$(docker run --rm --entrypoint python3 "$image" --version | awk '{print $2}')"
if docker run --rm --entrypoint sh "$image" -c \
  "command -v node || command -v lessc || command -v rtlcss || \
   dpkg-query -W -f='\${binary:Package}\t\${db:Status-Status}\n' 'node-*' 'libnode*' 2>/dev/null \
     | awk '\$2 == \"installed\" { found=1 } END { exit(found ? 0 : 1) }'"; then
  echo "[candidate.build] Node runtime package or executable remains" >&2
  exit 1
fi
archive="$artifacts/candidate-image.tar"
docker save --output "$archive" "$image" "$sha_image"
archive_sha="$(sha256sum "$archive" | awk '{print $1}')"
archive_config_digest="$(python3 - "$archive" <<'PY'
import json
import sys
import tarfile

with tarfile.open(sys.argv[1]) as archive:
    rows = json.load(archive.extractfile("manifest.json"))
if not isinstance(rows, list) or len(rows) != 1:
    raise SystemExit("candidate archive must contain exactly one image")
config = str(rows[0].get("Config") or "")
prefix = "blobs/sha256/"
if not config.startswith(prefix) or len(config) != len(prefix) + 64:
    raise SystemExit("candidate archive config digest is invalid")
print("sha256:" + config.removeprefix(prefix))
PY
)"

IMAGE="$image" SHA_IMAGE="$sha_image" IMAGE_ID="$image_id" SOURCE_SHA="$source_sha" \
SOURCE_TREE_SHA="$source_tree_sha" PRODUCT_VERSION="$product_version" FRONTEND_HASH="$frontend_hash" \
BUILD_TIME="$build_time" ODOO_VERSION="$odoo_version" PYTHON_VERSION="$image_python" \
NODE_VERSION="$node_version" PNPM_VERSION="$pnpm_version" ARCHIVE_SHA="$archive_sha" \
ARCHIVE_CONFIG_DIGEST="$archive_config_digest" IMAGE_REPOSITORY="$image_repository" \
FRONTEND_BASE_DIGEST="$frontend_base_digest" RUNTIME_BASE_DIGEST="$runtime_base_digest" \
BASELINE_CHECKSUM="$baseline_checksum" \
MODULE_MATRIX_JSON="$module_matrix" \
python3 - <<'PY'
import json, os
from pathlib import Path

out = Path(os.environ.get("CANDIDATE_ARTIFACTS", "artifacts/release/immutable-production-candidate-v1"))
payload = {
    "schema_version": 2,
    "source_sha": os.environ["SOURCE_SHA"],
    "oci_revision": os.environ["SOURCE_SHA"],
    "container_source_revision": os.environ["SOURCE_SHA"],
    "source_tree_sha": os.environ["SOURCE_TREE_SHA"],
    "product_version": os.environ["PRODUCT_VERSION"],
    "image": os.environ["IMAGE"],
    "image_tags": [os.environ["IMAGE"], os.environ["SHA_IMAGE"]],
    "registry_repository": os.environ["IMAGE_REPOSITORY"],
    "local_image_id": os.environ["IMAGE_ID"],
    "image_digest": None,
    "publish_status": "not_published",
    "base_image_digests": {
        "frontend_builder": os.environ["FRONTEND_BASE_DIGEST"],
        "odoo_runtime": os.environ["RUNTIME_BASE_DIGEST"],
    },
    "baseline_checksum": os.environ["BASELINE_CHECKSUM"],
    "frontend_build_sha256": os.environ["FRONTEND_HASH"],
    "build_time": os.environ["BUILD_TIME"],
    "versions": {
        "odoo": os.environ["ODOO_VERSION"],
        "python": os.environ["PYTHON_VERSION"],
        "node": os.environ["NODE_VERSION"],
        "pnpm": os.environ["PNPM_VERSION"],
    },
    "module_version_matrix": json.loads(os.environ["MODULE_MATRIX_JSON"]),
    "archive": "candidate-image.tar",
    "archive_sha256": os.environ["ARCHIVE_SHA"],
    "archive_config_digest": os.environ["ARCHIVE_CONFIG_DIGEST"],
    "contains": ["odoo_backend", "production_frontend_static", "formal_addons", "python_dependencies", "startup_configuration", "nginx"],
    "host_source_mounts": 0,
}
(out / "image-manifest.json").write_text(json.dumps(payload, indent=2) + "\n")
PY

docker image rm "$image" "$sha_image" >/dev/null
docker load --input "$archive" >/dev/null
reloaded_id="$(docker image inspect "$image" --format '{{.Id}}')"
reloaded_sha_id="$(docker image inspect "$sha_image" --format '{{.Id}}')"
if [[ "$reloaded_id" != "$image_id" || "$reloaded_sha_id" != "$image_id" ]]; then
  echo "[candidate.build] immutable reload image ID mismatch" >&2
  exit 1
fi
printf '%s\n' "$reloaded_id" > "$artifacts/reloaded-image-id.txt"
echo "[candidate.build] PASS image=$image source_tag=$sha_image local_image_id=$image_id archive_config=$archive_config_digest frontend=$frontend_hash"
