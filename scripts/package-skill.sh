#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_name="candidate-screening"
output_dir="$repo_root/dist"
skill_archive_path="$output_dir/$skill_name-skill.zip"
plugin_archive_path="$output_dir/$skill_name-plugin.zip"

mkdir -p "$output_dir"
rm -f "$skill_archive_path" "$plugin_archive_path"

cd "$repo_root"
zip -qr "$skill_archive_path" "$skill_name" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*/tests/*" \
  -x "*/evals/*"

cd "$repo_root/plugins/$skill_name"
zip -qr "$plugin_archive_path" . \
  -x "*/__pycache__/*" \
  -x "*.pyc"

printf 'Created %s\n' "$skill_archive_path"
printf 'Created %s\n' "$plugin_archive_path"
