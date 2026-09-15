#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
expected_skills="extract-review-context professional-issue-format cross-discipline-conflict-check evidence-verification review-summary"

count=$(find "$project_dir/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
test "$count" = "5"
for skill in $expected_skills; do
  file="$project_dir/skills/$skill/SKILL.md"
  test -f "$file"
  for heading in Purpose Inputs Outputs "Invocation conditions" Dependencies "Failure handling" Validation "Security boundary" "Reuse value" Version; do
    grep -q "## $heading" "$file"
  done
done

python3 -m json.tool "$project_dir/docs/issue-schema.json" >/dev/null
python3 -m json.tool "$project_dir/samples/case-001/drawing-facts.json" >/dev/null

manifest="$project_dir/deploy/archmind-minimal.template.yaml"
test -f "$manifest"
test "$(grep -c '^kind: Worker$' "$manifest")" = "5"
test "$(grep -c '^kind: Team$' "$manifest")" = "1"
test "$(grep -c '^kind: Human$' "$manifest")" = "1"
test "$(grep -c '^kind: Manager$' "$manifest")" = "1"
test "$(grep -c 'package: PACKAGE_URI_' "$manifest")" = "5"
grep -q '"process"' "$project_dir/schemas/drawing-facts-v0.1.schema.json"

for runtime_script in bootstrap-runtime.sh runtime-preflight.sh runtime-healthcheck.sh runtime-down.sh runtime-lib.sh; do
  test -f "$project_dir/scripts/$runtime_script"
  sh -n "$project_dir/scripts/$runtime_script"
done
for python_script in render-deploy.py runtime-resource-check.py; do
  test -f "$project_dir/scripts/$python_script"
  python3 -c 'import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))' \
    "$project_dir/scripts/$python_script"
done

test -f "$project_dir/Makefile"
for make_target in verify runtime-preflight runtime-up runtime-health runtime-down; do
  grep -q "^$make_target:" "$project_dir/Makefile"
done

worker_last=$(grep -n '^kind: Worker$' "$manifest" | tail -1 | cut -d: -f1)
team_line=$(grep -n '^kind: Team$' "$manifest" | cut -d: -f1)
human_line=$(grep -n '^kind: Human$' "$manifest" | cut -d: -f1)
test "$worker_last" -lt "$team_line"
test "$team_line" -lt "$human_line"

echo "STATIC_VALIDATION_PASS"
