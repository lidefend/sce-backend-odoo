#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
artifacts="${CANDIDATE_ARTIFACTS:-artifacts/release/immutable-production-candidate-v1}"
source_sha="${SOURCE_SHA:?SOURCE_SHA is required}"
manifest="$artifacts/image-manifest.json"
[[ -f "$manifest" ]] || { echo "[candidate.publish] image manifest missing" >&2; exit 2; }

readarray -t identity < <(python3 - "$manifest" "$source_sha" <<'PY'
import json
import re
import sys

path, expected_sha = sys.argv[1:]
payload = json.load(open(path, encoding="utf-8"))
repository = "ghcr.io/lidefend/sce-product"
if payload.get("schema_version") != 2:
    raise SystemExit("candidate image manifest schema must be v2")
if payload.get("source_sha") != expected_sha or not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
    raise SystemExit("candidate source SHA mismatch")
if payload.get("registry_repository") != repository:
    raise SystemExit("candidate registry repository mismatch")
tags = payload.get("image_tags")
if not isinstance(tags, list) or len(tags) != 2:
    raise SystemExit("candidate image tags are incomplete")
if tags[0] != f"{repository}:{payload.get('product_version')}":
    raise SystemExit("candidate version tag mismatch")
if tags[1] != f"{repository}:sha-{expected_sha[:12]}":
    raise SystemExit("candidate source tag mismatch")
if payload.get("publish_status") != "not_published" or payload.get("image_digest") is not None:
    raise SystemExit("candidate manifest was already published or mutated")
print(tags[0])
print(tags[1])
print(payload.get("local_image_id") or "")
PY
)
image="${identity[0]}"
source_tag="${identity[1]}"
local_image_id="${identity[2]}"
[[ "$(docker image inspect "$image" --format '{{.Id}}')" == "$local_image_id" ]]
[[ "$(docker image inspect "$source_tag" --format '{{.Id}}')" == "$local_image_id" ]]

docker push "$image"
docker push "$source_tag"

version_descriptor="$artifacts/registry-version-descriptor.json"
source_descriptor="$artifacts/registry-source-descriptor.json"
docker manifest inspect --verbose "$image" > "$version_descriptor"
docker manifest inspect --verbose "$source_tag" > "$source_descriptor"

python3 - "$manifest" "$version_descriptor" "$source_descriptor" <<'PY'
import datetime
import json
import os
import re
import sys
from pathlib import Path

manifest_path, version_path, source_path = (Path(value) for value in sys.argv[1:])
payload = json.loads(manifest_path.read_text(encoding="utf-8"))

def descriptor_digest(path):
    row = json.loads(path.read_text(encoding="utf-8"))
    descriptor = row.get("Descriptor") if isinstance(row, dict) else None
    digest = str((descriptor or {}).get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SystemExit(f"registry manifest digest unavailable: {path.name}")
    return digest

version_digest = descriptor_digest(version_path)
source_digest = descriptor_digest(source_path)
if version_digest != source_digest:
    raise SystemExit("version and source tags resolved to different registry manifests")
payload["image_digest"] = version_digest
payload["registry_refs"] = [
    f"{payload['registry_repository']}@{version_digest}",
    f"{payload['registry_repository']}@{source_digest}",
]
payload["publish_status"] = "published"
payload["published_at"] = datetime.datetime.now(datetime.timezone.utc).replace(
    microsecond=0
).isoformat().replace("+00:00", "Z")
tmp = manifest_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(tmp, manifest_path)
manifest_path.with_name("registry-manifest-digest.txt").write_text(version_digest + "\n")
print(f"[candidate.publish] PASS digest={version_digest}")
PY
