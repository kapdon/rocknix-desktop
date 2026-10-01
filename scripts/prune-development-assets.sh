#!/bin/bash
# Retain the rolling pointer and its current bundle/checksum, never versioned assets.
set -Eeuo pipefail
repo=kapdon/rocknix-desktop
asset=${1:?provide the published current bundle filename}
[[ "$asset" =~ ^rocknix-desktop-rp6-arm64-[0-9a-f]{40}(-r[0-9]+a[0-9]+)?\.tar\.xz$ ]] || exit 1
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
gh release download development --repo "$repo" --pattern latest.json --dir "$scratch"
jq -e --arg asset "$asset" \
  '.asset == $asset and (.commit | test("^[0-9a-f]{40}$")) and (.sha256 | test("^[0-9a-f]{64}$"))' \
  "$scratch/latest.json" >/dev/null
gh api "repos/$repo/releases/tags/development" --jq '.assets' >"$scratch/assets.json"
# Validate the full inventory before deleting anything. Partial upload or an
# unexpected asset must not remove the last usable build.
jq -e --arg asset "$asset" --arg checksum "$asset.sha256" '
  ([.[] | select(.name == $asset or .name == $checksum or .name == "latest.json")
      | select(.state == "uploaded")] | length) == 3 and
  all(.[]; (.id | type) == "number" and .id > 0 and
    (.name == "latest.json" or (.name | test("^rocknix-(desktop|sway)-rp6-arm64-[0-9a-f]{40}(-r[0-9]+a[0-9]+)?\\.tar\\.xz(\\.sha256)?$"))))
' "$scratch/assets.json" >/dev/null
while IFS=$'\t' read -r id name; do
  printf 'Removing superseded dev asset: %s\n' "$name"
  gh api "repos/$repo/releases/assets/$id" --method DELETE
done < <(jq -r --arg asset "$asset" --arg checksum "$asset.sha256" \
  '.[] | select(.name != $asset and .name != $checksum and .name != "latest.json") | [.id,.name] | @tsv' \
  "$scratch/assets.json")
