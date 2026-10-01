#!/bin/bash
# Publish a versioned build from tested main, keeping assets immutable.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo=kapdon/rocknix-desktop
tag=${1:?provide a version such as v0.1.0-alpha.1 or v0.1.0}
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]] || {
  printf 'Invalid release version\n' >&2; exit 1;
}
revision=$(git rev-parse HEAD)
git merge-base --is-ancestor "$revision" origin/main || {
  printf 'Release source must belong to main\n' >&2; exit 1;
}
[ -z "$(git status --porcelain)" ] || { printf 'Source tree is dirty\n' >&2; exit 1; }
existing=$(git ls-remote --tags origin "refs/tags/$tag")
[ -z "$existing" ] || { printf 'Release tag already exists; choose a new version\n' >&2; exit 1; }
bundle=dist/rocknix-desktop-rp6-arm64.tar.xz
tar -xOf "$bundle" ./build-info | grep -Fx "commit=$revision"
asset="rocknix-desktop-rp6-arm64-$revision.tar.xz"
cp "$bundle" "dist/$asset"
checksum=$(sha256sum "dist/$asset")
checksum=${checksum%% *}
printf '%s  %s\n' "$checksum" "$asset" >"dist/$asset.sha256"
flags=()
channel=stable
if [[ "$tag" = *-* ]]; then flags+=(--prerelease); channel=prerelease; fi
gh release create "$tag" "dist/$asset" "dist/$asset.sha256" --repo "$repo" \
  --target "$revision" --draft "${flags[@]}" --title "ROCKNIX Desktop $tag" \
  --notes "Retroid Pocket 6 LXC Desktop. Install this version with the main installer and --release $tag."
# The tag API cannot find an unpublished draft. The release command resolves
# authenticated drafts and exposes the uploaded asset timestamp.
released_at=$(gh release view "$tag" --repo "$repo" --json assets \
  --jq ".assets[] | select(.name == \"$asset\") | .updatedAt")
test -n "$released_at"
jq -n --arg commit "$revision" --arg asset "$asset" --arg sha256 "$checksum" \
  --arg released_at "$released_at" --arg version "$tag" --arg channel "$channel" \
  '{commit:$commit,asset:$asset,sha256:$sha256,released_at:$released_at,version:$version,channel:$channel}' >dist/latest.json
gh release upload "$tag" dist/latest.json --repo "$repo"
# Make the release visible only after all installer assets are present.
if [ "$channel" = stable ]; then
  gh release edit "$tag" --repo "$repo" --draft=false --latest=true
else
  gh release edit "$tag" --repo "$repo" --draft=false --latest=false
fi
