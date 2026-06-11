#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_name="candidate-screening"
output_dir="$repo_root/dist"
archive_path="$output_dir/$skill_name.zip"

mkdir -p "$output_dir"
rm -f "$archive_path"

cd "$repo_root"
zip -qr "$archive_path" "$skill_name" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*/tests/*" \
  -x "*/evals/*"

printf 'Created %s\n' "$archive_path"
