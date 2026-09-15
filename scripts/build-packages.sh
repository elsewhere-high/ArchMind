#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dist_dir="$project_dir/packages/dist"
mkdir -p "$dist_dir"
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/archmind-packages.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM

sync_skill() {
  worker=$1
  skill=$2
  target="$project_dir/packages/$worker/skills/$skill"
  mkdir -p "$target"
  cp "$project_dir/skills/$skill/SKILL.md" "$target/SKILL.md"
}

sync_skill review-coordinator extract-review-context
sync_skill review-coordinator cross-discipline-conflict-check
sync_skill review-coordinator review-summary
sync_skill hardscape-reviewer extract-review-context
sync_skill hardscape-reviewer professional-issue-format
sync_skill planting-reviewer extract-review-context
sync_skill planting-reviewer professional-issue-format
sync_skill stormwater-sponge-reviewer extract-review-context
sync_skill stormwater-sponge-reviewer professional-issue-format
sync_skill evidence-verifier evidence-verification

for worker in review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  archive="$dist_dir/$worker.zip"
  stage="$build_dir/$worker"
  mkdir -p "$stage/docs"
  cp "$project_dir/packages/$worker/manifest.json" "$project_dir/packages/$worker/project.json" "$stage/"
  cp -R "$project_dir/packages/$worker/skills" "$stage/"
  cp "$project_dir/docs/issue-schema.json" "$stage/docs/"
  cp "$project_dir/LICENSE" "$project_dir/THIRD_PARTY_NOTICES.md" "$stage/"
  (cd "$stage" && zip -q -r "$build_dir/$worker.zip" manifest.json project.json skills docs LICENSE THIRD_PARTY_NOTICES.md)
  mv "$build_dir/$worker.zip" "$archive"
  unzip -tq "$archive" >/dev/null
done

if command -v shasum >/dev/null 2>&1; then
  (cd "$dist_dir" && shasum -a 256 ./*.zip > SHA256SUMS)
elif command -v sha256sum >/dev/null 2>&1; then
  (cd "$dist_dir" && sha256sum ./*.zip > SHA256SUMS)
else
  echo "FAIL shasum or sha256sum is required" >&2
  exit 1
fi

echo "BUILD_PACKAGES_PASS packages=5 checksums=5"
