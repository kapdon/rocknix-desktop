#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo=kapdon/rocknix-desktop
revision=$(git rev-parse HEAD)
asset="rocknix-sway-rp6-arm64-$revision.tar.xz"
bundle=dist/rocknix-sway-rp6-arm64.tar.xz
[ -z "$(git status --porcelain)" ] || { echo 'Source tree is dirty' >&2; exit 1; }
tar -xOf "$bundle" ./build-info | grep -Fx "commit=$revision"
cp "$bundle" "dist/$asset"
checksum=$(sha256sum "dist/$asset")
checksum=${checksum%% *}
printf '%s  %s\n' "$checksum" "$asset" >"dist/$asset.sha256"
jq -n --arg commit "$revision" --arg asset "$asset" --arg sha256 "$checksum" \
  '{commit:$commit,asset:$asset,sha256:$sha256}' >dist/latest.json

# Create the rolling release only when absent; other API failures remain fatal.
if ! gh release list --repo "$repo" --limit 100 --json tagName \
    --jq '.[].tagName' | grep -Fxq development; then
  gh release create development --repo "$repo" --target "$revision" \
    --prerelease --title 'Rolling development build' \
    --notes 'Unstable dev builds. latest.json identifies the latest successful build. Not an open-alpha release.'
fi
# Commit-qualified assets are never overwritten. Update the pointer only after upload.
gh release upload development "dist/$asset" "dist/$asset.sha256" --repo "$repo"
gh release upload development dist/latest.json --clobber --repo "$repo"
gh release edit development --repo "$repo" --notes \
  "Latest successful build: $revision. Use the dev installer. Unstable testing channel; existing installations are not upgraded automatically."
