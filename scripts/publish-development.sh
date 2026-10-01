#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo=kapdon/rocknix-desktop
revision=$(git rev-parse HEAD)
run_id=${GITHUB_RUN_ID:-$(date -u +%s)}
attempt=${GITHUB_RUN_ATTEMPT:-1}
[[ "$run_id" =~ ^[0-9]+$ && "$attempt" =~ ^[0-9]+$ ]] || { echo 'Invalid build identity' >&2; exit 1; }
build_id="r${run_id}a${attempt}"
asset="rocknix-desktop-rp6-arm64-$revision-$build_id.tar.xz"
bundle=dist/rocknix-desktop-rp6-arm64.tar.xz
[ -z "$(git status --porcelain)" ] || { echo 'Source tree is dirty' >&2; exit 1; }
tar -xOf "$bundle" ./build-info | grep -Fx "commit=$revision"
built_at=$(tar -xOf "$bundle" ./build-info | sed -n 's/^built=//p')
[[ "$built_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || exit 1
cp "$bundle" "dist/$asset"
checksum=$(sha256sum "dist/$asset")
checksum=${checksum%% *}
printf '%s  %s\n' "$checksum" "$asset" >"dist/$asset.sha256"

# Create the rolling release only when absent; other API failures remain fatal.
if ! gh release list --repo "$repo" --limit 100 --json tagName \
    --jq '.[].tagName' | grep -Fxq development; then
  gh release create development --repo "$repo" --target "$revision" \
    --prerelease --title 'Rolling development build' \
    --notes 'Unstable dev builds. latest.json identifies the latest successful build. Not an open-alpha release.'
fi
# Distinct names let a replacement finish uploading before retiring the old build.
# Update the rolling pointer only after its assets have finished uploading.
gh release upload development "dist/$asset" "dist/$asset.sha256" --repo "$repo"
released_at=$(gh api "repos/$repo/releases/tags/development" \
  --jq ".assets[] | select(.name == \"$asset\") | .updated_at")
test -n "$released_at"
jq -n --arg commit "$revision" --arg asset "$asset" --arg sha256 "$checksum" \
  --arg released_at "$released_at" --arg build_id "$build_id" --arg built_at "$built_at" \
  '{commit:$commit,asset:$asset,sha256:$sha256,released_at:$released_at,build_id:$build_id,built_at:$built_at}' >dist/latest.json
gh release upload development dist/latest.json --clobber --repo "$repo"
bash scripts/prune-development-assets.sh "$asset"
# Refresh only the rolling tag after its complete bundle is available. An
# annotated tag records this successful publication date for release ordering.
tag_object=$(gh api "repos/$repo/git/tags" --method POST \
  -f tag=development -f object="$revision" -f type=commit \
  -f message="Rolling development build $build_id ($revision)" --jq '.sha')
[[ "$tag_object" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid rolling tag object' >&2; exit 1; }
gh api "repos/$repo/git/refs/tags/development" --method PATCH \
  -f sha="$tag_object" -F force=true >/dev/null
gh release edit development --repo "$repo" --prerelease --latest=false --notes \
  "$(printf 'Commit: `%s`\nBuilt: %s\n\nRolling dev pre-release. Only the latest successful build is kept.' "$revision" "$built_at")"
